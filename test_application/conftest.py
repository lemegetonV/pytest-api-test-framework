"""Shared pytest reporting hooks for API test packs."""

from __future__ import annotations

import json
from collections.abc import Callable
from html import escape
from typing import Any

import pytest
from pytest_html import extras

from framework.core import APIClient
from framework.utils.api_context import build_response_context, format_context_for_log

API_CLIENTS_ATTR = "_api_test_clients"
API_CONTEXTS_ATTR = "_api_response_contexts"
FULL_BODY_PREVIEW_CHARS = 1_000_000


@pytest.fixture
def register_api_client(
    request: pytest.FixtureRequest,
) -> Callable[[APIClient], APIClient]:
    """Register API clients so failure reports can include their last response."""
    clients: list[APIClient] = []
    setattr(request.node, API_CLIENTS_ATTR, clients)

    def register(client: APIClient) -> APIClient:
        clients.append(client)
        return client

    return register


def _api_clients_from_fixtures(item: pytest.Item) -> list[APIClient]:
    """Return APIClient fixtures used by the current test item."""
    clients: list[APIClient] = []
    clients.extend(getattr(item, API_CLIENTS_ATTR, []))

    for value in getattr(item, "funcargs", {}).values():
        if isinstance(value, APIClient) and value not in clients:
            clients.append(value)
    return clients


def _response_contexts_for_item(item: pytest.Item) -> list[dict[str, Any]]:
    """Build redacted response contexts for clients used by a test item."""
    contexts: list[dict[str, Any]] = []
    for client in _api_clients_from_fixtures(item):
        if client.last_response is not None:
            contexts.append(
                build_response_context(
                    client.last_response,
                    max_body_chars=FULL_BODY_PREVIEW_CHARS,
                )
            )
    return contexts


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[Any],
) -> object:
    """Attach redacted API response context to pytest-html on failures."""
    outcome = yield
    report = outcome.get_result()

    if report.when not in {"setup", "call"} or not report.failed:
        return

    if not item.config.pluginmanager.hasplugin("html"):
        return

    contexts = _response_contexts_for_item(item)
    setattr(report, API_CONTEXTS_ATTR, contexts)

    report_extras = list(getattr(report, "extras", []))
    for index, context in enumerate(contexts, start=1):
        title = "API Response Context"
        if index > 1:
            title = f"{title} #{index}"

        report_extras.append(extras.text(format_context_for_log(context), name=title))
        report_extras.append(
            extras.json(
                context,
                name=f"{title} JSON",
            )
        )

    report.extras = report_extras


def pytest_html_results_table_html(report: pytest.TestReport, data: list[str]) -> None:
    """Show redacted API failure context inside expanded pytest-html rows."""
    contexts = getattr(report, API_CONTEXTS_ATTR, [])
    if not contexts:
        return

    for index, context in enumerate(contexts, start=1):
        title = "API Response Context"
        if index > 1:
            title = f"{title} #{index}"

        context_json = json.dumps(context, indent=2, default=str)
        data.append(f"{title}\n{escape(context_json)}")
