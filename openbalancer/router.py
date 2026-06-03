from __future__ import annotations

from collections.abc import AsyncIterator

from openbalancer.models import ChatCompletionRequest, ProviderHealth, ProviderResult
from openbalancer.providers import GeminiProvider, OpenAICompatibleProvider, ProviderAdapter, ProviderError
from openbalancer.settings import Settings


class LLMRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.providers = self._build_providers(settings)
        self.failures: dict[str, int] = {name: 0 for name in self.providers}
        self.latency_ms: dict[str, float] = {}
        self.last_error: dict[str, str] = {}

    def _build_providers(self, settings: Settings) -> dict[str, ProviderAdapter]:
        providers: dict[str, ProviderAdapter] = {
            "groq": OpenAICompatibleProvider(
                name="groq",
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
                default_model=settings.groq_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
            "openrouter": OpenAICompatibleProvider(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
                default_model=settings.openrouter_model,
                timeout_seconds=settings.request_timeout_seconds,
                extra_headers={
                    "HTTP-Referer": settings.openrouter_http_referer,
                    "X-Title": settings.openrouter_app_title,
                },
            ),
            "cerebras": OpenAICompatibleProvider(
                name="cerebras",
                base_url="https://api.cerebras.ai/v1",
                api_key=settings.cerebras_api_key,
                default_model=settings.cerebras_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
            "gemini": GeminiProvider(
                api_key=settings.gemini_api_key,
                default_model=settings.gemini_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
        }
        return providers

    def health(self) -> list[ProviderHealth]:
        items: list[ProviderHealth] = []
        for name, provider in self.providers.items():
            items.append(
                ProviderHealth(
                    name=name,
                    available=provider.available,
                    healthy=provider.available and self.failures.get(name, 0) < 3,
                    latency_ms=self.latency_ms.get(name),
                    failures=self.failures.get(name, 0),
                    last_error=self.last_error.get(name),
                )
            )
        return items

    async def chat(self, request: ChatCompletionRequest) -> ProviderResult:
        errors: list[str] = []
        for provider in self._candidate_providers(request):
            try:
                result = await provider.chat(request)
                self._mark_success(provider.name, result.latency_ms)
                return result
            except ProviderError as exc:
                self._mark_failure(provider.name, str(exc))
                errors.append(f"{provider.name}: {exc}")

        raise ProviderError("router", "all providers failed: " + "; ".join(errors), 502)

    async def stream_chat(self, request: ChatCompletionRequest) -> AsyncIterator[bytes]:
        errors: list[str] = []
        for provider in self._candidate_providers(request):
            if not provider.supports_streaming:
                continue
            try:
                async for chunk in provider.stream_chat(request):
                    yield chunk
                self._mark_success(provider.name, self.latency_ms.get(provider.name, 0))
                return
            except ProviderError as exc:
                self._mark_failure(provider.name, str(exc))
                errors.append(f"{provider.name}: {exc}")

        raise ProviderError("router", "all streaming providers failed: " + "; ".join(errors), 502)

    def _candidate_providers(self, request: ChatCompletionRequest) -> list[ProviderAdapter]:
        if request.provider:
            provider = self.providers.get(request.provider)
            return [provider] if provider else []

        ordered_names = list(self.settings.provider_order)
        if request.routing == "fastest":
            ordered_names.sort(key=lambda name: self.latency_ms.get(name, float("inf")))

        return [
            self.providers[name]
            for name in ordered_names
            if name in self.providers and self.providers[name].available and self.failures.get(name, 0) < 3
        ]

    def _mark_success(self, provider: str, latency_ms: float) -> None:
        self.failures[provider] = 0
        self.latency_ms[provider] = latency_ms
        self.last_error.pop(provider, None)

    def _mark_failure(self, provider: str, error: str) -> None:
        self.failures[provider] = self.failures.get(provider, 0) + 1
        self.last_error[provider] = error[:500]
