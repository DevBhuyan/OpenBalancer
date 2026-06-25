"""User authentication utilities for handling passwords and JWT tokens."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt

# JWT configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Should be set via environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class PasswordHasher:
    """Utility class for password hashing and verification."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hash of the password
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        return hashed_bytes.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a bcrypt hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Bcrypt hash to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False


class JWTHandler:
    """Utility class for creating and verifying JWT tokens."""
    
    @staticmethod
    def create_access_token(
        data: dict,
        secret_key: str = SECRET_KEY,
        algorithm: str = ALGORITHM,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, datetime]:
        """Create a JWT access token.
        
        Args:
            data: Data to encode in the token
            secret_key: Secret key for signing
            algorithm: Algorithm to use for signing
            expires_delta: Custom expiration time delta
            
        Returns:
            Tuple of (token, expiration_datetime)
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
        return encoded_jwt, expire
    
    @staticmethod
    def verify_token(
        token: str,
        secret_key: str = SECRET_KEY,
        algorithm: str = ALGORITHM
    ) -> Optional[dict]:
        """Verify a JWT token and return decoded data.
        
        Args:
            token: JWT token to verify
            secret_key: Secret key for verification
            algorithm: Algorithm used for signing
            
        Returns:
            Decoded token data if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def get_user_id_from_token(token: str) -> Optional[str]:
        """Extract user_id from a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            User ID if token is valid, None otherwise
        """
        payload = JWTHandler.verify_token(token)
        if payload and "user_id" in payload:
            return payload["user_id"]
        return None
