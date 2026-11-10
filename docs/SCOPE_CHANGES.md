# Scope changes

Changes to the approved plan that affect testing. Everything else in the proposal is unchanged.

| Planned | What we do instead | Why | Evidence |
|---|---|---|---|
| Cross-browser testing on **BrowserStack** (cloud browsers) | The browser suite runs on **three browser engines** (Chromium, Firefox and WebKit) locally and in CI on every push and pull request | The same flows, accessibility checks and 360 px layout check run on all three engines at no cost and on every change. The BrowserStack configuration (`frontend/playwright.browserstack.config.ts`) is kept but not used. | E2E-001 to E2E-015 in `docs/MavAssist_Test_Cases.xlsx`; `test-evidence-final-2026-11-10/logs/playwright-results.json`; CI `browser` job |
| **Cloud staging** deployment with **HTTPS** verification (and load testing on staging) | The demo runs on the **local Docker stack** (web, API, PostgreSQL with pgvector) | No hosted environment was set up this term. HTTPS, cloud cold-start and staging load numbers are therefore not measured; the local Docker stack is smoke-tested, load-tested and security-scanned instead. | DOCKER-001, PERF-003, SEC-001/002; STAGE-001/002 stay **Not run**. Decision owner: Ashwinder Singh |
