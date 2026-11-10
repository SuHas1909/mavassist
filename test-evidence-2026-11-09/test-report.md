# MavAssist Test Report

**Run date:** 2026-11-09  
**Target:** `http://127.0.0.1:5173/`  
**Browser:** Chromium (Playwright)  
**Backend:** local FastAPI on port 8000, isolated SQLite database, keyword/offline mode

## Result summary

| Test type | Result | Evidence |
|---|---|---|
| Frontend unit/component | **PASS** — 3/3 tests | `logs/frontend-unit-component.log` |
| Frontend build/type check | **PASS** — TypeScript and Vite production build | `logs/frontend-build.log` |
| Backend tests | **PASS** — 79/79; 92% statement coverage | `logs/backend-tests.log`, `logs/backend-tests.xml` |
| End-to-end and accessibility | **FAIL** — 2 passed, 2 failed | `logs/frontend-e2e.log` |
| 360 px mobile flow | **PASS** — 1/1; no horizontal overflow on the directory and assistant views | `logs/mobile-360.log` |
| Local HTTP smoke checks | **PASS** — frontend and `/health` both returned HTTP 200 | `logs/local-smoke.log` |
| Docker smoke | **BLOCKED** — Docker daemon unavailable | `logs/docker-smoke-live.log` |
| Docker live tests | **BLOCKED** — Docker daemon unavailable | `logs/docker-smoke-live.log` |
| Performance, 50 virtual users for 60 seconds | **FAIL** — latency thresholds met, error-rate threshold missed | `logs/performance-load.log`, `logs/local-api-full.log` |
| Performance diagnostic, 10 virtual users for 30 seconds | **PASS** — 600/600 requests succeeded | `logs/performance-load-10vu.log` |

**Overall:** Needs attention. Accessibility checks found serious text-contrast failures, and the 50-user performance run experienced API failures. Docker-based checks could not execute in this environment.

## Failed checks

### Accessibility

The existing Playwright suite reported serious WCAG AA color-contrast violations:

- Resource detail drawer text: contrast ratios of **4.15:1** and **3.71:1** (minimum expected: 4.5:1); one blue control measured **4.03:1**.
- Assistant example button: **2.50:1** (minimum expected: 4.5:1).

The affected E2E tests are the student registration/search/detail/bookmark/chat flow and the student-page accessibility/responsive-navigation flow. The tests stopped at the accessibility assertions, so later actions in those two flows were not verified in that run. No production styling was changed as part of this test-only task.

### 50-user performance

The run generated **3,100 requests**, of which **52 failed** (about **1.68%**). Directory p95 was **221 ms** and chat p95 was **469 ms**, meeting the documented latency targets, but the error-rate target (<1%) failed. The longest observed response was about **30.8 seconds**. The API log contains SQLAlchemy `QueuePool limit of size 5 overflow 10 reached` timeouts; this points to connection-pool exhaustion at this load.

## Environment and limitations

- Frontend: Node.js 24.7.0; frontend was already serving the requested URL.
- Backend tests: Python 3.13.5, pytest; isolated SQLite fixture database.
- Browser E2E: Chromium only. The local API was started with a separate temporary SQLite database and keyword/offline answering; hosted AI was not tested.
- Docker: `docker compose up --build --abort-on-container-exit` failed because the daemon socket was unavailable: `Cannot connect to the Docker daemon at unix:///Users/harmanpreetkaur/.docker/run/docker.sock. Is the docker daemon running?`
- Consequently, Docker image build, container startup/readiness, and containerized live flows remain unverified; they are **blocked**, not passed.
- Performance results are local measurements, not cloud/staging capacity evidence.

## Artifacts

- [Test case workbook](./test-cases.xlsx) — IDs, test types, names, steps, expected/actual results, status, and evidence for the full case inventory.
- [Screenshots](./screenshots/) — captures from desktop, 360 px, detail, assistant, and admin test flows.
- [Logs](./logs/) — frontend/backend test output, JUnit XML, API startup and full request/error log, Docker attempt, and performance runs.

## Test inventory

The workbook contains the 79 backend test cases individually, all 3 frontend unit/component cases, all 5 browser cases, build and local smoke checks, both Docker checks, and both performance scenarios.
