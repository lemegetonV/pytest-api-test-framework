"""Unit tests for redacted API report/log context helpers."""

from __future__ import annotations

import pytest
import requests
import responses

from framework.utils.api_context import (
    build_response_context,
    extract_request_id,
    is_truncated,
    redact_body_text,
    redact_sensitive_json,
    truncate_text,
)

pytestmark = pytest.mark.framework_unit_test


def test_truncate_text_returns_bounded_preview() -> None:
    assert truncate_text("abcdef", max_chars=3) == "abc..."
    assert truncate_text("abc", max_chars=3) == "abc"


def test_is_truncated_reports_whether_text_exceeds_limit() -> None:
    assert is_truncated("abcd", max_chars=3)
    assert not is_truncated("abc", max_chars=3)


def test_redact_sensitive_json_recursively_redacts_fields() -> None:
    value = {
        "accessToken": "abc",
        "profile": {"password": "secret", "name": "Emily"},
        "items": [{"refresh_token": "def"}],
    }

    assert redact_sensitive_json(value) == {
        "accessToken": "[REDACTED]",
        "profile": {"password": "[REDACTED]", "name": "Emily"},
        "items": [{"refresh_token": "[REDACTED]"}],
    }


def test_redact_body_text_redacts_json_body() -> None:
    assert redact_body_text('{"token": "abc", "name": "sample"}') == (
        '{"token": "[REDACTED]", "name": "sample"}'
    )


def test_redact_body_text_leaves_non_json_body_unchanged() -> None:
    assert redact_body_text("not-json") == "not-json"


def test_extract_request_id_prefers_headers() -> None:
    response = requests.Response()
    response.headers["X-Request-Id"] = "req-123"

    assert extract_request_id(response) == "req-123"


def test_extract_request_id_reads_json_body() -> None:
    response = requests.Response()
    response._content = b'{"requestId": "body-123"}'
    response.headers["Content-Type"] = "application/json"

    assert extract_request_id(response) == "body-123"


@responses.activate
def test_build_response_context_redacts_request_and_response_details() -> None:
    responses.add(
        responses.GET,
        "https://example.test/items?token=abc",
        json={"password": "secret", "name": "sample"},
        headers={"X-Request-Id": "req-123"},
        status=200,
    )

    response = requests.get(
        "https://example.test/items",
        params={"token": "abc"},
        headers={"Authorization": "Bearer secret"},
        timeout=1,
    )
    context = build_response_context(response)

    assert context["method"] == "GET"
    assert "token=%5BREDACTED%5D" in context["url"]
    assert context["status_code"] == 200
    assert context["request_id"] == "req-123"
    assert context["request_headers"]["Authorization"] == "[REDACTED]"
    assert '"password": "[REDACTED]"' in context["body_preview"]


@responses.activate
def test_build_response_context_can_include_full_body_preview() -> None:
    body = {"message": "x" * 600}
    responses.add(responses.GET, "https://example.test/large", json=body, status=500)

    response = requests.get("https://example.test/large", timeout=1)
    context = build_response_context(response, max_body_chars=10_000)

    assert context["body_truncated"] is False
    assert "x" * 600 in context["body_preview"]
