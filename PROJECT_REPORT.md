# Camply Code Explainer - Project Report

## Project Summary

Camply Code Explainer is an end-to-end Retrieval-Augmented Generation (RAG) application that answers technical questions about a TypeScript codebase with grounded, source-cited responses. It combines semantic code search, a PostgreSQL pgvector index, a tool-calling AI agent, strict citation validation, traceable run telemetry, and a FastAPI web interface.

The system was designed to avoid unsupported claims: answers are produced only from code evidence retrieved during the current run, and citations that cannot be matched to retrieved chunks are discarded. When evidence is insufficient, the application returns a structured insufficiency status instead of fabricating an answer.

## Key Features

- Semantic search across indexed source files using vector embeddings.
- PostgreSQL and pgvector storage for code chunks and embeddings.
- Incremental repository ingestion using file SHA-256 hashes.
- Secret redaction and repository-bound file access guards.
- Keyword search and bounded source-file reading tools.
- A Gemini tool-calling agent with:
  - A maximum of five tool rounds.
  - A 60-second wall-clock limit.
  - Structured answer validation and retry.
  - Citation overlap verification.
  - Confidence scoring and insufficiency detection.
- Persistent query records and detailed JSON traces for observability.
- REST endpoints for asking questions, retrieving traces, checking health, and loading design notes.
- A responsive dark-mode browser interface with source citations and Defend Mode trace explanations.
- A golden-question evaluation suite for retrieval hits, citation validity, refusal accuracy, latency, and token usage.

## Technical Architecture

The application is organized into modular ingestion, retrieval, agent, validation, database, API, evaluation, and UI layers.

- **Frontend:** HTML, CSS, and vanilla JavaScript.
- **API:** FastAPI and Uvicorn.
- **LLM:** Google Gemini through the `google-genai` SDK.
- **Embeddings:** `BAAI/bge-small-en-v1.5` through Sentence Transformers.
- **Database:** PostgreSQL 16 with the pgvector extension.
- **Database driver:** psycopg 3.
- **Data models:** Pydantic and Pydantic Settings.
- **Containerization:** Docker Compose.
- **Testing:** pytest.

The runtime flow begins with repository indexing, continues through semantic retrieval and optional agent tool calls, and ends with Pydantic answer validation and evidence-based citation verification. Query traces are stored alongside responses so results can be audited after the fact.

## Data and Safety Design

- Source files are chunked with start and end line metadata.
- Chunk content is stored with a 384-dimensional embedding.
- Existing files are skipped when their SHA-256 content hash is unchanged.
- Secrets are redacted before indexing.
- Absolute paths and paths outside `REPO_ROOT` are rejected.
- `read_file` only permits indexed, relative repository paths.
- Tool results are bounded and file slices are limited to 200 lines.
- Tool rounds, result limits, and wall-clock duration are enforced.
- Citation verification requires overlap with evidence seen during the run.

## Verification Status

- **Unit tests:** 6 passed.
- **Indexed repository:** 73 files skipped as unchanged; 151 chunks available.
- **Database:** PostgreSQL pgvector container healthy.
- **Application health:** `/health` returned database status `ok`.
- **Web application:** `/` and `/design-notes` served successfully.
- **Gemini integration:** Configured and updated to the available `gemini-3.8-flash` model ID.
- **Live provider behavior:** Initial live calls with the old `gemini-2.5-flash` model were rejected as unavailable. Retrying with `gemini-3.8-flash` reached Gemini but received temporary HTTP 503 capacity responses. Evaluation metrics should therefore remain unreported until live evaluation completes successfully.

## Resume Highlights

- Built a complete RAG-based code explanation system using FastAPI, PostgreSQL/pgvector, Sentence Transformers, and Google Gemini.
- Implemented incremental repository ingestion, 384-dimensional semantic embeddings, hybrid retrieval tools, path security, secret redaction, and source-grounded answer generation.
- Designed a bounded tool-calling agent loop with wall-clock and tool-round limits, Pydantic schema validation, retry behavior, citation verification, confidence scoring, and structured insufficiency handling.
- Added persistent query traces, latency and token telemetry, health/design endpoints, and an interactive evidence-exploration interface.
- Created and executed pytest coverage for agent loop behavior, citation validation, and path-traversal protection.

## Suggested Resume Bullet

**Built a full-stack RAG code-explanation platform** using FastAPI, PostgreSQL/pgvector, Sentence Transformers, and Google Gemini; implemented incremental repository indexing, secure tool-calling, citation verification, structured insufficiency detection, persistent run traces, a web UI, and automated pytest/evaluation workflows across 151 indexed code chunks.
