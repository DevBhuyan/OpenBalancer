import pytest

from openbalancer.providers import (
    GeminiProvider,
    OpenAICompatibleProvider,
    PROVIDER_DEFINITIONS,
    PROVIDER_REGISTRY,
    ProviderDefinition,
    ProviderRegistry,
)
from openbalancer.router import LLMRouter
from openbalancer.settings import Settings


def test_registry_registers_and_retrieves_definition():
    definition = ProviderDefinition(
        name="test-provider",
        display_name="Test Provider",
        adapter_factory=OpenAICompatibleProvider,
        credential_id="TEST_API_KEY",
        api_key_setting="test_api_key",
        default_model_setting="test_model",
        small_model_setting="test_small_model",
        large_model_setting="test_large_model",
        base_url="https://example.test/v1",
        default_model="test-model",
    )
    registry = ProviderRegistry()

    registry.register(definition)

    assert registry.get("test-provider") is definition
    assert registry.contains("test-provider")
    assert registry.is_registered("test-provider")


def test_registry_contains_all_existing_provider_definitions():
    assert {definition.name for definition in PROVIDER_REGISTRY.all()} == {
        "groq", "openrouter", "cerebras", "huggingface", "gemini"
    }
    assert len(PROVIDER_DEFINITIONS) == 5


def test_lookup_returns_correct_provider_definition():
    assert PROVIDER_REGISTRY.get("groq") is next(
        definition for definition in PROVIDER_DEFINITIONS if definition.name == "groq"
    )


def test_unknown_provider_raises_clear_key_error():
    with pytest.raises(KeyError, match="Unknown provider 'missing'"):
        PROVIDER_REGISTRY.get("missing")


def test_duplicate_registration_is_rejected():
    definition = PROVIDER_REGISTRY.get("groq")
    with pytest.raises(ValueError, match="already registered"):
        PROVIDER_REGISTRY.register(definition)


def test_definitions_construct_the_existing_adapter_types():
    groq = PROVIDER_REGISTRY.get("groq").create_adapter(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key="test",
        default_model="openai/gpt-oss-120b",
        timeout_seconds=1,
    )
    gemini = PROVIDER_REGISTRY.get("gemini").create_adapter(
        api_key="test",
        default_model="gemini-flash-latest",
        timeout_seconds=1,
    )

    assert isinstance(groq, OpenAICompatibleProvider)
    assert isinstance(gemini, GeminiProvider)


def test_representative_provider_metadata_is_preserved():
    groq = PROVIDER_REGISTRY.get("groq")
    openrouter = PROVIDER_REGISTRY.get("openrouter")
    gemini = PROVIDER_REGISTRY.get("gemini")

    assert (groq.display_name, groq.credential_id, groq.base_url) == (
        "Groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1"
    )
    assert openrouter.adapter_factory is OpenAICompatibleProvider
    assert gemini.adapter_factory is GeminiProvider
    assert gemini.small_model == "gemini-flash-lite-latest"


def test_router_constructs_all_registered_adapter_types_from_definitions():
    router = LLMRouter(Settings(
        groq_api_key="groq-key",
        openrouter_api_key="openrouter-key",
        cerebras_api_key="cerebras-key",
        hf_api_key="hf-key",
        gemini_api_key="gemini-key",
    ))

    assert isinstance(router.providers["groq"], OpenAICompatibleProvider)
    assert isinstance(router.providers["openrouter"], OpenAICompatibleProvider)
    assert isinstance(router.providers["cerebras"], OpenAICompatibleProvider)
    assert isinstance(router.providers["huggingface"], OpenAICompatibleProvider)
    assert isinstance(router.providers["gemini"], GeminiProvider)
    assert router.providers["groq"].base_url == PROVIDER_REGISTRY.get("groq").base_url
    assert router.providers["openrouter"].extra_headers == {
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "OpenBalancer",
    }


def test_router_uses_registry_construction_metadata(monkeypatch):
    original = PROVIDER_REGISTRY.get("groq")
    replacement = ProviderDefinition(
        name="groq",
        display_name=original.display_name,
        adapter_factory=original.adapter_factory,
        credential_id=original.credential_id,
        api_key_setting=original.api_key_setting,
        default_model_setting=original.default_model_setting,
        small_model_setting=original.small_model_setting,
        large_model_setting=original.large_model_setting,
        base_url="https://registry.example/v2",
        default_model=original.default_model,
    )
    monkeypatch.setattr(PROVIDER_REGISTRY, "_definitions", {"groq": replacement})

    providers = LLMRouter(Settings(groq_api_key="test")).providers

    assert list(providers) == ["groq"]
    assert providers["groq"].base_url == "https://registry.example/v2"
