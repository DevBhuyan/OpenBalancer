from openbalancer.models import ChatCompletionRequest
from openbalancer.providers.base import resolve_model


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
