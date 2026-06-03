from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
QUICKSTART_DIR = BASE_DIR / "quickstart_curls_and_api_keys"


def _read_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def _extract_bearer_key(path: Path, prefix: str) -> Optional[str]:
    text = _read_text(path)
    if not text:
        return None
    match = re.search(rf"({re.escape(prefix)}[A-Za-z0-9_\-]+)", text)
    return match.group(1) if match else None


def _extract_google_key(path: Path) -> Optional[str]:
    text = _read_text(path)
    if not text:
        return None
    match = re.search(r"X-goog-api-key:\s*([A-Za-z0-9_\-]+)", text)
    return match.group(1) if match else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OpenBalancer"
    request_timeout_seconds: float = 60.0
    provider_order: list[str] = Field(default_factory=lambda: ["groq", "openrouter", "cerebras", "gemini"])

    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    groq_model: str = "openai/gpt-oss-120b"
    openrouter_model: str = "openai/gpt-oss-120b"
    cerebras_model: str = "gpt-oss-120b"
    gemini_model: str = "gemini-flash-latest"

    openrouter_http_referer: str = "http://localhost:8000"
    openrouter_app_title: str = "OpenBalancer"

    @classmethod
    def with_quickstart_defaults(cls) -> "Settings":
        settings = cls()
        settings.groq_api_key = settings.groq_api_key or _read_text(QUICKSTART_DIR / "groq_api_key")
        settings.openrouter_api_key = settings.openrouter_api_key or _read_text(QUICKSTART_DIR / "openrouter_api_key")
        settings.cerebras_api_key = settings.cerebras_api_key or _extract_bearer_key(
            QUICKSTART_DIR / "cerebras_quickstart_curl", "csk-"
        )
        settings.gemini_api_key = settings.gemini_api_key or os.getenv("GOOGLE_API_KEY") or _extract_google_key(
            QUICKSTART_DIR / "gemini_quickstart_curl"
        )
        return settings


@lru_cache
def get_settings() -> Settings:
    return Settings.with_quickstart_defaults()
