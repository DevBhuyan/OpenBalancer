from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, list[dict[str, Any]]]] = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="auto")
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    stream: bool = False
    provider: Optional[str] = None
    routing: Literal["fallback", "fastest"] = "fallback"

    model_config = {"extra": "allow"}


class ProviderResult(BaseModel):
    provider: str
    payload: dict[str, Any]
    latency_ms: float


class ProviderHealth(BaseModel):
    name: str
    available: bool
    healthy: bool
    latency_ms: Optional[float] = None
    failures: int = 0
    last_error: Optional[str] = None
