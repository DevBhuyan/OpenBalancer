#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility module for loading OpenBalancer API key and configuration.

This module provides helpers for all integration tests to authenticate
with the OpenBalancer API.
"""

import os
from pathlib import Path
from typing import Optional


def load_api_key() -> str:
    """Load OpenBalancer API key from environment or .env file.
    
    Tries in order:
    1. OPENBALANCER_API_KEY environment variable
    2. .env file in parent directory (one level up from clients/)
    
    Returns:
        The OpenBalancer API key (format: obk_<32-hex>)
        
    Raises:
        ValueError: If no API key is found
    """
    # Try environment variable first
    api_key = os.environ.get("OPENBALANCER_API_KEY")
    if api_key:
        return api_key
    
    # Try reading from .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENBALANCER_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    if api_key:
                        return api_key
    
    raise ValueError(
        "OpenBalancer API key not found. "
        "Set OPENBALANCER_API_KEY environment variable or ensure .env file exists in project root."
    )


def get_api_headers() -> dict[str, str]:
    """Get HTTP headers with OpenBalancer API key for requests.
    
    Returns:
        Dict with Authorization header containing the API key
    """
    api_key = load_api_key()
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def get_api_key() -> str:
    """Get the OpenBalancer API key (alias for load_api_key).
    
    Returns:
        The OpenBalancer API key
    """
    return load_api_key()


if __name__ == "__main__":
    # Quick test to verify API key loading
    try:
        key = load_api_key()
        print(f"✓ API key loaded: {key[:10]}...{key[-10:]}")
    except ValueError as e:
        print(f"✗ Error: {e}")
