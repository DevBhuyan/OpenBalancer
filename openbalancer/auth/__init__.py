"""Authentication module for OpenBalancer API key management."""

from openbalancer.auth.bootstrap import bootstrap_api_key
from openbalancer.auth.db import APIKeyRecord, DatabaseManager, User, UserSession, UserAPIKey
from openbalancer.auth.exceptions import (
    APIKeyNotFoundError,
    DatabaseError,
    InvalidAPIKeyError,
    MissingAPIKeyError,
)
from openbalancer.auth.keygen import (
    generate_api_key,
    hash_api_key,
    verify_api_key,
)
from openbalancer.auth.middleware import APIKeyValidator, verify_api_key_dependency
from openbalancer.auth.user_auth import PasswordHasher, JWTHandler

__all__ = [
    "bootstrap_api_key",
    "APIKeyRecord",
    "DatabaseManager",
    "User",
    "UserSession",
    "UserAPIKey",
    "InvalidAPIKeyError",
    "MissingAPIKeyError",
    "APIKeyNotFoundError",
    "DatabaseError",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "APIKeyValidator",
    "verify_api_key_dependency",
    "PasswordHasher",
    "JWTHandler",
]
