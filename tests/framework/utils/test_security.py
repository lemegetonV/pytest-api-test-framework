"""Unit tests for framework security helpers."""

from __future__ import annotations

import pytest
from faker import Faker

from framework.utils.security import (
    find_sensitive_query_params,
    has_header,
    missing_security_headers,
    redact_headers,
    redact_url_query_params,
)

pytestmark = pytest.mark.framework_unit_test


def test_redact_headers_replaces_sensitive_values_case_insensitively() -> None:
    fake = Faker()
    fake.seed_instance(1234)
    api_key = fake.sha256()

    redacted = redact_headers(
        {
            "Authorization": f"Bearer {api_key}",
            "X-Request-Id": fake.uuid4(),
        }
    )

    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["X-Request-Id"] != "[REDACTED]"


def test_find_sensitive_query_params_returns_matching_names() -> None:
    found = find_sensitive_query_params(
        "https://example.test/items?api_key=abc&search=phone&token=def"
    )

    assert found == ["api_key", "token"]


def test_redact_url_query_params_replaces_sensitive_values() -> None:
    redacted = redact_url_query_params(
        "https://example.test/items?api_key=abc&search=phone"
    )

    assert "api_key=%5BREDACTED%5D" in redacted
    assert "search=phone" in redacted


def test_has_header_matches_case_insensitively() -> None:
    assert has_header({"Content-Type": "application/json"}, "content-type")
    assert not has_header({"Content-Type": "application/json"}, "authorization")


def test_missing_security_headers_returns_absent_headers() -> None:
    missing = missing_security_headers(
        {"Strict-Transport-Security": "max-age=1"},
        ["Strict-Transport-Security", "X-Content-Type-Options"],
    )

    assert missing == ["X-Content-Type-Options"]
