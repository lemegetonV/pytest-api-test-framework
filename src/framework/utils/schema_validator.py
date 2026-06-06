"""JSON Schema validation helpers for API responses."""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from framework.utils.data_loader import load_json_data


def load_schema(relative_path: str) -> dict[str, Any]:
    """Load a JSON Schema document from a project-relative path."""
    schema = load_json_data(relative_path)
    if not isinstance(schema, dict):
        raise TypeError("JSON Schema files must contain a JSON object at the top level")
    return schema


def validate_json(data: Any, schema: dict[str, Any]) -> None:
    """Raise ValidationError if data does not match the schema."""
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)


def collect_validation_errors(
    data: Any,
    schema: dict[str, Any],
) -> list[ValidationError]:
    """Return all validation errors sorted by their location in the payload."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return sorted(validator.iter_errors(data), key=lambda error: list(error.path))
