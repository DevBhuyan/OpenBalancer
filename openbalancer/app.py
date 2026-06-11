from __future__ import annotations

from typing import Callable

from fastapi import (
    FastAPI,
    Depends,
    Request,
)
from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
    RedirectResponse
)
from fastapi.middleware.cors import CORSMiddleware

from openbalancer.models import ChatCompletionRequest
from openbalancer.providers import ProviderError
from openbalancer.router import LLMRouter
from openbalancer.settings import get_settings
from openbalancer.auth import (
    DatabaseManager,
    APIKeyValidator,
    bootstrap_api_key,
    verify_api_key_dependency,
)
from openbalancer.routers.user_auth import router as auth_router
from openbalancer.routers.dashboard import router as dashboard_router


settings = get_settings()
router = LLMRouter(settings)

# Initialize authentication system
db_manager = DatabaseManager(settings.auth_db_path)
db_manager.initialize()
api_key_validator = APIKeyValidator(
    db_manager, cache_ttl_seconds=settings.auth_cache_ttl_seconds)

# Create dependency function


async def verify_api_key(request: Request) -> dict:
    """Dependency for API key verification."""
    return await verify_api_key_dependency(request, api_key_validator)

# Optional dependency that returns empty dict if auth is disabled


async def optional_verify_api_key(request: Request) -> dict:
    """Optional dependency for API key verification."""
    if settings.require_api_key:
        return await verify_api_key_dependency(request, api_key_validator)
    return {}

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/"
)


# Add CORS middleware to allow dashboard to communicate with API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(dashboard_router)


# Bootstrap API key on startup
@app.on_event("startup")
async def startup_event():
    if settings.require_api_key:
        bootstrap_api_key(db_manager)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_logger(request: Request, call_next):
    """Log each incoming HTTP request and its response status.

    The middleware prints the HTTP method and path before the request is
    processed, then prints the resulting status code after the response is
    generated. This is useful for quick debugging and visibility during
    development.
    """
    print(f"{request.method} {request.url.path}")
    body = await request.body()
    # print(body.decode())
    response = await call_next(request)
    print(f" -> {response.status_code}")
    return response


@app.get("/docs", include_in_schema=False)
def redirect_to_root():
    return RedirectResponse(url="/")


@app.get("/health")
async def health() -> dict[str, object]:
    providers = router.health()
    return {
        "status": "ok" if any(provider.healthy for provider in providers) else "degraded",
        "providers": [provider.model_dump() for provider in providers],
    }


@app.get("/v1/models")
async def models(auth_info: dict = Depends(optional_verify_api_key)) -> dict[str, object]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.groq_model,
                "object": "model",
                "owned_by": "groq"
            },
            {
                "id": settings.openrouter_model,
                "object": "model",
                "owned_by": "openrouter"
            },
            {
                "id": settings.cerebras_model,
                "object": "model",
                "owned_by": "cerebras"
            },
            {
                "id": settings.hf_model,
                "object": "model",
                "owned_by": "huggingface"
            },
            {
                "id": settings.gemini_model,
                "object": "model",
                "owned_by": "gemini"
            },
            {
                "id": "auto",
                "object": "model",
                "owned_by": "openbalancer"
            },
            {
                "id": "auto:small",
                "object": "model",
                "owned_by": "openbalancer"
            },
            {
                "id": "auto:large",
                "object": "model",
                "owned_by": "openbalancer"
            },
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, auth_info: dict = Depends(verify_api_key)):
    try:
        if request.stream:
            return StreamingResponse(router.stream_chat(request), media_type="text/event-stream")
        result = await router.chat(request)
        return result.payload
    except ProviderError as exc:
        return JSONResponse(
            status_code=exc.status_code or 502,
            content={
                "error": {
                    "message": str(exc),
                    "type": "provider_error",
                    "provider": exc.provider,
                },
                "openbalancer": {
                    "provider": exc.provider,
                    **exc.metadata,
                },
            },
        )
