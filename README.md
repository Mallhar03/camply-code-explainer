# Camply Code Explainer

A source-grounded Retrieval-Augmented Generation (RAG) application for asking questions about the Camply TypeScript codebase. It combines semantic code retrieval, a bounded Gemini tool-calling agent, citation verification, persistent traces, and a browser UI.

## Requirements

- Python 3.11 or newer
- Docker Compose
- A local Camply repository containing the supported source paths (`src/`, `tests/`, `prisma/schema.prisma`, `README.md`, and `.github/workflows/`)
- A Gemini API key for generated answers; obtain API credentials separately from any Gemini application subscription

## Setup

1. Create a virtual environment and install the app with its test dependencies:

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -e '.[test]'
   ```

2. Create local configuration:

   ```bash
   cp .env.example .env
   ```

   Set `GEMINI_API_KEY` and point `REPO_ROOT` at your local Camply checkout. `.env` is ignored by Git and must never be committed.

3. Start PostgreSQL with pgvector:

   ```bash
   docker compose up -d
   ```

4. Build or refresh the local code index:

   ```bash
   .venv/bin/python -m app.ingest.ingest
   ```

   Ingestion uses an allowlist of source and documentation paths, redacts likely secrets before indexing, and skips unchanged files based on SHA-256 hashes.

5. Start the API and open the UI:

   ```bash
   .venv/bin/python -m uvicorn app.api:app --reload
   ```

   Visit [http://127.0.0.1:8000](http://127.0.0.1:8000).

## API

- `GET /health` — database connectivity and indexed chunk count
- `GET /` — browser application
- `GET /design-notes` — UI explanation notes
- `POST /ask` — answer a question; JSON body: `{"question":"How does authentication work?"}`
- `GET /trace/{trace_id}` — retrieve the stored trace for a completed query

The agent can use semantic search, keyword search, and bounded file reads. It validates answer structure, verifies that citations overlap evidence retrieved in the current run, and reports insufficient evidence rather than treating unsupported claims as answers.

## Tests and Evaluation

Run unit tests:

```bash
.venv/bin/python -m pytest
```

Run the golden-question evaluation after configuring the database, index, and Gemini API:

```bash
.venv/bin/python -m evals.run
```

The evaluation writes `evals/report.md`. Metrics should only be treated as representative after a successful live run; provider availability and rate limits may affect results.

## Configuration

Configuration is loaded from environment variables or the ignored local `.env` file:

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://camply:camply@localhost:5433/camply_explainer` |
| `GEMINI_API_KEY` | Gemini API credential | unset |
| `LLM_MODEL` | Gemini model identifier | `gemini-3.8-flash` |
| `REPO_ROOT` | Local Camply repository to index and read | `/home/mallhar/Desktop/camply` |
| `SIM_THRESHOLD` | Similarity threshold used for confidence scoring | `0.45` |

Change `REPO_ROOT` for your machine. The application does not bundle or publish the target Camply checkout.

## Security and Operational Notes

- Never commit `.env`, API keys, or other credentials.
- File reads are restricted to indexed relative paths contained in `REPO_ROOT`.
- The agent is bounded by a five-round tool limit and a 60-second wall-clock limit.
- The default PostgreSQL credentials and port in Docker Compose are for local development only; do not expose this service publicly as configured.
- Gemini API access, model availability, quotas, and pricing are controlled by Google and can change. A Gemini application subscription is separate from API access.

## Project Report

See [PROJECT_REPORT.md](PROJECT_REPORT.md) for the architecture, implementation details, verification status, and resume-ready highlights.
