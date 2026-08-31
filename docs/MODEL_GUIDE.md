# Model Guide

Evidence Alpha supports exactly two answer models. The model is selected from the Service Health page, not from the chat page.

The app does not train or fine-tune any model. It uses retrieval-augmented generation:

1. Search all indexed SEC filings.
2. Select the strongest evidence chunks.
3. Add reusable financial-analysis style examples for formulas and answer structure.
4. Send the question, active-chat context, style examples, and evidence to the selected model.
5. Ask the model to answer only from the supplied evidence.
6. Return citations with document and page details.

The style examples are not answer keys. They describe methods such as capex/revenue, quick ratio, ROA, operating margin, and inventory turnover. They do not contain the benchmark answers.

## Recommended Default

Use OpenAI ChatGPT 4.1-mini for the reviewer demo unless there is a strong reason to avoid API usage.

Why:

- works on Render
- easiest for non-technical reviewers
- no local model installation
- better accuracy and instruction following than the local options in most demo cases
- good balance of quality and cost for a short 3-10 reviewer evaluation

## Model Comparison

| Model option | Runs where | Best for | Pros | Cons |
| --- | --- | --- | --- | --- |
| OpenAI ChatGPT 4.1-mini | Render and local | Main reviewer demo | Best setup experience, strong instruction following, good citation discipline, no local hardware requirement | Requires API key, has usage cost, needs internet |
| qwen3:14b local | Local only | Free local accuracy testing | No API cost, good reasoning for a local model, stronger than smaller local models when hardware is available | Requires Ollama, large download, needs enough RAM/CPU, cannot run on Render free plan |

## OpenAI ChatGPT 4.1-Mini

Configuration id:

```text
openai-gpt-4.1-mini
```

Backend model:

```text
gpt-4.1-mini
```

Use this when:

- the app is deployed on Render
- reviewers are not technical
- accuracy matters more than avoiding API cost
- the demo needs to work for 1-2 weeks without depending on your laptop

Pros:

- strongest option for the hosted demo
- no Ollama setup
- works from any reviewer machine through the web app
- handles instructions and JSON response format better
- better at declining unsupported answers when the prompt and evidence are clear

Cons:

- requires `OPENAI_API_KEY`
- has API cost
- needs internet access
- key must be configured securely in `backend/.env` locally or Render environment variables

Cost note:

For 3-10 reviewers asking a modest number of questions, this should normally stay low. Set a billing limit before sharing the demo.

## Qwen3:14B Local

Configuration id:

```text
local-qwen3-14b
```

Ollama model:

```text
qwen3:14b
```

Use this when:

- the app is running locally
- avoiding API cost is important
- the reviewer machine has enough memory and time for a larger local model
- accuracy matters more than speed among the local options

Pros:

- free after download
- no external API calls for answer generation
- good local reasoning capability compared with smaller free local models
- stronger free local option for this financial QA demo
- useful for demos where API keys are not available

Cons:

- local only
- requires Ollama
- large model download
- slower than hosted OpenAI on many laptops
- may be less consistent with strict JSON and citation rules
- judged accuracy will still depend heavily on retrieval quality and table parsing
- will not work on Render free plan

Observed local testing:

- Qwen3 14B passed the first practice-question UI smoke test.
- A prior interrupted 3-question local run had 1 correct answer and 2 UI/model timeouts.
- It is the best free local option in this project, but OpenAI GPT-4.1 mini remains the safer judged-accuracy mode.

## Launch-Time Learning

The app does not fine-tune Qwen3 14B when it starts. Instead, launch-time learning means:

1. build or load the filing index
2. retrieve relevant filing evidence for each question
3. add general finance style examples to the prompt
4. ask Qwen3 14B to answer only from cited evidence

This is an honest RAG pattern. It improves behavior without hiding benchmark answers in the model path.

Setup:

```bash
ollama pull qwen3:14b
ollama serve
```

## Render vs Local Decision

Use this decision rule:

| Situation | Choose |
| --- | --- |
| Reviewer opens the hosted Render URL | OpenAI ChatGPT 4.1-mini |
| Reviewer clones and runs locally, wants easiest setup | OpenAI ChatGPT 4.1-mini |
| Reviewer wants no API spend and has a capable machine | qwen3:14b local |

## Accuracy Notes

The model is only one part of answer quality. Accuracy also depends on:

- whether the right filing was indexed
- whether retrieval found the right evidence page
- whether the filing table was parsed cleanly
- whether the model follows the evidence-only instruction

For production, add hybrid retrieval, table-aware extraction, reranking, and an answer verifier.
