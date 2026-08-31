# Deployment

Evidence Alpha supports two demo modes:

- hosted Render demo for reviewers who do not want to run local servers
- local demo for reviewers who clone the repo

## Published Render Demo

- App: https://evidence-alpha.onrender.com
- Health: https://evidence-alpha.onrender.com/health
- API docs: https://evidence-alpha.onrender.com/docs
- Render dashboard: https://dashboard.render.com/web/srv-daam2buk1f9s73as2h5g/events

The service may sleep on the free Render plan. If the first request is slow or times out, wait 30-60 seconds and refresh.

On startup, FastAPI binds to Render's `$PORT` immediately and loads the filing index in the background. During that warm-up window, `/health` is available and Service Health may show the filing index as `working`.

## Render Architecture

The included `render.yaml` defines one web service named `evidence-alpha`.

Render uses the included `Dockerfile`:

1. Install frontend dependencies.
2. Build the React app.
3. Install backend dependencies.
4. Run FastAPI.
5. Serve both the API and the built React frontend from the same backend service.

This keeps the demo simple because reviewers only need one public URL.

The backend start command binds to:

```text
0.0.0.0:${PORT}
```

That is required for Render port detection.

## Render Environment Variables

Set these in Render:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=<set in Render dashboard>
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=true
OLLAMA_BASE_URL=http://localhost:11434/v1
```

`OPENAI_API_KEY` should be added as a secret environment variable. Do not commit a real key.

## Render Model Behavior

Render should use OpenAI ChatGPT 4.1-mini.

The app still shows the local model choices because the same UI is used for local and hosted demos. If a reviewer selects a local model on Render, Service Health explains that local Ollama models only work on a local machine.

## Local Deployment

Clone:

```bash
git clone git@github.com:vrize-poc-demo/evidence-alpha.git
cd evidence-alpha
```

Install:

```bash
./scripts/setup.sh
```

Run:

```bash
./scripts/start_app.sh
```

Open:

```text
http://127.0.0.1:5173
```

Backend:

```text
http://127.0.0.1:8000/api
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

## Data Persistence

Committed data:

- `data/filings`
- `data/practice-questions.jsonl`

Generated local data:

- `backend/.index/chunks.json`
- `backend/uploads`

Render free services have ephemeral storage. Runtime uploads can disappear after restart or redeploy. The committed filing dataset remains available because it is part of the repo.

## Cost Guidance

OpenAI API usage for 3-10 reviewers and a modest number of questions should normally stay low. Set a small spend limit in the OpenAI billing dashboard before sharing the demo.

Local Ollama mode has no API cost, but it requires a reviewer machine with enough RAM and the Ollama service running.

## Production Upgrade Notes

For a long-term hosted app, replace local JSON storage with persistent storage such as Postgres, object storage for uploads, and a production retrieval layer with embeddings or hybrid search.
