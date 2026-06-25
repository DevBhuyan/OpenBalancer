"""Server-rendered web dashboard for OpenBalancer."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from openbalancer.auth import DatabaseManager, PasswordHasher, User
from openbalancer.auth.keygen import generate_api_key, hash_api_key
from openbalancer.routers.dashboard import (
    AVAILABLE_PROVIDERS,
    ProviderCredentialsRequest,
)
from openbalancer.routers.user_auth import JWTHandler, get_db_manager
from openbalancer.user_router import router_for_credentials


SESSION_COOKIE = "ob_session"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _render(template_name: str, context: dict) -> HTMLResponse:
    template = jinja_env.get_template(template_name)
    return HTMLResponse(template.render(**context))

router = APIRouter(tags=["web-dashboard"])


def _get_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return request.cookies.get(SESSION_COOKIE)


def _get_user(request: Request, db: DatabaseManager) -> Optional[User]:
    token = _get_token(request)
    if not token:
        return None
    user_id = JWTHandler.get_user_id_from_token(token)
    if not user_id:
        return None
    session = db.get_session_by_token(token)
    if not session:
        return None
    return db.get_user_by_id(user_id)


def _require_user(request: Request, db: DatabaseManager = Depends(get_db_manager)) -> User:
    user = _get_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def _set_session(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )


def _clear_session(response: RedirectResponse) -> None:
    response.delete_cookie(SESSION_COOKIE)


def _user_provider_creds(db: DatabaseManager, user_id: str) -> dict[str, str]:
    user_api_keys = db.get_user_api_keys(user_id)
    if not user_api_keys:
        return {}
    return json.loads(user_api_keys[0].provider_credentials or "{}")


def _masked_provider_keys(provider_creds: dict[str, str]) -> dict[str, str]:
    masked: dict[str, str] = {}
    for env_var, api_key in provider_creds.items():
        if not api_key:
            continue
        if len(api_key) > 8:
            masked[env_var] = f"{api_key[:4]}...{api_key[-4:]}"
        else:
            masked[env_var] = "***"
    return masked


def _quickstart_snippets(api_key: str, base_url: str) -> dict[str, str]:
    return {
        "curl": f"""curl -X POST {base_url}/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {api_key}" \\
  -d '{{
    "model": "auto:small",
    "messages": [
      {{"role": "user", "content": "Hello!"}}
    ]
  }}'""",
        "python": f"""import requests

headers = {{
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
}}

response = requests.post(
    "{base_url}/v1/chat/completions",
    headers=headers,
    json={{
        "model": "auto:small",
        "messages": [
            {{"role": "user", "content": "Hello!"}}
        ]
    }}
)

print(response.json())""",
        "python-openai": f"""from openai import OpenAI

client = OpenAI(
    api_key="{api_key}",
    base_url="{base_url}/v1"
)

response = client.chat.completions.create(
    model="auto:small",
    messages=[
        {{"role": "user", "content": "Hello!"}}
    ]
)

print(response.choices[0].message.content)""",
        "typescript": f"""const apiKey = "{api_key}";

const response = await fetch("{base_url}/v1/chat/completions", {{
  method: "POST",
  headers: {{
    "Content-Type": "application/json",
    "Authorization": `Bearer ${{apiKey}}`
  }},
  body: JSON.stringify({{
    model: "auto:small",
    messages: [
      {{ role: "user", content: "Hello!" }}
    ]
  }})
}});

const data = await response.json();
console.log(data);""",
    }


async def _models_for_user(db: DatabaseManager, user_id: str) -> dict[str, list[str]]:
    provider_creds = _user_provider_creds(db, user_id)
    user_router = router_for_credentials(provider_creds or None)
    from openbalancer.app import FALLBACK_PROVIDER_MODELS
    from openbalancer.providers import ProviderError

    grouped: dict[str, list[str]] = {}
    for provider_name, provider in user_router.providers.items():
        if not provider.available:
            continue
        try:
            model_ids = await provider.list_models()
        except ProviderError:
            model_ids = []
        if not model_ids:
            model_ids = FALLBACK_PROVIDER_MODELS.get(provider_name, [])
        grouped[provider_name] = model_ids[:20]
    return grouped


def _dashboard_context(
    request: Request,
    user: User,
    db: DatabaseManager,
    *,
    message: str = "",
    error: str = "",
    language: str = "python",
) -> dict:
    provider_creds = _user_provider_creds(db, user.id)
    user_api_keys = db.get_user_api_keys(user.id)
    openbalancer_key = user_api_keys[0].openbalancer_api_key if user_api_keys else None
    key_created = user_api_keys[0].created_at.isoformat() if user_api_keys else None
    key_last_used = (
        user_api_keys[0].last_used.isoformat()
        if user_api_keys and user_api_keys[0].last_used
        else None
    )

    user_router = router_for_credentials(provider_creds or None)
    health_items = []
    for item in user_router.health():
        status_label = "healthy" if item.healthy else "unavailable"
        if item.available and not item.healthy:
            status_label = "degraded"
        health_items.append({
            "name": item.name,
            "display_name": AVAILABLE_PROVIDERS.get(item.name, {}).get("display_name", item.name),
            "status": status_label,
            "has_api_key": bool(provider_creds.get(
                AVAILABLE_PROVIDERS.get(item.name, {}).get("env_var", "")
            )),
        })

    base_url = str(request.base_url).rstrip("/")
    snippets = _quickstart_snippets(openbalancer_key, base_url) if openbalancer_key else {}
    selected_snippet = snippets.get(language, snippets.get("python", ""))

    return {
        "request": request,
        "user": user,
        "message": message,
        "error": error,
        "providers": health_items,
        "masked_keys": _masked_provider_keys(provider_creds),
        "openbalancer_key": openbalancer_key,
        "key_created": key_created,
        "key_last_used": key_last_used,
        "language": language,
        "languages": ["curl", "python", "python-openai", "typescript"],
        "quickstart_code": selected_snippet,
        "has_openbalancer_key": bool(openbalancer_key),
    }


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, db: DatabaseManager = Depends(get_db_manager)):
    user = _get_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return _render("login.html", {"request": request, "error": ""})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: DatabaseManager = Depends(get_db_manager)):
    user = _get_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return _render("login.html", {"request": request, "error": ""})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: DatabaseManager = Depends(get_db_manager),
):
    user = db.get_user_by_email(email.lower())
    if not user or not PasswordHasher.verify_password(password, user.password_hash):
        return _render(
            "login.html",
            {"request": request, "error": "Invalid email or password"},
        )

    token, expires_at = JWTHandler.create_access_token(
        data={"user_id": user.id, "email": user.email}
    )
    db.create_session(str(uuid.uuid4()), user.id, token, expires_at)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session(response, token)
    return response


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: DatabaseManager = Depends(get_db_manager),
):
    normalized_email = email.lower()
    if db.get_user_by_email(normalized_email):
        return _render(
            "login.html",
            {"request": request, "error": "Email is already registered"},
        )

    user_id = str(uuid.uuid4())
    password_hash = PasswordHasher.hash_password(password)
    db.create_user(user_id, normalized_email, password_hash)

    token, expires_at = JWTHandler.create_access_token(
        data={"user_id": user_id, "email": normalized_email}
    )
    db.create_session(str(uuid.uuid4()), user_id, token, expires_at)
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    _set_session(response, token)
    return response


@router.post("/logout")
async def logout_submit(
    request: Request,
    db: DatabaseManager = Depends(get_db_manager),
):
    token = _get_token(request)
    if token:
        db.invalidate_session(token)
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    _clear_session(response)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    language: str = "python",
    msg: str = "",
    err: str = "",
    db: DatabaseManager = Depends(get_db_manager),
):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    context = _dashboard_context(
        request,
        user,
        db,
        message=msg,
        error=err,
        language=language if language in {"curl", "python", "python-openai", "typescript"} else "python",
    )
    models = await _models_for_user(db, user.id)
    context["models_by_provider"] = models
    return _render("dashboard.html", context)


@router.post("/dashboard/provider-keys")
async def save_provider_keys(
    request: Request,
    groq_api_key: str = Form(""),
    openrouter_api_key: str = Form(""),
    cerebras_api_key: str = Form(""),
    gemini_api_key: str = Form(""),
    huggingface_api_key: str = Form(""),
    db: DatabaseManager = Depends(get_db_manager),
):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    payload = ProviderCredentialsRequest(
        groq_api_key=groq_api_key or None,
        openrouter_api_key=openrouter_api_key or None,
        cerebras_api_key=cerebras_api_key or None,
        gemini_api_key=gemini_api_key or None,
        huggingface_api_key=huggingface_api_key or None,
    )
    provider_creds = {
        "GROQ_API_KEY": payload.groq_api_key,
        "OPENROUTER_API_KEY": payload.openrouter_api_key,
        "CEREBRAS_API_KEY": payload.cerebras_api_key,
        "GEMINI_API_KEY": payload.gemini_api_key,
        "HF_API_KEY": payload.huggingface_api_key,
    }
    provider_creds = {k: v for k, v in provider_creds.items() if v}

    if not provider_creds:
        return RedirectResponse(
            url="/dashboard?err=Please+enter+at+least+one+provider+API+key",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user_api_keys = db.get_user_api_keys(user.id)
    api_key = None
    if user_api_keys:
        api_key = user_api_keys[0].openbalancer_api_key
        key_hash = None
        if not api_key:
            api_key = generate_api_key()
            key_hash = hash_api_key(api_key)
        db.update_user_provider_credentials(
            user.id,
            provider_creds,
            key_hash=key_hash,
            openbalancer_api_key=api_key,
            merge=True,
        )
    else:
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        db.create_user_api_key(
            str(uuid.uuid4()),
            user.id,
            key_hash,
            provider_creds,
            openbalancer_api_key=api_key,
        )

    return RedirectResponse(
        url="/dashboard?msg=Provider+credentials+saved+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/dashboard/regenerate-key")
async def regenerate_key(
    request: Request,
    db: DatabaseManager = Depends(get_db_manager),
):
    user = _get_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    user_api_keys = db.get_user_api_keys(user.id)
    if not user_api_keys:
        return RedirectResponse(
            url="/dashboard?err=Add+provider+credentials+before+regenerating+a+key",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    new_key = generate_api_key()
    new_hash = hash_api_key(new_key)
    db.regenerate_user_openbalancer_key(user.id, new_hash, new_key)

    from openbalancer.app import api_key_validator
    api_key_validator.clear_cache()

    return RedirectResponse(
        url="/dashboard?msg=OpenBalancer+API+key+regenerated",
        status_code=status.HTTP_303_SEE_OTHER,
    )
