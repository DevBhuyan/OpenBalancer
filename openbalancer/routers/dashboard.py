"""Dashboard API endpoints for API key and provider management."""

from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel

from openbalancer.auth import (
    DatabaseManager,
    User,
    UserAPIKey,
    generate_api_key,
    hash_api_key,
)
from openbalancer.routers.user_auth import get_current_user, get_db_manager
from openbalancer.user_router import router_for_credentials
from openbalancer.providers import ProviderError


# Request/Response models
class ProviderKeyRequest(BaseModel):
    """Request model for updating provider API keys."""
    provider: str
    api_key: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "groq",
                "api_key": "gsk_xxxxx..."
            }
        }


class ProviderCredentialsRequest(BaseModel):
    """Request model for updating all provider credentials at once."""
    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "groq_api_key": "gsk_xxxxx...",
                "openrouter_api_key": "sk-xxxxx...",
                "cerebras_api_key": "csk_xxxxx...",
                "gemini_api_key": "AIzaSy...",
                "huggingface_api_key": "hf_xxxxx..."
            }
        }


class ProviderResponse(BaseModel):
    """Response model for a provider."""
    name: str
    display_name: str
    has_api_key: bool
    healthy: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "groq",
                "display_name": "Groq",
                "has_api_key": True,
                "healthy": True
            }
        }


class OpenBalancerKeyResponse(BaseModel):
    """Response model for OpenBalancer API key."""
    api_key: str
    created_at: str
    last_used: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "obk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "created_at": "2024-01-15T10:30:00",
                "last_used": None
            }
        }


class MessageResponse(BaseModel):
    message: str


class ProviderCredentialsResponse(MessageResponse):
    api_key: Optional[str] = None


# Constants
AVAILABLE_PROVIDERS = {
    "groq": {"display_name": "Groq", "env_var": "GROQ_API_KEY"},
    "openrouter": {"display_name": "OpenRouter", "env_var": "OPENROUTER_API_KEY"},
    "cerebras": {"display_name": "Cerebras", "env_var": "CEREBRAS_API_KEY"},
    "gemini": {"display_name": "Google Gemini", "env_var": "GEMINI_API_KEY"},
    "huggingface": {"display_name": "Hugging Face", "env_var": "HF_API_KEY"},
}


# Create router
router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/providers", response_model=list[ProviderResponse])
async def get_providers(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager),
) -> list[ProviderResponse]:
    """Get list of available providers with connection status for the current user."""
    provider_creds: dict[str, str] = {}
    user_api_keys = db.get_user_api_keys(current_user.id)
    if user_api_keys:
        provider_creds = json.loads(user_api_keys[0].provider_credentials or "{}")

    user_router = router_for_credentials(provider_creds or None)
    health_map = {item.name: item for item in user_router.health()}

    providers = []
    for provider_key, provider_info in AVAILABLE_PROVIDERS.items():
        env_var = provider_info["env_var"]
        health = health_map.get(provider_key)
        providers.append(ProviderResponse(
            name=provider_key,
            display_name=provider_info["display_name"],
            has_api_key=bool(provider_creds.get(env_var)),
            healthy=health.healthy if health else None,
        ))
    return providers


@router.get("/user/provider-keys")
async def get_user_provider_keys(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager)
) -> dict:
    """Get user's provider API keys (masked for security).
    
    Args:
        current_user: The authenticated user
        db: Database manager
        
    Returns:
        Dictionary with provider API key information (masked values)
    """
    # Get user's API key record
    user_api_keys = db.get_user_api_keys(current_user.id)
    
    if not user_api_keys:
        return {"providers": {}}
    
    # Get the most recent API key
    user_api_key = user_api_keys[0]
    provider_creds = json.loads(user_api_key.provider_credentials)
    
    # Mask the keys for security (show only first/last few characters)
    masked_creds = {}
    for provider, api_key in provider_creds.items():
        if api_key:
            if len(api_key) > 8:
                masked = f"{api_key[:4]}...{api_key[-4:]}"
            else:
                masked = "***"
            masked_creds[provider] = masked
    
    return {
        "providers": masked_creds,
        "openbalancer_key_created": user_api_key.created_at.isoformat(),
        "openbalancer_key_last_used": user_api_key.last_used.isoformat() if user_api_key.last_used else None,
    }


@router.post("/user/provider-keys", response_model=ProviderCredentialsResponse)
async def update_user_provider_keys(
    request: ProviderCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager)
) -> ProviderCredentialsResponse:
    """Update user's provider API keys.
    
    Args:
        request: Provider credentials request
        current_user: The authenticated user
        db: Database manager
        
    Returns:
        MessageResponse confirming update
    """
    # Convert request to dict, filtering out None values
    provider_creds = {
        "GROQ_API_KEY": request.groq_api_key,
        "OPENROUTER_API_KEY": request.openrouter_api_key,
        "CEREBRAS_API_KEY": request.cerebras_api_key,
        "GEMINI_API_KEY": request.gemini_api_key,
        "HF_API_KEY": request.huggingface_api_key,
    }
    
    # Remove None values
    provider_creds = {k: v for k, v in provider_creds.items() if v is not None}
    
    # Check if user already has an API key
    user_api_keys = db.get_user_api_keys(current_user.id)
    api_key = None
    
    if user_api_keys:
        # Update existing credentials
        user_api_key = user_api_keys[0]
        api_key = user_api_key.openbalancer_api_key
        key_hash = None
        if not api_key:
            api_key = generate_api_key()
            key_hash = hash_api_key(api_key)
        db.update_user_provider_credentials(
            current_user.id,
            provider_creds,
            key_hash=key_hash,
            openbalancer_api_key=api_key,
            merge=True,
        )
    else:
        # Create new API key for user
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_id = str(uuid.uuid4())
        db.create_user_api_key(
            key_id,
            current_user.id,
            key_hash,
            provider_creds,
            openbalancer_api_key=api_key,
        )
    
    return ProviderCredentialsResponse(
        message="Provider credentials updated successfully",
        api_key=api_key,
    )


@router.get("/user/openbalancer-key", response_model=OpenBalancerKeyResponse)
async def get_user_openbalancer_key(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager)
) -> OpenBalancerKeyResponse:
    """Get user's OpenBalancer API key.
    
    Args:
        current_user: The authenticated user
        db: Database manager
        
    Returns:
        OpenBalancerKeyResponse with the user's API key
        
    Raises:
        HTTPException: If user doesn't have an API key yet
    """
    user_api_keys = db.get_user_api_keys(current_user.id)
    
    if not user_api_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have an OpenBalancer API key yet. Please add provider credentials first.",
        )
    
    # Get the most recent API key
    user_api_key = user_api_keys[0]
    
    api_key = user_api_key.openbalancer_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user key was created before key retrieval was supported. Please save provider credentials again to rotate it.",
        )
    
    return OpenBalancerKeyResponse(
        api_key=api_key,
        created_at=user_api_key.created_at.isoformat(),
        last_used=user_api_key.last_used.isoformat() if user_api_key.last_used else None,
    )


@router.post("/user/openbalancer-key/regenerate", response_model=OpenBalancerKeyResponse)
async def regenerate_openbalancer_key(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager),
) -> OpenBalancerKeyResponse:
    """Revoke the current OpenBalancer key and issue a fresh one."""
    user_api_keys = db.get_user_api_keys(current_user.id)
    if not user_api_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have an OpenBalancer API key yet. Please add provider credentials first.",
        )

    new_key = generate_api_key()
    new_hash = hash_api_key(new_key)
    user_api_key = db.regenerate_user_openbalancer_key(
        current_user.id,
        new_hash,
        new_key,
    )
    if not user_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User does not have an OpenBalancer API key yet.",
        )

    from openbalancer.app import api_key_validator
    api_key_validator.clear_cache()

    return OpenBalancerKeyResponse(
        api_key=new_key,
        created_at=user_api_key.created_at.isoformat(),
        last_used=None,
    )


@router.get("/providers/health")
async def get_provider_health(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """Get health status of providers using the current user's credentials."""
    provider_creds: dict[str, str] = {}
    user_api_keys = db.get_user_api_keys(current_user.id)
    if user_api_keys:
        provider_creds = json.loads(user_api_keys[0].provider_credentials or "{}")

    user_router = router_for_credentials(provider_creds or None)
    providers = []
    for item in user_router.health():
        status_label = "healthy" if item.healthy else "unavailable"
        if item.available and not item.healthy:
            status_label = "degraded"
        providers.append({
            "name": item.name,
            "status": status_label,
            "available": item.available,
        })

    overall = "ok" if any(p["status"] == "healthy" for p in providers) else "degraded"
    return {"status": overall, "providers": providers}


@router.get("/models")
async def get_user_models(
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager),
    max_per_provider: int = 20,
) -> dict:
    """List models available to the current user, grouped by provider."""
    provider_creds: dict[str, str] = {}
    user_api_keys = db.get_user_api_keys(current_user.id)
    if user_api_keys:
        provider_creds = json.loads(user_api_keys[0].provider_credentials or "{}")

    user_router = router_for_credentials(provider_creds or None)
    from openbalancer.app import FALLBACK_PROVIDER_MODELS

    grouped: dict[str, list[str]] = {}
    for provider_name, provider in user_router.providers.items():
        if not provider.available:
            continue
        model_ids: list[str] = []
        try:
            model_ids = await provider.list_models()
        except ProviderError:
            model_ids = []
        if not model_ids:
            model_ids = FALLBACK_PROVIDER_MODELS.get(provider_name, [])
        grouped[provider_name] = model_ids[:max_per_provider]

    return {"providers": grouped}


@router.get("/quickstart-code")
async def get_quickstart_code(
    language: str = "python",
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager)
) -> dict:
    """Get quickstart code snippets in various languages.
    
    Args:
        language: Programming language (python, typescript, curl, etc.)
        current_user: The authenticated user
        db: Database manager
        
    Returns:
        Dictionary with code snippet for the requested language
    """
    user_api_keys = db.get_user_api_keys(current_user.id)
    
    if not user_api_keys:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Please add provider credentials first",
        )
    
    api_key = user_api_keys[0].openbalancer_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user key was created before key retrieval was supported. Please save provider credentials again to rotate it.",
        )
    
    snippets = {
        "curl": f'''curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer {api_key}" \\
  -d '{{
    "model": "auto:small",
    "messages": [
      {{"role": "user", "content": "Hello!"}}
    ]
  }}'
''',
        "python": f'''import requests

headers = {{
    "Authorization": "Bearer {api_key}",
    "Content-Type": "application/json"
}}

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers=headers,
    json={{
        "model": "auto:small",
        "messages": [
            {{"role": "user", "content": "Hello!"}}
        ]
    }}
)

print(response.json())
''',
        "python-openai": f'''from openai import OpenAI

client = OpenAI(
    api_key="{api_key}",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="auto:small",
    messages=[
        {{"role": "user", "content": "Hello!"}}
    ]
)

print(response.choices[0].message.content)
''',
        "typescript": f'''import fetch from "node-fetch";

const apiKey = "{api_key}";

const response = await fetch("http://localhost:8000/v1/chat/completions", {{
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
console.log(data);
'''
    }
    
    return {
        "language": language,
        "code": snippets.get(language, snippets["python"]),
        "available_languages": list(snippets.keys())
    }
