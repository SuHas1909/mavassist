# Verification — October 20, 2026 (Sprint 2 progress build)

Machine-readable records live next to this file: `test-run-summary.json`, `backend-tests.xml`, `backend-coverage.json`, `playwright-results.json`, `k6-load-results.json`, `k6-fallback-results.json`, `ai-evaluation-*.json`, and the dependency audits. All runs were made on the local build (SQLite, keyword/offline AI mode, single Uvicorn process) on October 20, 2026. They do not certify a cloud deployment.

## Results against the proposal's quality targets

| Requirement / target | Method | Result | Status |
|---|---|---|---|
| Backend tests (FR-01…FR-10, NFR-02/03/05) | pytest, 28 tests | **28 passed** | Pass |
| NFR-05 backend coverage ≥ 70% | pytest-cov | **93%** statement coverage | Pass |
| Frontend unit tests | Vitest | **3 passed** | Pass |
| Production build | `tsc -b && vite build` | Passed | Pass |
| End-to-end flows (registration, search/filter, detail, bookmark, recent, chat, rating, admin CRUD/archive/categories/notices, analytics, clarification) | Playwright, Chromium | **4 / 4 passed** | Pass |
| NFR-04 zero serious/critical WCAG 2.1 AA issues on primary pages | axe-core inside the Playwright flows (sign-in, directory, detail drawer, saved, recent, assistant, admin manage/notices, insights) | **0 serious / 0 critical** | Pass |
| Mobile layout | 390 px viewport, horizontal overflow | 0 px overflow | Pass |
| NFR-01 p95 ≤ 1 s non-AI, ≤ 5 s chat at 50 users | k6, 50 VUs × 60 s, 4,420 requests | non-AI p95 **391 ms**; chat p95 **756 ms**; 0% errors | Pass (local) |
| NFR-05 fallback ≤ 3 s when AI is unavailable | k6, 50 VUs × 60 s against an API with an unreachable provider key | 100% answers in fallback mode; fallback p95 **643 ms**; non-AI p95 291 ms; 0% errors | Pass (local) |
| AI top-1 ≥ 80%, top-3 ≥ 95%, 0 unknown offices (100-question set v2) | `scripts/evaluate_ai.py` against the live API | top-1 **97%**, top-3 **100%**, unknown offices **0** | Pass (offline mode) |
| Same metrics on a held-out set written after tuning (50 questions) | same script, `ai-evaluation-holdout-50.json` | top-1 **90%**, top-3 **100%**, unknown offices **0**; 5/5 out-of-scope questions ask for clarification | Pass (offline mode) |
| Baseline before Sprint 2 AI work (same v2 set) | same script, Sprint 1 code | top-1 64%, top-3 64% | Reference |
| NFR-02 dependency security | `pip-audit` (backend), `npm audit` (frontend) | 0 known vulnerabilities each | Pass |

Screenshots in `screenshots/` were captured from the running application (desktop 1440 px and mobile 390 px).

## What changed between the baseline and this build

* **Directory data (FR-02, risk R-03):** all 50 services now carry location, hours, contact and source URL collected from public uta.edu pages (`backend/app/services_seed.json`, `DATA_SOURCES.md`); 48 are marked verified, 2 are flagged for review.
* **Chatbot (FR-04):** service-level ranking with domain vocabulary normalisation and phrase matching; each answer returns one recommended office with a reason, details and last-updated date, up to two alternatives, 2–3 cited steps, or a clarifying question with suggested offices when no match is confident. A circuit breaker skips the hosted model for 60 s after a provider failure.
* **Search (FR-03):** results are ordered by relevance (name, then tag, then description matches).
* **Analytics (FR-09):** totals and a daily series were added for the dashboard chart.
* **UI:** full redesign in UTA colours with a side detail drawer, routing-slip answers, admin filtering/pagination and an accessible activity chart with a table view.

## Not established by these results

* **Hosted LLM accuracy.** No OpenAI key was available in this environment, so every AI number above is the offline (keyword) path. Set `OPENAI_API_KEY`/`OPENAI_MODEL` and rerun `scripts/evaluate_ai.py --require-rag` for the hosted path.
* **MiniLM/pgvector.** The model host was not reachable from this environment; the hybrid code path is covered by a unit test with a stub encoder but not by a real-model run.
* **Evaluation independence.** Both question sets were written by the development side. The team (PB-12 owners) should review labels and add questions written by students before final acceptance.
* **Cloud stack.** k6 ran against one local Uvicorn process with SQLite; repeat on the Render/Neon staging stack. PostgreSQL CI, Docker images, Firefox/WebKit/BrowserStack runs, OWASP ZAP and the SUS study (≥ 10 students) were not executed here.
* **Data freshness.** Office details reflect the public pages on October 20, 2026; some pages publish seasonal hours (Spring 2026 values are labelled as such).
