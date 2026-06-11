"""FastAPI middleware and dependencies for API key authentication."""

from __future__ import annotations

import time
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException, Request

from openbalancer.auth.db import DatabaseManager
from openbalancer.auth.exceptions import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
)
from openbalancer.auth.keygen import extract_api_key_from_header, hash_api_key, verify_api_key


class APIKeyValidator:
    """Validates API keys against the database with in-memory caching."""
    
    def __init__(self, db_manager: DatabaseManager, cache_ttl_seconds: int = 300):
        """Initialize the API key validator.
        
        Args:
            db_manager: DatabaseManager instance
            cache_ttl_seconds: Time-to-live for in-memory cache in seconds
        """
        self.db_manager = db_manager
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache: dict[str, tuple[bool, float]] = {}  # key_hash -> (is_valid, timestamp)
    
    def validate(self, api_key: str) -> dict:
        """Validate an API key and return provider credentials.
        
        Args:
            api_key: The plaintext API key from the request
            
        Returns:
            Dict containing:
              - key_hash: The hash of the key
              - provider_credentials: Dict of provider API keys
              
        Raises:
            InvalidAPIKeyError: If the key is invalid or not found
        """
        key_hash = hash_api_key(api_key)
        
        # Check cache first
        if key_hash in self.cache:
            is_valid, timestamp = self.cache[key_hash]
            if time.time() - timestamp < self.cache_ttl_seconds:
                if is_valid:
                    # Update last_used timestamp in DB (non-blocking)
                    self.db_manager.update_last_used(key_hash)
                    return {"key_hash": key_hash}
                else:
                    raise InvalidAPIKeyError("API key is invalid")
        
        # Cache miss or expired - query database
        record = self.db_manager.get_key_by_hash(key_hash)
        if not record:
            self.cache[key_hash] = (False, time.time())
            raise InvalidAPIKeyError("API key not found")
        
        # Valid key - cache it
        self.cache[key_hash] = (True, time.time())
        
        # Update last_used timestamp in DB (non-blocking)
        self.db_manager.update_last_used(key_hash)
        
        return {
            "key_hash": key_hash,
            "key_id": record.id,
            "provider_credentials": record.provider_credentials,
        }
    
    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self.cache.clear()
    
    def get_cache_size(self) -> int:
        """Get the current number of cached entries."""
        return len(self.cache)


async def verify_api_key_dependency(request: Request, validator: APIKeyValidator) -> dict:
    """FastAPI dependency for verifying API keys.
    
    Extracts the API key from the Authorization header and validates it.
    
    Args:
        request: The FastAPI request object
        validator: APIKeyValidator instance
        
    Returns:
        Dict with key validation info
        
    Raises:
        HTTPException: 401 Unauthorized if key is missing or invalid
    """
    auth_header = request.headers.get("authorization")
    
    # Extract key from header
    api_key = extract_api_key_from_header(auth_header)
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Use 'Authorization: Bearer <api_key>'",
        )
    
    # Validate key against database
    try:
        result = validator.validate(api_key)
        return result
    except InvalidAPIKeyError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e.message),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication",
        )
