"""Helpers for loading external test data files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def project_path(relative_path: str) -> Path:
    """Return an absolute path inside the project root."""
    return PROJECT_ROOT / relative_path


def load_json_data(relative_path: str) -> Any:
    """Load JSON test data from a project-relative path."""
    with project_path(relative_path).open(encoding="utf-8") as data_file:
        return json.load(data_file)


def load_csv_data(relative_path: str) -> list[dict[str, str]]:
    """Load CSV test data as a list of dictionaries."""
    with project_path(relative_path).open(newline="", encoding="utf-8") as data_file:
        return list(csv.DictReader(data_file))
