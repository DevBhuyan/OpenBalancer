from __future__ import annotations

import time
from typing import Any

import httpx

from openbalancer.models import ChatCompletionRequest, ProviderResult
from openbalancer.providers.base import ProviderAdapter, ProviderError


class GeminiProvider(ProviderAdapter):
    name = "gemini"
    supports_streaming = False

    def __init__(self, *, api_key: str | None, default_model: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def chat(self, request: ChatCompletionRequest) -> ProviderResult:
        if not self.available:
            raise ProviderError(self.name, "missing API key")
        if request.stream:
            raise ProviderError(self.name, "Gemini streaming is not implemented in this MVP")

        model = self.default_model if request.model == "auto" else request.model
        body = self._to_gemini_body(request)
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"Content-Type": "application/json", "X-goog-api-key": self.api_key or ""},
                json=body,
            )
        latency_ms = (time.perf_counter() - started) * 1000
        if response.status_code >= 400:
            raise ProviderError(self.name, response.text, response.status_code)

        return ProviderResult(
            provider=self.name,
            payload=self._to_openai_response(request, response.json(), model),
            latency_ms=latency_ms,
        )

    def _to_gemini_body(self, request: ChatCompletionRequest) -> dict[str, Any]:
        contents: list[dict[str, Any]] = []
        system_parts: list[dict[str, str]] = []

        for message in request.messages:
            text = self._message_text(message.content)
            if message.role == "system":
                system_parts.append({"text": text})
                continue
            contents.append(
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": text}],
                }
            )

        body: dict[str, Any] = {"contents": contents}
        if system_parts:
            body["system_instruction"] = {"parts": system_parts}

        generation_config: dict[str, Any] = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.top_p is not None:
            generation_config["topP"] = request.top_p
        token_limit = request.max_completion_tokens or request.max_tokens
        if token_limit is not None:
            generation_config["maxOutputTokens"] = token_limit
        if generation_config:
            body["generationConfig"] = generation_config

        return body

    def _to_openai_response(self, request: ChatCompletionRequest, payload: dict[str, Any], model: str) -> dict[str, Any]:
        candidates = payload.get("candidates") or []
        first = candidates[0] if candidates else {}
        parts = first.get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts)
        usage = payload.get("usageMetadata", {})
        return {
            "id": f"chatcmpl-gemini-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": first.get("finishReason", "stop").lower(),
                }
            ],
            "usage": {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            },
            "openbalancer": {"provider": self.name},
        }

    def _message_text(self, content: str | list[dict[str, Any]] | None) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        return "\n".join(str(part.get("text", "")) for part in content if part.get("type") in {None, "text"})
