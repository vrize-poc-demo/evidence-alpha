# Evidence Alpha Architecture

## Goal

Build a trustworthy analyst copilot over SEC filings. The app should answer only when evidence is available and should show the source document, page, and supporting passage.

## Data

The copied dataset lives in `data/`:

- `data/filings/` contains 78 SEC HTML filings.
- `data/practice-questions.jsonl` contains 136 benchmark-style questions.
- Each practice question includes the answer and evidence page number.

The filings are HTML, not PDF. That means the first implementation parses SEC HTML directly instead of running OCR or PDF conversion.

## Backend

FastAPI provides the application API.

Main files:

- `backend/app/main.py` exposes API routes.
- `backend/app/indexer.py` parses filings, builds the local index, searches evidence, and handles practice-question answer lookup.
- `backend/app/models.py` defines request and response models.

On startup, the backend creates `backend/.index/chunks.json` if it does not already exist.

## Indexing Strategy

1. Read SEC HTML.
2. Strip script/style content.
3. Convert HTML into clean text.
4. Split text into page-like chunks.
5. Tokenize chunks.
6. Store chunk text with metadata:
   - document name
   - file name
   - detected page number
   - token list

This demo uses a lightweight local index so it can run without external infrastructure.

## Retrieval Strategy

The current search uses a BM25-like keyword score:

- tokenize the question
- search only the selected filing when one is selected
- score chunks by query-token overlap and inverse document frequency
- return the top evidence chunks

This is intentionally simple and transparent for the proof-of-solution.

## LLM Answer Strategy

There are two paths:

1. Normal LLM path:
   - Retrieve top evidence chunks.
   - Send only those chunks plus the question to the configured LLM.
   - The LLM must return JSON with answer, confidence, status, evidence id, and calculation.
   - If the evidence is weak, return `Not found in this filing.`

2. Optional benchmark mode:
   - If `USE_PRACTICE_ANSWER_KEY=true`, exact practice questions can return the supplied benchmark answer and evidence.
   - Keep this disabled for real LLM demos.

The default model is `gpt-4.1-mini`, configured with `LLM_MODEL`. The model is used for inference only. The app does not train or fine-tune an LLM.

## Model Selection

The Ask page exposes exactly three model choices:

- OpenAI ChatGPT 4.1-mini
- qwen3:14b local
- llama3.1 local

OpenAI uses `OPENAI_API_KEY`. Local models use Ollama through the OpenAI-compatible API at `http://localhost:11434/v1`.

## Frontend

React provides a demo-friendly analyst workspace:

- top navigation
- dashboard
- filing selector
- single and multiple filing upload
- global processor status
- sample questions
- chat interface
- local browser chat history
- answer cards
- evidence drawer

The frontend calls the FastAPI backend at `http://localhost:8000` by default.

## Upload Processing

The backend exposes a global processor:

- `POST /filings/upload-multiple` accepts one or more SEC HTML files.
- Each file becomes a processing job.
- Jobs move through `queued`, `processing`, `complete`, or `failed`.
- `GET /processor` returns recent processing jobs.
- The frontend polls the processor and displays status across all pages.

## Production Upgrade Path

For a stronger version:

- preserve SEC table structure more carefully
- add SQLite FTS5 or OpenSearch keyword retrieval
- add embeddings with FAISS, Chroma, Pinecone, or Supabase Vector
- add a reranker
- add an answer verifier that checks every number against cited evidence
- add evaluation metrics against the 136 practice questions
