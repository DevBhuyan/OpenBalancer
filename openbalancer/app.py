from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from openbalancer.models import ChatCompletionRequest
from openbalancer.providers import ProviderError
from openbalancer.router import LLMRouter
from openbalancer.settings import get_settings


settings = get_settings()
router = LLMRouter(settings)

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
async def health() -> dict[str, object]:
    providers = router.health()
    return {
        "status": "ok" if any(provider.healthy for provider in providers) else "degraded",
        "providers": [provider.model_dump() for provider in providers],
    }


@app.get("/v1/models")
async def models() -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {"id": settings.groq_model, "object": "model", "owned_by": "groq"},
            {"id": settings.openrouter_model, "object": "model", "owned_by": "openrouter"},
            {"id": settings.cerebras_model, "object": "model", "owned_by": "cerebras"},
            {"id": settings.gemini_model, "object": "model", "owned_by": "gemini"},
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    try:
        if request.stream:
            return StreamingResponse(router.stream_chat(request), media_type="text/event-stream")
        result = await router.chat(request)
        return result.payload
    except ProviderError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
