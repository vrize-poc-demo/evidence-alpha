# Reviewer Guide

This guide is for someone who wants to run Evidence Alpha locally after cloning the repository.

## Published Demo

- App: https://evidence-alpha.onrender.com
- Health: https://evidence-alpha.onrender.com/health
- API docs: https://evidence-alpha.onrender.com/docs

If the Render app is slow at first, the free service may be waking up. Wait 30-60 seconds and refresh.

## Local Requirements

Install these before running the project:

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- OpenAI API key for the easiest answer-generation path

Ollama is optional and only needed for local LLM testing.

## Clone The Repo

```bash
git clone git@github.com:vrize-poc-demo/evidence-alpha.git
cd evidence-alpha
```

## One-Time Setup

```bash
./scripts/setup.sh
```

This installs backend and frontend dependencies and creates `backend/.env` if it does not already exist.

## Configure OpenAI

Open `backend/.env` and set:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OLLAMA_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=false
```

Do not commit a real API key to GitHub.

## Start The App

```bash
./scripts/start_app.sh
```

Open:

```text
http://127.0.0.1:5173
```

Backend pages:

```text
http://127.0.0.1:8000/api
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

## How To Demo

1. Open Dashboard and confirm filings are indexed.
2. Open Service Health and confirm OpenAI ChatGPT 4.1-mini is selected.
3. Open Upload and upload one or many `.htm` or `.html` SEC filings.
4. Watch the processor status until files are complete.
5. Open Ask and ask:

```text
Is 3M a capital-intensive business based on FY2022 data?
```

6. Ask a follow-up in the same chat:

```text
What page supports that answer?
```

7. Create a new chat and ask another question. The new chat will not use the first chat's history.
8. Open the evidence drawer to inspect citations.
9. Open History to see saved chats.

## Choosing A Model

Open Service Health and use the Answer Model dropdown.

Supported options:

- OpenAI ChatGPT 4.1-mini
- qwen3:14b local

Use OpenAI for the easiest reviewer setup. Use Qwen3 14B local only when Ollama is installed and running.

## Local LLM Setup

Install Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Start Ollama:

```bash
ollama serve
```

Download supported models:

```bash
ollama pull qwen3:14b
```

The Service Health page can also help start Ollama and download the selected local model.

## Troubleshooting

If the app opens but answers fail:

- Check Service Health.
- Confirm `OPENAI_API_KEY` is set in `backend/.env`.
- Confirm the selected model is healthy.
- Confirm filings are indexed on the Dashboard.

If `http://127.0.0.1:8000/` opens the frontend, that is expected. Use `http://127.0.0.1:8000/docs` for Swagger API documentation.

If a local model says Ollama is not reachable, start Ollama with `ollama serve` or use OpenAI mode.
