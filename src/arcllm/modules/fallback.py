"""FallbackModule — provider chain switching on failure."""

from typing import Any

from arcllm.exceptions import ArcLLMConfigError
from arcllm.modules.base import BaseModule
from arcllm.types import LLMProvider, LLMResponse, Message, Tool

_MAX_FALLBACK_CHAIN_LENGTH = 10


def load_model(provider: str) -> LLMProvider:
    """Lazy import to avoid circular dependency with registry."""
    from arcllm.registry import load_model as _load_model

    return _load_model(provider)


class FallbackModule(BaseModule):
    """Falls back to alternative providers when the primary fails.

    On any exception from the inner provider, walks a config-driven chain
    of provider names, creating each fallback adapter on-demand via
    load_model(). If all fallbacks also fail, raises the original
    (primary) error.

    Config keys:
        chain: List of provider names to try on failure (default: []).
    """

    def __init__(self, config: dict[str, Any], inner: LLMProvider) -> None:
        super().__init__(config, inner)
        self._chain: list[str] = config.get("chain", [])
        if len(self._chain) > _MAX_FALLBACK_CHAIN_LENGTH:
            raise ArcLLMConfigError(
                f"Fallback chain too long ({len(self._chain)} providers, "
                f"max {_MAX_FALLBACK_CHAIN_LENGTH})"
            )

    async def invoke(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        try:
            return await self._inner.invoke(messages, tools, **kwargs)
        except Exception as primary_error:
            for provider_name in self._chain:
                try:
                    fallback = load_model(provider_name)
                    return await fallback.invoke(messages, tools, **kwargs)
                except Exception:
                    continue
            raise primary_error
