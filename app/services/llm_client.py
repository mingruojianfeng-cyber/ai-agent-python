import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings, get_settings


logger = logging.getLogger("yu_ai_agent.llm")


class OpenAICompatibleClientProtocol(Protocol):
    """Minimal SDK shape LLMClient needs.

    For Java developers: think of this as a tiny interface that lets tests pass a
    fake implementation, similar to mocking a `ChatModel` bean.
    """

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
        self.settings = settings or get_settings()
        if not self.settings.llm_base_url or not self.settings.llm_api_key:
            raise ValueError("LLM_BASE_URL and LLM_API_KEY must be configured.")

        self.provider = self.settings.llm_provider
        self.model = self.settings.llm_model
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
        started_at = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                **self._completion_kwargs(messages=messages, stream=False)
            )
        except OpenAIError as exc:
            raise LLMClientError("Model provider request failed.") from exc

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info("llm_chat provider=%s model=%s elapsed_ms=%s", self.provider, self.model, elapsed_ms)

        if not response.choices:
            raise LLMClientError("Model provider returned no choices.")

        content = response.choices[0].message.content
        if not content:
            raise LLMClientError("Model provider returned empty content.")
        return content

    async def chat_json(self, messages: list[dict[str, str]]) -> str:
        """请求模型返回 JSON 对象文本，用于后续 Pydantic 结构化校验。"""
        started_at = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
                **self._completion_kwargs(
                    messages=messages,
                    stream=False,
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
        try:
            stream = await self._client.chat.completions.create(
                **self._completion_kwargs(messages=messages, stream=True)
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
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
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }

        if response_format:
            kwargs["response_format"] = response_format

        if self.settings.llm_reasoning_effort:
            kwargs["reasoning_effort"] = self.settings.llm_reasoning_effort

        if self.settings.llm_extra_body_json:
            kwargs["extra_body"] = json.loads(self.settings.llm_extra_body_json)

        return kwargs
