"""DummyJSON tests for authentication and token flows."""

from __future__ import annotations

import pytest

from framework.core import APIClient
from framework.utils.api_context import build_response_context
from framework.utils.schema_validator import validate_json
from test_application.dummyjson.helpers import (
    load_dummyjson_schema,
    load_dummyjson_test_data,
)

pytestmark = pytest.mark.dummyjson


@pytest.mark.dummyjson_smoke
def test_login_returns_user_identity_and_tokens(
    dummyjson_login_data: dict[str, object],
    dummyjson_expected_user: dict[str, object],
) -> None:
    schema = load_dummyjson_schema("auth_login.schema.json")

    validate_json(dummyjson_login_data, schema)

    assert dummyjson_login_data["username"] == dummyjson_expected_user["username"]
    assert dummyjson_login_data["email"] == dummyjson_expected_user["email"]
    assert isinstance(dummyjson_login_data["accessToken"], str)
    assert isinstance(dummyjson_login_data["refreshToken"], str)


def test_auth_me_uses_bearer_token(
    authenticated_dummyjson_client: APIClient,
    dummyjson_expected_user: dict[str, object],
) -> None:
    response = authenticated_dummyjson_client.get("/auth/me")
    body = response.json()

    assert response.status_code == 200
    assert body["username"] == dummyjson_expected_user["username"]
    assert body["email"] == dummyjson_expected_user["email"]
    assert body["id"] == dummyjson_expected_user["id"]


def test_refresh_token_returns_usable_token_pair(
    dummyjson_client: APIClient,
    dummyjson_login_data: dict[str, object],
) -> None:
    response = dummyjson_client.post(
        "/auth/refresh",
        json={
            "refreshToken": dummyjson_login_data["refreshToken"],
            "expiresInMins": 30,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert isinstance(body["accessToken"], str)
    assert isinstance(body["refreshToken"], str)


def test_invalid_login_returns_clear_400_error(
    dummyjson_client: APIClient,
    dummyjson_auth_user: dict[str, object],
) -> None:
    dummyjson_invalid_login_data = load_dummyjson_test_data("invalid_login.json")
    expected = dummyjson_invalid_login_data["expected"]
    assert isinstance(expected, dict)

    response = dummyjson_client.post(
        "/auth/login",
        json={
            "username": dummyjson_auth_user["username"],
            "password": dummyjson_invalid_login_data["password"],
        },
    )
    body = response.json()

    assert response.status_code == expected["status_code"]
    assert body["message"] == expected["message"]


def test_login_report_context_redacts_token_body(
    dummyjson_client: APIClient,
    dummyjson_credentials: dict[str, str],
) -> None:
    response = dummyjson_client.post(
        "/auth/login",
        json={**dummyjson_credentials, "expiresInMins": 30},
    )
    context = build_response_context(response)

    assert response.status_code == 200
    assert "accessToken" in context["body_preview"]
    assert "refreshToken" in context["body_preview"]
    assert response.json()["accessToken"] not in context["body_preview"]
    assert response.json()["refreshToken"] not in context["body_preview"]
