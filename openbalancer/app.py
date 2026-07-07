from __future__ import annotations

from typing import Callable

from fastapi import (
    FastAPI,
    Depends,
    Request,
    Query,
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
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from openbalancer.routers.user_auth import router as auth_router
from openbalancer.routers.dashboard import router as dashboard_router
from openbalancer.user_router import router_for_credentials
from openbalancer.web.routes import router as web_router


settings = get_settings()
router = LLMRouter(settings)


def router_for_auth(auth_info: dict) -> LLMRouter:
    """Use user-provided credentials for authenticated BYOK requests."""
    return router_for_credentials(auth_info.get("provider_credentials"))

# Initialize authentication system
db_manager = DatabaseManager(settings.auth_db_path)
db_manager.initialize()
api_key_validator = APIKeyValidator(
    db_manager, cache_ttl_seconds=settings.auth_cache_ttl_seconds)


FALLBACK_PROVIDER_MODELS: dict[str, list[str]] = {
    "groq": [
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "qwen/qwen3-32b",
    ],
    "openrouter": [
        "openai/gpt-oss-120b",
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "meta-llama/llama-3.3-70b-instruct",
        "qwen/qwen-2.5-72b-instruct",
        "mistralai/mistral-7b-instruct:free",
    ],
    "cerebras": [
        "gpt-oss-120b",
        "llama3.1-8b",
        "llama-3.3-70b",
        "qwen-3-32b",
    ],
    "huggingface": [
        "openai/gpt-oss-120b:fastest",
        "Qwen/Qwen3-4B-Thinking-2507:fastest",
        "Qwen/Qwen2.5-72B-Instruct:fastest",
        "meta-llama/Llama-3.1-8B-Instruct:fastest",
        "mistralai/Mistral-7B-Instruct-v0.3:fastest",
    ],
    "gemini": [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
    ],
}

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
    docs_url="/docs"
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
app.include_router(web_router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
brand_dir = Path(__file__).resolve().parent.parent / "favicon_io"
app.mount("/brand", StaticFiles(directory=str(brand_dir)), name="brand")


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


@app.get("/", include_in_schema=False)
def redirect_to_dashboard():
    return RedirectResponse(url="/dashboard", status_code=307)


@app.get("/health")
async def health() -> dict[str, object]:
    providers = router.health()
    return {
        "status": "ok" if any(provider.healthy for provider in providers) else "degraded",
        "providers": [provider.model_dump() for provider in providers],
    }


@app.get("/v1/models")
async def models(
    auth_info: dict = Depends(optional_verify_api_key),
    max_per_provider: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    request_router = router_for_auth(auth_info)
    data: list[dict[str, object]] = [
        {
            "id": "auto",
            "object": "model",
            "owned_by": "openbalancer",
            "openbalancer": {"type": "routing_alias", "profile": "default"},
        },
        {
            "id": "auto:small",
            "object": "model",
            "owned_by": "openbalancer",
            "openbalancer": {"type": "routing_alias", "profile": "small"},
        },
        {
            "id": "auto:large",
            "object": "model",
            "owned_by": "openbalancer",
            "openbalancer": {"type": "routing_alias", "profile": "large"},
        },
    ]

    seen = {model["id"] for model in data}
    for provider_name, provider in request_router.providers.items():
        if not provider.available:
            continue

        source = "live"
        try:
            model_ids = await provider.list_models()
        except ProviderError:
            source = "fallback"
            model_ids = []

        if not model_ids:
            source = "fallback"
            model_ids = FALLBACK_PROVIDER_MODELS.get(provider_name, [])

        for raw_model_id in _unique_model_ids(model_ids)[:max_per_provider]:
            qualified_id = f"{provider_name}/{raw_model_id}"
            if qualified_id in seen:
                continue
            seen.add(qualified_id)
            data.append(
                {
                    "id": qualified_id,
                    "object": "model",
                    "owned_by": provider_name,
                    "openbalancer": {
                        "provider": provider_name,
                        "provider_model": raw_model_id,
                        "source": source,
                    },
                }
            )

    return {"object": "list", "data": data}


def _unique_model_ids(model_ids: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for model_id in model_ids:
        if not model_id or model_id in seen:
            continue
        seen.add(model_id)
        unique.append(model_id)
    return unique


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, auth_info: dict = Depends(verify_api_key)):
    request_router = router_for_auth(auth_info)
    try:
        if request.stream:
            return StreamingResponse(request_router.stream_chat(request), media_type="text/event-stream")
        result = await request_router.chat(request)
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
