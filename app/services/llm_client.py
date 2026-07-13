# json 用于把供应商私有请求参数从配置字符串转换为 Python 字典。
import json
# logging 记录模型调用的供应商、模型名和耗时，不记录提示词与密钥。
import logging
# perf_counter 提供适合测量耗时的高精度单调时钟。
import time
# AsyncIterator 描述流式输出，Callable 描述可替换的 SDK 客户端工厂。
from collections.abc import AsyncIterator, Callable
# Protocol 是结构化接口；Any 用于第三方 SDK 未细化的动态对象。
from typing import Any, Protocol

# AsyncOpenAI 使用异步 HTTP；OpenAIError 是 SDK 的统一异常基类。
from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings, get_settings


# 仅按名称获取日志器；实际 Handler 和级别由应用启动阶段配置。
logger = logging.getLogger("yu_ai_agent.llm")


class OpenAICompatibleClientProtocol(Protocol):
    """Minimal SDK shape LLMClient needs.

    For Java developers: think of this as a tiny interface that lets tests pass a
    fake implementation, similar to mocking a `ChatModel` bean.
    """

    # LLMClient 只依赖 chat 属性这一个最小能力，降低对具体 SDK 类型的耦合。
    chat: Any


class LLMClientError(Exception):
    """Project-level exception for model provider failures.

    For Java developers: this is like wrapping vendor SDK exceptions into a
    business exception before the controller maps it to an HTTP response.
    """


class LLMClient:
    """Generic OpenAI-compatible model client.

    For Java developers: this class is the Python equivalent of the part where
    Spring AI `ChatClient` hides the concrete `ChatModel` provider. Controllers
    and services should depend on this wrapper, not on DeepSeek, Bailian, or
    Zhipu SDK details.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[..., OpenAICompatibleClientProtocol] = AsyncOpenAI,
    ) -> None:
        """Build the underlying SDK client from configuration.

        `client_factory` is injectable so tests can use a fake client instead of
        calling a real model provider, similar to constructor injection in Java.
        """
        # 优先使用构造器传入配置，测试可借此避免读取真实 .env。
        self.settings = settings or get_settings()
        # 启动即校验关键配置，避免请求进行到一半才暴露模糊的供应商错误。
        if not self.settings.llm_base_url or not self.settings.llm_api_key:
            raise ValueError("LLM_BASE_URL and LLM_API_KEY must be configured.")

        # 保存日志需要的供应商与模型名，避免每次调用重复访问配置对象。
        self.provider = self.settings.llm_provider
        self.model = self.settings.llm_model
        # 统一按 OpenAI-compatible 协议创建客户端，兼容不同模型供应商。
        self._client = client_factory(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.request_timeout_seconds,
        )

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a non-streaming chat request and return assistant text.

        Java analogy: this corresponds to
        `chatClient.prompt().user(...).call().chatResponse()` followed by reading
        `getResult().getOutput().getText()`.
        """
        # perf_counter 适合测量耗时，不是业务时间，也不应拿来生成时间戳。
        # 在网络调用前取单调时钟起点，计算请求端到端耗时。
        started_at = time.perf_counter()
        try:
            # SDK 调用是协程；** 将公共请求参数字典展开为关键字参数。
            response = await self._client.chat.completions.create(
                **self._completion_kwargs(messages=messages, stream=False)
            )
        except OpenAIError as exc:
            raise LLMClientError("Model provider request failed.") from exc

        # 秒级浮点差值乘 1000 后转整数，形成日志常用毫秒耗时。
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info("llm_chat provider=%s model=%s elapsed_ms=%s", self.provider, self.model, elapsed_ms)

        # choices 为空表示供应商虽响应成功但没有生成候选内容。
        if not response.choices:
            raise LLMClientError("Model provider returned no choices.")

        # 当前策略只消费第一个候选回答，与多数 Chat API 的默认语义一致。
        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("Model provider returned empty content.")
        return content

    async def chat_json(self, messages: list[dict[str, str]]) -> str:
        """请求模型返回 JSON 对象文本，用于后续 Pydantic 结构化校验。"""
        # JSON 模式调用也独立计时，便于区分普通聊天与结构化任务的性能。
        started_at = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                **self._completion_kwargs(
                    messages=messages,
                    stream=False,
                    # 请求供应商输出 JSON 对象；仍由上层 Pydantic 做字段 Schema 校验。
                    response_format={"type": "json_object"},
                )
            )
        except OpenAIError as exc:
            raise LLMClientError("Model provider JSON request failed.") from exc

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info("llm_json provider=%s model=%s elapsed_ms=%s", self.provider, self.model, elapsed_ms)

        if not response.choices:
            raise LLMClientError("Model provider returned no choices.")

        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("Model provider returned empty content.")
        return content

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """Stream assistant text chunks from the model.

        Java analogy: this is the Python async-iterator version of Spring AI's
        `chatClient.prompt().user(...).stream().content()` returning `Flux`.
        """
        # async for 会异步等待网络片段，对应 Java 响应式流中的逐项消费。
        try:
            # stream=True 返回可异步遍历的事件流，而不是一个完整 response。
            stream = await self._client.chat.completions.create(
                **self._completion_kwargs(messages=messages, stream=True)
            )
            async for chunk in stream:
                # 心跳或元数据事件可能没有 choices，应跳过而不是访问下标 0。
                if not chunk.choices:
                    continue
                # delta 只包含“新增片段”，前端需要按顺序拼接而非覆盖全文。
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except OpenAIError as exc:
            raise LLMClientError("Model provider stream request failed.") from exc

    def _completion_kwargs(
        self,
        *,
        messages: list[dict[str, str]],
        stream: bool,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build provider request parameters in one place.

        Java analogy: this method is a lightweight version of assembling
        `ChatOptions`, keeping model-specific knobs out of the service layer.
        """
        # 用字典集中组装可选参数，避免供应商配置泄漏到上层 Service。
        # 先构造所有供应商都支持的最小公共参数集合。
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }

        # 只有结构化任务才传 response_format，普通聊天不附带该供应商参数。
        if response_format:
            kwargs["response_format"] = response_format

        # 空字符串时不传 reasoning_effort，避免不支持该字段的供应商报错。
        if self.settings.llm_reasoning_effort:
            kwargs["reasoning_effort"] = self.settings.llm_reasoning_effort

        # extra_body 是供应商扩展参数入口，配置存在时才将 JSON 文本解析为对象。
        if self.settings.llm_extra_body_json:
            kwargs["extra_body"] = json.loads(self.settings.llm_extra_body_json)

        return kwargs
