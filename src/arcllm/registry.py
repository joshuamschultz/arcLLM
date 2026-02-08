"""Provider registry — convention-based adapter discovery and load_model()."""

import importlib
from typing import Any

from arcllm.config import ProviderConfig, load_global_config, load_provider_config
from arcllm.exceptions import ArcLLMConfigError
from arcllm.types import LLMProvider

# Module-level caches: loaded once per provider, reused across calls.
# Thread safety: relies on CPython GIL for atomic dict operations.
# Under free-threaded Python (PEP 703, --disable-gil), a threading.Lock
# would be needed around cache-miss writes. Current async-first design
# means all access is single-threaded within an event loop.
_provider_config_cache: dict[str, ProviderConfig] = {}
_adapter_class_cache: dict[str, type[LLMProvider]] = {}
_global_config_cache: dict[str, Any] | None = None
_module_settings_cache: dict[str, dict[str, Any]] = {}


def clear_cache() -> None:
    """Reset all registry caches. Use in tests for isolation."""
    global _global_config_cache
    _provider_config_cache.clear()
    _adapter_class_cache.clear()
    _global_config_cache = None
    _module_settings_cache.clear()


def _get_adapter_class(provider_name: str) -> type[LLMProvider]:
    """Look up the adapter class by naming convention.

    Convention:
        provider_name -> module: arcllm.adapters.{provider_name}
        provider_name -> class:  {provider_name.title()}Adapter
    """
    if provider_name in _adapter_class_cache:
        return _adapter_class_cache[provider_name]

    module_path = f"arcllm.adapters.{provider_name}"
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise ArcLLMConfigError(
            f"No adapter module found for provider '{provider_name}'. "
            f"Expected module: {module_path}"
        )

    class_name = f"{provider_name.title()}Adapter"
    adapter_class = getattr(module, class_name, None)
    if adapter_class is None:
        raise ArcLLMConfigError(
            f"No adapter class '{class_name}' found in module '{module_path}'"
        )

    _adapter_class_cache[provider_name] = adapter_class
    return adapter_class


def _resolve_module_config(
    module_name: str,
    kwarg_value: bool | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge config.toml module settings with load_model() kwarg override.

    Resolution priority (highest first):
        1. kwarg=False  → disabled (returns None)
        2. kwarg={...}  → use kwarg dict (merged over config.toml defaults)
        3. kwarg=True    → use config.toml settings (or empty defaults)
        4. kwarg=None    → check config.toml enabled flag

    Returns:
        Module config dict if enabled, None if disabled.
    """
    global _global_config_cache
    if _global_config_cache is None:
        _global_config_cache = load_global_config()
        # Pre-extract module settings (avoids model_dump() per call)
        for name, cfg in _global_config_cache.modules.items():
            _module_settings_cache[name] = {
                k: v for k, v in cfg.model_dump().items() if k != "enabled"
            }

    # Get config.toml settings for this module
    module_cfg = _global_config_cache.modules.get(module_name)
    config_enabled = module_cfg.enabled if module_cfg else False
    config_settings = _module_settings_cache.get(module_name, {})

    # Resolve based on kwarg
    if kwarg_value is False:
        return None
    if kwarg_value is True:
        return config_settings
    if isinstance(kwarg_value, dict):
        # Kwarg dict overrides config.toml defaults
        merged = {**config_settings, **kwarg_value}
        return merged
    # kwarg_value is None — use config.toml enabled flag
    if config_enabled:
        return config_settings
    return None


def load_model(
    provider: str,
    model: str | None = None,
    *,
    retry: bool | dict[str, Any] | None = None,
    fallback: bool | dict[str, Any] | None = None,
) -> LLMProvider:
    """Load a configured model object for the given provider.

    The returned adapter is a **long-lived object** — create it once and
    reuse it for many ``invoke()`` calls within your agent's lifecycle.
    Each call to ``load_model()`` creates a new httpx connection pool,
    so avoid calling it per-request.

    Recommended usage::

        async with load_model("anthropic") as model:
            resp = await model.invoke(messages, tools)

    Module kwargs control opt-in wrapping:
        - ``True``: enable with config.toml defaults
        - ``False``: disable (overrides config.toml)
        - ``dict``: enable with custom settings (merged over defaults)
        - ``None`` (default): use config.toml enabled flag

    Stacking order (outermost first): Retry → Fallback → Adapter.

    Args:
        provider: Provider name (e.g., "anthropic", "openai").
            Must match a TOML file in providers/ and a module in adapters/.
        model: Model identifier. If None, uses default_model from provider config.
        retry: RetryModule configuration override.
        fallback: FallbackModule configuration override.

    Returns:
        A configured LLMProvider instance ready for invoke().

    Raises:
        ArcLLMConfigError: On missing config, missing adapter, or invalid provider name.
    """
    # Load and cache provider config
    if provider not in _provider_config_cache:
        _provider_config_cache[provider] = load_provider_config(provider)
    config = _provider_config_cache[provider]

    # Resolve model name
    model_name = model or config.provider.default_model

    # Look up adapter class by convention (cached after first lookup)
    adapter_class = _get_adapter_class(provider)

    # Construct adapter
    result: LLMProvider = adapter_class(config, model_name)

    # Apply module wrapping (innermost first): Fallback, then Retry
    fallback_config = _resolve_module_config("fallback", fallback)
    if fallback_config is not None:
        from arcllm.modules.fallback import FallbackModule

        result = FallbackModule(fallback_config, result)

    retry_config = _resolve_module_config("retry", retry)
    if retry_config is not None:
        from arcllm.modules.retry import RetryModule

        result = RetryModule(retry_config, result)

    return result
