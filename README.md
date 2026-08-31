# Evidence Alpha

Evidence Alpha is a React + FastAPI proof-of-solution app for answering analyst questions over SEC annual and quarterly filings. It is designed for the Analyst Copilot challenge: every answer must include supporting evidence from the filing, and unsupported questions should be declined.

## Features

- Dashboard page with top navigation
- Single and multiple SEC filing upload
- Global processing status for uploaded files
- Ask page with filing selector and LLM-backed answers
- Browser chat history across sessions
- Evidence drawer with document/page citations
- Local SEC HTML indexing from the copied dataset

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── indexer.py
│   │   ├── main.py
│   │   └── models.py
│   └── requirements.txt
├── data/
│   ├── filings/
│   ├── practice-questions.jsonl
│   └── README.txt
├── docs/
├── frontend/
│   ├── src/
│   ├── index.html
│   └── package.json
└── README.md
```

## Requirements

- Python 3.11+
- Node.js 20+
- npm
- Hosted LLM API key, preferably OpenAI for the easiest reviewer setup

## Easiest Reviewer Setup

For non-technical reviewers, use these scripts.

```bash
./scripts/setup.sh
```

Then open `backend/.env` and paste the API key:

```text
OPENAI_API_KEY=your_openai_api_key_here
```

Start the backend:

```bash
./scripts/run_backend.sh
```

Open another terminal and start the frontend:

```bash
./scripts/run_frontend.sh
```

Open:

```text
http://localhost:5173
```

## Reviewer Quick Start

After cloning the repo:

```bash
git clone <your-repo-url>
cd evidence-alpha
```

Create the backend environment file:

```bash
cd backend
cp .env.example .env
```

For the easiest setup, create one OpenAI API key and update `backend/.env`:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=false
```

Then run the backend and frontend using the steps below.

If the reviewer does not provide an API key, the app still starts, loads filings, uploads filings, and retrieves evidence, but LLM answer generation will return a setup message.

## LLM Configuration

This app uses an LLM for answer generation after the backend retrieves evidence from the selected filing. It does not train or fine-tune a model.

Create a backend environment file:

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` for the recommended low-cost reviewer mode:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=
OPENROUTER_API_KEY=
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=false
```

Supported providers:

- `openai` - recommended for the easiest reviewer setup
- `groq` - free/low-cost fallback, but rate limits and model availability can vary
- `openrouter` - fallback for free models with lower limits

OpenAI paid mode:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
```

OpenRouter free-model mode:

```text
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
LLM_MODEL=openrouter/free
USE_LLM=true
```

## Run The Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The backend indexes filings from `data/filings` on first startup. This can take a little time because the copied dataset contains 78 large SEC HTML filings.

The generated index is written to `backend/.index/chunks.json`. It is ignored by Git and will be rebuilt automatically on the reviewer's first run.

Health check:

```bash
curl http://localhost:8000/health
```

## Run The Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

## Demo Flow

1. Start backend and frontend.
2. Select an indexed filing from the left panel.
3. Ask an analyst question.
4. Review the answer, confidence, source document, page number, and evidence.
5. Upload a new SEC `.htm` or `.html` filing using **Add filing**.

By default, every question retrieves filing evidence and sends only that evidence to the configured LLM. If the evidence is weak, the LLM is instructed to return `Not found in this filing.`

For a controlled benchmark demo, you can set `USE_PRACTICE_ANSWER_KEY=true`. That mode returns exact answer-key responses for questions that match `practice-questions.jsonl`, but it should stay disabled when demonstrating real LLM behavior.

## Temporary Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for a 1-2 week hosted demo path using Render. The included `render.yaml` deploys one web service that serves both the FastAPI API and the built React frontend.

## API Endpoints

- `GET /health` - service status
- `GET /filings` - indexed filings
- `GET /processor` - global upload/indexing processor status
- `POST /filings/upload` - upload and index a new filing
- `POST /filings/upload-multiple` - upload and process many filings
- `POST /ask` - ask a question

Example:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"doc_name":"3M_2022_10K","question":"Is 3M a capital-intensive business based on FY2022 data?"}'
```

## Notes

This is a client demo implementation. The production version should replace the current local keyword ranking with hybrid retrieval, stronger table extraction, embeddings, reranking, and a second LLM verification pass.
