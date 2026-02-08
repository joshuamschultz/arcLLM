"""ArcLLM — Unified LLM abstraction layer for autonomous agents."""

from arcllm.adapters.anthropic import AnthropicAdapter
from arcllm.adapters.base import BaseAdapter
from arcllm.adapters.openai import OpenAIAdapter
from arcllm.config import (
    DefaultsConfig,
    GlobalConfig,
    ModelMetadata,
    ModuleConfig,
    ProviderConfig,
    ProviderSettings,
    load_global_config,
    load_provider_config,
)
from arcllm.exceptions import (
    ArcLLMAPIError,
    ArcLLMConfigError,
    ArcLLMError,
    ArcLLMParseError,
)
from arcllm.types import (
    ContentBlock,
    ImageBlock,
    LLMProvider,
    LLMResponse,
    Message,
    StopReason,
    TextBlock,
    Tool,
    ToolCall,
    ToolResultBlock,
    ToolUseBlock,
    Usage,
)

__all__ = [
    # Adapters
    "AnthropicAdapter",
    "BaseAdapter",
    "OpenAIAdapter",
    # Config types
    "DefaultsConfig",
    "GlobalConfig",
    "ModelMetadata",
    "ModuleConfig",
    "ProviderConfig",
    "ProviderSettings",
    # Config loaders
    "load_global_config",
    "load_provider_config",
    # Types
    "StopReason",
    "ContentBlock",
    "ImageBlock",
    "LLMProvider",
    "LLMResponse",
    "Message",
    "TextBlock",
    "Tool",
    "ToolCall",
    "ToolResultBlock",
    "ToolUseBlock",
    "Usage",
    # Exceptions
    "ArcLLMAPIError",
    "ArcLLMConfigError",
    "ArcLLMError",
    "ArcLLMParseError",
    # Public API
    "load_model",
]


def load_model(provider: str, model: str | None = None, **kwargs) -> LLMProvider:
    """Load a model object for the given provider.

    Placeholder — will be implemented in Step 6 (Provider Registry).
    """
    raise NotImplementedError(
        "load_model() is not yet implemented. Coming in Step 6."
    )
