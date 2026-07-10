from pydantic import ValidationError

from app.schemas.intent import IntentClassification
from app.services.llm_client import LLMClient
from app.services.structured_output import parse_structured_output


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
        self.llm_client = llm_client or LLMClient()

    async def classify(self, message: str) -> IntentClassification:
        last_error: ValidationError | None = None

        for attempt in range(2):
            raw_content = await self.llm_client.chat_json(self._build_messages(message, attempt))
            try:
                return parse_structured_output(raw_content, IntentClassification)
            except ValidationError as exc:
                last_error = exc

        raise IntentClassificationError("Model structured output parse failed.") from last_error

    def _build_messages(self, message: str, attempt: int) -> list[dict[str, str]]:
        user_prompt = f"请分类这条用户消息：{message}"
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
