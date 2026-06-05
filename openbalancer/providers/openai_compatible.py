from __future__ import annotations

import time
from collections.abc import AsyncIterator

import httpx

from openbalancer.models import ChatCompletionRequest, ProviderResult
from openbalancer.providers.base import ProviderAdapter, ProviderError, request_body


class OpenAICompatibleProvider(ProviderAdapter):
    supports_streaming = True

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str | None,
        default_model: str,
        timeout_seconds: float,
        small_model: str | None = None,
        large_model: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_profiles = {
            "default": default_model,
            "small": small_model or default_model,
            "large": large_model or default_model,
        }
        self.timeout_seconds = timeout_seconds
        self.extra_headers = extra_headers or {}

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    async def chat(self, request: ChatCompletionRequest) -> ProviderResult:
        if not self.available:
            raise ProviderError(self.name, "missing API key")

        body = request_body(request, self.model_profiles)
        body["stream"] = False
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            raise ProviderError(self.name, response.text, response.status_code)

        payload = response.json()
        payload.setdefault("openbalancer", {})["provider"] = self.name
        return ProviderResult(provider=self.name, payload=payload, latency_ms=latency_ms)

    async def stream_chat(self, request: ChatCompletionRequest) -> AsyncIterator[bytes]:
        if not self.available:
            raise ProviderError(self.name, "missing API key")

        body = request_body(request, self.model_profiles)
        body["stream"] = True
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            ) as response:
                if response.status_code >= 400:
                    text = await response.aread()
                    raise ProviderError(self.name, text.decode("utf-8", errors="replace"), response.status_code)
                async for chunk in response.aiter_bytes():
                    yield chunk
