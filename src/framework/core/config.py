"""Centralized configuration for the API testing framework."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _get_int(name: str, default: int) -> int:
    """Read an integer environment variable with a clear fallback."""
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return int(raw_value)


def _get_float(name: str, default: float) -> float:
    """Read a float environment variable with a clear fallback."""
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return float(raw_value)


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    timeout: int = field(default_factory=lambda: _get_int("TEST_TIMEOUT", 10))
    retry_count: int = field(default_factory=lambda: _get_int("TEST_RETRY_COUNT", 1))
    retry_backoff_seconds: float = field(
        default_factory=lambda: _get_float("TEST_RETRY_BACKOFF_SECONDS", 0.5)
    )
    test_env: str = field(default_factory=lambda: os.getenv("TEST_ENV", "local"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


def get_settings() -> Settings:
    """Return a Settings object for the current process environment."""
    return Settings()
