"""Base adapter — shared plumbing for all provider adapters."""

import os
from typing import Any

import httpx

from arcllm.config import ModelMetadata, ProviderConfig
from arcllm.exceptions import ArcLLMConfigError
from arcllm.types import LLMProvider, LLMResponse, Message, Tool


class BaseAdapter(LLMProvider):
    """Concrete base class for provider adapters.

    Handles config storage, API key resolution, httpx client lifecycle,
    and async context manager support. Subclasses implement invoke().
    """

    def __init__(self, config: ProviderConfig, model_name: str) -> None:
        self._config = config
        self._model_name = model_name
        self._model_meta: ModelMetadata | None = config.models.get(model_name)

        env_var = config.provider.api_key_env
        api_key = os.environ.get(env_var, "")
        if not api_key:
            raise ArcLLMConfigError(
                f"Missing environment variable '{env_var}' for provider. "
                "Set it to your API key."
            )
        self._api_key = api_key

        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    @property
    def name(self) -> str:
        return self._config.provider.api_format

    async def invoke(
        self,
        messages: list[Message],
        tools: list[Tool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        raise NotImplementedError

    def validate_config(self) -> bool:
        return bool(self._api_key)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None  # type: ignore[assignment]

    async def __aenter__(self) -> "BaseAdapter":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
