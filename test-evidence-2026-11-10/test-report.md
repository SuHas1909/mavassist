# MavAssist re-run - 2026-11-10

Local run after the final fixes (branch final-fixes). Logs and screenshots are in this folder; defects are tracked in docs/DEFECTS.md.

| Check | Result | Status |
|---|---|---|
| Backend tests (pytest) | 0 passed, 0 failed; 0% coverage | Fail |
| Production build | tsc -b && vite build | Pass |
| Frontend unit tests (Vitest) | 3 passed | Pass |
| End-to-end + axe (Playwright, Chromium) | 5 passed, 0 failed | Pass |
| k6, 50 users x 60 s | errors 4.31%; non-AI p95 4827 ms; chat p95 5516 ms | Fail |
| Hosted AI, 100-question set | Not run | Pending |
| Hosted AI, 50-question holdout | Not run | Pending |
| Docker smoke (db, api, web) | all containers healthy; web and /health return 200 | Pass |

SUS participants recorded in docs/usability-results.csv: 0 (target: 10 or more).
