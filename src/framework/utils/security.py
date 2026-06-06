"""Security-focused helpers for introductory API test checks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
}

DEFAULT_SENSITIVE_QUERY_PARAM_NAMES = {
    "access_token",
    "api_key",
    "apikey",
    "key",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def redact_headers(
    headers: Mapping[str, str],
    sensitive_names: Iterable[str] | None = None,
    replacement: str = "[REDACTED]",
) -> dict[str, str]:
    """Return a copy of headers with sensitive values replaced."""
    sensitive_lookup = {
        name.lower() for name in (sensitive_names or DEFAULT_SENSITIVE_HEADER_NAMES)
    }

    return {
        name: replacement if name.lower() in sensitive_lookup else value
        for name, value in headers.items()
    }


def find_sensitive_query_params(
    url: str,
    sensitive_names: Iterable[str] | None = None,
) -> list[str]:
    """Return sensitive query parameter names found in a URL."""
    sensitive_source = sensitive_names or DEFAULT_SENSITIVE_QUERY_PARAM_NAMES
    sensitive_lookup = {name.lower() for name in sensitive_source}
    query_pairs = parse_qsl(urlsplit(url).query, keep_blank_values=True)

    found: list[str] = []
    for name, _value in query_pairs:
        if name.lower() in sensitive_lookup and name not in found:
            found.append(name)
    return found


def redact_url_query_params(
    url: str,
    sensitive_names: Iterable[str] | None = None,
    replacement: str = "[REDACTED]",
) -> str:
    """Return a URL with sensitive query parameter values redacted."""
    sensitive_source = sensitive_names or DEFAULT_SENSITIVE_QUERY_PARAM_NAMES
    sensitive_lookup = {name.lower() for name in sensitive_source}
    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    redacted_pairs = [
        (name, replacement if name.lower() in sensitive_lookup else value)
        for name, value in query_pairs
    ]
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(redacted_pairs),
            parts.fragment,
        )
    )


def has_header(headers: Mapping[str, str], expected_name: str) -> bool:
    """Return whether a header name exists, ignoring case."""
    expected = expected_name.lower()
    return any(name.lower() == expected for name in headers)


def missing_security_headers(
    headers: Mapping[str, str],
    required_headers: Iterable[str],
) -> list[str]:
    """Return required security headers that are not present."""
    return [name for name in required_headers if not has_header(headers, name)]
