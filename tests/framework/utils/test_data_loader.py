"""Unit tests for framework data loading helpers."""

from __future__ import annotations

import pytest

from framework.utils.data_loader import load_csv_data, load_json_data, project_path

pytestmark = pytest.mark.framework_unit_test


def test_project_path_resolves_from_project_root() -> None:
    path = project_path("tests/framework/test_data/sample.json")

    assert path.is_absolute()
    assert path.name == "sample.json"


def test_load_json_data_reads_project_relative_json() -> None:
    data = load_json_data("tests/framework/test_data/sample.json")

    assert data == {
        "name": "framework-sample",
        "enabled": True,
        "count": 3,
    }


def test_load_csv_data_reads_rows_as_dicts() -> None:
    data = load_csv_data("tests/framework/test_data/sample.csv")

    assert data == [
        {"name": "alpha", "value": "1"},
        {"name": "beta", "value": "2"},
    ]
