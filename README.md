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
- [Directory data sources](docs/DATA_SOURCES.md)

## Contributors

- Ashwinder Singh
- Krisha Patel
- Suhas Surendra Kumar
- Harmanpreet Kaur

Independent student project; not an official UTA service.
