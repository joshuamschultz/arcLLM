"""BaseModule — transparent wrapper foundation for all modules."""

from typing import Any

from arcllm.types import LLMProvider, LLMResponse, Message, Tool


class BaseModule(LLMProvider):
    """Base class for ArcLLM modules.

    Wraps an inner LLMProvider and delegates all calls by default.
    Subclasses override invoke() to add behavior (retry, fallback, etc.).
    """

    def __init__(self, config: dict[str, Any], inner: LLMProvider) -> None:
        self._config = config
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def model_name(self) -> str:
        return self._inner.model_name

    async def invoke(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        return await self._inner.invoke(messages, tools, **kwargs)

    def validate_config(self) -> bool:
        return self._inner.validate_config()

    async def close(self) -> None:
        """Close resources held by the inner provider."""
        if hasattr(self._inner, "close"):
            await self._inner.close()
