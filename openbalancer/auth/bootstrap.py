"""Bootstrap module for auto-generating API keys on startup."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Optional

from openbalancer.auth.db import DatabaseManager
from openbalancer.auth.keygen import generate_api_key, hash_api_key


def get_provider_credentials_from_env() -> dict[str, str]:
    """Extract all provider API credentials from environment variables.
    
    Returns:
        Dict mapping env var names to their values for all configured providers
    """
    provider_env_vars = [
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "CEREBRAS_API_KEY",
        "GEMINI_API_KEY",
        "HF_API_KEY",
    ]
    
    credentials = {}
    for var_name in provider_env_vars:
        value = os.environ.get(var_name)
        if value:
            credentials[var_name] = value
    
    return credentials


def bootstrap_api_key(
    db_manager: DatabaseManager,
    env_file_path: Optional[str] = None
) -> tuple[str, str]:
    """Bootstrap the OpenBalancer API key system on startup.
    
    If an API key already exists in the database, returns that key.
    If not, generates a new key and stores it in the database and .env file.
    
    Args:
        db_manager: Initialized DatabaseManager instance
        env_file_path: Path to .env file (default: .env in current directory)
        
    Returns:
        Tuple of (plaintext_api_key, key_id)
    """
    if env_file_path is None:
        env_file_path = ".env"
    
    env_path = Path(env_file_path)
    
    # Check if there's already an API key in .env
    existing_key = _read_env_var("OPENBALANCER_API_KEY", env_file_path)
    if existing_key:
        print(f"✓ Found existing OpenBalancer API key in {env_file_path}")
        # Verify it exists in database
        key_hash = hash_api_key(existing_key)
        existing_record = db_manager.get_key_by_hash(key_hash)
        if existing_record:
            return existing_key, existing_record.id
    
    # No existing key - generate a new one
    new_key = generate_api_key()
    key_id = str(uuid.uuid4())
    key_hash = hash_api_key(new_key)
    
    # Get current provider credentials from environment
    credentials = get_provider_credentials_from_env()
    
    if not credentials:
        print("⚠ Warning: No provider API keys found in environment variables")
        print("  Make sure to set: GROQ_API_KEY, OPENROUTER_API_KEY, etc.")
    
    # Store in database
    db_manager.create_key(
        key_id=key_id,
        key_hash=key_hash,
        provider_credentials=credentials,
        description="Default API key - auto-generated on startup"
    )
    
    # Save to .env file
    _write_env_var("OPENBALANCER_API_KEY", new_key, env_file_path)
    
    # Print information (only once, on creation)
    print("\n" + "=" * 70)
    print("🔑 NEW OpenBalancer API Key Generated")
    print("=" * 70)
    print(f"API Key: {new_key}")
    print(f"Key ID:  {key_id}")
    print("\n⚠️  SAVE THIS KEY - YOU WILL NOT SEE IT AGAIN!")
    print("   Use it in the Authorization header:")
    print(f"   Authorization: Bearer {new_key}")
    print("\n✓ Key automatically saved to: " + env_file_path)
    print("=" * 70 + "\n")
    
    return new_key, key_id


def _read_env_var(var_name: str, env_file_path: str) -> Optional[str]:
    """Read a variable value from .env file.
    
    Args:
        var_name: Name of the environment variable
        env_file_path: Path to .env file
        
    Returns:
        Value of the variable or None if not found
    """
    env_path = Path(env_file_path)
    if not env_path.exists():
        return None
    
    content = env_path.read_text()
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith(f"{var_name}="):
            return line.split("=", 1)[1].strip()
    
    return None


def _write_env_var(var_name: str, value: str, env_file_path: str) -> None:
    """Write or update a variable in .env file.
    
    Args:
        var_name: Name of the environment variable
        value: Value to set
        env_file_path: Path to .env file
    """
    env_path = Path(env_file_path)
    
    # Read existing content
    if env_path.exists():
        content = env_path.read_text()
    else:
        content = ""
    
    # Check if variable already exists
    lines = content.split("\n")
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{var_name}="):
            lines[i] = f"{var_name}={value}"
            found = True
            break
    
    if not found:
        # Add new variable
        if content and not content.endswith("\n"):
            content += "\n"
        lines.append(f"{var_name}={value}")
    
    # Write back to file
    new_content = "\n".join(lines)
    env_path.write_text(new_content)
