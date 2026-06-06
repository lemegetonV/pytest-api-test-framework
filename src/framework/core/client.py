"""Reusable API client built on top of requests.Session."""

from __future__ import annotations

import json
import logging
from time import sleep
from typing import Any
from urllib.parse import urljoin

import requests

from framework.utils.api_context import (
    redact_body_text,
    redact_sensitive_json,
    truncate_text,
)

logger = logging.getLogger(__name__)


class APIClient:
    """Small HTTP client wrapper for API test code."""

    RETRYABLE_METHODS = {"GET"}

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        retry_count: int = 1,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_backoff_seconds = retry_backoff_seconds
        self.last_response: requests.Response | None = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def get(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Send a GET request."""
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Send a POST request."""
        return self._request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Send a PUT request."""
        return self._request("PUT", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Send a PATCH request."""
        return self._request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> requests.Response:
        """Send a DELETE request."""
        return self._request("DELETE", endpoint, **kwargs)

    def set_bearer_token(self, token: str) -> None:
        """Apply a bearer token to all future requests in this client session."""
        self.session.auth = None
        self.session.headers["Authorization"] = f"Bearer {token}"

    def set_basic_auth(self, username: str, password: str) -> None:
        """Apply HTTP Basic authentication to all future requests."""
        self.session.headers.pop("Authorization", None)
        self.session.auth = (username, password)

    def clear_auth(self) -> None:
        """Remove authentication state from the client session."""
        self.session.headers.pop("Authorization", None)
        self.session.auth = None

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        """Apply framework defaults and send the HTTP request."""
        url = self._build_url(endpoint)
        kwargs.setdefault("timeout", self.timeout)

        logger.info("%s %s", method, url)
        self._log_request_payload(kwargs)
        response = self._send_with_retries(method, url, **kwargs)
        self.last_response = response
        logger.info(
            "Response: %s %s",
            response.status_code,
            response.reason,
        )
        self._log_response_payload(response)
        return response

    def _send_with_retries(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Send a request, retrying transient network errors for safe methods."""
        max_attempts = self.retry_count + 1
        retryable = method.upper() in self.RETRYABLE_METHODS

        for attempt in range(1, max_attempts + 1):
            try:
                return self.session.request(method, url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as error:
                if not retryable or attempt == max_attempts:
                    raise

                logger.warning(
                    "Retrying %s %s after %s on attempt %s/%s",
                    method,
                    url,
                    error.__class__.__name__,
                    attempt,
                    max_attempts,
                )
                sleep(self.retry_backoff_seconds)

        raise RuntimeError("request retry loop exited unexpectedly")

    def _build_url(self, endpoint: str) -> str:
        """Build an absolute URL from a relative endpoint."""
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return urljoin(f"{self.base_url}/", endpoint.lstrip("/"))

    def _log_request_payload(self, request_kwargs: dict[str, Any]) -> None:
        """Log a redacted preview of request params and body payload."""
        payload: dict[str, Any] = {}
        for key in ("params", "json", "data"):
            if key in request_kwargs:
                payload[key] = self._safe_log_value(request_kwargs[key])

        if not payload:
            logger.info("Request payload: none")
            return

        logger.info("Request payload: %s", self._to_log_text(payload))

    def _log_response_payload(self, response: requests.Response) -> None:
        """Log a redacted preview of the response body."""
        redacted_body = redact_body_text(response.text)
        logger.info("Response payload: %s", truncate_text(redacted_body))

    def _safe_log_value(self, value: Any) -> Any:
        """Return a JSON-compatible, redacted value for logs."""
        if isinstance(value, bytes):
            return f"<{len(value)} bytes>"
        return redact_sensitive_json(value)

    def _to_log_text(self, value: Any) -> str:
        """Serialize log values consistently without failing test execution."""
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            return str(value)

    def close(self) -> None:
        """Close the underlying requests session."""
        self.session.close()

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
