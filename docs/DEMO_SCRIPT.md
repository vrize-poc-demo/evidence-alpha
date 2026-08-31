# Demo Script

## Setup

Start backend:

```bash
./scripts/start_app.sh
```

Open `http://127.0.0.1:5173`.

## Demo Story

1. Show indexed SEC filings and evidence chunk counts on the dashboard.
2. Show the dashboard metrics and model status.
3. Open Upload and select one or many `.htm` filings.
4. Show the global processor status.
5. Open Ask, select `3M_2022_10K`, and choose the model from the dropdown.
6. Ask: `Is 3M a capital-intensive business based on FY2022 data?`
7. Show the answer, source document, page, and evidence drawer.
8. Open History and show the saved chat.
9. Ask an unsupported or vague question and show `Not found in this filing.`

## Talking Points

- The product does not just answer; it proves where the answer came from.
- The LLM answers only after the backend retrieves filing evidence.
- Optional benchmark mode can show exact expected outputs, but normal mode uses the LLM.
- For unseen questions, it searches the selected filing and declines weak evidence.
- The next production step is hybrid retrieval plus LLM verification.
