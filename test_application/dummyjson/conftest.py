"""Fixtures for the DummyJSON API test pack."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from framework.core import APIClient, get_settings
from test_application.dummyjson.helpers import load_dummyjson_test_data


@pytest.fixture(scope="session")
def dummyjson_base_url() -> str:
    """Base URL for the DummyJSON application pack."""
    return os.getenv("DUMMYJSON_URL", "https://dummyjson.com")


@pytest.fixture
def dummyjson_client(
    dummyjson_base_url: str,
    register_api_client: Callable[[APIClient], APIClient],
) -> Iterator[APIClient]:
    """Function-scoped client for live DummyJSON API tests."""
    settings = get_settings()
    client = register_api_client(
        APIClient(
            base_url=dummyjson_base_url,
            timeout=settings.timeout,
            retry_count=settings.retry_count,
            retry_backoff_seconds=settings.retry_backoff_seconds,
        )
    )

    yield client

    client.close()


@pytest.fixture
def dummyjson_auth_user() -> dict[str, Any]:
    """Public DummyJSON demo auth user and expected identity."""
    return load_dummyjson_test_data("auth_user.json")


@pytest.fixture
def dummyjson_credentials(dummyjson_auth_user: dict[str, Any]) -> dict[str, str]:
    """Public DummyJSON demo credentials, overridable for CI experiments."""
    username = dummyjson_auth_user["username"]
    password = dummyjson_auth_user["password"]
    assert isinstance(username, str)
    assert isinstance(password, str)

    return {
        "username": os.getenv("DUMMYJSON_USERNAME", username),
        "password": os.getenv("DUMMYJSON_PASSWORD", password),
    }


@pytest.fixture
def dummyjson_expected_user(dummyjson_auth_user: dict[str, Any]) -> dict[str, object]:
    """Expected identity for the configured DummyJSON demo auth user."""
    expected = dummyjson_auth_user["expected"]
    assert isinstance(expected, dict)
    return expected


@pytest.fixture
def dummyjson_login_data(
    dummyjson_client: APIClient,
    dummyjson_credentials: dict[str, str],
) -> dict[str, object]:
    """Log in once for tests that need real DummyJSON auth tokens."""
    response = dummyjson_client.post(
        "/auth/login",
        json={**dummyjson_credentials, "expiresInMins": 30},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def authenticated_dummyjson_client(
    dummyjson_client: APIClient,
    dummyjson_login_data: dict[str, object],
) -> APIClient:
    """DummyJSON client with an access token applied."""
    token = dummyjson_login_data["accessToken"]
    assert isinstance(token, str)
    dummyjson_client.set_bearer_token(token)
    return dummyjson_client
