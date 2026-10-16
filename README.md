# Portfolio RAG Agent

A retrieval-augmented generation (RAG) agent that answers questions about my portfolio using grounded context from my resume and project writeups. It ships with a simple RAG endpoint and an advanced LangGraph pipeline with classification, retrieval filtering, and optional session memory.

## Highlights

- FastAPI API with two chat modes (simple RAG and advanced agent).
- LangGraph routing for resume vs project questions.
- Pinecone vector store with OpenAI embeddings.
- Optional Redis-backed chat memory for follow-ups.
- Clean ingestion pipeline for resume and project sources.

## Architecture (high level)

1. Ingest markdown resume and project files into Pinecone with metadata.
2. Classify the incoming question as resume, project, or unknown.
3. Retrieve relevant chunks using metadata filters and score thresholds.
4. Generate a grounded response with optional conversation history.
5. Fallback when the query is out of scope or confidence is low.

Entry point: [app/main.py](app/main.py)

## Data sources

Ingestion uses markdown files in:

- [data/raw/resume](data/raw/resume)
- [data/raw/projects](data/raw/projects)

Update these files to refresh the knowledge base, then re-run ingestion.

## API

Base path: `/api/v1`

Endpoints:

- `POST /chat` simple RAG chain
- `POST /advanced-chat` full agent pipeline with memory and debug options

Request body:

```json
{
  "question": "What backend technologies did you use at Wiz Freight?",
  "session_id": "optional-session-id"
}
```

Example curl:

```bash
curl -X POST http://localhost:8000/api/v1/advanced-chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What projects use Go?"}'
```

## Quickstart (local)

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Set the required environment variables (see below). dotenv is supported.
3. Ingest data:
   ```bash
   python scripts/ingest.py
   ```
4. Run the API:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Environment variables

Set the following environment variables:

```bash
# OpenAI
OPENAI_API_KEY=...

# Pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=...
PINECONE_DIMENSIONS=1536

# Retrieval thresholds
MIN_SCORE_THRESHOLD=0.2
CONFIDENCE_THRESHOLD=0.25

# Debug
DEBUG_RAG=false

# Optional Redis memory
USE_REDIS_MEMORY=false
REDIS_URL=redis://localhost:6379/0
```

Notes:

- `MIN_SCORE_THRESHOLD` filters individual matches; `CONFIDENCE_THRESHOLD` gates the final answer.
- When `DEBUG_RAG=true`, `/advanced-chat` includes retrieval scores and metadata.

## Deployment

This repo includes an AWS Lambda-friendly Dockerfile that uses Mangum to serve FastAPI:

- [Dockerfile](Dockerfile)
- Lambda handler: `app.main.handler`

If you want local Docker testing, build the image and run it with your preferred Lambda runtime tooling.

## Project structure (key files)

- [app/api/routes.py](app/api/routes.py) request routing and API responses
- [app/langgraph](app/langgraph) LangGraph nodes and edges
- [app/services/rag_service.py](app/services/rag_service.py) simple RAG chain
- [scripts/ingest.py](scripts/ingest.py) ingestion pipeline

## Roadmap ideas

- Add tech-stack filtering for project queries at ingestion time.
- Improve prompt grounding and add citations in responses.
- Add automated evaluation with `ragas`.
