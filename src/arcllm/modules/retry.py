"""RetryModule — exponential backoff with jitter on transient failures."""

import asyncio
import random
from typing import Any

import httpx

from arcllm.exceptions import ArcLLMAPIError, ArcLLMConfigError
from arcllm.modules.base import BaseModule
from arcllm.types import LLMProvider, LLMResponse, Message, Tool

# Default retryable HTTP status codes.
_DEFAULT_RETRYABLE_CODES = [429, 500, 502, 503, 529]


class RetryModule(BaseModule):
    """Retries transient failures with exponential backoff + jitter.

    Wraps an inner LLMProvider. On retryable errors (specific HTTP status
    codes or connection-level failures), waits with exponential backoff
    and retries up to max_retries times.

    Config keys:
        max_retries: Maximum retry attempts after initial try (default: 3).
        backoff_base_seconds: Base wait time in seconds (default: 1.0).
        max_wait_seconds: Maximum wait time cap (default: 60.0).
        retryable_status_codes: HTTP codes to retry (default: [429,500,502,503,529]).
    """

    def __init__(self, config: dict[str, Any], inner: LLMProvider) -> None:
        super().__init__(config, inner)
        self._max_retries: int = config.get("max_retries", 3)
        self._backoff_base: float = config.get("backoff_base_seconds", 1.0)
        self._max_wait: float = config.get("max_wait_seconds", 60.0)
        self._retryable_codes: set[int] = set(
            config.get("retryable_status_codes", _DEFAULT_RETRYABLE_CODES)
        )
        # Validate config bounds
        if self._max_retries < 0:
            raise ArcLLMConfigError("max_retries must be >= 0")
        if self._backoff_base <= 0:
            raise ArcLLMConfigError("backoff_base_seconds must be > 0")
        if self._max_wait <= 0:
            raise ArcLLMConfigError("max_wait_seconds must be > 0")

    async def invoke(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return await self._inner.invoke(messages, tools, **kwargs)
            except (ArcLLMAPIError, httpx.ConnectError, httpx.TimeoutException) as e:
                if not self._is_retryable(e):
                    raise
                last_error = e
                if attempt < self._max_retries:
                    wait = self._calculate_wait(attempt)
                    await asyncio.sleep(wait)

        raise last_error  # type: ignore[misc]

    def _is_retryable(self, error: Exception) -> bool:
        """Check if an error is retryable."""
        if isinstance(error, ArcLLMAPIError):
            return error.status_code in self._retryable_codes
        if isinstance(error, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        return False

    def _calculate_wait(self, attempt: int) -> float:
        """Calculate wait time with exponential backoff + proportional jitter."""
        backoff = self._backoff_base * (2**attempt)
        jitter = random.uniform(0, backoff)
        return min(backoff + jitter, self._max_wait)
