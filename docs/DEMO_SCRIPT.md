# Demo Script

Use this script for a 5-10 minute client or reviewer walkthrough.

## Start

Local:

```bash
./scripts/start_app.sh
```

Open:

```text
http://127.0.0.1:5173
```

Hosted:

```text
https://evidence-alpha.onrender.com
```

## Story

Evidence Alpha is an analyst copilot for SEC filings. It does not answer from general memory. It searches filing evidence first, sends that evidence to the selected LLM, and returns an answer with citations.

## Walkthrough

1. Open Dashboard.
2. Point out indexed filings, evidence chunks, processing status, chat count, and selected model.
3. Open Service Health.
4. Show the Answer Model dropdown.
5. Keep OpenAI ChatGPT 4.1-mini selected for the hosted demo.
6. Explain that qwen3:14b local is available only when running locally with Ollama.
7. Open Upload.
8. Select one or many SEC `.htm` or `.html` filings.
9. Upload and show the processor status moving through queued, processing, and complete.
10. Open Ask.
11. Explain that questions search all uploaded and indexed filings automatically.
12. Ask:

```text
Is 3M a capital-intensive business based on FY2022 data?
```

13. Show answer, confidence, document, page number, and evidence drawer.
14. Ask a follow-up in the same chat:

```text
What page supports that answer?
```

15. Explain that follow-ups use only the current chat's history.
16. Create a new chat and explain that the new chat does not use the previous chat's memory.
17. Open History and show saved chats.
18. Open Service Health and show the guarded Delete all documents action. Do not confirm unless the demo needs a reset.

## Talking Points

- The app prioritizes accuracy over speed by requiring filing evidence before answer generation.
- The LLM is used for answer generation, not training.
- OpenAI ChatGPT 4.1-mini is the easiest hosted path.
- Local models reduce API cost but require Ollama and enough machine resources.
- The current proof-of-solution uses local JSON indexing, so no database setup is needed.
- Production should add hybrid search, better table extraction, persistent storage, and answer verification.

## Fallback If OpenAI Key Is Missing

If OpenAI is not configured:

1. Open Service Health.
2. Show that OpenAI is unhealthy or missing a key.
3. Switch to a local model only if Ollama is installed and running.
4. Otherwise explain that uploads, indexing, search, health checks, and API docs still work, but LLM answers need a configured model.
