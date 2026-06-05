from openbalancer.models import ChatCompletionRequest
from openbalancer.providers import ProviderError
from openbalancer.router import LLMRouter
from openbalancer.settings import Settings


def test_fastest_policy_prefers_lowest_observed_latency():
    router = LLMRouter(
        Settings(
            groq_api_key="test",
            openrouter_api_key="test",
            cerebras_api_key="test",
            gemini_api_key="test",
            hf_api_key="test",
        )
    )
    router.latency_ms["openrouter"] = 900
    router.latency_ms["groq"] = 100
    router.latency_ms["huggingface"] = 500

    providers = router._candidate_providers(ChatCompletionRequest(messages=[], routing="fastest"))

    assert providers[0].name == "groq"


def test_cheapest_policy_prefers_lowest_cost_rank():
    router = LLMRouter(
        Settings(
            provider_order=["openrouter", "groq", "huggingface"],
            openrouter_cost_rank=10,
            groq_cost_rank=1,
            hf_cost_rank=2,
            groq_api_key="test",
            openrouter_api_key="test",
            hf_api_key="test",
        )
    )

    providers = router._candidate_providers(ChatCompletionRequest(messages=[], routing="cheapest"))

    assert [provider.name for provider in providers[:3]] == ["groq", "huggingface", "openrouter"]


def test_stable_policy_prefers_lower_failure_rate():
    router = LLMRouter(
        Settings(
            provider_order=["openrouter", "groq"],
            groq_api_key="test",
            openrouter_api_key="test",
        )
    )
    router.successes["openrouter"] = 1
    router.total_failures["openrouter"] = 9
    router.failures["openrouter"] = 2
    router.successes["groq"] = 10
    router.total_failures["groq"] = 1

    providers = router._candidate_providers(ChatCompletionRequest(messages=[], routing="stable"))

    assert providers[0].name == "groq"


def test_non_retryable_client_provider_errors_are_detected():
    router = LLMRouter(Settings(openrouter_api_key="test"))

    assert router._is_non_retryable_error(ProviderError("openrouter", "bad model", 400)) is True
    assert router._is_non_retryable_error(ProviderError("openrouter", "rate limited", 429)) is False
    assert router._is_non_retryable_error(ProviderError("openrouter", "unavailable", 503)) is False
