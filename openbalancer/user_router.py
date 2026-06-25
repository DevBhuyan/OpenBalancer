"""Build an LLMRouter scoped to a user's provider credentials."""

from __future__ import annotations

from openbalancer.router import LLMRouter
from openbalancer.settings import Settings, get_settings


def router_for_credentials(
    provider_credentials: dict[str, str] | None,
    settings: Settings | None = None,
) -> LLMRouter:
    """Return an LLMRouter using the given provider credentials."""
    base_settings = settings or get_settings()
    if not provider_credentials:
        return LLMRouter(base_settings)

    request_settings = base_settings.model_copy()
    request_settings.groq_api_key = provider_credentials.get("GROQ_API_KEY")
    request_settings.openrouter_api_key = provider_credentials.get("OPENROUTER_API_KEY")
    request_settings.cerebras_api_key = provider_credentials.get("CEREBRAS_API_KEY")
    request_settings.gemini_api_key = provider_credentials.get("GEMINI_API_KEY")
    request_settings.hf_api_key = provider_credentials.get("HF_API_KEY")
    return LLMRouter(request_settings)
