"""Database models and initialization for API key management."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, String, Text, Boolean, create_engine, inspect, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker

from openbalancer.auth.exceptions import DatabaseError


Base = declarative_base()


class User(Base):
    """SQLAlchemy model for storing user accounts."""
    
    __tablename__ = "users"
    
    # Columns
    id = Column(String(36), primary_key=True)  # UUID
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class UserSession(Base):
    """SQLAlchemy model for storing user sessions."""
    
    __tablename__ = "user_sessions"
    
    # Columns
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True, index=True)  # JWT token
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_valid = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"


class UserAPIKey(Base):
    """SQLAlchemy model linking users to their OpenBalancer API keys."""
    
    __tablename__ = "user_api_keys"
    
    # Columns
    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    openbalancer_key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 hash
    openbalancer_api_key = Column(String(64), nullable=True)  # Plaintext key for local MVP/dashboard display
    provider_credentials = Column(Text, nullable=False)  # JSON string with provider API keys
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self) -> str:
        return f"<UserAPIKey(id={self.id}, user_id={self.user_id})>"


class APIKeyRecord(Base):
    """SQLAlchemy model for storing API keys and their provider credentials."""
    
    __tablename__ = "api_keys"
    
    # Columns
    id = Column(String(36), primary_key=True)  # UUID
    key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA-256 hash
    provider_credentials = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    enabled = Column(String(1), nullable=False, default="Y")  # Y or N
    description = Column(String(255), nullable=True)  # For future dashboard
    
    def __repr__(self) -> str:
        return f"<APIKeyRecord(id={self.id}, created_at={self.created_at})>"


class DatabaseManager:
    """Manages database connections and operations for API key storage."""
    
    def __init__(self, db_path: str):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file or PostgreSQL connection string
                     Examples: 
                       - "sqlite:////absolute/path/to/openbalancer.db"
                       - "postgresql://user:password@localhost/openbalancer"
        """
        self.db_path = db_path
        self.engine = None
        self.SessionLocal = None
    
    def initialize(self) -> None:
        """Initialize database connection and create tables if needed."""
        try:
            # For SQLite, create directory if it doesn't exist
            if self.db_path.startswith("sqlite://"):
                db_file_path = self.db_path.replace("sqlite:///", "")
                db_dir = "/".join(db_file_path.split("/")[:-1])
                if db_dir:
                    import os
                    os.makedirs(db_dir, exist_ok=True)
            
            self.engine = create_engine(self.db_path, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
            
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            self._ensure_user_api_key_columns()
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {str(e)}")

    def _ensure_user_api_key_columns(self) -> None:
        """Apply tiny SQLite-compatible migrations for existing local databases."""
        inspector = inspect(self.engine)
        if "user_api_keys" not in inspector.get_table_names():
            return

        columns = {column["name"] for column in inspector.get_columns("user_api_keys")}
        if "openbalancer_api_key" not in columns:
            with self.engine.begin() as connection:
                connection.execute(text("ALTER TABLE user_api_keys ADD COLUMN openbalancer_api_key VARCHAR(64)"))
    
    def get_session(self):
        """Get a new database session."""
        if not self.SessionLocal:
            raise DatabaseError("Database not initialized. Call initialize() first.")
        return self.SessionLocal()
    
    def get_key_by_hash(self, key_hash: str) -> Optional[APIKeyRecord]:
        """Retrieve an API key record by its hash.
        
        Args:
            key_hash: SHA-256 hash of the API key
            
        Returns:
            APIKeyRecord if found, None otherwise
        """
        try:
            session = self.get_session()
            try:
                record = session.query(APIKeyRecord).filter(
                    APIKeyRecord.key_hash == key_hash,
                    APIKeyRecord.enabled == "Y"
                ).first()
                if record:
                    session.expunge(record)
                return record
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve API key: {str(e)}")
    
    def create_key(
        self,
        key_id: str,
        key_hash: str,
        provider_credentials: dict,
        description: str | None = None
    ) -> APIKeyRecord:
        """Create a new API key record.
        
        Args:
            key_id: Unique identifier (UUID)
            key_hash: SHA-256 hash of the API key
            provider_credentials: Dict mapping provider env var names to values
            description: Optional description for the key
            
        Returns:
            The created APIKeyRecord
        """
        try:
            session = self.get_session()
            try:
                record = APIKeyRecord(
                    id=key_id,
                    key_hash=key_hash,
                    provider_credentials=json.dumps(provider_credentials),
                    description=description
                )
                session.add(record)
                session.commit()
                return record
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to create API key: {str(e)}")
    
    def update_last_used(self, key_hash: str) -> None:
        """Update the last_used timestamp for an API key.
        
        Args:
            key_hash: SHA-256 hash of the API key
        """
        try:
            session = self.get_session()
            try:
                session.query(APIKeyRecord).filter(
                    APIKeyRecord.key_hash == key_hash
                ).update({"last_used": datetime.utcnow()})
                session.commit()
            finally:
                session.close()
        except Exception as e:
            # Don't raise, just log silently - this is non-critical
            pass
    
    def get_all_keys(self) -> list[APIKeyRecord]:
        """Get all API key records (for admin purposes).
        
        Returns:
            List of all APIKeyRecord objects
        """
        try:
            session = self.get_session()
            try:
                records = session.query(APIKeyRecord).all()
                return records
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve API keys: {str(e)}")
    
    def disable_key(self, key_hash: str) -> None:
        """Disable an API key by setting enabled to 'N'.
        
        Args:
            key_hash: SHA-256 hash of the API key
        """
        try:
            session = self.get_session()
            try:
                session.query(APIKeyRecord).filter(
                    APIKeyRecord.key_hash == key_hash
                ).update({"enabled": "N"})
                session.commit()
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to disable API key: {str(e)}")
    
    # User management methods
    
    def create_user(self, user_id: str, email: str, password_hash: str) -> User:
        """Create a new user account.
        
        Args:
            user_id: Unique identifier (UUID)
            email: User email address
            password_hash: Bcrypt hash of the password
            
        Returns:
            The created User object
        """
        try:
            session = self.get_session()
            try:
                user = User(
                    id=user_id,
                    email=email,
                    password_hash=password_hash
                )
                session.add(user)
                session.commit()
                return user
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to create user: {str(e)}")
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User if found, None otherwise
        """
        try:
            session = self.get_session()
            try:
                user = session.query(User).filter(
                    User.email == email,
                    User.is_active == True
                ).first()
                if user:
                    session.expunge(user)
                return user
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user: {str(e)}")
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Retrieve a user by ID.
        
        Args:
            user_id: User ID (UUID)
            
        Returns:
            User if found, None otherwise
        """
        try:
            session = self.get_session()
            try:
                user = session.query(User).filter(
                    User.id == user_id,
                    User.is_active == True
                ).first()
                if user:
                    session.expunge(user)
                return user
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user: {str(e)}")
    
    # User session methods
    
    def create_session(self, session_id: str, user_id: str, token: str, expires_at: datetime) -> UserSession:
        """Create a new user session.
        
        Args:
            session_id: Unique session identifier (UUID)
            user_id: ID of the user
            token: JWT token
            expires_at: Expiration datetime
            
        Returns:
            The created UserSession object
        """
        try:
            session = self.get_session()
            try:
                user_session = UserSession(
                    id=session_id,
                    user_id=user_id,
                    token=token,
                    expires_at=expires_at
                )
                session.add(user_session)
                session.commit()
                return user_session
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to create session: {str(e)}")
    
    def get_session_by_token(self, token: str) -> Optional[UserSession]:
        """Retrieve a session by token.
        
        Args:
            token: JWT token
            
        Returns:
            UserSession if found and valid, None otherwise
        """
        try:
            session = self.get_session()
            try:
                user_session = session.query(UserSession).filter(
                    UserSession.token == token,
                    UserSession.is_valid == True,
                    UserSession.expires_at > datetime.utcnow()
                ).first()
                if user_session:
                    session.expunge(user_session)
                return user_session
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve session: {str(e)}")
    
    def invalidate_session(self, token: str) -> None:
        """Invalidate a session by setting is_valid to False.
        
        Args:
            token: JWT token
        """
        try:
            session = self.get_session()
            try:
                session.query(UserSession).filter(
                    UserSession.token == token
                ).update({"is_valid": False})
                session.commit()
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to invalidate session: {str(e)}")
    
    # User API key methods
    
    def create_user_api_key(
        self,
        key_id: str,
        user_id: str,
        key_hash: str,
        provider_credentials: dict,
        openbalancer_api_key: str | None = None
    ) -> UserAPIKey:
        """Create a new API key for a user.
        
        Args:
            key_id: Unique identifier (UUID)
            user_id: ID of the user
            key_hash: SHA-256 hash of the API key
            provider_credentials: Dict of provider API keys
            openbalancer_api_key: Plaintext OpenBalancer API key for local MVP retrieval
            
        Returns:
            The created UserAPIKey object
        """
        try:
            session = self.get_session()
            try:
                user_api_key = UserAPIKey(
                    id=key_id,
                    user_id=user_id,
                    openbalancer_key_hash=key_hash,
                    openbalancer_api_key=openbalancer_api_key,
                    provider_credentials=json.dumps(provider_credentials)
                )
                session.add(user_api_key)
                session.commit()
                return user_api_key
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to create user API key: {str(e)}")
    
    def get_user_api_key_by_hash(self, key_hash: str) -> Optional[UserAPIKey]:
        """Retrieve a user API key by hash.
        
        Args:
            key_hash: SHA-256 hash of the API key
            
        Returns:
            UserAPIKey if found and enabled, None otherwise
        """
        try:
            session = self.get_session()
            try:
                user_api_key = session.query(UserAPIKey).filter(
                    UserAPIKey.openbalancer_key_hash == key_hash,
                    UserAPIKey.enabled == True
                ).first()
                if user_api_key:
                    session.expunge(user_api_key)
                return user_api_key
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user API key: {str(e)}")
    
    def get_user_api_keys(self, user_id: str) -> list[UserAPIKey]:
        """Get all API keys for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of UserAPIKey objects for this user
        """
        try:
            session = self.get_session()
            try:
                keys = session.query(UserAPIKey).filter(
                    UserAPIKey.user_id == user_id,
                    UserAPIKey.enabled == True
                ).order_by(UserAPIKey.created_at.desc()).all()
                for key in keys:
                    session.expunge(key)
                return keys
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve user API keys: {str(e)}")
    
    def regenerate_user_openbalancer_key(
        self,
        user_id: str,
        key_hash: str,
        openbalancer_api_key: str,
    ) -> Optional[UserAPIKey]:
        """Replace a user's OpenBalancer API key while keeping provider credentials."""
        try:
            session = self.get_session()
            try:
                user_api_key = session.query(UserAPIKey).filter(
                    UserAPIKey.user_id == user_id,
                    UserAPIKey.enabled == True,
                ).first()
                if not user_api_key:
                    return None
                user_api_key.openbalancer_key_hash = key_hash
                user_api_key.openbalancer_api_key = openbalancer_api_key
                user_api_key.last_used = None
                session.commit()
                session.expunge(user_api_key)
                return user_api_key
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to regenerate user API key: {str(e)}")

    def update_user_provider_credentials(
        self,
        user_id: str,
        provider_credentials: dict,
        key_hash: str | None = None,
        openbalancer_api_key: str | None = None,
        merge: bool = False,
    ) -> Optional[UserAPIKey]:
        """Update provider credentials for a user's active API key.
        
        Args:
            user_id: ID of the user
            provider_credentials: Updated dict of provider credentials
            key_hash: Optional replacement SHA-256 hash
            openbalancer_api_key: Optional replacement plaintext key
            
        Returns:
            The updated UserAPIKey object, or None if not found
        """
        try:
            session = self.get_session()
            try:
                user_api_key = session.query(UserAPIKey).filter(
                    UserAPIKey.user_id == user_id,
                    UserAPIKey.enabled == True
                ).first()
                if user_api_key:
                    if merge:
                        existing = json.loads(user_api_key.provider_credentials or "{}")
                        existing.update(provider_credentials)
                        provider_credentials = existing
                    user_api_key.provider_credentials = json.dumps(provider_credentials)
                    if key_hash:
                        user_api_key.openbalancer_key_hash = key_hash
                    if openbalancer_api_key:
                        user_api_key.openbalancer_api_key = openbalancer_api_key
                    session.commit()
                return user_api_key
            finally:
                session.close()
        except Exception as e:
            raise DatabaseError(f"Failed to update provider credentials: {str(e)}")
    
    def update_user_api_key_last_used(self, key_hash: str) -> None:
        """Update last_used timestamp for a user API key.
        
        Args:
            key_hash: SHA-256 hash of the API key
        """
        try:
            session = self.get_session()
            try:
                session.query(UserAPIKey).filter(
                    UserAPIKey.openbalancer_key_hash == key_hash
                ).update({"last_used": datetime.utcnow()})
                session.commit()
            finally:
                session.close()
        except Exception as e:
            # Don't raise, just log silently - this is non-critical
            pass
