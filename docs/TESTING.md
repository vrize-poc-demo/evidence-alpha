# Testing

This project includes backend smoke tests and a frontend production build check.

## Backend Smoke Test

Run from the project root:

```bash
backend/.venv/bin/python scripts/smoke_test.py
```

The smoke test validates:

- FastAPI app imports
- `/health`
- `/models`
- `/filings`
- `/processor`
- copied filing dataset
- supported model choices
- sample question answer behavior
- evidence document and page citation
- unsupported question not-found behavior
- multiple-file upload processor flow

Latest local result:

```text
Smoke test passed.
```

## Frontend Build Test

Run:

```bash
cd frontend
npm run build
```

Latest local result:

```text
build completed successfully
```

## Practice Question UI Evaluation

The repository includes a Playwright evaluator that drives the app through the browser UI, asks the FinanceBench-style practice questions, scores each answer, and writes JSON plus Markdown reports.

Install the evaluator dependencies once from the project root:

```bash
npm install
npx playwright install chromium
```

Run a quick UI smoke test:

```bash
npm run eval:ui -- --limit 1 --model local-qwen3-14b --out reports/practice-ui-smoke.json
```

Run against `qwen3:14b`:

```bash
npm run eval:ui -- --model local-qwen3-14b --timeout-ms 300000 --out reports/practice-ui-qwen3-14b-full.json
```

Run against OpenAI GPT-4.1 mini:

```bash
npm run eval:ui -- --model openai-gpt-4.1-mini --timeout-ms 120000 --out reports/practice-ui-openai-gpt-4.1-mini-full.json
```

The evaluator starts a fresh chat for every practice question, asks through the same UI a user sees, reads the displayed answer card, and checks:

- expected answer match
- expected filing match
- expected evidence page match
- not-found or abstention behavior
- UI timeout or browser errors

Scoring:

- `+1` for correct answer with correct filing/page evidence
- `0` for correct answer with wrong evidence location
- `0` for not-found or abstained
- `-1` for wrong answer
- `-1` for UI/timeout error

Latest local UI evaluation notes:

- Real UI/model testing should keep `USE_PRACTICE_ANSWER_KEY=false`.
- Do not present practice answer-key results as model accuracy; that mode is only for internal deterministic demos.
- OpenAI real sample testing could not score answers locally because the local `.env` still contains the placeholder API key. The UI flow worked, but answers returned API-key errors.
- `qwen3:14b` smoke test passed `1/1`, scoring `1/1`.
- A prior interrupted `qwen3:14b` local UI run reached `3` completed/recorded questions with `1` correct and `2` UI/model timeouts.
- The timeout errors started repeating around the Best Buy filings, so the run was stopped instead of waiting several more hours on the local machine.
- Detailed output is written under `reports/`.

## Manual Browser Test

Use this checklist before a reviewer demo:

1. Start the app with `./scripts/start_app.sh`.
2. Open `http://127.0.0.1:5173`.
3. Confirm Dashboard shows indexed filings and chunks.
4. Open Service Health and confirm the selected model is healthy.
5. Change the Answer Model dropdown and verify the health card updates.
6. Open Upload, select one or many SEC HTML files, and verify progress messages appear.
7. Open Ask and confirm there is no filing selector and no model selector.
8. Ask a question and verify the answer includes evidence.
9. Ask a follow-up in the same chat and verify the answer can use that chat's context.
10. Create a new chat and verify it does not reuse the previous chat's context.
11. Open History and confirm chat sessions are saved.
12. Open Service Health, start the document reset flow, and confirm it requires typing `DELETE`.

## Sample Questions

Good smoke/demo question:

```text
Is 3M a capital-intensive business based on FY2022 data?
```

Follow-up question in the same chat:

```text
What page supports that answer?
```

Local context test that was verified with `qwen3:14b`:

```text
We are discussing Microsoft 2016 10-K.
What was revenue in 2016 compared with 2015?
```

Expected behavior:

- retrieval should target `MICROSOFT_2016_10K`
- the answer should cite filing evidence
- the answer should not use another chat's history

## LLM Test Notes

The app uses the selected LLM for inference only. It does not train or fine-tune a model.

OpenAI testing requires a valid `OPENAI_API_KEY` in `backend/.env` or in Render environment variables.

Local model testing requires Ollama running at:

```text
http://localhost:11434
```

Supported local models:

- `qwen3:14b`
