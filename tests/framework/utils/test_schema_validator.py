"""Unit tests for framework JSON Schema helpers."""

from __future__ import annotations

import pytest
from jsonschema.exceptions import ValidationError

from framework.utils.schema_validator import (
    collect_validation_errors,
    load_schema,
    validate_json,
)

pytestmark = pytest.mark.framework_unit_test


def test_load_schema_returns_schema_object() -> None:
    schema = load_schema("tests/framework/test_data/valid_schema.json")

    assert schema["type"] == "object"


def test_load_schema_rejects_non_object_schema_file() -> None:
    with pytest.raises(TypeError, match="JSON Schema files"):
        load_schema("tests/framework/test_data/invalid_schema_array.json")


def test_validate_json_accepts_valid_payload() -> None:
    schema = load_schema("tests/framework/test_data/valid_schema.json")

    validate_json({"id": 1, "name": "sample"}, schema)


def test_validate_json_raises_for_invalid_payload() -> None:
    schema = load_schema("tests/framework/test_data/valid_schema.json")

    with pytest.raises(ValidationError):
        validate_json({"id": "not-an-int"}, schema)


def test_collect_validation_errors_returns_sorted_errors() -> None:
    schema = load_schema("tests/framework/test_data/valid_schema.json")
    errors = collect_validation_errors({"id": "not-an-int"}, schema)

    assert [list(error.path) for error in errors] == [[], ["id"]]
