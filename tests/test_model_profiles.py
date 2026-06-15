from openbalancer.models import ChatCompletionRequest
from openbalancer.providers.base import resolve_model
from openbalancer.router import LLMRouter
from openbalancer.settings import Settings


def test_auto_model_profiles_resolve_to_provider_specific_models():
    profiles = {
        "default": "provider-default",
        "small": "provider-small",
        "large": "provider-large",
    }

    assert resolve_model(ChatCompletionRequest(model="auto", messages=[]), profiles) == "provider-default"
    assert resolve_model(ChatCompletionRequest(model="auto:small", messages=[]), profiles) == "provider-small"
    assert resolve_model(ChatCompletionRequest(model="auto:large", messages=[]), profiles) == "provider-large"
    assert resolve_model(ChatCompletionRequest(model="exact-model", messages=[]), profiles) == "exact-model"


def test_provider_qualified_model_selects_provider_and_strips_prefix():
    router = LLMRouter(Settings(groq_api_key="test", openrouter_api_key="test"))
    request = ChatCompletionRequest(model="groq/openai/gpt-oss-120b", messages=[])

    providers = router._candidate_providers(request)
    provider_request = router._request_for_provider(request, "groq")

    assert [provider.name for provider in providers] == ["groq"]
    assert provider_request.model == "openai/gpt-oss-120b"
