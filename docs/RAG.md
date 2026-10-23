# Contextual answers with retrieval-augmented generation

The chat now answers questions from **source passages**, not just directory cards. Every answer paragraph and next step includes citations. Follow-ups send the last three question/answer pairs as transient context; the backend redacts them and does not persist the conversation.

## How it works

0. **Guardrails first** (`app/guard.py`): self-harm, violence, emergencies, dishonest/illegal requests, explicit content, dating requests, small talk and clear off-topic questions are answered by deterministic, tested templates before any retrieval or model call.
1. Redact known account-name parts, email addresses and long numeric identifiers in the current question and history.
2. Resolve a follow-up against the preceding question; a new topic is retrieved separately.
3. Retrieve relevant knowledge passages from active services. Local mode uses BM25 with word normalization and relevance filtering. Full semantic mode combines MiniLM/pgvector retrieval and BM25 by reciprocal rank fusion.
4. Expand adjacent reviewed passages within the winning topic, so an answer about refunds includes the actual status-checking instructions. Conditional Flywire content is retrieved only when Flywire is mentioned.
5. If a hosted model is configured, ask it to explain the retrieved content and produce paragraphs/steps with source IDs. Reject missing/unknown citations, malformed output and arbitrary generated URLs.
6. If no model is configured or generation fails, display curated retrieved summaries with source citations, explicitly labeled as source-based/fallback. Do not claim this is model-generated prose.
7. Show related offices below the explanation, without padding the answer with irrelevant alternatives.

Citation validation proves that references are from the retrieved set; it is not an automatic proof that every model-written claim follows from them. Review factual accuracy with independent questions before release.

## Enable conversational generation (OpenRouter)

In **backend/.env** (git-ignored), add:

```dotenv
AI_MODE=keyword
OPENROUTER_API_KEY=your-private-openrouter-key
OPENROUTER_MODEL=openai/gpt-4o-mini
LLM_TIMEOUT=12
```

Restart the API. Requests go to `https://openrouter.ai/api/v1/chat/completions` in JSON mode. Two model calls are used:

- **Answer generation** — the model receives the question, redacted history and retrieved passages, and must return cited paragraphs/steps. It can also return `in_scope: false` when the retrieved office does not genuinely answer the question, which becomes a **Not found** reply instead of a wrong office.
- **Triage** (only when retrieval is not confident) — the model reads the whole active directory (names and one-line descriptions) and decides `campus` (with a service id), `unclear`, `off_topic`, `greeting` or `unsafe`. A chosen office is then answered with that office's own passages.

Every model output is validated (known source IDs, no URLs, length limits). Network or provider errors open a 60-second circuit breaker and fall back to cited source summaries. Any OpenAI-compatible endpoint works through `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`; `OPENAI_API_KEY`/`OPENAI_MODEL` still work for OpenAI directly.

For semantic retrieval, install requirements-ai.txt, use PostgreSQL/pgvector, set `AI_MODE=rag`, run `python -m app.manage reindex`, and restart. This loads MiniLM and uses both dense and lexical ranking. See DEPLOYMENT.md for the full infrastructure setup.

## Upgrade an existing installation

Use the same database configuration and keep your existing JWT secret/accounts. From backend:

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.manage seed
```

Migration **002** adds `knowledge_chunks`; the seed command creates directory overview passages and inserts missing built-in reviewed passages. Existing services are not overwritten. If you need to refresh the shipped reviewed passages explicitly, after reviewing changes:

```powershell
..\.venv\Scripts\python.exe -m app.manage import-knowledge --file app/knowledge_seed.json
```

Restart the API/frontend afterward. The local preview accompanying this package has already received migration 002 and the updated passages.

## Add your own reviewed source content

Create a JSON array with this structure, keeping the summaries in your own words and preserving conditions:

```json
[
  {
    "key": "stable-unique-article-key",
    "service_name": "Student Accounts",
    "title": "Specific question this passage answers",
    "content": "A concise, fact-checked summary of the official source.",
    "steps": ["First source-supported action.", "Second supported action."],
    "keywords": ["refund", "status", "credit balance"],
    "source_url": "https://www.uta.edu/business-affairs/student-accounts/refunds",
    "reviewed_at": "2026-10-15"
  }
]
```

The **first keyword is the primary topic** for related-passage expansion. Use consistent topic names for passages that belong together; use a separate topic for conditional subcases. The service must already exist, citation URLs must use HTTPS without embedded credentials, and dates must be valid ISO dates. Import validates all service references before committing. Import by stable key updates that passage instead of duplicating it:

```powershell
..\.venv\Scripts\python.exe -m app.manage import-knowledge --file path/to/reviewed-passages.json
```

In semantic mode, imports compute passage embeddings. Reindex after changing embedding models or enabling semantic mode. Archiving a service excludes its passages from retrieval. Editing its directory record updates the directory-overview passage but preserves separately reviewed policy articles.

The application does not scrape arbitrary submitted URLs. Imported content is reviewed by the team, which avoids a runtime URL-fetching security issue and makes source provenance explicit.

## Included knowledge and limits

The directory contributes 50 short, explicitly unverified overview passages. Five richer reviewed passages cover credit-balance refunds, MyMav refund status/contact, delivery/holds, conditional Flywire overpayment handling, and online payments. They are paraphrased summaries of these official pages, reviewed October 14, 2026:

* [Refund overview](https://www.uta.edu/business-affairs/student-accounts/refunds)
* [Refund FAQ](https://www.uta.edu/business-affairs/student-accounts/faq/refunds)
* [Where is my refund?](https://www.uta.edu/business-affairs/student-accounts/refunds/where-is-my-refund)
* [Make a payment](https://www.uta.edu/business-affairs/student-accounts/payment-information/make-a-payment)

The corpus is not a complete university policy collection. When a department has only an overview, the response says detailed policy is missing. Add reviewed passages across the remaining topics for richer coverage. The bot never has access to a student's actual balance, refund approval, payment history or MyMav account.
