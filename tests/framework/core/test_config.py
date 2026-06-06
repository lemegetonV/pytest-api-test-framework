"""Unit tests for framework runtime settings."""

from __future__ import annotations

import pytest

from framework.core.config import get_settings

pytestmark = pytest.mark.framework_unit_test


def test_settings_use_defaults_when_environment_is_absent(monkeypatch) -> None:
    for name in (
        "TEST_TIMEOUT",
        "TEST_RETRY_COUNT",
        "TEST_RETRY_BACKOFF_SECONDS",
        "TEST_ENV",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.timeout == 10
    assert settings.retry_count == 1
    assert settings.retry_backoff_seconds == 0.5
    assert settings.test_env == "local"
    assert settings.log_level == "INFO"


def test_settings_read_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("TEST_TIMEOUT", "3")
    monkeypatch.setenv("TEST_RETRY_COUNT", "2")
    monkeypatch.setenv("TEST_RETRY_BACKOFF_SECONDS", "0.25")
    monkeypatch.setenv("TEST_ENV", "unit")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = get_settings()

    assert settings.timeout == 3
    assert settings.retry_count == 2
    assert settings.retry_backoff_seconds == 0.25
    assert settings.test_env == "unit"
    assert settings.log_level == "DEBUG"


def test_blank_numeric_environment_values_use_defaults(monkeypatch) -> None:
    monkeypatch.setenv("TEST_TIMEOUT", "")
    monkeypatch.setenv("TEST_RETRY_COUNT", " ")
    monkeypatch.setenv("TEST_RETRY_BACKOFF_SECONDS", "")

    settings = get_settings()

    assert settings.timeout == 10
    assert settings.retry_count == 1
    assert settings.retry_backoff_seconds == 0.5
