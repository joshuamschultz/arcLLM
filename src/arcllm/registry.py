"""Provider registry — convention-based adapter discovery and load_model()."""

import importlib

from arcllm.config import ProviderConfig, load_provider_config
from arcllm.exceptions import ArcLLMConfigError
from arcllm.types import LLMProvider

# Module-level caches: loaded once per provider, reused across calls.
# Thread safety: relies on CPython GIL for atomic dict operations.
# Under free-threaded Python (PEP 703, --disable-gil), a threading.Lock
# would be needed around cache-miss writes. Current async-first design
# means all access is single-threaded within an event loop.
_provider_config_cache: dict[str, ProviderConfig] = {}
_adapter_class_cache: dict[str, type[LLMProvider]] = {}


def clear_cache() -> None:
    """Reset all registry caches. Use in tests for isolation."""
    _provider_config_cache.clear()
    _adapter_class_cache.clear()


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


def load_model(
    provider: str,
    model: str | None = None,
) -> LLMProvider:
    """Load a configured model object for the given provider.

    The returned adapter is a **long-lived object** — create it once and
    reuse it for many ``invoke()`` calls within your agent's lifecycle.
    Each call to ``load_model()`` creates a new httpx connection pool,
    so avoid calling it per-request.

    Recommended usage::

        async with load_model("anthropic") as model:
            resp = await model.invoke(messages, tools)

    Args:
        provider: Provider name (e.g., "anthropic", "openai").
            Must match a TOML file in providers/ and a module in adapters/.
        model: Model identifier. If None, uses default_model from provider config.

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

    # Construct and return
    return adapter_class(config, model_name)
