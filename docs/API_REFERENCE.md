# API Reference

FastAPI serves the backend API. Locally, API docs are available at:

```text
http://127.0.0.1:8000/docs
```

Published API docs:

```text
https://evidence-alpha.onrender.com/docs
```

## Health

### `GET /health`

Basic health endpoint for the backend.

### `GET /health/services`

Detailed health for the web UI status bar and Service Health page.

Query parameters:

- `model_choice` optional selected model id

Returns backend, index, processor, and selected model health.

### `POST /services/restart`

Runs a safe restart/reload action from the Service Health page.

Request body:

```json
{
  "service": "index"
}
```

Supported service values:

- `backend` - on Render, requests a process restart; locally, returns terminal restart instructions
- `index` - reloads the filing index in the background
- `processor` - resets processor queue/status
- `openai` - reloads OpenAI configuration from `backend/.env`
- `ollama` - starts/rechecks Ollama locally

## Models

### `GET /models`

Returns the exact supported model choices:

- `openai-gpt-4.1-mini`
- `local-qwen3-14b`
- `local-llama3.1`

## Local Models

### `GET /local-models/status`

Returns Ollama installation, running status, installed models, and any model download jobs.

### `POST /local-models/start`

Attempts to start Ollama locally when the `ollama` command is installed.

### `POST /local-models/pull`

Downloads one approved local model through Ollama.

Request body:

```json
{
  "model_choice": "local-qwen3-14b"
}
```

## Filings

### `GET /filings`

Returns indexed filing summaries.

### `POST /filings/upload`

Uploads and indexes one SEC HTML filing.

### `POST /filings/upload-multiple`

Uploads one or many SEC HTML filings and creates processor jobs.

## Processor

### `GET /processor`

Returns recent global upload/indexing jobs.

Job statuses:

- `queued`
- `processing`
- `complete`
- `failed`

## Documents

### `POST /documents/delete-all`

Deletes active indexed/uploaded documents after confirmation.

Request body:

```json
{
  "confirmation": "DELETE"
}
```

## Ask

### `POST /ask`

Asks a question across all indexed filings.

Request body:

```json
{
  "question": "Is 3M a capital-intensive business based on FY2022 data?",
  "model_choice": "openai-gpt-4.1-mini",
  "chat_context": [
    {
      "role": "user",
      "text": "We are discussing 3M FY2022."
    }
  ]
}
```

Notes:

- `doc_name` is optional for backward compatibility, but the UI searches all indexed filings.
- `chat_context` should contain only messages from the active chat.
- A new chat should send no previous chat context.

Response includes:

- answer status
- answer text
- confidence
- model used
- document
- page
- evidence passages
- optional calculation
