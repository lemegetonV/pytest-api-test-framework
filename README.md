# Pytest API Test Framework

A reusable Pytest-based framework for API testing. The project separates
API-agnostic framework code from concrete API test packs, so new APIs can be
added without changing the core framework.

The current repository includes DummyJSON as the reference API pack.

## Project Structure

```text
src/framework/
  core/
    client.py              # reusable requests-based API client
    config.py              # framework runtime settings
  utils/
    api_context.py         # redacted request/response context
    data_loader.py         # project-relative JSON/CSV loading
    schema_validator.py    # JSON Schema helpers
    security.py            # redaction and security helpers
    performance.py         # lightweight timing helpers

test_application/
  conftest.py              # shared pytest hooks for API packs
  <api_name>/
    conftest.py            # API-specific fixtures
    helpers.py             # API-specific schema/data helpers
    schemas/               # API-specific JSON Schemas
    test_data/             # API-specific test data
    tests/                 # API-specific test cases
    services/              # optional future service clients

tests/framework/
  core/                    # framework unit tests
  utils/                   # framework utility unit tests
  test_data/               # framework-only test data
```

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional local environment file:

```bash
cp .env.example .env
```

## Configuration

Framework-wide settings:

```text
TEST_TIMEOUT=10
TEST_RETRY_COUNT=1
TEST_RETRY_BACKOFF_SECONDS=0.5
TEST_ENV=local
LOG_LEVEL=INFO
```

API packs may define their own environment variables, such as base URLs,
credentials, account IDs, or feature flags. API-specific settings should stay
with the API pack and should not be added to `src/framework/core/config.py`.

## Test Suites

The framework uses marker-based suites.

| Marker pattern | Purpose |
| --- | --- |
| `framework_unit_test` | Unit tests for reusable framework code. These should not call live APIs. |
| `<api_name>` | Full test coverage for a concrete API pack. |
| `<api_name>_smoke` | Minimal happy-path suite for a concrete API pack. |

Current API-pack markers:

```text
dummyjson
dummyjson_smoke
```

## Local Commands

Run all collected tests:

```bash
python -m pytest
```

Run framework unit tests:

```bash
python -m pytest -m framework_unit_test
```

Run the current smoke suite:

```bash
python -m pytest -m dummyjson_smoke
```

Run the current full API pack suite:

```bash
python -m pytest -m dummyjson
```

Run the default CI selection locally:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke"
```

Run tests in parallel:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke" -n auto
```

Run code quality checks:

```bash
python -m ruff check .
python -m compileall -q src tests test_application
```

## Reports

Generate local HTML, JUnit, and Allure result files:

```bash
python -m pytest \
  -m "framework_unit_test or dummyjson_smoke" \
  -n auto \
  --html=reports/pytest-report.html \
  --self-contained-html \
  --alluredir=reports/allure-results \
  --junitxml=reports/junit.xml
```

Generated reports are written under `reports/` and are ignored by Git.

The API client logs request and response details at `INFO` level. Sensitive
headers, query parameters, and common token/password fields are redacted before
they are logged or attached to failure reports.

## Client Defaults

`APIClient` defaults to:

```http
Accept: application/json
```

It does not set a global `Content-Type`. Request body content type is inferred
per request by `requests`, for example:

```python
client.post("/json-endpoint", json={"name": "example"})
client.post("/form-endpoint", data={"name": "example"})
```

Use request-level headers when an endpoint needs a custom media type.

## CI

GitHub Actions workflow:

```text
.github/workflows/framework-tests.yml
```

Runs on:

- push to `main`
- pull request to `main`
- manual workflow dispatch

Python matrix:

```text
3.10
3.12
```

CI runs:

```bash
python -m compileall -q src tests test_application
python -m ruff check .
python -m pytest -m "framework_unit_test or dummyjson_smoke" -n auto
```

The pytest command also generates HTML, JUnit, and Allure result artifacts.

Manual workflow dispatch currently supports:

| Scope | Runs |
| --- | --- |
| `framework_unit_test` | Framework unit tests only |
| `dummyjson_smoke` | Current API smoke suite |
| `dummyjson` | Current full API pack suite |

Manual dispatch also supports `parallel=true|false`. It defaults to `true`.

## Adding APIs

Add new APIs under:

```text
test_application/<api_name>/
```

Recommended pack structure:

```text
test_application/<api_name>/
  conftest.py
  helpers.py
  schemas/
  test_data/
  tests/
  services/
```

The framework should stay reusable and API-agnostic. API-specific fixtures,
schemas, expected identities, credentials, and base URLs belong to the API pack.

See [docs/architecture.md](docs/architecture.md) for detailed framework
architecture, conventions, and guidance for adding new API test packs.
