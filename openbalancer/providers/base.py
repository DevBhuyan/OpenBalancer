from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from openbalancer.models import ChatCompletionRequest, ProviderResult


class ProviderError(Exception):
    def __init__(self, provider: str, message: str, status_code: int | None = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class ProviderAdapter(ABC):
    name: str
    supports_streaming: bool = False

    @property
    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def chat(self, request: ChatCompletionRequest) -> ProviderResult:
        raise NotImplementedError

    async def stream_chat(self, request: ChatCompletionRequest) -> AsyncIterator[bytes]:
        raise ProviderError(self.name, f"{self.name} does not support streaming in this MVP")


def request_body(request: ChatCompletionRequest, model: str) -> dict[str, Any]:
    body = request.model_dump(exclude={"provider", "routing"}, exclude_none=True)
    body["model"] = model if request.model == "auto" else request.model
    if "max_completion_tokens" not in body and request.max_tokens is not None:
        body["max_completion_tokens"] = request.max_tokens
    return body
