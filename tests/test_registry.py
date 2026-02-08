"""Tests for ArcLLM provider registry and load_model()."""

import types as stdlib_types
from unittest.mock import patch

import pytest

from arcllm.config import load_provider_config as _real_load_provider_config
from arcllm.exceptions import ArcLLMConfigError
from arcllm.types import LLMProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _set_api_keys(monkeypatch):
    """Set fake API keys for adapter construction."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear the registry cache before and after each test."""
    from arcllm.registry import clear_cache

    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# TestLoadModelHappyPath
# ---------------------------------------------------------------------------


class TestLoadModelHappyPath:
    def test_load_anthropic_adapter(self):
        from arcllm.adapters.anthropic import AnthropicAdapter
        from arcllm.registry import load_model

        model = load_model("anthropic")
        assert isinstance(model, AnthropicAdapter)

    def test_load_openai_adapter(self):
        from arcllm.adapters.openai import OpenaiAdapter
        from arcllm.registry import load_model

        model = load_model("openai")
        assert isinstance(model, OpenaiAdapter)

    def test_load_default_model(self):
        from arcllm.registry import load_model

        model = load_model("anthropic")
        # default_model from anthropic.toml is claude-sonnet-4-20250514
        assert model.model_name == "claude-sonnet-4-20250514"

    def test_load_explicit_model(self):
        from arcllm.registry import load_model

        model = load_model("anthropic", "claude-haiku-4-5-20251001")
        assert model.model_name == "claude-haiku-4-5-20251001"

    def test_returns_llm_provider(self):
        from arcllm.registry import load_model

        model = load_model("anthropic")
        assert isinstance(model, LLMProvider)

    def test_nonexistent_model_accepted(self):
        """Unknown model name is allowed — adapter constructed with model_meta=None."""
        from arcllm.registry import load_model

        model = load_model("anthropic", "claude-nonexistent-99")
        assert model.model_name == "claude-nonexistent-99"
        assert model._model_meta is None

    def test_same_provider_different_models_returns_distinct_instances(self):
        """Cache stores config, not adapter instances. Each call returns a fresh adapter."""
        from arcllm.registry import load_model

        m1 = load_model("anthropic", "claude-sonnet-4-20250514")
        m2 = load_model("anthropic", "claude-haiku-4-5-20251001")
        assert m1 is not m2
        assert m1.model_name != m2.model_name


# ---------------------------------------------------------------------------
# TestConfigCaching
# ---------------------------------------------------------------------------


class TestConfigCaching:
    def test_config_cached(self):
        from arcllm.registry import load_model

        with patch(
            "arcllm.registry.load_provider_config",
            wraps=_real_load_provider_config,
        ) as mock_load:
            load_model("anthropic")
            load_model("anthropic")
            # Should only load config once — second call uses cache
            assert mock_load.call_count == 1

    def test_clear_cache_resets(self):
        from arcllm.registry import clear_cache, load_model

        with patch(
            "arcllm.registry.load_provider_config",
            wraps=_real_load_provider_config,
        ) as mock_load:
            load_model("anthropic")
            assert mock_load.call_count == 1

            clear_cache()
            load_model("anthropic")
            assert mock_load.call_count == 2

    def test_different_providers_cached_separately(self):
        from arcllm.registry import load_model

        with patch(
            "arcllm.registry.load_provider_config",
            wraps=_real_load_provider_config,
        ) as mock_load:
            load_model("anthropic")
            load_model("openai")
            load_model("anthropic")
            load_model("openai")
            # Each provider loaded once
            assert mock_load.call_count == 2

    def test_adapter_class_cached(self):
        """Adapter class is cached — importlib only called once per provider."""
        from arcllm.registry import _adapter_class_cache, load_model

        load_model("anthropic")
        assert "anthropic" in _adapter_class_cache

        load_model("anthropic")
        # Still just one entry — class was reused from cache
        assert len(_adapter_class_cache) == 1


# ---------------------------------------------------------------------------
# TestErrorHandling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_missing_provider_toml(self):
        from arcllm.registry import load_model

        with pytest.raises(ArcLLMConfigError, match="nonexistent"):
            load_model("nonexistent")

    def test_missing_adapter_module(self):
        from arcllm.registry import load_model

        # Patch load_provider_config to succeed, but module won't exist
        with patch("arcllm.registry.load_provider_config") as mock_config:
            mock_config.return_value = type("FakeConfig", (), {
                "provider": type("FakeProvider", (), {"default_model": "test"})()
            })()
            with pytest.raises(ArcLLMConfigError, match="adapter module"):
                load_model("nosuchadapter")

    def test_missing_adapter_class(self):
        from arcllm.registry import _get_adapter_class

        with patch("importlib.import_module") as mock_import:
            fake_module = stdlib_types.ModuleType("arcllm.adapters.fakeprov")
            mock_import.return_value = fake_module
            with pytest.raises(ArcLLMConfigError, match="FakeprovAdapter"):
                _get_adapter_class("fakeprov")

    def test_invalid_provider_name(self):
        from arcllm.registry import load_model

        with pytest.raises(ArcLLMConfigError, match="Invalid provider name"):
            load_model("../etc/passwd")

    def test_empty_provider_name(self):
        from arcllm.registry import load_model

        with pytest.raises(ArcLLMConfigError, match="cannot be empty"):
            load_model("")

    def test_uppercase_provider_name(self):
        from arcllm.registry import load_model

        with pytest.raises(ArcLLMConfigError, match="Invalid provider name"):
            load_model("ANTHROPIC")

    def test_broken_adapter_module_caught(self):
        """ImportError from a broken adapter (not just missing) is caught cleanly."""
        from arcllm.registry import _get_adapter_class

        with patch("importlib.import_module", side_effect=ImportError("bad dependency")):
            with pytest.raises(ArcLLMConfigError, match="adapter module"):
                _get_adapter_class("brokenprovider")


# ---------------------------------------------------------------------------
# TestModuleStacking
# ---------------------------------------------------------------------------


class TestModuleStacking:
    """Registry integration: load_model() wraps adapters with modules."""

    def test_load_model_with_retry_kwarg(self):
        """retry=True wraps adapter with RetryModule."""
        from arcllm.modules.retry import RetryModule
        from arcllm.registry import load_model

        model = load_model("anthropic", retry=True)
        assert isinstance(model, RetryModule)

    def test_load_model_with_retry_dict(self):
        """retry={...} wraps adapter with RetryModule using custom config."""
        from arcllm.modules.retry import RetryModule
        from arcllm.registry import load_model

        model = load_model("anthropic", retry={"max_retries": 5})
        assert isinstance(model, RetryModule)
        assert model._max_retries == 5

    def test_load_model_with_config_retry(self):
        """Config.toml retry.enabled=true wraps adapter with RetryModule."""
        from arcllm.config import GlobalConfig, ModuleConfig
        from arcllm.modules.retry import RetryModule
        from arcllm.registry import load_model

        mock_global = GlobalConfig(
            defaults={"provider": "anthropic", "temperature": 0.7, "max_tokens": 4096},
            modules={"retry": ModuleConfig(enabled=True, max_retries=2)},
        )
        with patch("arcllm.registry.load_global_config", return_value=mock_global):
            model = load_model("anthropic")
        assert isinstance(model, RetryModule)

    def test_load_model_retry_false_overrides_config(self):
        """retry=False disables retry even if config.toml enables it."""
        from arcllm.adapters.anthropic import AnthropicAdapter
        from arcllm.config import GlobalConfig, ModuleConfig
        from arcllm.modules.retry import RetryModule
        from arcllm.registry import load_model

        mock_global = GlobalConfig(
            defaults={"provider": "anthropic", "temperature": 0.7, "max_tokens": 4096},
            modules={"retry": ModuleConfig(enabled=True, max_retries=2)},
        )
        with patch("arcllm.registry.load_global_config", return_value=mock_global):
            model = load_model("anthropic", retry=False)
        assert not isinstance(model, RetryModule)
        assert isinstance(model, AnthropicAdapter)

    def test_load_model_with_fallback(self):
        """fallback=True wraps adapter with FallbackModule."""
        from arcllm.modules.fallback import FallbackModule
        from arcllm.registry import load_model

        model = load_model("anthropic", fallback=True)
        assert isinstance(model, FallbackModule)

    def test_load_model_with_fallback_dict(self):
        """fallback={...} wraps adapter with FallbackModule using custom config."""
        from arcllm.modules.fallback import FallbackModule
        from arcllm.registry import load_model

        model = load_model("anthropic", fallback={"chain": ["openai"]})
        assert isinstance(model, FallbackModule)
        assert model._chain == ["openai"]

    def test_load_model_retry_and_fallback_stacking_order(self):
        """Stacking order: Retry(Fallback(adapter))."""
        from arcllm.adapters.anthropic import AnthropicAdapter
        from arcllm.modules.fallback import FallbackModule
        from arcllm.modules.retry import RetryModule
        from arcllm.registry import load_model

        model = load_model("anthropic", retry=True, fallback=True)
        # Outermost is Retry
        assert isinstance(model, RetryModule)
        # Inner is Fallback
        assert isinstance(model._inner, FallbackModule)
        # Innermost is the adapter
        assert isinstance(model._inner._inner, AnthropicAdapter)

    def test_load_model_no_modules_unchanged(self):
        """Without module kwargs, adapter returned directly (existing behavior)."""
        from arcllm.adapters.anthropic import AnthropicAdapter
        from arcllm.registry import load_model

        model = load_model("anthropic")
        assert isinstance(model, AnthropicAdapter)

    def test_load_model_retry_kwarg_overrides_config_values(self):
        """retry={max_retries: 10} overrides config.toml max_retries=2."""
        from arcllm.config import GlobalConfig, ModuleConfig
        from arcllm.modules.retry import RetryModule
        from arcllm.registry import load_model

        mock_global = GlobalConfig(
            defaults={"provider": "anthropic", "temperature": 0.7, "max_tokens": 4096},
            modules={"retry": ModuleConfig(enabled=True, max_retries=2)},
        )
        with patch("arcllm.registry.load_global_config", return_value=mock_global):
            model = load_model("anthropic", retry={"max_retries": 10})
        assert isinstance(model, RetryModule)
        assert model._max_retries == 10
