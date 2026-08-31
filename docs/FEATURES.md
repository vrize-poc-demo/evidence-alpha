# Feature Guide

## Dashboard

The dashboard gives a quick operational view:

- indexed filing count
- evidence chunk count
- active processing jobs
- chat session count
- active LLM provider and model
- quick actions for Upload, Ask, and History

## Upload

The Upload page supports:

- one SEC `.htm` or `.html` filing
- multiple SEC `.htm` or `.html` filings at once
- background processing for each file
- global status updates

Each uploaded file is parsed, chunked, indexed, and then added to the filing selector.

## Global Processor

The global processor appears across pages when upload jobs exist.

Job states:

- `queued`
- `processing`
- `complete`
- `failed`

The frontend polls `GET /processor` so the user can move around the app while files are being processed.

## Ask

The Ask page supports:

- filing selection
- model selection
- sample questions
- evidence-backed answers
- not-found responses

Supported model choices:

- OpenAI ChatGPT 4.1-mini
- qwen3:14b local
- llama3.1 local

## Chat History

Chat history is stored in browser local storage. This keeps the demo simple and avoids database setup.

Each history item stores:

- chat title
- selected filing
- messages
- last updated time

## Render And Local Behavior

Render should use OpenAI ChatGPT 4.1-mini.

Local runs can use OpenAI or Ollama. The UI still shows local model options on Render, but displays an information message that they only work locally with Ollama.
