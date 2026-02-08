"""ArcLLM — Unified LLM abstraction layer for autonomous agents."""

from arcllm.exceptions import ArcLLMConfigError, ArcLLMError, ArcLLMParseError
from arcllm.types import (
    ContentBlock,
    ImageBlock,
    LLMProvider,
    LLMResponse,
    Message,
    TextBlock,
    Tool,
    ToolCall,
    ToolResultBlock,
    ToolUseBlock,
    Usage,
)

__all__ = [
    # Types
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
