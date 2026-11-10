# MavAssist Test Report

**Retest date:** 2026-11-10 (baseline: 2026-11-09)
**Targets:** `http://127.0.0.1:5173/` and Docker Compose `http://127.0.0.1:8080/`
**Browser:** Chromium (Playwright)  
**Backend:** Docker retest used PostgreSQL 16/pgvector with keyword/offline mode; the separate 79-test pytest suite used isolated SQLite

## Result summary

| Test type | Result | Evidence |
|---|---|---|
| Frontend unit/component | **PASS** — 3/3 tests (retest also passed) | `logs/defect-retest-unit.log` |
| Frontend build/type check | **PASS** — TypeScript and Vite production build | `logs/defect-retest-build.log` |
| Backend tests | **PASS** — 79/79; 92% statement coverage | `logs/defect-retest-backend.log`, `logs/defect-retest-backend.xml` |
| End-to-end and accessibility | **PASS on retest** — 5/5 Chromium tests; zero serious/critical Axe findings | `logs/defect-retest-e2e.log` |
| 360 px mobile flow | **PASS** — included in the 5/5 Chromium retest; no horizontal overflow | `logs/defect-retest-e2e.log` |
| Local HTTP smoke checks | **PASS** — frontend and `/health` both returned HTTP 200 | `logs/local-smoke.log` |
| Docker smoke | **PASS** — PostgreSQL/API healthy; web, health, and directory routes returned HTTP 200 | `logs/docker-smoke-retest.log` |
| Docker live browser tests | **PASS** — 5/5 Chromium flows against the Compose web/API services | `logs/docker-live-e2e.log` |
| Performance, canonical k6 profile (50 VUs × 60 seconds) | **PASS** — 5,838 requests, 0% errors; directory p95 23.84 ms, chat p95 79.88 ms | `logs/defect-retest-performance.log` |
| Noncanonical concurrent-pair diagnostic | **FAIL** — 52/3,100 requests failed; this harness ran search and chat concurrently per VU instead of the published sequential profile | `logs/performance-load.log` |
| Performance diagnostic (10 VUs × 30 seconds) | **PASS** — 600/600 requests succeeded | `logs/performance-load-10vu.log` |

**Overall:** **94/94 inventoried test cases passed** across unit/component, backend, browser, smoke, Docker, and canonical performance testing. The additional noncanonical concurrent-request diagnostic failed and is retained separately; cloud deployment, hosted AI, and hosted-capacity validation remain outside this local result.

## Baseline findings and fixes

### Accessibility — resolved

The first Axe run reported serious WCAG AA contrast ratios of 4.15:1 and 3.71:1 in the detail drawer and 2.50:1 for an assistant example button. Investigation showed Axe ran during finite CSS entrance animations, when opacity blended the text with the background. The E2E tests now wait for finite Web Animations to finish before auditing. The complete Chromium suite passed **5/5**, including accessibility and 360 px checks, with no serious or critical violations. See `logs/defect-retest-e2e.log`.

### Performance — canonical profile resolved; hosted capacity unverified

The initial custom load harness issued search and chat concurrently for each VU and saw pool timeouts. The repository's documented k6 test sends those operations sequentially. Rerunning that canonical script with **50 VUs for 60 seconds** completed **2,919 iterations / 5,838 requests with 0% errors**; directory p95 was **23.84 ms**, and chat p95 was **79.88 ms**. The first run is retained as a noncanonical stress diagnostic in `logs/performance-load.log`; canonical retest evidence is in `logs/defect-retest-performance.log`.

## Docker verification and environment limits

The original run had two Docker checks blocked because the Docker daemon was unavailable. Docker Desktop was subsequently started. The isolated Compose stack built and ran PostgreSQL, API, and web; PostgreSQL and API health checks passed, and the web/API health/directory endpoints returned HTTP 200. All five browser flows then passed against the Docker web/API. Evidence is in `logs/docker-smoke-retest.log` and `logs/docker-live-e2e.log`.

## Environment and limitations

- Frontend: Node.js 24.7.0; frontend was already serving the requested URL.
- Backend tests: Python 3.13.5, pytest; isolated SQLite fixture database.
- Browser E2E: Chromium only. The local API was started with a separate temporary SQLite database and keyword/offline answering; hosted AI was not tested.
- Docker: initial daemon-start blocker was resolved by starting Docker Desktop; a project-scoped Compose stack subsequently passed its smoke and live browser tests.
- The canonical performance profile ran locally on SQLite; it is not cloud/PostgreSQL capacity evidence.

## Artifacts

- [Test case workbook](./test-cases.xlsx) — IDs, test types, names, steps, expected/actual results, status, and evidence for the full case inventory.
- [Defect report and retest record](./defects.md) — baseline findings, fixes, and blocked checks.
- [Screenshots](./screenshots/) — captures from desktop, 360 px, detail, assistant, and admin test flows.
- [Logs](./logs/) — frontend/backend test output, JUnit XML, API startup and full request/error log, Docker attempt, and performance runs.

## Test inventory

The workbook contains the 79 backend test cases individually, all 3 frontend unit/component cases, all 5 browser cases, build and local smoke checks, both Docker checks, and both performance scenarios.
