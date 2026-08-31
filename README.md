# Evidence Alpha

Evidence Alpha is a proof-of-solution Analyst Copilot app for asking questions over SEC filings. It uses a React web UI, a FastAPI backend, local document indexing, and an LLM answer layer that must cite evidence from the indexed filings.

The app is built for a short client or reviewer demo: reviewers can upload one or many filings, ask questions across all indexed filings, see chat history, inspect citations, and check service health from the browser.

## Published Demo

- Published app: https://evidence-alpha.onrender.com
- Health check: https://evidence-alpha.onrender.com/health
- API docs: https://evidence-alpha.onrender.com/docs
- Render dashboard: https://dashboard.render.com/web/srv-daam2buk1f9s73as2h5g/events

Render free services can sleep after inactivity. If the published app is slow on first open, wait 30-60 seconds and refresh.

## Main Features

- Dashboard with indexed filing counts, evidence chunk counts, upload activity, chat count, and selected model status.
- Top navigation for Dashboard, Upload, Ask, History, and Service Health.
- Single file upload for SEC `.htm` and `.html` filings.
- Multiple file upload for bulk filing processing.
- Global processor that shows queued, processing, complete, and failed upload jobs.
- Ask page with chat-style Q&A over all uploaded and indexed filings.
- Per-chat memory for follow-up questions. A new chat starts with a clean history and does not use other chats.
- Browser chat history stored locally for the reviewer.
- Evidence-backed answers with confidence, source document, page number, and supporting passages.
- Service Health page with backend, index, processor, selected LLM, and Ollama/local model setup status.
- Model selection from Service Health only, with exactly three supported choices:
  - OpenAI ChatGPT 4.1-mini
  - qwen3:14b local
  - llama3.1 local
- Local Ollama controls to open/download Ollama, start Ollama, and pull the selected local model.
- Confirmed document reset flow. The reviewer must type `DELETE` before all indexed/uploaded documents are cleared.
- Render-compatible single service where FastAPI serves both the API and the built React app.

## Tech Stack

- Frontend: React, Vite, lucide-react icons, browser localStorage for chat history and model preference.
- Backend: FastAPI, Uvicorn, Pydantic.
- Parsing: BeautifulSoup for SEC HTML cleanup and chunking.
- Retrieval: local BM25-style keyword search over filing chunks.
- LLMs:
  - OpenAI `gpt-4.1-mini` for hosted and easiest reviewer mode.
  - Ollama `qwen3:14b` for local-only mode.
  - Ollama `llama3.1` for local-only mode.
- Storage:
  - Source filings in `data/filings`.
  - Generated index in `backend/.index/chunks.json`.
  - Uploaded files in `backend/uploads`.
  - Chat history in browser localStorage.
  - No external database is required.
- Deployment: Docker and Render free web service.

## Quick Start For Reviewers

Clone the repository:

```bash
git clone git@github.com:vrize-poc-demo/evidence-alpha.git
cd evidence-alpha
```

Run setup once:

```bash
./scripts/setup.sh
```

Add the OpenAI API key in `backend/.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=false
```

Start the full app with one command:

```bash
./scripts/start_app.sh
```

Open the local app:

```text
http://127.0.0.1:5173
```

Useful backend URLs:

```text
API helper page: http://127.0.0.1:8000/api
Swagger docs:    http://127.0.0.1:8000/docs
Health check:    http://127.0.0.1:8000/health
```

The backend root `http://127.0.0.1:8000/` intentionally serves the React app. Use `/docs`, `/api`, or `/health` when you want backend pages.

## Local Model Option

Local models are optional. OpenAI ChatGPT 4.1-mini is the default and easiest reviewer mode.

To use a local LLM, install and run Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Then pull one of the supported models:

```bash
ollama pull qwen3:14b
ollama pull llama3.1
```

In the app, open Service Health and change the Answer Model dropdown to `qwen3:14b local` or `llama3.1 local`.

On Render, local model choices are visible for clarity, but they show an information message because Ollama runs only on a local reviewer machine.

## Demo Flow

1. Open the Dashboard and show filing/chunk counts.
2. Open Service Health and confirm the selected answer model is healthy.
3. Open Upload and upload one or many SEC HTML filings.
4. Watch the global processor finish the upload jobs.
5. Open Ask and ask a question. The app searches all indexed filings automatically.
6. Ask a follow-up question in the same chat. The app uses only that chat's history.
7. Create a new chat and ask a question. The new chat does not inherit prior chat memory.
8. Open the evidence drawer and show source document, page, and passage.
9. Open History to show saved chats.

Sample question:

```text
Is 3M a capital-intensive business based on FY2022 data?
```

Follow-up example:

```text
What page supports that answer?
```

## Testing

Run the backend smoke test:

```bash
backend/.venv/bin/python scripts/smoke_test.py
```

Run the frontend build:

```bash
cd frontend
npm run build
```

The smoke test checks health endpoints, model options, indexed filings, the processor endpoint, sample answer behavior, and multi-file upload processing.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Feature Guide](docs/FEATURES.md)
- [Reviewer Guide](docs/REVIEWER_GUIDE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Testing](docs/TESTING.md)
- [Demo Script](docs/DEMO_SCRIPT.md)
- [Sample Questions](docs/SAMPLE_QUESTIONS.md)
- [Requirements From Prompt](docs/REQUIREMENTS.md)
- [Approach Note](docs/APPROACH.md)

## API Endpoints

- `GET /api` - backend helper page with documentation links.
- `GET /health` - basic backend health.
- `GET /health/services` - detailed service health for the UI.
- `GET /models` - supported model choices.
- `GET /local-models/status` - Ollama and local model status.
- `POST /local-models/start` - start Ollama locally when installed.
- `POST /local-models/pull` - download an approved local model.
- `GET /filings` - indexed filing summaries.
- `GET /processor` - global upload/indexing processor jobs.
- `POST /filings/upload` - upload one filing.
- `POST /filings/upload-multiple` - upload multiple filings.
- `POST /documents/delete-all` - delete indexed/uploaded documents after confirmation.
- `POST /ask` - ask a question with optional current-chat context.

## Notes For Reviewers

This app does not train or fine-tune an LLM. It retrieves relevant evidence from filings, sends that evidence to the selected LLM, and asks the LLM to answer only from the supplied evidence.

For the most accurate demo path, use OpenAI ChatGPT 4.1-mini. For the lowest running cost on a capable local machine, use Ollama with `qwen3:14b`.
