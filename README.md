# MavAssist

A UTA student-services assistant built for **CSE 6324 — Team 3**. Find campus resources, ask questions, and get next steps with links to official sources.

## Features

- Directory of 50 UTA offices and services with location, hours, contact details and the date they were checked against the official page.
- Relevance-ranked keyword search, popular searches and multi-select category filters.
- Assistant that routes a plain-language question to one recommended office (with the reason, details and next steps), up to two alternatives and numbered sources, or asks a clarifying question when nothing matches confidently.
- Student accounts, saved resources and recently viewed services.
- Admin tools: service create/edit/archive with filtering and pagination, categories, time-limited notices and a usage dashboard with a daily activity chart.

Screenshots of every screen are in `docs/screenshots/`; test, load and AI-evaluation results are in `docs/VERIFICATION.md`.

## Technology

React, TypeScript, Vite, Tailwind CSS, FastAPI, and SQLAlchemy. Local setup uses SQLite and source-based answers. PostgreSQL/pgvector and AI-generated answers are available through additional configuration.

## Run locally on Windows

Install **Python 3.12** and **Node.js 22.12+**. Open PowerShell in the project folder.

**1. Set up and start the backend:**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe scripts/configure.py
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.manage seed
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

**2. Open another PowerShell window in the project folder and start the frontend:**

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

**3. Open [MavAssist](http://localhost:5173) and create a student account.** Keep both terminals running: one serves the API and the other serves the website. API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

To create an administrator, run this from the `backend` folder in another terminal:

```powershell
..\.venv\Scripts\python.exe -m app.manage create-admin
```

The local setup works without an API key. It returns cited source summaries; AI-generated answers require a configured API key and model. Verify current campus details on the linked official pages.

### Turn on AI answers (OpenRouter)

`scripts/configure.py` asks for an optional OpenRouter key (hidden input) and saves it only in `backend/.env`, which is git-ignored. To add it later, put these lines in `backend/.env` and restart the API:

```dotenv
OPENROUTER_API_KEY=sk-or-...your key...
OPENROUTER_MODEL=openai/gpt-4o-mini
```

**Free tier:** OpenRouter's free models (ids ending `:free`) allow 50 requests per day and 20 per minute. Once the daily allowance is used up, or the provider refuses a request, MavAssist answers from cited sources (keyword and semantic retrieval) until the limit resets; nothing breaks, but answers are no longer AI-written.

`http://127.0.0.1:8000/health` shows `"llm": true` when the key is loaded. Answers then carry the badge **AI answer with sources**. Never commit the key or put it in frontend code; on Render, add it as a secret environment variable.

### What the assistant does with different questions

| Question type | Example | Response |
|---|---|---|
| Campus need | "I paid extra tuition, how do I get a refund?" | Recommended office, AI-written explanation from its official guidance, next steps, numbered sources |
| Unclear | "ambiguous question" | Asks for one detail and suggests likely offices |
| Off-topic | "tell me a joke", "I want a girlfriend" | **Not found in MavAssist**, with a kind redirect (e.g. Student Organizations) when one fits |
| Small talk | "hi", "thanks" | Short greeting with example questions |
| Dishonest/illegal | "help me cheat on my exam" | Declines and points to Tutoring / Writing Center |
| Violence or danger | threats, weapons, "active shooter" | Declines, shows 911 and UTA Police call buttons |
| Crisis | self-harm or suicide | MAVS TALK 817-272-8255, 988 and 911 call buttons, plus CAPS |

Safety categories are decided by tested rules in `backend/app/guard.py`, not by the model, so they work even if the AI provider is down. See [docs/RAG.md](docs/RAG.md).

## Documentation

- [Deployment instructions](DEPLOYMENT.md)
- [Chat and RAG setup](docs/RAG.md)
- [User guide](docs/USER_GUIDE.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Test results](docs/VERIFICATION.md)
- [Defect log](docs/DEFECTS.md)
- [Scope changes](docs/SCOPE_CHANGES.md)
- [Security scan](docs/SECURITY_SCAN.md)
- [Directory data sources](docs/DATA_SOURCES.md)

## Test evidence

| What | Where |
|---|---|
| Test case workbook (145 passed cases listed; AI routing cases, summary, defects, traceability) | [docs/MavAssist_Test_Cases.xlsx](docs/MavAssist_Test_Cases.xlsx) |
| Test summary and defect report | [docs/MavAssist_Test_Summary_and_Defect_Report.docx](docs/MavAssist_Test_Summary_and_Defect_Report.docx) |
| Final run, Nov 10: raw results (JUnit XML, browser results, logs), ZAP reports, screenshots | [test-evidence-final-2026-11-10/](test-evidence-final-2026-11-10/) |
| Nov 10 re-run: load tests (SQLite and Docker PostgreSQL), Docker smoke, AI evaluations | [test-evidence-2026-11-10/](test-evidence-2026-11-10/) |
| Nov 9 baseline and retest | [test-evidence-2026-11-09/](test-evidence-2026-11-09/) |
| Label review (not run yet) | [docs/LABEL_REVIEW.md](docs/LABEL_REVIEW.md) |

The workbook and report are generated from the raw results by `scripts/build_test_report.py`, which stops if any
total differs between the two files or from the raw results.

### Requirement status (final run, Nov 10)

152 cases defined: 145 run and passed, 2 run and failed (PERF-003, AI-005), 5 not executed (blocked: AI-003; descoped: XB-001; not run: LABEL-001, STAGE-001, STAGE-002). IDs and reasons are in section 8 (Scope and known limitations) of the [test summary report](docs/MavAssist_Test_Summary_and_Defect_Report.docx).

| Status | Requirements |
|---|---|
| Met | FR-01, FR-02, FR-03, FR-05, FR-06, FR-07, FR-08, FR-09, FR-10, NFR-03 |
| Partial | FR-04 (offline routing passes: 97% / 90% top-1; full hosted evaluation blocked by provider limits; labels not reviewed), NFR-01 (local SQLite load passes; Docker PostgreSQL and hosted answer latency miss the targets), NFR-02 (role tests and security scan pass; HTTPS staging not run), NFR-04 (accessibility and 360 px pass on three browser engines; usability study not run because the site is a local demo and is not hosted), NFR-05 (fallback and coverage pass; staging not run) |

### Running the tests

```powershell
# Backend (isolated test database). Run it as CI does, with no AI key in backend/.env, so no hosted calls are made.
cd backend; python -m pytest tests --cov=app

# Frontend build and unit tests
cd frontend; npm run build; npm test

# Browser tests on Chromium, Firefox and WebKit (API on :8000 and web on :5173 running; test administrator provisioned)
cd frontend; $env:E2E_ADMIN_EMAIL='...'; $env:E2E_ADMIN_PASSWORD='...'; npx playwright test

# Load test: 50 users for 60 s (needs a student token; disable the rate limit only on a private test server)
k6 run -e MAVASSIST_TOKEN=<token> -e API_URL=http://127.0.0.1:8000 scripts/load-test.js

# Routing evaluation (offline, or hosted with --require-rag; --sample N keeps a free-tier key within its daily cap)
python scripts/evaluate_ai.py --api http://127.0.0.1:8000 --output results.json

# Rebuild the test workbook and report from the raw results
pip install -r scripts/requirements-report.txt; python scripts/build_test_report.py --pdf
```

## Contributors

Commits are counted from the git history (merges included); Azure DevOps counts are the stories and tasks assigned on
the board, not a measure of who wrote which code.

| Name | Commits | Azure DevOps stories / tasks assigned |
|---|---|---|
| Ashwinder Singh | 14 | 8 / 24 |
| Krisha Patel | 1 | 4 / 13 |
| Suhas Surendra Kumar | 4 | 1 / 13 |
| Harmanpreet Kaur | 3 | 1 / 12 |

Independent student project; not an official UTA service.
