"""Custom exceptions for API key authentication."""

from __future__ import annotations


class InvalidAPIKeyError(Exception):
    """Raised when an API key is invalid, missing, or expired."""
    
    def __init__(self, message: str = "Invalid or missing API key"):
        self.message = message
        super().__init__(self.message)


class APIKeyNotFoundError(InvalidAPIKeyError):
    """Raised when an API key is not found in the database."""
    
    def __init__(self):
        super().__init__("API key not found")


class MissingAPIKeyError(InvalidAPIKeyError):
    """Raised when Authorization header is missing."""
    
    def __init__(self):
        super().__init__("Missing Authorization header")


class DatabaseError(Exception):
    """Raised when a database operation fails."""
    
    def __init__(self, message: str = "Database operation failed"):
        self.message = message
        super().__init__(self.message)
