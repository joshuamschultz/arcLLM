"""ArcLLM modules — opt-in functionality that wraps adapters."""

from arcllm.modules.base import BaseModule
from arcllm.modules.fallback import FallbackModule
from arcllm.modules.rate_limit import RateLimitModule
from arcllm.modules.retry import RetryModule

__all__ = [
    "BaseModule",
    "FallbackModule",
    "RateLimitModule",
    "RetryModule",
]
