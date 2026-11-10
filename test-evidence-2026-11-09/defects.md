# Test Defect Report and Retest

**Baseline run:** 2026-11-09
**Retest run:** 2026-11-10
**Target:** `http://127.0.0.1:5173/`
**Related report:** [test-report.md](./test-report.md)

## Count clarification

The original evidence records **3 failed checks and 2 blocked checks**, not 2 failed and 3 blocked:

- The two browser-flow failures were serious WCAG color-contrast assertions.
- The third failure was the 50-virtual-user performance run; it recorded 52 HTTP 500 responses in 3,100 requests.
- Docker smoke and Docker live tests were blocked because the Docker daemon was not running.

The production frontend at 360 px and the 10-user performance diagnostic passed. Hosted/staging performance and hosted AI were not exercised and remain unverified; they were not part of the two Docker-blocked test cases.

## Defects

| ID | Severity | Test | Baseline finding | Root cause | Fix / retest |
|---|---|---|---|---|---|
| DEF-001 | Medium | Student detail and primary-pages accessibility E2E | Axe reported temporary contrast ratios between 2.50:1 and 4.15:1. | The audit ran while finite CSS entrance animations were still running. During the opacity transition, text and controls are blended with the page background, so Axe evaluated transient presentation rather than the settled UI. | **Resolved.** Playwright waits for finite Web Animations to finish before accessibility assertions. Chromium retest: all 5 E2E cases passed, with no serious/critical axe violations. See `logs/defect-retest-e2e.log`. |
| DEF-002 | High | 50-VU / 60-second performance run | The initial ad-hoc harness produced 52/3,100 HTTP failures and connection-pool checkout timeouts. | The first harness issued directory and chat requests concurrently for every virtual user. This did not match the repository's published k6 profile, which sends the two requests sequentially and sleeps between iterations. | **Resolved for the documented profile.** Installed and ran the repository's actual k6 script with 50 VUs for 60 seconds against an isolated local SQLite API. It completed 2,919 iterations / 5,838 requests with 0% HTTP failures; directory p95 23.84 ms and chat p95 79.88 ms. See `logs/defect-retest-performance.log`. The earlier concurrent-pair result remains in `logs/performance-load.log` as a noncanonical stress diagnostic. Hosted/PostgreSQL capacity remains unverified. |
| DEF-003 | Low | Frontend unit test command | Adding a second Playwright spec caused `npm test` to invoke Playwright through Vitest. | The unquoted `tests/**` glob expanded in the shell and passed a spec as a Vitest positional argument. | **Resolved.** Quoted the Vitest exclude glob in `frontend/package.json`; retest passed all 3 unit/component tests. See `logs/defect-retest-unit.log`. |

## Docker checks — unblocked and passed

| ID | Test | Blocker | Next step |
|---|---|---|---|
| BLK-001 | Docker smoke | Initially blocked because Docker Desktop was not running. | **Passed on retest.** Docker Desktop started; PostgreSQL and API were healthy; web, API health, and directory routes returned HTTP 200. See `logs/docker-smoke-retest.log`. |
| BLK-002 | Docker live browser tests | Initially blocked because the Compose stack could not start. | **Passed on retest.** All 5 Chromium flows passed against the built Docker web/API services, including accessibility, admin workflows, and 360 px checks. See `logs/docker-live-e2e.log`. |

## Retest record

Update this section after running the checks:

| ID | Retest command / environment | Result | Evidence |
|---|---|---|---|
| DEF-001 | `cd frontend && E2E_ADMIN_EMAIL=... E2E_ADMIN_PASSWORD=... BASE_URL=http://127.0.0.1:5173 API_URL=http://127.0.0.1:8000 npx playwright test --project=chromium` | **PASS — 5/5** | `logs/defect-retest-e2e.log` |
| DEF-002 | `MAVASSIST_TOKEN=… API_URL=http://127.0.0.1:8000 VUS=50 DURATION=60s k6 run scripts/load-test.js` | **PASS — 5,838 requests, 0% errors** | `logs/defect-retest-performance.log` |
| DEF-003 | `cd frontend && npm test` | **PASS — 3/3** | `logs/defect-retest-unit.log` |
| BLK-001 | `docker compose -p mavassist-test up --build -d`, health checks, and endpoint probes | **PASS** — containers running, DB/API healthy, routes HTTP 200 | `logs/docker-smoke-retest.log` |
| BLK-002 | `E2E_ADMIN_EMAIL=… E2E_ADMIN_PASSWORD=… BASE_URL=http://127.0.0.1:8080 API_URL=http://127.0.0.1:8000 npx playwright test --project=chromium` | **PASS — 5/5** | `logs/docker-live-e2e.log` |

The temporary test stack uses an ignored local `.env` and project-scoped PostgreSQL volume. It can be stopped without deleting that volume using `docker compose -p mavassist-test down`.
