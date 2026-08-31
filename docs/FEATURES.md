# Feature Guide

This document lists the current Evidence Alpha features and how they behave in the reviewer demo.

## Dashboard

The Dashboard is the first operational view. It shows:

- indexed filing count
- evidence chunk count
- active upload or indexing jobs
- saved chat count
- selected answer model
- quick links to Upload, Ask, History, and Service Health

The Dashboard is intentionally simple so a reviewer can quickly confirm that data exists before asking questions.

## Top Navigation

The app uses top navigation across the main pages:

- Dashboard
- Upload
- Ask
- History
- Service Health

The backend also serves the React app at `/` for Render deployment, so opening the backend root shows the same web UI.

## Upload

The Upload page supports one or many SEC filing uploads.

Supported upload types:

- `.htm`
- `.html`

Upload behavior:

- selected files are shown before upload
- upload progress/status is visible after submission
- files are sent to the backend processor
- each uploaded filing is parsed, chunked, indexed, and included in future searches
- all future questions search across all indexed filings, including uploaded files

## Multiple File Upload

The reviewer can select multiple SEC HTML files in one upload action. The backend creates one processor job per file.

Each job tracks:

- file name
- generated document name
- current status
- status message
- chunk count after completion

## Global Processor

The global processor is available across the app. It shows whether uploaded files are queued, processing, complete, or failed.

Processor states:

- `queued`
- `processing`
- `complete`
- `failed`

The frontend polls `GET /processor`, so the reviewer can navigate away from Upload and still see processing status.

## Ask

The Ask page is the main analyst workspace.

Current behavior:

- questions search all indexed filings automatically
- there is no filing picker in the chat
- there is no model picker in the chat
- the selected model is controlled from Service Health
- answers are shown in a chat-style interface
- answer cards include confidence, model used, document, page, and evidence
- unsupported questions should return `Not found in the indexed filings.`

The backend retrieves evidence first and sends only the question, current-chat context, and retrieved evidence to the selected LLM.

## Per-Chat Memory

Each chat has isolated memory.

What this means:

- follow-up questions inside one chat can use that chat's previous turns
- a new chat starts clean
- chats do not share history with each other
- chat history is used only to understand references such as "that company", "same year", or "what page supports it"
- final answers still need evidence from filings

The backend will not answer from chat history alone. The cited filing evidence must support the answer.

## Chat History

Chat history is stored in browser localStorage. This avoids database setup and keeps the demo easy to run on reviewer machines.

Each saved chat stores:

- chat title
- messages
- timestamps
- evidence attached to answers
- last updated time

Because history is browser-local, different browsers or machines do not share chat history.

## Evidence Citations

Every answered response includes supporting evidence when available:

- document name
- page number when detected
- evidence passage
- confidence score
- optional calculation text

The evidence drawer helps reviewers inspect why the answer was produced.

## Service Health

Service Health is the central operations page for the demo.

It shows:

- backend API health
- local index health
- upload processor health
- selected answer model health
- local Ollama status when a local model is selected

The bottom status bar provides a compact health indicator and a Details entry point.

## Model Selection

The Answer Model dropdown lives in Service Health. The Ask page reads the selected model and uses it for answers.

Supported choices:

- OpenAI ChatGPT 4.1-mini
- qwen3:14b local
- llama3.1 local

Default:

- OpenAI ChatGPT 4.1-mini

The selected model is stored in browser localStorage so the reviewer does not need to choose it repeatedly.

For model-by-model reasoning, pros, cons, and setup details, see `docs/MODEL_GUIDE.md`.

## OpenAI Mode

OpenAI mode uses:

- provider: OpenAI
- model: `gpt-4.1-mini`
- required env var: `OPENAI_API_KEY`

This is the recommended hosted demo mode because it works on Render and does not require a local machine with enough memory for large models.

## Local Ollama Mode

Local mode uses Ollama on the reviewer's machine.

Supported local models:

- `qwen3:14b`
- `llama3.1`

Local model features:

- Service Health shows whether Ollama is installed
- Service Health shows whether Ollama is reachable at `http://localhost:11434`
- the UI can start Ollama if the command is installed
- the UI can pull the selected approved model when Ollama is running but the model is missing
- the chat shows a clear setup message if the selected local model is not downloaded
- Render shows an information message because local Ollama cannot run inside the free hosted app

## Document Reset

Service Health includes a guarded document reset option.

To delete indexed/uploaded documents:

1. Open Service Health.
2. Choose Delete all documents.
3. Type `DELETE` in the confirmation dialog.
4. Confirm the reset.

This clears the active index and uploaded files used by the running app. It does not remove the committed source dataset from Git.

## Published And Local Versions

Published Render app:

- https://evidence-alpha.onrender.com
- API docs: https://evidence-alpha.onrender.com/docs

Local app:

- frontend: http://127.0.0.1:5173
- backend API helper: http://127.0.0.1:8000/api
- backend docs: http://127.0.0.1:8000/docs

## Known Demo Limits

- The app uses local file/index storage, not a production database.
- Uploaded files on Render can disappear after service restart or redeploy.
- Render free service can sleep after inactivity.
- Retrieval is keyword-based. Production accuracy should add hybrid search, table-aware extraction, reranking, and answer verification.
