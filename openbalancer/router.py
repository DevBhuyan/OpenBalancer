from __future__ import annotations
import asyncio
import re
import threading
import time
from collections import deque
from collections.abc import AsyncIterator
from typing import Optional
from openbalancer.models import (
    ChatCompletionRequest,
    ProviderHealth,
    ProviderResult
)
from openbalancer.providers import (
    GeminiProvider,
    OpenAICompatibleProvider,
    ProviderAdapter,
    ProviderError
)
from openbalancer.settings import Settings


class ArtificialProviderLimiter:
    def __init__(self, *, max_concurrent: int = 0, rpm: int = 0) -> None:
        self.max_concurrent = max(0, max_concurrent)
        self.rpm = max(0, rpm)
        self.in_flight = 0
        self.request_times: deque[float] = deque()
        self._lock = threading.Lock()

    async def try_acquire(self) -> tuple[bool, Optional[str], float]:
        with self._lock:
            now = time.monotonic()
            self._prune(now)

            if self.max_concurrent and self.in_flight >= self.max_concurrent:
                return False, f"artificial concurrency limit reached ({self.in_flight}/{self.max_concurrent})", 0.05

            if self.rpm and len(self.request_times) >= self.rpm:
                retry_after = max(0.05, 60 - (now - self.request_times[0])) if self.request_times else 1.0
                return False, f"artificial RPM limit reached ({len(self.request_times)}/{self.rpm})", retry_after

            self.in_flight += 1
            self.request_times.append(now)
            return True, None, 0.0

    async def release(self) -> None:
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)
            self._prune(time.monotonic())

    def snapshot(self) -> dict[str, int]:
        self._prune(time.monotonic())
        return {
            "in_flight": self.in_flight,
            "artificial_max_concurrent": self.max_concurrent,
            "artificial_rpm": self.rpm,
            "artificial_window_used": len(self.request_times),
        }

    def _prune(self, now: float) -> None:
        while self.request_times and now - self.request_times[0] >= 60:
            self.request_times.popleft()


class LLMRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.providers = self._build_providers(settings)
        self.failures: dict[str, int] = {name: 0 for name in self.providers}
        self.total_failures: dict[str, int] = {name: 0 for name in self.providers}
        self.successes: dict[str, int] = {name: 0 for name in self.providers}
        self.latency_ms: dict[str, float] = {}
        self.last_error: dict[str, str] = {}
        self.cooldown_until: dict[str, float] = {}
        self.limiters = {
            "openrouter": ArtificialProviderLimiter(
                max_concurrent=settings.openrouter_artificial_max_concurrent,
                rpm=settings.openrouter_artificial_rpm,
            )
        }

    def _build_providers(self, settings: Settings) -> dict[str, ProviderAdapter]:
        providers: dict[str, ProviderAdapter] = {
            "groq": OpenAICompatibleProvider(
                name="groq",
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.groq_api_key,
                default_model=settings.groq_model,
                small_model=settings.groq_small_model,
                large_model=settings.groq_large_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
            "openrouter": OpenAICompatibleProvider(
                name="openrouter",
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
                default_model=settings.openrouter_model,
                small_model=settings.openrouter_small_model,
                large_model=settings.openrouter_large_model,
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
                small_model=settings.cerebras_small_model,
                large_model=settings.cerebras_large_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
            "huggingface": OpenAICompatibleProvider(
                name="huggingface",
                base_url="https://router.huggingface.co/v1",
                api_key=settings.hf_api_key,
                default_model=settings.hf_model,
                small_model=settings.hf_small_model,
                large_model=settings.hf_large_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
            "gemini": GeminiProvider(
                api_key=settings.gemini_api_key,
                default_model=settings.gemini_model,
                small_model=settings.gemini_small_model,
                large_model=settings.gemini_large_model,
                timeout_seconds=settings.request_timeout_seconds,
            ),
        }
        return providers

    def health(self) -> list[ProviderHealth]:
        items: list[ProviderHealth] = []
        for name, provider in self.providers.items():
            limiter_state = self._limiter_state(name)
            cooldown_remaining = self._cooldown_remaining(name)
            successes = self.successes.get(name, 0)
            failures = self.failures.get(name, 0)
            items.append(
                ProviderHealth(
                    name=name,
                    available=provider.available,
                    healthy=provider.available and cooldown_remaining <= 0,
                    latency_ms=self.latency_ms.get(name),
                    failures=failures,
                    total_failures=self.total_failures.get(name, 0),
                    successes=successes,
                    failure_rate=self._failure_rate(name),
                    last_error=self.last_error.get(name),
                    cooldown_remaining_seconds=cooldown_remaining,
                    cost_rank=self._cost_rank(name),
                    **limiter_state,
                )
            )
        return items

    async def chat(self, request: ChatCompletionRequest) -> ProviderResult:
        errors: dict[str, str] = {}
        attempted_providers: list[str] = []
        non_retryable_providers: set[str] = set()
        deadline = time.monotonic() + self.settings.router_max_wait_seconds

        while True:
            retry_after_options: list[float] = []

            for provider in self._candidate_providers(request):
                if provider.name in non_retryable_providers:
                    continue

                if provider.name not in attempted_providers:
                    attempted_providers.append(provider.name)

                cooldown_remaining = self._cooldown_remaining(provider.name)
                if cooldown_remaining > 0:
                    errors[provider.name] = f"{provider.name}: cooling down for {cooldown_remaining:.2f}s"
                    retry_after_options.append(cooldown_remaining)
                    continue

                acquired, reason, retry_after = await self._try_acquire(provider.name)
                if not acquired:
                    errors[provider.name] = f"{provider.name}: {reason}"
                    retry_after_options.append(retry_after)
                    continue

                try:
                    result = await provider.chat(request)
                    self._mark_success(provider.name, result.latency_ms)
                    return result
                except ProviderError as exc:
                    cooldown_seconds = self._cooldown_seconds_for_error(exc)
                    self._mark_failure(provider.name, str(exc), cooldown_seconds)
                    errors[provider.name] = f"{provider.name}: {exc}"
                    if self._is_non_retryable_error(exc):
                        non_retryable_providers.add(provider.name)
                    else:
                        retry_after_options.append(self._cooldown_remaining(provider.name))
                finally:
                    await self._release(provider.name)

            remaining = deadline - time.monotonic()
            if remaining <= 0 or not retry_after_options:
                break

            retry_after = self._retry_after(retry_after_options)
            await asyncio.sleep(min(retry_after, remaining))

        raise ProviderError(
            "router",
            "all providers failed: " + "; ".join(errors.values()),
            502,
            {
                "attempted_providers": attempted_providers,
                "errors": list(errors.values()),
            },
        )

    async def stream_chat(self, request: ChatCompletionRequest) -> AsyncIterator[bytes]:
        errors: list[str] = []
        attempted_providers: list[str] = []
        for provider in self._candidate_providers(request):
            attempted_providers.append(provider.name)
            if not provider.supports_streaming:
                continue
            acquired, reason, _retry_after = await self._try_acquire(provider.name)
            if not acquired:
                errors.append(f"{provider.name}: {reason}")
                continue

            try:
                async for chunk in provider.stream_chat(request):
                    yield chunk
                self._mark_success(
                    provider.name, self.latency_ms.get(provider.name, 0))
                return
            except ProviderError as exc:
                self._mark_failure(provider.name, str(exc), self._cooldown_seconds_for_error(exc))
                errors.append(f"{provider.name}: {exc}")
            finally:
                await self._release(provider.name)

        raise ProviderError(
            "router",
            "all streaming providers failed: " + "; ".join(errors),
            502,
            {
                "attempted_providers": attempted_providers,
                "errors": errors,
            },
        )

    def _candidate_providers(self, request: ChatCompletionRequest) -> list[ProviderAdapter]:
        if request.provider:
            provider = self.providers.get(request.provider)
            return [provider] if provider else []

        ordered_names = list(self.settings.provider_order)
        if request.routing == "fastest":
            ordered_names.sort(
                key=lambda name: self.latency_ms.get(name, float("inf")))
        elif request.routing == "cheapest":
            ordered_names.sort(key=self._cheapest_score)
        elif request.routing in {"stable", "slow_and_stable"}:
            ordered_names.sort(key=self._stable_score)
        elif request.routing == "balanced":
            ordered_names.sort(key=self._balanced_score)

        return [
            self.providers[name]
            for name in ordered_names
            if name in self.providers and self.providers[name].available
        ]

    def _mark_success(self, provider: str, latency_ms: float) -> None:
        self.failures[provider] = 0
        self.successes[provider] = self.successes.get(provider, 0) + 1
        self.latency_ms[provider] = latency_ms
        self.last_error.pop(provider, None)
        self.cooldown_until.pop(provider, None)

    def _mark_failure(self, provider: str, error: str, cooldown_seconds: Optional[float] = None) -> None:
        self.failures[provider] = self.failures.get(provider, 0) + 1
        self.total_failures[provider] = self.total_failures.get(provider, 0) + 1
        self.last_error[provider] = error[:500]
        if cooldown_seconds and cooldown_seconds > 0:
            self.cooldown_until[provider] = time.monotonic() + cooldown_seconds

    async def _try_acquire(self, provider: str) -> tuple[bool, Optional[str], float]:
        limiter = self.limiters.get(provider)
        if not limiter:
            return True, None, 0.0
        return await limiter.try_acquire()

    async def _release(self, provider: str) -> None:
        limiter = self.limiters.get(provider)
        if limiter:
            await limiter.release()

    def _limiter_state(self, provider: str) -> dict[str, int]:
        limiter = self.limiters.get(provider)
        if not limiter:
            return {}
        return limiter.snapshot()

    def _cooldown_remaining(self, provider: str) -> float:
        return max(0.0, self.cooldown_until.get(provider, 0.0) - time.monotonic())

    def _retry_after(self, options: list[float]) -> float:
        positive_options = [option for option in options if option > 0]
        if not positive_options:
            return self.settings.router_retry_sleep_seconds
        return max(self.settings.router_retry_sleep_seconds, min(positive_options))

    def _cooldown_seconds_for_error(self, exc: ProviderError) -> float:
        retry_after = self._retry_after_from_message(str(exc))
        if retry_after is not None:
            return retry_after

        message = str(exc).lower()
        if exc.status_code == 429 or "rate limit" in message or "too many requests" in message:
            return self.settings.provider_cooldown_seconds
        if exc.status_code == 503 or "unavailable" in message or "high demand" in message:
            return self.settings.provider_unavailable_cooldown_seconds
        if "queue" in message:
            return self.settings.provider_cooldown_seconds
        if exc.status_code and exc.status_code >= 500:
            return self.settings.provider_cooldown_seconds
        return 0.0

    def _retry_after_from_message(self, message: str) -> Optional[float]:
        match = re.search(r"try again in\s+(\d+(?:\.\d+)?)\s*s", message, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _is_non_retryable_error(self, exc: ProviderError) -> bool:
        if exc.status_code is None:
            return False
        return 400 <= exc.status_code < 500 and exc.status_code != 429

    def _failure_rate(self, provider: str) -> float:
        successes = self.successes.get(provider, 0)
        failures = self.total_failures.get(provider, 0)
        total = successes + failures
        if total == 0:
            return 0.0
        return failures / total

    def _cost_rank(self, provider: str) -> int:
        return {
            "openrouter": self.settings.openrouter_cost_rank,
            "groq": self.settings.groq_cost_rank,
            "huggingface": self.settings.hf_cost_rank,
            "cerebras": self.settings.cerebras_cost_rank,
            "gemini": self.settings.gemini_cost_rank,
        }.get(provider, 100)

    def _order_index(self, provider: str) -> int:
        try:
            return self.settings.provider_order.index(provider)
        except ValueError:
            return 100

    def _cheapest_score(self, provider: str) -> tuple[float, float, int]:
        return (
            self._cooldown_remaining(provider),
            self._cost_rank(provider),
            self._order_index(provider),
        )

    def _stable_score(self, provider: str) -> tuple[float, float, int, float, int]:
        return (
            self._cooldown_remaining(provider),
            self._failure_rate(provider),
            self.failures.get(provider, 0),
            self.latency_ms.get(provider, 0.0),
            self._order_index(provider),
        )

    def _balanced_score(self, provider: str) -> tuple[float, float, float, int, int]:
        latency = self.latency_ms.get(provider, 1000.0)
        return (
            self._cooldown_remaining(provider),
            self._failure_rate(provider),
            latency / 1000.0,
            self._cost_rank(provider),
            self._order_index(provider),
        )
