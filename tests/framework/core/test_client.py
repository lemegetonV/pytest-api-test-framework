"""Unit tests for the reusable API client."""

from __future__ import annotations

import logging

import pytest
import requests
import responses

from framework.core import APIClient

pytestmark = pytest.mark.framework_unit_test


def test_build_url_combines_base_url_and_relative_endpoint() -> None:
    client = APIClient("https://example.test/api")

    assert client._build_url("/users") == "https://example.test/api/users"
    assert client._build_url("users") == "https://example.test/api/users"


def test_build_url_preserves_absolute_endpoint() -> None:
    client = APIClient("https://example.test")

    assert client._build_url("https://other.test/users") == "https://other.test/users"


@responses.activate
def test_get_sends_default_headers_timeout_and_stores_last_response() -> None:
    responses.add(responses.GET, "https://example.test/users", json={"ok": True})
    client = APIClient("https://example.test", timeout=7)

    response = client.get("/users")

    assert response.status_code == 200
    assert client.last_response is response
    request = responses.calls[0].request
    assert request.headers["Accept"] == "application/json"
    assert "Content-Type" not in request.headers


@responses.activate
def test_post_json_sets_json_content_type() -> None:
    responses.add(responses.POST, "https://example.test/login", json={"ok": True})
    client = APIClient("https://example.test")

    response = client.post("/login", json={"username": "user"})

    assert response.status_code == 200
    request = responses.calls[0].request
    assert request.headers["Accept"] == "application/json"
    assert request.headers["Content-Type"] == "application/json"
    assert request.body == b'{"username": "user"}'


@responses.activate
def test_post_form_data_sets_form_content_type() -> None:
    responses.add(responses.POST, "https://example.test/token", json={"ok": True})
    client = APIClient("https://example.test")

    response = client.post(
        "/token",
        data={"grant_type": "client_credentials", "password": "secret"},
    )

    assert response.status_code == 200
    request = responses.calls[0].request
    assert request.headers["Accept"] == "application/json"
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.body == "grant_type=client_credentials&password=secret"


@responses.activate
def test_request_headers_can_override_default_accept() -> None:
    responses.add(responses.GET, "https://example.test/export", body="a,b\n1,2\n")
    client = APIClient("https://example.test")

    response = client.get("/export", headers={"Accept": "text/csv"})

    assert response.status_code == 200
    request = responses.calls[0].request
    assert request.headers["Accept"] == "text/csv"


def test_auth_helpers_set_and_clear_session_auth_state() -> None:
    client = APIClient("https://example.test")

    client.set_bearer_token("abc")
    assert client.session.headers["Authorization"] == "Bearer abc"
    assert client.session.auth is None

    client.set_basic_auth("user", "pass")
    assert "Authorization" not in client.session.headers
    assert client.session.auth == ("user", "pass")

    client.clear_auth()
    assert "Authorization" not in client.session.headers
    assert client.session.auth is None


@responses.activate
def test_request_and_response_payload_logs_are_redacted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    responses.add(
        responses.POST,
        "https://example.test/login",
        json={"accessToken": "response-secret"},
    )
    client = APIClient("https://example.test")

    with caplog.at_level(logging.INFO, logger="framework.core.client"):
        client.post("/login", json={"username": "user", "password": "secret"})

    messages = [record.getMessage() for record in caplog.records]
    assert any('"password": "[REDACTED]"' in message for message in messages)
    assert any('"accessToken": "[REDACTED]"' in message for message in messages)
    assert not any("response-secret" in message for message in messages)


def test_get_retries_timeout_once_then_succeeds(
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    attempts = {"count": 0}
    sleep_calls: list[float] = []
    client = APIClient(
        "https://example.test",
        retry_count=1,
        retry_backoff_seconds=0.25,
    )

    def fake_request(method: str, url: str, **kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise requests.Timeout("temporary timeout")
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response.reason = "OK"
        response._content = b'{"ok": true}'
        return response

    monkeypatch.setattr(client.session, "request", fake_request)
    monkeypatch.setattr("framework.core.client.sleep", sleep_calls.append)

    with caplog.at_level(logging.WARNING, logger="framework.core.client"):
        response = client.get("/users")

    assert response.status_code == 200
    assert attempts["count"] == 2
    assert sleep_calls == [0.25]
    assert "Retrying GET" in caplog.text


def test_get_raises_after_retry_is_exhausted(monkeypatch) -> None:
    client = APIClient("https://example.test", retry_count=1, retry_backoff_seconds=0)
    monkeypatch.setattr(
        client.session,
        "request",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("timeout")),
    )
    monkeypatch.setattr("framework.core.client.sleep", lambda _seconds: None)

    with pytest.raises(requests.Timeout):
        client.get("/users")


def test_post_does_not_retry_timeout(monkeypatch) -> None:
    attempts = {"count": 0}
    client = APIClient("https://example.test", retry_count=1)

    def fake_request(*args, **kwargs):
        attempts["count"] += 1
        raise requests.Timeout("timeout")

    monkeypatch.setattr(client.session, "request", fake_request)

    with pytest.raises(requests.Timeout):
        client.post("/login", json={"username": "user"})

    assert attempts["count"] == 1


def test_retry_count_zero_disables_get_retry(monkeypatch) -> None:
    attempts = {"count": 0}
    client = APIClient("https://example.test", retry_count=0)

    def fake_request(*args, **kwargs):
        attempts["count"] += 1
        raise requests.ConnectionError("connection failed")

    monkeypatch.setattr(client.session, "request", fake_request)

    with pytest.raises(requests.ConnectionError):
        client.get("/users")

    assert attempts["count"] == 1
