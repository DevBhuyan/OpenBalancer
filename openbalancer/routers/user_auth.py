"""User authentication API endpoints."""

from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from openbalancer.auth import (
    DatabaseManager,
    PasswordHasher,
    JWTHandler,
    User,
)


# Request/Response models
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "token_type": "bearer",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com"
            }
        }


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "created_at": "2024-01-15T10:30:00"
            }
        }


class MessageResponse(BaseModel):
    message: str


def get_db_manager() -> DatabaseManager:
    """Get the database manager instance. Should be injected by the app."""
    from openbalancer.app import db_manager
    return db_manager


# ---------------------------------------------------------------------------
# Router definition
# ---------------------------------------------------------------------------
# The file defines several endpoint functions using the ``@router`` decorator,
# but the ``router`` variable was never instantiated, leading to a
# ``NameError`` at import time. We create a dedicated ``APIRouter`` for the
# authentication routes with a ``/auth`` prefix and an appropriate tag.
router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_current_user(request: Request, db: DatabaseManager = Depends(get_db_manager)) -> User:
    """Extract and validate the current user from the Authorization header.

    The function validates the Bearer token, checks that a corresponding session
    exists, and then loads the ``User`` record by the ``user_id`` encoded in the
    JWT. It returns the ``User`` ORM instance (still attached to the session) so
    that downstream endpoints can safely access its attributes.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # Strip "Bearer "

    # Verify token and extract user_id
    user_id = JWTHandler.get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify session exists and is valid
    session = db.get_session_by_token(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load the user record
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def _create_user_session(user_id: str, email: str, db: DatabaseManager) -> TokenResponse:
    session_id = str(uuid.uuid4())
    token, expires_at = JWTHandler.create_access_token(
        data={"user_id": user_id, "email": email}
    )
    db.create_session(session_id, user_id, token, expires_at)
    return TokenResponse(access_token=token, user_id=user_id, email=email)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: DatabaseManager = Depends(get_db_manager)
) -> TokenResponse:
    """Create a user account and return an access token."""
    email = request.email.lower()
    if db.get_user_by_email(email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user_id = str(uuid.uuid4())
    password_hash = PasswordHasher.hash_password(request.password)
    db.create_user(user_id, email, password_hash)
    return _create_user_session(user_id, email, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: DatabaseManager = Depends(get_db_manager)
) -> TokenResponse:
    """Authenticate user and return access token.

    Args:
        request: Login request with email and password

    Returns:
        TokenResponse with access token and user info

    Raises:
        HTTPException: If email not found or password incorrect
    """
    # Get user by email
    user = db.get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    if not PasswordHasher.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create session/token
    return _create_user_session(user.id, user.email, db)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    request: Request = None,
    db: DatabaseManager = Depends(get_db_manager)
) -> MessageResponse:
    """Logout user by invalidating their session.

    Args:
        current_user: The authenticated user
        request: The HTTP request
        db: Database manager

    Returns:
        MessageResponse confirming logout
    """
    # Get token from header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        db.invalidate_session(token)

    return MessageResponse(message="Logout successful")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current authenticated user information.

    Args:
        current_user: The authenticated user

    Returns:
        UserResponse with user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at.isoformat()
    )
