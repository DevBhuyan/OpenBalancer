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
    provider_order: list[str] = Field(default_factory=lambda: ["openrouter", "groq", "huggingface", "cerebras", "gemini"])

    groq_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    cerebras_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    hf_api_key: Optional[str] = None

    groq_model: str = "openai/gpt-oss-120b"
    openrouter_model: str = "openai/gpt-oss-120b"
    cerebras_model: str = "gpt-oss-120b"
    gemini_model: str = "gemini-flash-latest"
    hf_model: str = "openai/gpt-oss-120b:fastest"

    groq_small_model: str = "llama-3.1-8b-instant"
    openrouter_small_model: str = "google/gemma-2-9b-it:free"
    cerebras_small_model: str = "llama3.1-8b"
    gemini_small_model: str = "gemini-flash-lite-latest"
    hf_small_model: str = "Qwen/Qwen3-4B-Thinking-2507:fastest"

    groq_large_model: str = "openai/gpt-oss-120b"
    openrouter_large_model: str = "openai/gpt-oss-120b"
    cerebras_large_model: str = "gpt-oss-120b"
    gemini_large_model: str = "gemini-flash-latest"
    hf_large_model: str = "openai/gpt-oss-120b:fastest"

    openrouter_cost_rank: int = 2
    groq_cost_rank: int = 1
    hf_cost_rank: int = 1
    cerebras_cost_rank: int = 1
    gemini_cost_rank: int = 1

    openrouter_http_referer: str = "http://localhost:8000"
    openrouter_app_title: str = "OpenBalancer"
    openrouter_artificial_max_concurrent: int = 5
    openrouter_artificial_rpm: int = 0
    router_max_wait_seconds: float = 30.0
    router_retry_sleep_seconds: float = 0.15
    provider_cooldown_seconds: float = 2.0
    provider_unavailable_cooldown_seconds: float = 5.0

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
        settings.hf_api_key = settings.hf_api_key or os.getenv("HF_TOKEN") or _read_text(QUICKSTART_DIR / "hf_api_key")
        return settings


@lru_cache
def get_settings() -> Settings:
    return Settings.with_quickstart_defaults()
