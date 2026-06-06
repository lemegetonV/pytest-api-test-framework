# Architecture

This project is a reusable API test framework plus concrete API test packs. The
framework layer provides general-purpose testing utilities; API packs provide
fixtures, data, schemas, and tests for a specific external API.

The primary design rule is:

```text
src/framework must not depend on test_application.
test_application may depend on src/framework.
```

That boundary keeps the framework portable. A new API pack, such as Stripe, can
reuse the same client, reporting hooks, schema validation, data loading, and
security helpers without changing framework internals.

## Layer Overview

```text
src/framework/
  core/
    client.py
    config.py
  utils/
    api_context.py
    data_loader.py
    performance.py
    schema_validator.py
    security.py

test_application/
  conftest.py
  dummyjson/
    conftest.py
    helpers.py
    schemas/
    test_data/
    tests/
    services/

tests/framework/
  core/
  utils/
  test_data/
```

## Framework Layer

The framework layer lives under `src/framework`. It should contain only reusable
code that can support any HTTP API.

### `framework.core.APIClient`

`APIClient` is a small wrapper around `requests.Session`.

Responsibilities:

- own the base URL
- apply reusable response negotiation defaults
- expose HTTP methods: `get`, `post`, `put`, `patch`, `delete`
- apply default timeout
- support bearer token auth
- support basic auth
- clear auth state
- keep `last_response` for failure reporting
- log request and response details
- retry transient failures for safe methods

The client accepts:

```python
APIClient(
    base_url="https://example.test",
    timeout=10,
    retry_count=1,
    retry_backoff_seconds=0.5,
)
```

Endpoints may be relative:

```python
client.get("/users/1")
```

or absolute:

```python
client.get("https://example.test/users/1")
```

Absolute URLs are preserved. Relative URLs are joined with the configured
`base_url`.

### Default Headers And Body Formats

The framework default is:

```http
Accept: application/json
```

This means the client prefers JSON responses by default, which is appropriate for
most API test suites in this project. It is still request-level overrideable:

```python
client.get("/export.csv", headers={"Accept": "text/csv"})
```

The framework does not set a global `Content-Type` header. `Content-Type`
describes the request body format, so it should be chosen per request instead of
being fixed on the client session.

Use standard `requests` conventions:

```python
client.post("/auth/login", json={"username": "demo"})
```

This sends a JSON body and lets `requests` set:

```http
Content-Type: application/json
```

For form-encoded APIs:

```python
client.post("/oauth/token", data={"grant_type": "client_credentials"})
```

This sends form data and lets `requests` set:

```http
Content-Type: application/x-www-form-urlencoded
```

For unusual request body formats, pass request-level headers explicitly:

```python
client.post(
    "/xml-endpoint",
    data="<request />",
    headers={"Content-Type": "application/xml"},
)
```

This convention keeps the framework reusable across JSON APIs, form-encoded
APIs, and future APIs with custom media types. Tests should only call
`response.json()` when the endpoint contract says the response is JSON; text,
CSV, XML, or binary endpoints should assert against `response.text` or
`response.content`.

### Retry Policy

Retries currently apply only to `GET`.

Retryable exception types:

- `requests.ConnectionError`
- `requests.Timeout`

Default behavior:

```text
TEST_RETRY_COUNT=1
TEST_RETRY_BACKOFF_SECONDS=0.5
```

`retry_count` means retries after the first request. With `retry_count=1`, the
client may make two attempts total:

```text
attempt 1 -> transient failure -> wait 0.5 seconds -> attempt 2
```

Non-GET methods are not retried. This avoids accidentally repeating operations
that may create, update, or delete server state.

### Request And Response Logging

`APIClient` logs:

- method and URL
- request params/body
- response status
- response body preview

Sensitive values are redacted before logging. Redaction covers common sensitive
field names such as:

```text
password
token
access_token
accessToken
refresh_token
refreshToken
secret
authorization
x-api-key
cookie
```

Response body logs are intentionally previews. Failure report context uses a much
larger body limit so debugging failures has more context.

### `framework.core.config`

Framework runtime configuration is environment-based and `.env` aware.

Current framework settings:

| Setting | Environment variable | Default |
| --- | --- | --- |
| `timeout` | `TEST_TIMEOUT` | `10` |
| `retry_count` | `TEST_RETRY_COUNT` | `1` |
| `retry_backoff_seconds` | `TEST_RETRY_BACKOFF_SECONDS` | `0.5` |
| `test_env` | `TEST_ENV` | `local` |
| `log_level` | `LOG_LEVEL` | `INFO` |

`config.py` should remain API-agnostic. Do not add API-specific values such as
`STRIPE_API_KEY`, `DUMMYJSON_URL`, or account IDs here. Those belong in the API
pack that uses them.

## Utility Layer

### Data Loading

`framework.utils.data_loader` provides project-relative data loading:

```python
load_json_data("test_application/dummyjson/test_data/auth_user.json")
load_csv_data("tests/framework/test_data/sample.csv")
project_path("some/project/file.txt")
```

Use these helpers instead of manual path construction in tests.

### JSON Schema Validation

`framework.utils.schema_validator` provides:

```python
load_schema(relative_path)
validate_json(data, schema)
collect_validation_errors(data, schema)
```

Use schemas for response shape validation. Keep API-specific schemas inside the
API pack:

```text
test_application/<api_name>/schemas/
```

### API Context And Reporting

`framework.utils.api_context` builds redacted response context from a
`requests.Response`.

Context includes:

- method
- redacted URL
- status code
- reason
- elapsed time
- request id or correlation id, when available
- redacted request headers
- redacted response headers
- redacted body preview
- whether the body preview was truncated

This module is framework code because it knows only about HTTP responses and
redaction, not about any specific API.

### Security Helpers

`framework.utils.security` provides helpers for:

- redacting sensitive headers
- redacting sensitive query parameters
- finding sensitive query parameters
- checking whether headers exist
- identifying missing security headers

These helpers can support future API-level security checks without embedding a
specific API contract into the framework.

### Performance Helpers

`framework.utils.performance` provides lightweight timing utilities:

```python
measure_call(...)
is_within_budget(...)
percentile(...)
summarize_timings(...)
```

These helpers are intentionally small. They are useful for simple response-time
assertions, not as a replacement for a load-testing tool.

## Pytest Integration

### Application-Level Reporting Hooks

`test_application/conftest.py` contains shared pytest hooks for API test packs.

It provides:

```python
register_api_client
```

API pack fixtures should register every `APIClient` they create:

```python
client = register_api_client(APIClient(...))
```

The reporting hooks also inspect fixture values and can discover `APIClient`
fixtures automatically. Explicit registration is still preferred because it is
clear and works well when a fixture creates more than one client.

On failed tests, the hook attaches redacted response context to pytest-html
reports. Passing tests do not get full response context attachments; they rely on
normal `INFO` logs from `APIClient`.

### Pytest Configuration

Pytest is configured in `pyproject.toml`.

Important settings:

```toml
testpaths = ["tests", "test_application"]
pythonpath = ["src"]
addopts = "-v --tb=short"
log_cli = true
log_cli_level = "INFO"
```

The project collects both:

- framework unit tests under `tests/`
- live API tests under `test_application/`

### Markers

Current markers:

```toml
framework_unit_test
dummyjson
dummyjson_smoke
```

Marker meaning:

| Marker | Meaning |
| --- | --- |
| `framework_unit_test` | Unit tests for reusable framework code. No live API calls. |
| `dummyjson` | Full DummyJSON API pack coverage. Live API calls. |
| `dummyjson_smoke` | Minimal happy-path DummyJSON tests for fast confidence. |

Use marker expressions to define suites:

```bash
python -m pytest -m framework_unit_test
python -m pytest -m dummyjson_smoke
python -m pytest -m dummyjson
python -m pytest -m "framework_unit_test or dummyjson_smoke"
```

## DummyJSON API Pack

DummyJSON is the first concrete API pack.

```text
test_application/dummyjson/
  conftest.py
  helpers.py
  schemas/
  test_data/
  tests/
  services/
```

### Fixtures

`test_application/dummyjson/conftest.py` owns DummyJSON-specific fixtures.

Current fixtures:

| Fixture | Purpose |
| --- | --- |
| `dummyjson_base_url` | Reads `DUMMYJSON_URL`, defaulting to `https://dummyjson.com`. |
| `dummyjson_client` | Creates a function-scoped registered `APIClient`. |
| `dummyjson_auth_user` | Loads auth user test data. |
| `dummyjson_credentials` | Builds credentials, allowing env overrides. |
| `dummyjson_expected_user` | Returns expected identity for auth/user assertions. |
| `dummyjson_login_data` | Logs in and returns token response data. |
| `authenticated_dummyjson_client` | Applies bearer token to the client. |

### Helpers

`test_application/dummyjson/helpers.py` wraps framework helpers with
DummyJSON-specific paths:

```python
load_dummyjson_schema("user.schema.json")
load_dummyjson_test_data("auth_user.json")
```

Tests should use these helpers instead of hardcoding full schema/test-data paths.

### Schemas

Schemas live in:

```text
test_application/dummyjson/schemas/
```

They validate response shapes for auth, users, products, carts, posts, and
comments.

### Test Data

DummyJSON test data lives in:

```text
test_application/dummyjson/test_data/
```

Current data files:

| File | Purpose |
| --- | --- |
| `auth_user.json` | Public demo credentials and expected identity. |
| `invalid_login.json` | Negative login password and expected error. |
| `user_search.json` | Search query and expected user identity. |

### Tests

DummyJSON tests live in:

```text
test_application/dummyjson/tests/
```

Current areas:

- authentication and token flows
- user collection, single user, and search
- product detail, pagination, search, and categories
- cart collection and product total consistency
- posts and comments

Every DummyJSON test module sets:

```python
pytestmark = pytest.mark.dummyjson
```

Only the minimal happy-path tests additionally set:

```python
@pytest.mark.dummyjson_smoke
```

This means:

```bash
python -m pytest -m dummyjson
```

runs all DummyJSON tests, while:

```bash
python -m pytest -m dummyjson_smoke
```

runs only the smoke subset.

## Framework Unit Tests

Framework tests live under:

```text
tests/framework/
```

They use separate framework-only data:

```text
tests/framework/test_data/
```

They should not depend on DummyJSON files or live external APIs.

Current coverage:

- `APIClient`
- runtime settings
- API context redaction
- data loading
- schema validation
- performance helpers
- security helpers

All framework unit test modules set:

```python
pytestmark = pytest.mark.framework_unit_test
```

Use `responses` to mock HTTP behavior in framework unit tests. Use Faker only in
a deterministic way, for example:

```python
fake = Faker()
fake.seed_instance(1234)
```

## CI Architecture

CI lives in:

```text
.github/workflows/framework-tests.yml
```

It runs on:

- push to `main`
- pull request to `main`
- manual workflow dispatch

Matrix:

```text
Python 3.10
Python 3.12
```

CI steps:

1. Check out repository.
2. Set up Python with pip cache.
3. Install `requirements.txt`.
4. Compile Python files:

   ```bash
   python -m compileall -q src tests test_application
   ```

5. Run Ruff:

   ```bash
   python -m ruff check .
   ```

6. Run pytest with reports:

   ```bash
   python -m pytest -m "$PYTEST_MARKER" -n auto \
     --html=reports/pytest-report.html \
     --self-contained-html \
     --alluredir=reports/allure-results \
     --junitxml=reports/junit.xml
   ```

7. Upload `reports/` as a workflow artifact.

### Default CI Suite

For push and pull request runs, CI uses an internal `ci_default` scope:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke" -n auto
```

This gives fast feedback on:

- framework unit behavior
- a minimal live API happy path

The full DummyJSON suite is intentionally manual.

### Manual CI Scopes

Manual workflow dispatch supports:

| Scope | Runs |
| --- | --- |
| `framework_unit_test` | Framework unit tests only |
| `dummyjson_smoke` | DummyJSON smoke only |
| `dummyjson` | Full DummyJSON API suite |

Manual dispatch also supports:

```text
parallel=true|false
```

Default is `true`, which runs pytest-xdist with `-n auto`.

Set `parallel=false` when:

- debugging test order
- investigating report output
- reducing concurrent calls to a live API
- working with an API that enforces tight rate limits

## Adding A New API Pack

New APIs should be added under:

```text
test_application/<api_name>/
```

Recommended structure:

```text
test_application/<api_name>/
  conftest.py
  helpers.py
  schemas/
  test_data/
  tests/
  services/
```

The `services/` directory is optional. It is reserved for future service clients
that wrap endpoint-specific operations. At the moment, tests may call
`APIClient` directly.

### Step 1: Create API-Specific Configuration

Add API-specific environment variables to `.env.example` only when they are safe
examples. Do not commit real credentials.

Example for a Stripe pack:

```text
STRIPE_BASE_URL=https://api.stripe.com
STRIPE_API_KEY=replace-me
```

Do not add `STRIPE_BASE_URL` or `STRIPE_API_KEY` to
`src/framework/core/config.py`. The API pack owns them.

### Step 2: Add Pack Fixtures

Create:

```text
test_application/<api_name>/conftest.py
```

Typical fixture shape:

```python
import os
from collections.abc import Callable, Iterator

import pytest

from framework.core import APIClient, get_settings


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.getenv("API_BASE_URL", "https://example.test")


@pytest.fixture
def api_client(
    api_base_url: str,
    register_api_client: Callable[[APIClient], APIClient],
) -> Iterator[APIClient]:
    settings = get_settings()
    client = register_api_client(
        APIClient(
            base_url=api_base_url,
            timeout=settings.timeout,
            retry_count=settings.retry_count,
            retry_backoff_seconds=settings.retry_backoff_seconds,
        )
    )

    yield client

    client.close()
```

If the API needs auth, add auth fixtures in the same API pack. Keep credentials
and expected identity in API-specific test data when possible.

### Step 3: Add Helpers

Create:

```text
test_application/<api_name>/helpers.py
```

Recommended helper style:

```python
from typing import Any

from framework.utils.data_loader import load_json_data
from framework.utils.schema_validator import load_schema


def load_api_schema(schema_name: str) -> dict[str, Any]:
    return load_schema(f"test_application/<api_name>/schemas/{schema_name}")


def load_api_test_data(file_name: str) -> dict[str, Any]:
    data = load_json_data(f"test_application/<api_name>/test_data/{file_name}")
    if not isinstance(data, dict):
        raise TypeError("API test data files must contain a JSON object")
    return data
```

Tests should call the API pack helper rather than constructing paths directly.

### Step 4: Add Schemas And Test Data

Put JSON Schemas here:

```text
test_application/<api_name>/schemas/
```

Put API-specific test data here:

```text
test_application/<api_name>/test_data/
```

Use test data for:

- expected identities
- known public demo users
- expected error messages
- reusable request payloads
- search queries
- IDs used across multiple tests

Avoid hardcoded expected identities in tests when the data represents API-specific
business/demo data.

### Step 5: Add Tests

Create tests under:

```text
test_application/<api_name>/tests/
```

Module convention:

```python
from __future__ import annotations

import pytest

from framework.core import APIClient
from framework.utils.schema_validator import validate_json
from test_application.<api_name>.helpers import load_api_schema

pytestmark = pytest.mark.<api_marker>
```

Test convention:

```python
def test_single_resource_matches_schema(api_client: APIClient) -> None:
    response = api_client.get("/resources/1")
    body = response.json()
    schema = load_api_schema("resource.schema.json")

    assert response.status_code == 200
    validate_json(body, schema)
    assert body["id"] == 1
```

### Step 6: Register Markers

Add markers in `pyproject.toml`:

```toml
markers = [
    "framework_unit_test: unit tests for reusable framework code only",
    "dummyjson: tests that target the DummyJSON API",
    "dummyjson_smoke: minimal happy-path tests for the DummyJSON API",
    "stripe: tests that target the Stripe API",
    "stripe_smoke: minimal happy-path tests for the Stripe API",
]
```

Use underscore names for marker identifiers, not hyphens.

### Step 7: Update CI Deliberately

Do not automatically add every full API suite to default CI. Live API suites can
be slower or dependent on external availability.

Recommended pattern:

- framework unit tests always in default CI
- one minimal smoke suite in default CI
- full live API suites as manual workflow scopes

For a new Stripe pack, a reasonable default could be:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke or stripe_smoke"
```

Only add this after considering credentials, rate limits, stability, and runtime.

## Service Client Convention

`services/` directories are reserved for future endpoint-specific clients. The
current DummyJSON pack does not use service clients yet.

When service clients are introduced, they should:

- live inside the API pack, not `src/framework`
- wrap endpoint paths and request payload construction
- use `framework.core.APIClient` internally
- avoid hiding assertions inside service methods
- return `requests.Response` or simple parsed data consistently

Example:

```python
class ProductService:
    def __init__(self, client: APIClient) -> None:
        self.client = client

    def get_product(self, product_id: int):
        return self.client.get(f"/products/{product_id}")
```

Tests should still own the assertions:

```python
response = product_service.get_product(1)
assert response.status_code == 200
```

## Reporting Conventions

Use the framework client for API calls whenever possible. This ensures:

- request and response logs are emitted
- sensitive values are redacted
- `last_response` is available for failure context
- pytest-html can attach failure context

If a test creates multiple clients, register each one:

```python
client = register_api_client(APIClient(...))
admin_client = register_api_client(APIClient(...))
```

Failure context should be rich, but redacted. Do not attach raw secrets, tokens,
cookies, or API keys to reports.

## Parallel Execution Conventions

The project uses pytest-xdist in CI by default.

Design tests so they can run in parallel:

- avoid shared mutable global state
- keep clients function-scoped unless there is a strong reason not to
- avoid tests depending on execution order
- avoid writing to fixed file names from tests
- avoid reusing live resources that cannot tolerate concurrent operations

For live APIs with rate limits, prefer:

- a small smoke suite in default CI
- full suite as manual CI
- `parallel=false` when debugging or when rate limits are tight

## Code Quality

Ruff is configured in `pyproject.toml`.

Current rule families:

```toml
select = ["E", "F", "I", "B", "PT"]
```

This covers:

- Pycodestyle basics
- Pyflakes errors
- import sorting
- common bugbear issues
- pytest-style checks

Run locally:

```bash
python -m ruff check .
```

CI runs the same check.

## Git-Ignored Artifacts

Generated files should not be committed.

Important ignored paths:

```text
.venv/
.pytest_cache/
.ruff_cache/
__pycache__/
reports/
allure-results/
allure-report/
htmlcov/
.coverage
coverage.xml
*.log
```

Report HTML files are ignored through `reports/`, not through a global `*.html`
rule. This allows future intentional HTML docs or assets to be committed.

## Design Principles

Keep these rules in mind when expanding the framework:

1. Framework code must stay API-agnostic.
2. API-specific configuration belongs to the API pack.
3. Tests should use API pack helpers for schemas and test data.
4. Expected business/demo identities belong in test data, not hardcoded in tests.
5. Framework unit tests must not call live APIs.
6. Default CI should remain fast and reliable.
7. Full live API suites should be manual unless they are stable, fast, and safe.
8. Logs and reports should be useful but redacted.
9. Parallel execution should be assumed unless a suite explicitly opts out.
10. Add abstractions only when they remove real duplication or clarify ownership.

## Future Improvements

- Add explicit API-key authentication helpers only when a concrete API pack needs
  them. Stripe can use the existing bearer-token support because Stripe accepts
  `Authorization: Bearer <api_key>`. Other APIs may require headers such as
  `X-API-Key`, `x-api-key`, or `Api-Key`; those can be supported with a small
  helper such as `set_api_key_header(header_name, api_key)`.

- Keep query-parameter API key support as a last resort. Some APIs accept keys as
  `?api_key=...`, but this is easier to leak through URLs, logs, browser history,
  and reports. If added, it should integrate with the existing URL redaction
  helpers and should be documented as less preferred than header-based auth.

- Consider first-class helpers for multiple common auth styles once the framework
  has at least two real API packs with different needs. Possible additions
  include custom header auth, API key auth, OAuth client-credentials token
  retrieval, signed request auth, and refreshable bearer tokens.

- Introduce API-specific service clients when endpoint usage becomes repetitive
  enough to justify them. Service clients should live inside
  `test_application/<api_name>/services/`, wrap endpoint paths and request
  payload construction, use `framework.core.APIClient` internally, and leave
  assertions in tests.

- Avoid promoting service clients into `src/framework` unless the abstraction is
  truly API-agnostic. A Stripe customer service, product service, or price service
  belongs to the Stripe pack; a generic HTTP client behavior belongs to the
  framework.
