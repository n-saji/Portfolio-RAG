# Portfolio RAG Agent

The portfolio chat runs on FastAPI in AWS Lambda. Its original LangGraph shape is
preserved: **classifier → optional follow-up rewriter → retriever → generator or
fallback**. Pinecone holds the evidence, and Redis stores the last ten exchanges
for a browser session. Both `/api/v1/chat` and `/api/v1/advanced-chat` use the
same grounded graph. The website reads `/api/v1/history` to restore prior turns.

## What the agent knows

- `data/knowledge/profile.json` contains reviewed career, education, skill and
  contact facts. It includes the owner-provided LinkedIn details from 2026-10-16:
  concurrent ACTFORE and Holiday Channel roles and the split Wiz Freight dates.
- The published resume PDF is fetched and parsed on refresh. Its SHA-256 and
  retrieval date are stored in the source snapshot.
- Public non-fork GitHub repositories are listed; recent README files provide
  detailed project evidence. Related repositories are grouped by project name.
- The portfolio publishes `/portfolio-facts.json` on each site build. A reviewed
  copy in `data/knowledge/portfolio.json` is the fallback.

LinkedIn blocks automated full-profile retrieval. The current owner-provided
details are reviewed in `profile.json`; later LinkedIn changes need a new export
or owner-provided profile text before they can be added. Raw LinkedIn exports
must stay outside Git and Pinecone.

## Refreshing Pinecone

The weekly GitHub Actions workflow runs these commands and activates a verified,
versioned namespace. A failed fetch, missing core fact, vector-count mismatch or
readback failure prevents activation. The previous namespace remains available
for rollback.

```bash
python scripts/refresh_sources.py
python scripts/refresh_index.py --activate
```

For local review, run `refresh_sources.py --resume-file PATH --portfolio-file
PATH`, inspect `data/generated/records.json`, then run `refresh_index.py`
without `--activate`. The source snapshot is ignored by Git. The indexer uses
`AWS_PROFILE=portfolio-rag` locally if AWS credentials are needed; in Actions
it uses the configured AWS credentials and reads provider keys from the Lambda
configuration. The runtime reads `PINECONE_NAMESPACE`; an unset value keeps the
original default Pinecone namespace available.

## API

`POST /api/v1/advanced-chat` accepts `{"question":"..."}` (1–500 characters).
`POST /api/v1/chat` is an alias. Responses contain `answer`, `classification`
and a retrieved document count. `GET /api/v1/history` returns this browser's
recent `{role, content}` messages; `DELETE /api/v1/history` clears them. A secure
HTTP-only `session_id` cookie connects these requests. Redis history expires
after seven days and is bounded to 20 messages. Provider failures do not reveal
keys or internal errors in the answer.

## Local development

Use Python 3.12. Install `requirements.lock` and configure `.env` with
`OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, and
`PINECONE_DIMENSIONS` (1024 for the current index). `USE_REDIS_MEMORY=true` and
`REDIS_URL` enable session memory. `RAG_ROUTER_MODEL` and `RAG_ANSWER_MODEL` are
optional; defaults are `gpt-4.1-mini` and `gpt-4.1`.

```bash
python -m unittest discover -s tests -v
uvicorn app.main:app --reload
```
