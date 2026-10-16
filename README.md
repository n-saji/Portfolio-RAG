# Portfolio RAG API

A first-person, source-grounded portfolio chat service. The normal path uses local exact/lexical retrieval, optional Pinecone dense retrieval, and one OpenAI answer call. It runs as FastAPI on Lambda through Mangum.

## Public knowledge and review

- `data/approved/facts.json` contains reviewed public career, profile, and featured-project facts. The published resume is primary for employment and education; portfolio copy is primary for featured project descriptions.
- `data/approved/sources.json` holds the published resume text, SHA-256 and source date, plus metadata for all original public repositories from `n-saji` (forks excluded). Related repositories share a project ID.
- The Monday source-refresh workflow compares the published resume and GitHub metadata and opens a **review PR** when they change. Reviewers must update `facts.json` if a title, date, or achievement changed before merging. A merge triggers reindexing and Lambda deployment.
- LinkedIn is an optional, manually supplied cross-check. Put a personal export ZIP under `data/private/`, run `python scripts/import_linkedin.py data/private/<export>.zip`, review `data/candidates/linkedin.json`, and update `facts.json` in a PR. Raw exports and candidates are ignored by Git and are never indexed. Only public career fields are extracted; messages and contacts are skipped.
- At request time, the service reads only the approved packaged snapshot. It never fetches LinkedIn, GitHub, or the PDF for a visitor. When the resume source date is over 90 days old, current-role answers are qualified with its date.

## Local setup

Use Python 3.12 or newer:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python scripts/build_chunks.py
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
OPENAI_API_KEY='' PINECONE_API_KEY='' PYTHONPATH=. .venv/bin/python scripts/evaluate.py
.venv/bin/python -m uvicorn app.main:app --port 8000
```

Lambda uses Mangum while `uvicorn` serves the API locally. `python-dotenv` loads a local `.env` when present. A virtual environment from the former setup may point to a missing interpreter; recreate it if necessary.

Required for chat: `OPENAI_API_KEY`. Dense search additionally uses `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, and `PINECONE_DIMENSIONS` (default `1024`, matching the existing `portfolio-rag` index). Without Pinecone, exact and lexical retrieval still work. Optional: `ANSWER_MODEL` (default `gpt-6-luna`), `EMBEDDING_MODEL` (default `text-embedding-3-small`), `USE_REDIS_MEMORY`, `REDIS_URL`, and `DEBUG_RAG`.

## API

Both `POST /api/v1/chat` and `POST /api/v1/advanced-chat` accept:

```json
{
  "question": "What are you building at your current job?",
  "session_id": "optional-session-id",
  "history": [{"role": "user", "content": "Tell me about SyncBeat"}]
}
```

`history` is optional and limited to eight turns; `/advanced-chat` also uses an optional Redis-backed cookie session. Both routes return `answer` and `sources`; the advanced route preserves `classification` and `debug_docs_retrieved`. Only `DEBUG_RAG=true` adds diagnostic metadata and timings. Health checks use `GET /health`.

## Refresh, deploy, and rollback

1. Review the source-update PR, especially the current role and any resume/LinkedIn conflicts. Merge only approved public facts.
2. On `main`, CI runs unit tests and the offline recall@5 gate, builds token-sized chunks, stages them in a new Pinecone namespace, probes the namespace, writes an active pointer into the Docker image, then deploys that image to Lambda. Configure GitHub secrets `OPENAI_API_KEY`, `PINECONE_API_KEY`, and `PINECONE_INDEX_NAME` in addition to the existing AWS credentials. GitHub Actions must be allowed to create pull requests for the scheduled review workflow.
3. To stage manually, run `PYTHONPATH=. python scripts/build_chunks.py` then `PYTHONPATH=. python scripts/build_index.py --namespace portfolio-<version>`. Add `--activate` only after verification. The active pointer records the prior namespace. Roll back by redeploying the prior image or restoring that namespace in the pointer and redeploying.

Keep the old namespace until the new release passes live checks. Do not publish `data/private/` or `data/candidates/`.

## Quality and latency

`scripts/evaluate.py` checks retrieval recall@5 across reviewed career/project questions and every original public repository. Use `--answers` to create a private answer-review file for manual checking of unsupported claims. Release targets are recall@5 ≥ 90%, no unsupported claims in the reviewed answer set, and visitor p95 below four seconds across at least 100 representative warm/cold requests.

Stage timings are logged as `rag_timing` with local retrieval, embedding, Pinecone, model, and total milliseconds. Lambda `Init Duration`, duration, and memory require CloudWatch access. Tune Lambda memory only after those measurements; add provisioned concurrency only if cold starts remain a significant cause of misses.

The separate portfolio website currently answers many questions from fixed third-person text before it calls this API. This repository does not change that proxy, so measure website and backend timing separately and treat the fixed responses as a follow-up integration task.
