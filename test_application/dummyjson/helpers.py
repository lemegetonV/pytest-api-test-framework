"""Helper functions for the DummyJSON API test pack."""

from __future__ import annotations

from typing import Any

from framework.utils.data_loader import load_json_data
from framework.utils.schema_validator import load_schema


def load_dummyjson_schema(schema_name: str) -> dict[str, Any]:
    """Load a JSON Schema document from the DummyJSON schema directory."""
    return load_schema(f"test_application/dummyjson/schemas/{schema_name}")


def load_dummyjson_test_data(file_name: str) -> dict[str, Any]:
    """Load a JSON test data file from the DummyJSON test data directory."""
    data = load_json_data(f"test_application/dummyjson/test_data/{file_name}")
    if not isinstance(data, dict):
        raise TypeError("DummyJSON test data files must contain a JSON object")
    return data
