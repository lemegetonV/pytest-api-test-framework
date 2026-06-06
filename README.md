# Pytest API Test Framework

A reusable Pytest-based API testing framework with a sample DummyJSON API test
pack. The project is organized so the framework code remains API-agnostic, while
each concrete API owns its fixtures, schemas, test data, and tests.

## What This Repo Contains

```text
src/framework/
  core/
    client.py              # reusable requests-based API client
    config.py              # framework runtime settings
  utils/
    api_context.py         # redacted request/response context for logs/reports
    data_loader.py         # project-relative JSON/CSV loading
    schema_validator.py    # JSON Schema helpers
    security.py            # redaction and security assertion helpers
    performance.py         # lightweight timing helpers

test_application/
  conftest.py              # shared pytest reporting hooks for API packs
  dummyjson/
    conftest.py            # DummyJSON fixtures and clients
    helpers.py             # DummyJSON schema/test-data helpers
    schemas/               # DummyJSON JSON Schema files
    test_data/             # DummyJSON-specific test data
    tests/                 # DummyJSON API tests
    services/              # reserved for future service clients

tests/framework/
  core/                    # framework unit tests for core code
  utils/                   # framework unit tests for utility code
  test_data/               # framework-only test data
```

## Prerequisites

- Python 3.10 or newer
- `pip`

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

Framework-wide runtime settings are loaded from environment variables, with
`.env` support.

```text
TEST_TIMEOUT=10
TEST_RETRY_COUNT=1
TEST_RETRY_BACKOFF_SECONDS=0.5
TEST_ENV=local
LOG_LEVEL=INFO
```

DummyJSON-specific settings live with the DummyJSON API pack:

```text
DUMMYJSON_URL=https://dummyjson.com
```

`DUMMYJSON_USERNAME` and `DUMMYJSON_PASSWORD` may also be set to override the
public demo credentials used by the DummyJSON auth fixtures.

## Test Suites

The project uses three pytest markers:

| Marker | Purpose |
| --- | --- |
| `framework_unit_test` | Unit tests for reusable framework code only. These tests do not call live APIs. |
| `dummyjson` | Full DummyJSON API coverage. These tests call the live DummyJSON API. |
| `dummyjson_smoke` | Minimal happy-path DummyJSON coverage for fast CI confidence. |

## Local Commands

Run all tests:

```bash
python -m pytest
```

Run framework unit tests only:

```bash
python -m pytest -m framework_unit_test
```

Run DummyJSON smoke tests only:

```bash
python -m pytest -m dummyjson_smoke
```

Run full DummyJSON API coverage:

```bash
python -m pytest -m dummyjson
```

Run the default CI selection locally:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke"
```

Run tests in parallel with pytest-xdist:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke" -n auto
```

Run Ruff:

```bash
python -m ruff check .
```

Check Python syntax:

```bash
python -m compileall -q src tests test_application
```

## Reports

The CI command generates:

```text
reports/pytest-report.html
reports/junit.xml
reports/allure-results/
```

You can generate the same report locally:

```bash
python -m pytest \
  -m "framework_unit_test or dummyjson_smoke" \
  -n auto \
  --html=reports/pytest-report.html \
  --self-contained-html \
  --alluredir=reports/allure-results \
  --junitxml=reports/junit.xml
```

Reports are ignored by Git through the `reports/` entry in `.gitignore`.

### Logging And Failure Context

The API client logs each request and response at `INFO` level:

- HTTP method and URL
- redacted request params/body
- response status
- redacted response body preview

On test failures, `test_application/conftest.py` attaches redacted API response
context to the pytest-html report. Failure context includes method, URL, status,
headers, request id when available, elapsed time, and a redacted body preview.
Sensitive headers, query parameters, and common token/password fields are
redacted before being logged or attached to reports.

## Retry Behavior

`APIClient` retries transient network failures for `GET` requests only.

Current defaults:

```text
TEST_RETRY_COUNT=1
TEST_RETRY_BACKOFF_SECONDS=0.5
```

This means one retry after the first failed `GET`, with a 0.5 second wait before
retrying. Retries currently apply to `requests.ConnectionError` and
`requests.Timeout`.

Non-GET methods are not retried by default.

## CI Behavior

GitHub Actions workflow:

```text
.github/workflows/framework-tests.yml
```

Runs on:

- push to `main`
- pull request to `main`
- manual workflow dispatch

Python versions:

```text
3.10
3.12
```

Default push/PR CI runs:

```bash
python -m pytest -m "framework_unit_test or dummyjson_smoke" -n auto
```

CI also runs:

```bash
python -m compileall -q src tests test_application
python -m ruff check .
```

Manual workflow dispatch supports these scopes:

| Scope | Marker expression |
| --- | --- |
| `framework_unit_test` | `framework_unit_test` |
| `dummyjson_smoke` | `dummyjson_smoke` |
| `dummyjson` | `dummyjson` |

Manual dispatch also exposes a `parallel` boolean. It defaults to `true`; set it
to `false` when debugging ordering-sensitive behavior or when live API
concurrency needs to be reduced.

## Adding More APIs

New APIs should be added under `test_application/<api_name>/`, not under
`src/framework/`.

Recommended shape:

```text
test_application/<api_name>/
  conftest.py
  helpers.py
  schemas/
  test_data/
  tests/
  services/
```

The framework should stay reusable and API-agnostic. API-specific base URLs,
credentials, schemas, and expected identities should live inside the API pack.

See [docs/architecture.md](docs/architecture.md) for detailed conventions.
