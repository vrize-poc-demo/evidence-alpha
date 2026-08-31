# Temporary Demo And Reviewer Deployment

## Reviewer Clone Workflow

The other reviewer can clone the repo and run it locally without copying any extra dataset manually, as long as `data/` is committed to GitHub.

They need:

- Python 3.11+
- Node.js 20+
- npm
- an LLM API key

Recommended easiest reviewer LLM provider:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
LLM_MODEL=gpt-4.1-mini
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=false
```

This is paid API usage, but for 3-10 reviewers asking a modest number of questions it should usually stay far below a ₹1,000 budget. Set a low usage limit in the provider billing dashboard before sharing the project.

The first backend startup rebuilds `backend/.index/chunks.json` from `data/filings`.

## Hosted Free/Low-Cost Path

For a 1-2 week client demo that may not run on your own machine, use:

- Render Free Web Service for the FastAPI backend and React frontend
- OpenAI API key for hosted LLM inference

This avoids running a local LLM on your laptop.

## Why This Path

The app needs CPU/RAM for HTML parsing and indexing, but not GPU compute if the LLM is hosted. The filing dataset is about 336 MB and the generated local index is about 70 MB. On first startup, the backend can rebuild the index from `data/filings`.

## Important Free-Tier Limits

Free hosting is enough for a demo, but not production:

- Free web services can sleep after inactivity.
- Files uploaded at runtime may disappear after redeploy/restart on ephemeral hosts.
- Free LLM APIs have rate limits.
- Accuracy depends more on retrieval quality and model quality than hosting.

For the demo, keep the provided filings committed under `data/filings` and use uploads only during the live session.

## Environment Variables

Backend:

```text
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
LLM_MODEL=qwen/qwen3.8-27b
USE_LLM=true
USE_PRACTICE_ANSWER_KEY=false
```

Frontend:

```text
VITE_API_URL=https://your-backend-url
```

## Accuracy Settings

For better accuracy:

- Send only the top retrieved evidence chunks to the LLM.
- Keep `temperature=0`.
- Use a stronger model if free limits allow it.
- Ask the LLM to return `not_found` when evidence is insufficient.
- Use optional benchmark mode only for controlled evaluation, not live LLM behavior.

## Free LLM Options

Preferred temporary option:

- Groq with `qwen/qwen3.8-27b`

Fallback:

- OpenRouter with `openrouter/free`

Paid higher-accuracy fallback:

- OpenAI with `gpt-4.1-mini` or a stronger model

## Render Notes

The included `render.yaml` defines one service:

- `evidence-alpha` for FastAPI plus the built React frontend

The service uses the included Dockerfile. Docker builds the React frontend with Node, then runs FastAPI with Python and serves the built frontend from the same app.
