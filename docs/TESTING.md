# Testing

## Smoke Test

Run:

```bash
backend/.venv/bin/python scripts/smoke_test.py
```

The smoke test validates:

- FastAPI app imports
- `/health`
- `/models`
- `/filings`
- `/processor`
- sample question answer and page citation
- unsupported question not-found path
- multiple-file upload processor

## Latest Local Test Result

Status:

```text
Smoke test passed.
```

Validated sample questions:

| Filing | Expected page | Result |
| --- | ---: | --- |
| `3M_2022_10K` | 47 | Capital intensity answer returned with evidence |
| `3M_2018_10K` | 59 | FY2018 capex answer returned as `$1577.00` |
| `3M_2022_10K` | 26 | Operating margin change answer returned with evidence |

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

## Notes About LLM Testing

The smoke test uses controlled benchmark mode and local fallback mode so it can run without spending OpenAI API calls.

For live LLM testing:

1. Set `OPENAI_API_KEY` in `backend/.env`.
2. Keep `USE_LLM=true`.
3. Keep `USE_PRACTICE_ANSWER_KEY=false`.
4. Start the backend and frontend.
5. Choose `OpenAI ChatGPT 4.1-mini` from the Ask page.
