# ValidationError 表示模型 JSON 无法满足 Pydantic Schema。
from pydantic import ValidationError

from app.schemas.intent import IntentClassification
from app.services.llm_client import LLMClient
from app.services.structured_output import parse_structured_output


# 多行字符串是发给模型的 system prompt，strip() 去掉源码缩进带来的首尾空白。
INTENT_SYSTEM_PROMPT = """
你是 Yu AI Agent 的任务路由器，只负责把用户输入分类成固定 JSON。
必须只输出 JSON 对象，不要输出 Markdown、解释文字或代码块。

可选 intent：
- rag_search：用户需要检索知识库、文档、资料、教程或历史内容。
- tool_call：用户明确要求调用具体工具、查询外部系统或执行确定动作。
- mcp_call：用户需要通过 MCP 访问外部服务、资源或工具集合。
- yuagent_handoff：用户请求迁移、调用或委托给 YuAgent 相关能力。
- chat：普通聊天、解释、建议、非执行类问答。
- unknown：无法判断。

输出结构：
{
  "intent": "rag_search | tool_call | mcp_call | yuagent_handoff | chat | unknown",
  "confidence": 0.0,
  "entities": {}
}
""".strip()


class IntentClassificationError(Exception):
    """意图识别结构化输出失败时抛出的业务异常。"""


class IntentService:
    """负责把自然语言消息转换成后续 Agent 编排可消费的结构化意图。"""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        # 允许测试注入伪造客户端，生产环境则构造真实 LLMClient。
        self.llm_client = llm_client or LLMClient()

    async def classify(self, message: str) -> IntentClassification:
        # 最多尝试两次；第二次会使用更严格的提示词修正上次 Schema 校验失败。
        # ValidationError 只在本方法内吸收，最终统一包装为领域异常交给 API 层。
        # 保存最后一次校验错误，用于最终异常链，便于诊断模型输出为什么不合规。
        last_error: ValidationError | None = None

        # range(2) 依次产生 0、1，对应首次请求和一次纠错重试。
        for attempt in range(2):
            # 请求供应商启用 JSON 模式，但仍需本地 Schema 校验才能保证业务正确性。
            raw_content = await self.llm_client.chat_json(self._build_messages(message, attempt))
            try:
                # 成功即提前返回；泛型解析函数会还原为 IntentClassification 实例。
                return parse_structured_output(raw_content, IntentClassification)
            except ValidationError as exc:
                # 首次失败不立即报错，保存原因后通过更严格提示词重试一次。
                last_error = exc

        # 两次都失败才向上层暴露领域异常，而非泄漏 Pydantic 的内部异常类型。
        raise IntentClassificationError("Model structured output parse failed.") from last_error

    def _build_messages(self, message: str, attempt: int) -> list[dict[str, str]]:
        # f-string 将当前用户消息嵌入提示词，类似 Java String.format 的简写。
        user_prompt = f"请分类这条用户消息：{message}"
        # 第二轮追加失败反馈，要求模型严格遵守固定字段和值。
        if attempt > 0:
            user_prompt = (
                "上一次输出没有通过 JSON Schema 校验。"
                "请严格按指定字段和值重新输出 JSON。"
                f"用户消息：{message}"
            )

        return [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
