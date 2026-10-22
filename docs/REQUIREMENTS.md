# Requirement traceability and acceptance

“Implemented” describes source/application functionality. It does not mean every deployed acceptance target has already been achieved. See VERIFICATION.md for runs actually completed. WBS owners remain proposal assignments and are not proof of individual authorship.

| ID | Implementation | Automated check / remaining acceptance |
|---|---|---|
| FR-01 | Student registration/login, JWT 60 minutes, bcrypt 12, CLI-only administrator provisioning, server role gate | pytest auth and every-admin-route inventory; browser student/admin login |
| FR-02 | Active directory and full detail fields, category, source/freshness and current notices | pytest directory/detail/curated-data checks; 50 records with location/hours/contact from public uta.edu pages (48 verified, 2 flagged) — see DATA_SOURCES.md |
| FR-03 | Bound literal keyword matching on name/description/tags with relevance ordering (name > tag > description); multiple OR category filters; offset/limit | pytest tag, keyword, multi-category, escaped wildcard and pagination checks |
| FR-04 | Service-level BM25 ranking + optional MiniLM hybrid; one recommended office with reason, location/hours/contact, last-updated date, ≤2 alternatives, 2–3 cited steps; clarification with suggested offices below the confidence threshold; LLM answers validated against retrieved IDs | pytest FR-04 contract, out-of-scope clarification and accuracy gate; offline routing 97% top-1 / 100% top-3 (v2 set), 90% / 100% (held-out); hosted-model accuracy pending an API key |
| FR-05 | Admin create/update/archive/restore; excluded from directory/search/chat and saved/history display | pytest lifecycle; browser admin lifecycle |
| FR-06 | Category CRUD with reference guards; service notices with timezone-aware dates and validity checks | pytest CRUD/date/visibility; browser category/notice paths |
| FR-07 | Per-user idempotent bookmark add/remove and private list | pytest isolation, idempotence; browser save/retrieve |
| FR-08 | At-most-ten distinct per-user recent views, newest first; revisits move to front | pytest 12-service cap/revisit/isolation; browser history |
| FR-09 | Date-range analytics for searched terms, viewed services, chatbot categories, plus totals and a daily activity series | pytest and browser admin analytics; production data will accumulate after use |
| FR-10 | One helpful/not-helpful rating per answer UUID, aggregate helpfulness | pytest duplicate/not-found and aggregation; browser rating |
| NFR-01 | k6 script with 50 VUs and p95 1s non-AI / 5s AI thresholds | Local run Oct 20: non-AI p95 391 ms, chat p95 756 ms, 0% errors (k6-load-results.json). Repeat on hosted staging. |
| NFR-02 | bcrypt 12, 60-min JWT, issuer/audience checks, input validation, no public admin role, explicit CORS, security headers | All admin methods denied to student in tests; HTTPS supplied by cloud hosts, loopback development uses HTTP. OWASP/audit/host configuration still required. |
| NFR-03 | No raw question/history/account/IP in chat table; redacted transient history; name/email/numeric redaction; store:false; anonymous usage; startup/hourly 90-day prune | Payload and retention tests. **Clarification required:** RAG sends redacted question + public context despite original literal “only question text.” Arbitrary sensitive text redaction is not guaranteed; hosting logs/backups and idle-time scheduled prune need review. |
| NFR-04 | Responsive, semantic forms, focus/keyboard/modal behavior, axe browser checks | See actual browser results; SUS >=70 and service-finding median <=60s with >=10 real students require the included human study protocol. |
| NFR-05 | Keyword fallback after hosted failures, 60 s circuit breaker, unknown-ID rejection, >=70% coverage CI gate | Coverage 93%; forced-outage k6 run at 50 users: 100% fallback, p95 643 ms (k6-fallback-results.json); cold-start on hosted staging remains to measure. |

## AI/product design changes requiring acknowledgment

The model now writes paragraphs and next steps using retrieved source passages, with source IDs required for every part. Unknown/missing citations and arbitrary generated URLs are rejected. Related service records are derived from the cited passages. Without a model the app displays curated source summaries; citation validity does not prove factual entailment, so independent accuracy evaluation remains required.

Source records are untrusted too: instructions embedded in descriptions cannot expand the valid ID set. The response parser rejects malformed output and unknown source citations and falls back. Seed source links are review candidates, not evidence of current operating details. A student services app should not present guessed details as authoritative.

## Backlog / WBS implementation mapping

| Backlog | WBS / proposal owner | Files / acceptance |
|---|---|---|
| PB-01 | 2.2, 3.1 / Ashwinder | db.py, migrations, Dockerfiles, compose, CI, OpenAPI /docs |
| PB-02 | 3.2 / Ashwinder | auth routes, Register/Login, role tests |
| PB-03 | 2.1, 2.3, 3.3 / Krisha | React directory/detail, seed.py; data verification remains |
| PB-04 | 3.4 / Krisha | search/filter route and UI |
| PB-05 | 5.1 / Harmanpreet | protected service CRUD/archive; tests |
| PB-06 | 4.1 / Suhas | ai.py encoder/candidates, pgvector HNSW index, reindex command |
| PB-07 | 4.2 Suhas; 4.3 Krisha | structured hosted routing, grounded facts, chat UI/fallback |
| PB-08 | 5.2 / Harmanpreet | category/notice CRUD and validity |
| PB-09 | 5.3 / Ashwinder | bookmarks/recent API and client |
| PB-10 | 5.4 / Suhas | anonymous usage aggregation, analytics view |
| PB-11 | 5.5 / Krisha | answer rating API and UI |
| PB-12 | 4.4 Harmanpreet; 4.5 Suhas | 100 synthetic review-required cases; evaluation runner; independently reviewed AI scores pending |
| PB-13 | 6.3 Harmanpreet; 6.4 Krisha | pytest, Vitest, Playwright/axe, k6, security and SUS protocols |
| PB-14 | 7.2 / All | README, deployment/user/testing/architecture docs; team-specific report/presentation remains |

The original proposal schedule is unchanged. This package does not manufacture commit history, Scrum ceremonies, hours, human participants, grades or completed contributions. Add real evidence to the progress report after your team reviews and runs the project.
