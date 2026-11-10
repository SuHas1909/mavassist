# Defect log

Defects found by the team during manual testing, CI and the November 9 test run. Each one should also exist as a **Bug** work item in Azure DevOps (Boards â†’ New Work Item â†’ Bug), linked to its user story, with the same ID in the title.

Severity: **High** = wrong or unsafe answer, failed requirement or blocked release; **Medium** = test or tooling failure with a workaround; **Low** = cosmetic.

| ID | Found | Where | Summary | Severity | Story / req. | Root cause | Fix | Status |
|---|---|---|---|---|---|---|---|---|
| D-01 | Oct 23 | Assistant (hosted) | "someone mollested me" answered "That's not something MavAssist can help with" | High | 83 / FR-04 | Model flagged the message as unsafe and the app mapped every unsafe intent to the explicit-content refusal | Victim-support rules (sexual and physical harm) run before the model; harm reports can never become "Not found"; emergency buttons always shown | Fixed (this patch) |
| D-02 | Oct 23 | Assistant (hosted) | Complaint about racist treatment by a staff member at "accounts" was routed to Student Accounts | High | 83 / FR-04 | Keyword ranking chose the office; the model only stepped in when keywords failed | AI-first routing over all 50 offices with retrieval as hints | Fixed (this patch) |
| D-03 | Oct 23 | Assistant | "i wanna hit someone" answered "Not found" | High | 83 / FR-04 | Violence rule had no hit/punch/fight verbs | Added verbs with a target filter ("hit my head", "hit the gym" stay normal) | Fixed (this patch) |
| D-04 | Oct 23 | Assistant | "i got scammed" answered "Not found" | Medium | 83 / FR-04 | No scam/fraud vocabulary | Scam and fraud map to theft reporting (UTA Police); model routing also handles it | Fixed (this patch) |
| D-05 | Oct 23 | Assistant | Insults ("fuck you") answered "Needs a detail" | Low | 83 / FR-04 | No abuse category | Calm boundary reply with example questions | Fixed (Oct 23) |
| D-06 | Oct 23 | Assistant UI | Scroll arrows visible inside the one-line question box | Low | 83 / NFR-04 | Auto-grow height ignored the border width | Height includes the border; overflow hidden until 160 px | Fixed (Oct 23) |
| D-07 | Oct 23 | Docker | API container exits: `password authentication failed` after unzipping a new copy | Medium | 77 / NFR-05 | New random `POSTGRES_PASSWORD` in `.env`, but the old Postgres volume was reused | Troubleshooting row in DEPLOYMENT.md; keep one working folder | Fixed (docs) |
| D-08 | Oct 23 | GitHub Actions | `browser` job failing on the AI pull request | Medium | 89 / NFR-04 | axe measured text during fade-in animations | Playwright runs with `reducedMotion: 'reduce'` | Fixed - verified 2026-11-10 (Playwright) |
| D-09 | Nov 9 | Playwright + axe | Serious contrast failures: drawer text 4.15:1, verified badge 3.71:1, example chip 2.50:1 | Medium | 89 / NFR-04 | Same as D-08: the drawer slide-in (0.22 s) and chip fade-in were captured at partial opacity; real colours are about 6.6:1 | Same fix as D-08; re-run E2E to confirm | Fixed - verified 2026-11-10 (Playwright) |
| D-10 | Nov 9 | k6, 50 users Ã— 60 s | 52 of 3,100 requests failed (1.68%, target < 1%); slowest 30.8 s | High | 89 / NFR-01 | SQLAlchemy default pool (15 connections) smaller than FastAPI's 40 worker threads; requests waited 30 s and returned HTTP 500 | Pool 20 + 20 overflow, 10 s timeout (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`) | Fixed, re-test pending |
| D-11 | Nov 9 | Docker smoke and live tests | Blocked on the macOS test machine (Docker daemon not running) | Medium | 89 / NFR-05 | Environment, not code | Re-run on a machine with Docker Desktop running | Closed - Docker smoke passed 2026-11-10 |
| D-12 | Nov 9 | Hosted AI evaluation | `all_hosted_rag` is false in every stored evaluation file; hosted accuracy not yet recorded | High | 86 / FR-04 | Evaluations ran in offline mode without an OpenRouter key | Run `scripts/evaluate_ai.py --require-rag` with the key set and commit the results | Open |
| D-13 | Nov 9 | Usability | `docs/usability-results.csv` has no participant rows | High | 89 / NFR-04 | SUS study data not recorded in the repository | Add the 10+ participants' task times and SUS answers (IDs only) | Open |
