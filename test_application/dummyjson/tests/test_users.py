"""DummyJSON tests for users, search, and nested profile objects."""

from __future__ import annotations

import pytest

from framework.core import APIClient
from framework.utils.schema_validator import validate_json
from test_application.dummyjson.helpers import (
    load_dummyjson_schema,
    load_dummyjson_test_data,
)

pytestmark = pytest.mark.dummyjson


@pytest.mark.dummyjson_smoke
def test_user_collection_matches_schema(dummyjson_client: APIClient) -> None:
    response = dummyjson_client.get("/users", params={"limit": 3})
    body = response.json()
    schema = load_dummyjson_schema("user_collection.schema.json")

    assert response.status_code == 200
    validate_json(body, schema)
    assert body["limit"] == 3
    assert len(body["users"]) == 3


def test_single_user_contains_nested_address_and_company(
    dummyjson_client: APIClient,
    dummyjson_expected_user: dict[str, object],
) -> None:
    response = dummyjson_client.get(f"/users/{dummyjson_expected_user['id']}")
    body = response.json()
    schema = load_dummyjson_schema("user.schema.json")

    assert response.status_code == 200
    validate_json(body, schema)
    assert body["username"] == dummyjson_expected_user["username"]
    assert body["address"]["coordinates"]["lat"] != 0
    assert body["company"]["department"]


def test_user_search_finds_expected_public_demo_user(
    dummyjson_client: APIClient,
) -> None:
    dummyjson_user_search_data = load_dummyjson_test_data("user_search.json")
    expected = dummyjson_user_search_data["expected"]
    assert isinstance(expected, dict)

    response = dummyjson_client.get(
        "/users/search",
        params={"q": dummyjson_user_search_data["query"]},
    )
    body = response.json()

    assert response.status_code == 200
    assert any(user["username"] == expected["username"] for user in body["users"])
    assert body["total"] >= len(body["users"])
