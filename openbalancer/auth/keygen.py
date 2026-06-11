"""API key generation and hashing utilities."""

from __future__ import annotations

import hashlib
import secrets
from typing import Tuple


API_KEY_PREFIX = "obk_"
API_KEY_LENGTH = 32  # 32 hex chars = 128 bits of entropy


def generate_api_key() -> str:
    """Generate a new API key with the OpenBalancer prefix.
    
    Format: obk_<32-char-random-hex>
    Returns a plaintext key that should be shown to user once and stored securely.
    """
    random_bytes = secrets.token_hex(16)  # 16 bytes = 32 hex chars
    return f"{API_KEY_PREFIX}{random_bytes}"


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256 for secure storage.
    
    Args:
        key: The plaintext API key (e.g., "obk_abc123...")
        
    Returns:
        SHA-256 hex digest of the key
    """
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(plaintext_key: str, stored_hash: str) -> bool:
    """Verify a plaintext API key against its stored hash.
    
    Args:
        plaintext_key: The plaintext key from the request
        stored_hash: The stored hash from the database
        
    Returns:
        True if the key matches the hash, False otherwise
    """
    computed_hash = hash_api_key(plaintext_key)
    return computed_hash == stored_hash


def extract_api_key_from_header(auth_header: str | None) -> str | None:
    """Extract API key from Authorization header.
    
    Expected format: "Bearer obk_<key>"
    
    Args:
        auth_header: The Authorization header value
        
    Returns:
        The API key if valid format, None otherwise
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    key = parts[1]
    if not key.startswith(API_KEY_PREFIX):
        return None
    
    return key
