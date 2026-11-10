# Tests and release evidence

## Backend

From backend, with the virtual environment installed:

```powershell
..\.venv\Scripts\python.exe -m pytest tests --cov=app --cov-fail-under=70 --cov-report=term-missing --junitxml=api-tests.xml
```

Default test database is isolated temporary SQLite, never your configured application DB. To test PostgreSQL, set **TEST_DATABASE_URL** to a dedicated disposable test database. The suite drops/recreates its tables; never use production or shared course data. CI supplies a pgvector/PostgreSQL 16 service for this purpose.

Checks include expired JWTs, bcrypt cost, denial for every admin route/method discovered from OpenAPI, no public role escalation, search/filter/pagination, role and record isolation, archive exclusion, date-bounded notices, ten-item recents, ratings, analytics, 90-day deletion, outgoing provider payload and unknown-ID rejection, forced timeout fallback and rate limits.

## Frontend and browsers

From frontend:

```powershell
npm.cmd ci
npm.cmd run build
npm.cmd test
npx.cmd playwright install chromium firefox webkit
```

Run backend at 8000 and frontend at 5173 in separate terminals. Provision a **test-only** admin with the maintenance CLI. Set E2E_ADMIN_EMAIL/E2E_ADMIN_PASSWORD in the test terminal using your local secret-entry method; do not commit them. Then:

```powershell
npm.cmd run test:e2e
```

BASE_URL/API_URL override test origins when needed. Administrator tests skip if admin credentials are absent, so a green run with skipped tests is not full admin evidence. Browser tests mutate test data; use a separate staging/local database. Traces/screenshots can contain demo inputs and credentials: review before sharing and keep them out of version control. Tests inspect errors and accessibility without weakening functional assertions.

BrowserStack: set BROWSERSTACK_USERNAME, BROWSERSTACK_ACCESS_KEY, HTTPS BASE_URL/API_URL and test admin credentials, then `npm.cmd run test:cloud`. This configuration uses its remote Chrome endpoint and requires your own account/plan. It has not been run here and should not be reported as a verified cloud-browser result.

## AI evaluation

`docs/ai-evaluation-100.json` has 100 **synthetic draft** cases. Team members must review labels, add independent paraphrases and ambiguous/non-native phrasing, and record reviewer/date/version before using it for acceptance. Name/tag-derived cases are smoke checks, not independent accuracy evidence.

Set MAVASSIST_TOKEN to an authenticated student's token without committing it, then run from root:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_ai.py --api http://localhost:8000 --require-rag --output ai-evaluation-results.json
```

The runner respects the demo's chat rate limit and may take about six minutes. `--require-rag` fails if any case used keyword/fallback mode or thresholds are missed (top-1 >=80%, top-3 >=95%, unknown offices =0). Running without it reports offline behavior honestly. Do not call offline evaluation “AI accuracy.” Helpful-rating acceptance >=75% needs actual collected participant feedback, not the synthetic test's one-click positive example.

CI runs offline evaluation on pull requests. Hosted evaluation is an explicit workflow_dispatch job using your staging API and a fresh 60-minute student token in GitHub secrets. Do not store expiring real student tokens long-term. For automated recurring runs, provision dedicated test accounts using an approved secret-management flow.

## Performance, reliability and security

Install k6 separately. In a private staging deployment, set API_URL/MAVASSIST_TOKEN and run `k6 run scripts/load-test.js`. It uses 50 VUs for 60 seconds, measures non-AI p95 <1000ms and chatbot p95 <5000ms, and tracks fallback <3000ms when the provider is disabled. Run both provider-on and forced-provider-off scenarios. The shipped limiter is per-IP: record whether RATE_LIMIT was disabled for processing-capacity measurements, then restore it. A hosted cold-start run must be measured separately.

Run `npm audit` in frontend and `python -m pip_audit -r backend/requirements.txt` after installing pip-audit in your test environment. Capture actionable findings and fixes. Use OWASP ZAP baseline against your authorized staging URL, e.g. its official Docker image `ghcr.io/zaproxy/zaproxy:stable` with `zap-baseline.py -t YOUR_STAGING_URL`. Never scan systems you do not own/control. ZAP, k6, dependency audits and BrowserStack are not implied to have passed because their commands are documented.

Hosted RAG outages are simulated in unit tests with a forced timeout; real network stalls, embedding cold starts and 50-user contention require deployed testing. Source-level timeout settings are not a latency measurement.

## Usability study

Not run. The site is a local demo and is not hosted, so usability (SUS) sessions with students could not be held. This is future work once the site is deployed (see section 8 of docs/MavAssist_Test_Summary_and_Defect_Report.docx and defect D-13).

## GitHub review gate

After pushing this directory as your repository root, enable branch protection/rulesets for the main branch: require a peer-reviewed pull request and successful `api`/`browser` checks. The workflow alone cannot change your account's repository settings or guarantee that direct merges are blocked. Document real sprint reviews/retrospectives, acceptance decisions, issue-to-commit links and defects separately.
