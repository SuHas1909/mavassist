# Deployment instructions

Choose one path: **A** to run immediately without Docker; **B** for the full local PostgreSQL/AI system; **C** for the proposal's cloud architecture. Commands assume the extracted `mavassist` directory is the project root. Never commit `.env` files, database files, API keys or bearer tokens.

## A. Local application without Docker

### Windows

1. Install Python **3.12** and Node.js **22.12+ LTS**. Confirm `python --version` and `node --version`.
2. Create the isolated backend environment and configuration:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe scripts/configure.py
```

3. Initialize the database and create your administrator. The CLI asks for name, email and a password of at least 10 characters; it does not print the password or allow public administrator registration.

```powershell
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.manage seed
..\.venv\Scripts\python.exe -m app.manage create-admin
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

4. Leave the API running. In a second terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

5. Open **http://localhost:5173**. New accounts are students. Use your CLI-created administrator for management and analytics. Health: `http://127.0.0.1:8000/health`; OpenAPI: `/docs` and `/openapi.json`.

### macOS/Linux equivalent

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python scripts/configure.py
cd backend
../.venv/bin/python -m alembic upgrade head
../.venv/bin/python -m app.manage seed
../.venv/bin/python -m app.manage create-admin
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Second terminal: `cd frontend`, `npm ci`, `npm run dev`.

The generated **backend/.env** controls this path. Do not use the root Docker `.env` to configure a directly launched API. Local HTTP is only for loopback development; cloud deployments must use HTTPS.

## B. Full local system: Docker + PostgreSQL + pgvector + MiniLM

1. Install/start Docker Desktop with Linux containers. Confirm **`docker info` succeeds**. Allow several GB of disk and enough RAM for PostgreSQL plus CPU PyTorch/MiniLM (a practical development starting point is 4 GB available to Docker; measure your own workload).
2. From project root run `python scripts/configure.py`. This creates a root **.env** with unique database/JWT secrets, without overwriting existing configuration.
3. In the root `.env`, set:

```dotenv
INSTALL_AI=true
AI_MODE=rag
OPENAI_API_KEY=your-private-project-api-key
OPENAI_MODEL=your-enabled-model-supporting-Responses-structured-outputs
```

Keep generated POSTGRES_PASSWORD and JWT_SECRET values. Select an enabled, cost-appropriate model in your OpenAI project; the application does not silently select or claim a specific model. The first image build downloads CPU PyTorch and all-MiniLM-L6-v2 and can take several minutes. Hugging Face download access is needed.

4. Build and launch:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --tail 100 api
```

Startup applies the initial migration and idempotently inserts missing seed records. With `AI_MODE=rag`, seed and edited records receive 384-dimensional embeddings. PostgreSQL receives the vector extension and HNSW cosine index. The API warms the local embedding model before becoming ready.

5. Create the administrator interactively:

```powershell
docker compose exec api python -m app.manage create-admin
```

6. Visit **http://localhost:8080**. Database is internal to Docker; API is bound to localhost:8000. Verify `/health` returns `ai_mode: rag`. Ask a question and inspect the UI response badge: **AI with sources** means the external model succeeded; **Source-based fallback** means generation failed; **Source-based answer** means no hosted model is configured. `/health` alone does not prove external AI availability.
7. If you enable RAG after seeding in keyword mode, re-embed every record:

```powershell
docker compose exec api python -m app.manage reindex
```

**Small offline Docker demo:** use `INSTALL_AI=false` and `AI_MODE=keyword` in root `.env`, leave AI credentials blank, then rebuild. This is explicitly not the AI acceptance deployment.

Stop while retaining data: `docker compose down`. The named PostgreSQL volume persists. Do not add `--volumes` unless you intend to delete the database and have a backup.

## C. Cloud: Vercel frontend + Render API + Neon/Supabase PostgreSQL

This source is deployable, but no live cloud deployment or account configuration is included. Account limits/prices change; review the current provider plans before spending money. CPU embedding memory and cold-start requirements may exceed a free API instance. The proposal's total $25 budget is a target, not a guarantee that every selected service fits it.

### 1. Publish your repository

Create a GitHub repository owned by your team. Push **the contents of `mavassist` as the repository root** so `.github/workflows`, `backend`, `frontend`, and `render.yaml` are at its root. Review `.gitignore`; ensure `.env`, local SQLite data, browser credentials and test tokens are excluded. Do not upload `node_modules`, `.venv`, generated browser downloads or local databases.

### 2. Create PostgreSQL

Create a PostgreSQL database in Neon or Supabase. Use a connection URL suitable for the SQLAlchemy/psycopg API and enable the `vector` extension using that provider's permitted SQL console:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The application migration also requests the extension; the migration account must have permission. Store the database password privately. Use TLS, e.g. add `sslmode=require` to the connection URL. Example shape only:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Use the provider's direct connection for migrations when required by its pooling configuration. Select a connection method supported by your API hosting network (IPv4/IPv6 availability can differ). SQLAlchemy runs in a persistent API process, not an edge Worker.

### 3. Deploy the API on Render

Create a **Web Service**, connect your team repository, choose Docker, set **Root Directory = backend**, **Dockerfile Path = ./Dockerfile**, and **Health Check Path = /health**. Alternatively import `render.yaml` as a Blueprint and review its resources before creating them. Choose a memory allocation suitable for the model; the blueprint intentionally does not promise a free plan.

Set private runtime variables:

| Variable | Value |
|---|---|
| APP_ENV | production |
| DATABASE_URL | TLS PostgreSQL URL from the previous step |
| JWT_SECRET | Random secret of at least 32 characters; generated by Render Blueprint or `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| CORS_ORIGINS | Exact HTTPS frontend origin(s), comma-separated; no wildcard and no trailing slash |
| AI_MODE | rag |
| OPENAI_API_KEY | Your private OpenAI project key; never VITE-prefixed |
| OPENAI_MODEL | A model enabled in your project with Responses structured output support |
| RATE_LIMIT | true |
| SIMILARITY_THRESHOLD | 0.28 initially; tune on the reviewed labeled set |

The image startup applies migrations and inserts missing seed records, then binds to Render's PORT. The model is pre-downloaded into the image. One API worker is intentional: it avoids loading multiple model copies and is consistent with the single-process rate limiter. Record `/health`, a real authenticated chatbot response, model identifier and deployment commit as evidence.

If the Vercel domain is not yet known, create the Vercel project first to obtain it, then set the exact CORS origin and redeploy the API. Production startup rejects HTTP origins and non-PostgreSQL URLs.

### 4. Deploy frontend on Vercel

Import the same repository. Set **Root Directory = frontend**, **Framework = Vite**, **Build = npm run build**, **Output = dist**, and Node.js 22.12+. Add:

```dotenv
VITE_API_URL=https://YOUR-API.onrender.com
```

This is a **public build-time URL**, never an API secret. Redeploy after changing it. Keep the frontend `vercel.json` for SPA handling/security headers. Add the actual HTTPS Vercel origin to API CORS_ORIGINS and restart/redeploy the API. New Vercel preview origins must be explicitly listed if you choose to allow them.

### 5. Migrate, seed and create admin against cloud data

If your hosting plan provides a shell, run in the API service:

```bash
python -m alembic upgrade head
python -m app.manage seed
python -m app.manage create-admin
python -m app.manage reindex
```

If a remote shell is unavailable, use your local Python environment from the **backend** folder. Temporarily set environment variables to the cloud database URL and model mode in that terminal, run the same migration/maintenance commands, then close the terminal. Keep secrets out of shell history; enter them with a hidden prompt or your platform's secret tooling. Use `AI_MODE=keyword` for local admin provisioning if MiniLM is not installed; embeddings should then be rebuilt in the full API environment. Public registration can never create or promote an administrator.

### 6. Release smoke test

* HTTPS frontend loads; console/network show no CORS/mixed-content failures.
* Register a new student. Confirm every `/api/admin/*` method returns 403 with the student's token (automated route-inventory check provided).
* Create and edit a service as admin; publish a current notice; verify it from a student detail page.
* Archive it. Confirm it disappears from directory, search, bookmarks/recent display and chatbot retrieval.
* Save/unsave a resource; revisit detail pages; check newest-first, at-most-ten history.
* Ask a real question, check an **AI with sources** response, source link, current facts, last-updated timestamp and 2–3 steps.
* Disable the external model temporarily in a staging instance; verify keyword fallback, then restore the key. Do not expose secrets or record them in screenshots.
* Rate an answer; check analytics by date range.
* Run reviewed AI accuracy, k6, accessibility, security and human usability checks before marking NFRs met.

## AI cost and privacy setup

Use a dedicated API project/key. Configure project budget alerts at about $15 and monitor actual spend. Alerts must not be assumed to be a hard cap: check the current provider controls. This implementation limits generated output to 900 tokens and requires citations for every paragraph and step; it does not implement a billing ledger or guaranteed cash stop. Citation IDs and generated URLs are validated, but factual entailment still needs evaluation. See docs/RAG.md for lightweight BM25 + hosted generation without a local embedding model.

**Free tier:** with an OpenRouter free model (`OPENROUTER_MODEL=...:free`) the key allows 50 requests per day and 20 per minute. When the daily allowance is used up, or the provider returns HTTP 429/402, the API logs the status code and answers from cited sources (the same offline path as keyword mode) until the limit resets. Plan demos and evaluations within the cap: `scripts/evaluate_ai.py --sample N` runs N evenly spread questions with 3.2 s between requests and stops at the first 429 or 402.

The last three turns may be sent as redacted transient follow-up context. No raw question, conversation history or account ID is stored in chat rows. Known account-name parts, emails and numeric identifiers are removed before the external request. Arbitrary sensitive free text cannot be perfectly detected; the UI warns users not to enter it. Responses use `store:false`. Review the provider's applicable data controls/retention policy for your organization; this flag is not a promise of zero provider-side retention.

The original proposal conflicts between "only question text" in NFR-03 and sending retrieved directory records for RAG. This implementation sends **redacted question + public service context**, without account metadata. Approve/document that clarification, or revise the product design before claiming literal NFR-03 compliance.

Anonymous chat/usage rows older than 90 days are pruned at startup and hourly while running. For strict retention when the API can sleep, schedule a daily maintenance command using the host's scheduler: `python -m app.manage prune`. Personal recent views/bookmarks are intentionally account-linked; they are separate from anonymous chat data. Disable upstream request-body logging and review hosting/access logs and backup retention too.

## Operations and troubleshooting

| Symptom | Check / fix |
|---|---|
| Docker cannot connect to the engine | Start Docker Desktop; wait until `docker info` succeeds; select Linux containers. |
| JWT startup error | Run configure.py or set a real random JWT_SECRET; do not copy the placeholder. |
| No tables / no directory | Run `alembic upgrade head`, then `python -m app.manage seed` against the same DATABASE_URL as the API. |
| Frontend cannot reach API | Confirm API health; exact CORS origin; VITE_API_URL; redeploy frontend after env changes. |
| Chat says Source-based answer/fallback | Offline mode or provider error. Check AI_MODE, model access, project credit, key and timeout; verify retrieval embeddings. |
| RAG returns clarification for every query | Reindex after enabling rag; inspect seed vocabulary and tune threshold on reviewed questions. |
| API build/start runs out of memory | Increase memory or use offline mode for a labeled limited demo. Do not claim full AI deployment in keyword mode. |
| API container exits with `password authentication failed for user "mavassist"` | The Postgres volume keeps the password from its first start. If `scripts/configure.py` generated a new root `.env`, restore the old `POSTGRES_PASSWORD`, or reset local data with `docker compose down -v` and start again. Keep one working folder so `.env` and the volume stay matched. |
| HTTP 500 under load with `QueuePool limit … reached` | Raise `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` (PostgreSQL only; defaults 20/20 cover FastAPI's 40 worker threads. SQLite uses the default pool with WAL and a 30 s busy timeout). Keep the total below the database's connection limit. |
| HTTP 429 | Rate limit is per process/IP. Wait a minute. For isolated load testing disable it only in a private staging instance; re-enable before release. |
| Migration denied CREATE EXTENSION | Ask the database owner to enable vector; use a migration account with the necessary permissions. |
| Password rejected | Minimum 10 characters and maximum 72 UTF-8 bytes; bcrypt limit is bytes, not characters. |
| Ports occupied | Stop the previous local process or choose different ports and update proxy/CORS/test settings together. |

Before upgrades: take a database backup using the provider's backup tool or `pg_dump`, test a restore in staging, then apply reviewed Alembic revisions. The shipped `001` creates a fresh schema; future structural changes require new migrations. Do not modify the initial migration after deployment or use `downgrade base` on live data. Rotating JWT_SECRET invalidates all sessions; frontend tokens expire in 60 minutes and are cleared on logout/401.

## Official setup references

Checked during implementation; use the current provider docs for account-specific details:

* [FastAPI security/JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
* [Render FastAPI deployment](https://render.com/docs/deploy-fastapi) and [health checks](https://render.com/docs/health-checks)
* [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)
* [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)
* [pgvector installation](https://github.com/pgvector/pgvector)
* [Neon pgvector](https://neon.tech/docs/extensions/pgvector) / [Supabase vector](https://supabase.com/docs/guides/database/extensions/pgvector)
