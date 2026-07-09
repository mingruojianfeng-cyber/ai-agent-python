import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from typing import Any, Protocol

from openai import AsyncOpenAI, OpenAIError

from app.core.config import Settings, get_settings


logger = logging.getLogger("yu_ai_agent.llm")


class OpenAICompatibleClientProtocol(Protocol):
    chat: Any


class LLMClientError(Exception):
    """Raised when the configured model provider call fails."""


class LLMClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client_factory: Callable[..., OpenAICompatibleClientProtocol] = AsyncOpenAI,
    ) -> None:
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

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
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

    def _completion_kwargs(self, *, messages: list[dict[str, str]], stream: bool) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }

        if self.settings.llm_reasoning_effort:
            kwargs["reasoning_effort"] = self.settings.llm_reasoning_effort

        if self.settings.llm_extra_body_json:
            kwargs["extra_body"] = json.loads(self.settings.llm_extra_body_json)

        return kwargs
