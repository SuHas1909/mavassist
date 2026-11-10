# MavAssist re-run - 2026-11-10

Local run after the final fixes (branch final-fixes). Logs and screenshots are in this folder; defects are tracked in docs/DEFECTS.md.

| Check | Result | Status |
|---|---|---|
| Backend tests (pytest) | 101 passed, 0 failed; 94% coverage | Pass |
| Production build | tsc -b && vite build | Pass |
| Frontend unit tests (Vitest) | 3 passed | Pass |
| End-to-end + axe (Playwright, Chromium) | 5 passed, 0 failed | Pass |
| k6, 50 users x 60 s (local Uvicorn, SQLite, keyword mode) | errors 0%; non-AI p95 192 ms; chat p95 639 ms | Pass |
| k6, 50 users x 60 s (Docker stack, PostgreSQL; rate limit off and AI keys blank via a temporary override, `AI_MODE=rag` image default) | errors 0% (0 / 648); non-AI p95 1,893 ms (target < 1,000); chat p95 12,026 ms (target < 5,000); 324 iterations | Fail (latency) |
| Hosted AI, 100-question set | Not a hosted result: only 14 / 100 answers were hosted (`rag`); after AI-014 OpenRouter returned HTTP 402 and 85 answers came from the offline fallback (1 safety reply). Mixed-mode scores: top-1 98%, top-3 100%, unknown offices 0 | Fail (blocked: HTTP 402) |
| Hosted AI, 50-question holdout | Not a hosted result: 0 / 50 hosted; 49 fallback, 1 safety reply (OpenRouter HTTP 402). Fallback scores: top-1 90%, top-3 100%, unknown offices 0 | Fail (blocked: HTTP 402) |
| Docker smoke (db, api, web) | all containers healthy; web and /health return 200 | Pass |

Notes on this run:

* **Hosted AI (D-12) is blocked by the provider account, not by code.** The evaluation server ran with a 1 s circuit breaker (evaluation only). Both provider calls made after AI-014 returned HTTP 402 (Payment Required); the OpenRouter account shows 0 purchased credits. An earlier run the same day had the same pattern (one 402 after AI-012; 12 / 100 hosted). Hosted accuracy stays unverified until credits are added and `scripts/evaluate_ai.py --require-rag` passes.
* **Docker / PostgreSQL load:** no errors, so the pool change holds on PostgreSQL, but both latency targets were missed. The Docker image runs `AI_MODE=rag` (semantic embedding per query on CPU) while the local run uses keyword mode, which is the likely cause; not yet confirmed by a separate run. Logs: `logs/k6-50vu-docker-postgres.log`.
* An earlier local SQLite k6 run the same day (before this one) also passed: errors 0%, non-AI p95 854 ms, chat p95 1,608 ms.

Additional AI evaluation records (2026-11-10):

| Run | Answers | Top-1 | Top-3 | Unknown offices | Evidence |
|---|---|---|---|---|---|
| **Offline**, 100-question set (AI keys blank, rate limit off on the test server only) | 99 cited-source + 1 safety; 0 hosted | 97% | 100% | 0 | `ai-eval-offline-100.json` |
| **Offline**, 50-question holdout (same setup) | 49 cited-source + 1 safety; 0 hosted | 90% | 100% | 0 | `ai-eval-offline-holdout-50.json` |
| **Hosted diagnostic, before OpenRouter credit ran out** (gpt-4o-mini, timing script, 100-question set) | 63 hosted, then 37 fallback after a provider error | 100% of hosted (63 / 63) | 100% of hosted | not stored | `ai-eval-hosted-diagnostic-gpt-4o-mini.json` |

The offline rows measure keyword + semantic retrieval only, not the hosted model. Hosted latency in the diagnostic: p50 6.3 s, p95 15.8 s, max 18.3 s (NFR-01 target 5 s; D-15). Free-model probes (3 requests): Gemma 4 31B `:free` returned HTTP 429; Nemotron 3.5 Super `:free` replied in 8.5 s and 9.4 s but our parser rejected the JSON; no free-model sample was run.

SUS participants recorded in docs/usability-results.csv: 0 (target: 10 or more).
