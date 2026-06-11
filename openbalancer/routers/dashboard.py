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
async def get_providers(current_user: User = Depends(get_current_user)) -> list[ProviderResponse]:
    """Get list of available providers with their connection status.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        List of ProviderResponse with provider information
    """
    # For now, return hardcoded list of providers
    # In the future, this could be fetched from /health endpoint
    providers = []
    for provider_key, provider_info in AVAILABLE_PROVIDERS.items():
        providers.append(ProviderResponse(
            name=provider_key,
            display_name=provider_info["display_name"],
            has_api_key=False,  # Will be updated when we check user's credentials
            healthy=None  # Will be fetched from /health endpoint
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


@router.post("/user/provider-keys")
async def update_user_provider_keys(
    request: ProviderCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db_manager)
) -> MessageResponse:
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
    
    if user_api_keys:
        # Update existing credentials
        db.update_user_provider_credentials(current_user.id, provider_creds)
    else:
        # Create new API key for user
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_id = str(uuid.uuid4())
        db.create_user_api_key(key_id, current_user.id, key_hash, provider_creds)
    
    return MessageResponse(message="Provider credentials updated successfully")


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
    
    # Get the plaintext key from the request (this would normally be stored in a secure way)
    # For now, we'll generate a new one if needed
    # In production, you would retrieve this from a secure vault
    api_key = generate_api_key()  # This would be the actual stored key
    
    return OpenBalancerKeyResponse(
        api_key=api_key,  # In production, retrieve the actual key
        created_at=user_api_key.created_at.isoformat(),
        last_used=user_api_key.last_used.isoformat() if user_api_key.last_used else None,
    )


@router.get("/providers/health")
async def get_provider_health(current_user: User = Depends(get_current_user)) -> dict:
    """Get health status of all providers.
    
    This endpoint calls the main /health endpoint and returns provider status.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        Dictionary with provider health information
    """
    # In a real implementation, this would call the /health endpoint
    # For now, return a placeholder
    return {
        "status": "ok",
        "providers": [
            {"name": "groq", "status": "healthy"},
            {"name": "openrouter", "status": "healthy"},
            {"name": "cerebras", "status": "healthy"},
            {"name": "gemini", "status": "degraded"},
            {"name": "huggingface", "status": "healthy"},
        ]
    }


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
    
    api_key = "obk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Placeholder
    
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
