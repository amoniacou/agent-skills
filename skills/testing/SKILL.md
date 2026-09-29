---
name: testing
description: Rules for writing tests - which level to test at, when a mock is allowed, isolation, waiting, structure and fixtures. Load it yourself, without being asked, before writing or changing tests.
when_to_use: Before creating or editing a test file (*_test.go, *_spec.rb, test_*.py, *.test.ts), a test suite or helper, fixtures, or CI steps that run tests. Before adding a mock, stub, fake or sleep to a test. Also on "write tests", "add a test", "cover this", "mock", "e2e", "integration test".
---

# Testing

## 1. Pick the level

```
logic with no I/O              ──► unit test
your code + database / broker  ──► integration test with the real thing (the default)
Kubernetes operator            ──► envtest (real API server) + e2e on kind
third-party API you don't own  ──► record and replay (go-vcr, VCR) or an HTTP mock (httpmock, webmock)
```

- Most tests are integration tests. Write scenarios with several records and several steps, not one call with one row.
- Run the same dependencies locally and in CI: docker-compose, a service container or a GitHub action for the broker.
- Run e2e against every supported version (a k8s version matrix). On failure, save logs and cluster objects as a CI artifact.

## 2. Mocks only for failures you cannot cause

First try to break the real dependency: cancel the real subscription, close the real connection, stop the container. Then check how the code reacts. Use a mock or double only when the failure cannot be caused for real or not reliably.

Never mock your own code to test your own code.

## 3. Isolation

- Every test gets its own resources: unique names (`jobs_#{suffix}`), a separate database or Redis DB, its own namespace.
- Reset data before the run: SQL fixtures, `database_cleaner`, dropping and recreating the schema.
- If tests share state and cannot be isolated, run them one after another (`go test -p=1`) and make that visible in the Makefile or CI, not hidden.
- Tests do not depend on each other or on their order.

## 4. Wait for a condition, never sleep

Wait until the condition holds, with a timeout: `wait_until { consumer.healthy? }`, `Eventually(...)`. Read the timeout from the environment (`RABBITMQ_TIMEOUT`) so slow CI can raise it.

## 5. Missing dependencies

Locally, a test may `Skip` when its dependency (cluster, database, broker) is not reachable. In CI (`CI` is set), a missing dependency is a failure, not a skip. Otherwise a whole suite can stop running and nobody notices.

## 6. Structure

- One suite file per package with the shared setup: `*_suite_test.go`, `suite_test.go`, `spec/support/`.
- One test file per source file, with the same name (see the naming skill).
- A family of classes shares one set of examples: RSpec `it_behaves_like` with `valid_list` / `invalid_list` per type, table-driven tests in Go.
- Keep expected output in fixture files next to the test (`fixtures/*.json`). Check XML against its XSD.
- Name a test after the behaviour: "is unhealthy once the subscription channel is gone", not "test health 2".

## 7. Every assertion must be explainable

If you cannot say why the expected value is right, the test proves nothing. Find out, or do not assert it. `Equal(http.StatusTooManyRequests, code)` with nobody knowing why is a bug report, not a test.

## 8. No disabled tests

Delete a test that is switched off. Do not comment it out or rename it so the runner skips it (`ATestTokenProcessor`). Git remembers it.
