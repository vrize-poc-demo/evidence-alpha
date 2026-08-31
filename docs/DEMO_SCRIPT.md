# Demo Script

## Setup

Start backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Start frontend:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`.

## Demo Story

1. Show indexed SEC filings in the left panel.
2. Select `3M_2022_10K`.
3. Ask: `Is 3M a capital-intensive business based on FY2022 data?`
4. Show the answer, source document, page, and evidence drawer.
5. Ask an unsupported or vague question and show `Not found in this filing.`
6. Upload a new `.htm` filing and show that it gets indexed.

## Talking Points

- The product does not just answer; it proves where the answer came from.
- The LLM answers only after the backend retrieves filing evidence.
- Optional benchmark mode can show exact expected outputs, but normal mode uses the LLM.
- For unseen questions, it searches the selected filing and declines weak evidence.
- The next production step is hybrid retrieval plus LLM verification.
