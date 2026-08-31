# Architecture

Evidence Alpha is a React + FastAPI retrieval-augmented generation app. It does not train an LLM. It retrieves relevant SEC filing passages first, then asks the selected LLM to answer only from those passages.

## High-Level System

```mermaid
flowchart LR
    Reviewer["Reviewer"] --> UI["React + Vite UI"]
    UI --> API["FastAPI backend"]
    API --> Indexer["SEC HTML parser + chunker"]
    Indexer --> LocalIndex["Local evidence index<br/>backend/.index/chunks.json"]
    API --> Retriever["BM25-style retriever"]
    Retriever --> LocalIndex
    Retriever --> Evidence["Top evidence chunks"]
    Evidence --> LLMRouter["LLM router"]
    LLMRouter --> OpenAI["OpenAI<br/>gpt-4.1-mini"]
    LLMRouter --> Ollama["Local Ollama<br/>qwen3:14b / llama3.1"]
    API --> UI
    UI --> BrowserStore["Browser localStorage<br/>chat history + model choice"]
```

## Main Components

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Web UI | React, Vite, lucide-react | Dashboard, upload, chat, history, health, model selection |
| API | FastAPI, Pydantic | Routes, validation, upload handling, service health, answer orchestration |
| Parser | BeautifulSoup | SEC HTML cleanup and text extraction |
| Index | JSON file | Local searchable filing chunks and metadata |
| Retrieval | BM25-style keyword search | Finds relevant evidence across all indexed filings |
| LLM | OpenAI or Ollama | Generates evidence-grounded answers |
| Browser storage | localStorage | Saves chat sessions and selected model for the reviewer |

## Data Flow

```mermaid
flowchart TB
    Data["data/filings<br/>committed SEC HTML files"] --> Startup["Backend startup"]
    Startup --> BuildIndex["Build or load local index"]
    Upload["Reviewer uploads files"] --> Processor["Global processor jobs"]
    Processor --> BuildIndex
    BuildIndex --> Searchable["Searchable chunks"]
    Searchable --> Ask["Question answering"]
```

The copied dataset lives in `data/filings`. On first backend startup, the app builds `backend/.index/chunks.json`. Uploaded files are stored under `backend/uploads` and added to the active index.

## Upload Processing

```mermaid
sequenceDiagram
    participant U as Reviewer
    participant UI as React UI
    participant API as FastAPI
    participant P as Processor
    participant IDX as Local Index

    U->>UI: Select one or many .htm/.html files
    UI->>API: POST /filings/upload-multiple
    API->>P: Create one job per file
    P->>P: Parse and clean SEC HTML
    P->>P: Split into page-like chunks
    P->>IDX: Add chunks and metadata
    UI->>API: Poll GET /processor
    API-->>UI: Return queued/processing/complete/failed
```

## Question Answering

```mermaid
sequenceDiagram
    participant U as Reviewer
    participant UI as Ask Page
    participant API as FastAPI
    participant R as Retriever
    participant L as Selected LLM

    U->>UI: Ask question in active chat
    UI->>API: POST /ask with question, model_choice, current chat context
    API->>API: Clean current-chat context only
    API->>R: Search all indexed filings
    R-->>API: Top evidence chunks
    API->>L: Send question + current-chat context + evidence
    L-->>API: Return JSON answer with evidence id
    API-->>UI: Answer, confidence, document, page, evidence
```

Important behavior:

- The retriever searches all indexed filings.
- Chat context comes only from the active chat.
- New chats do not use older chat history.
- The LLM must cite supplied filing evidence.
- If evidence is weak, the expected answer is `Not found in the indexed filings.`

## Model Selection

```mermaid
flowchart LR
    Health["Service Health page"] --> Choice["Answer Model dropdown"]
    Choice --> LocalStorage["Saved in browser localStorage"]
    LocalStorage --> Ask["Ask page uses selected model"]
    Ask --> Backend["POST /ask model_choice"]
    Backend --> Router["LLM router"]
    Router --> GPT["OpenAI gpt-4.1-mini"]
    Router --> Qwen["Ollama qwen3:14b"]
    Router --> Llama["Ollama llama3.1"]
```

The model selector is intentionally not inside the chat page. This keeps each chat focused on the conversation while Service Health controls the operating mode.

## Service Health

Service Health calls:

- `GET /health`
- `GET /health/services`
- `GET /models`
- `GET /local-models/status`

It shows only the selected model's detailed health. For example, if OpenAI is selected, local Ollama details are not shown as the active model health. If a local model is selected, Ollama setup and model download controls are shown.

## Storage Model

| Data | Location | Notes |
| --- | --- | --- |
| Original filings | `data/filings` | Committed with the repo |
| Practice questions | `data/practice-questions.jsonl` | Used for smoke tests and optional benchmark mode |
| Generated index | `backend/.index/chunks.json` | Rebuilt automatically if missing |
| Uploaded filings | `backend/uploads` | Local runtime files |
| Chat history | Browser localStorage | Per browser and per machine |
| Processor jobs | Backend memory | Runtime-only status |

There is no external database in this proof-of-solution.

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Render["Render hosted demo"]
        Docker["Docker build"] --> ReactBuild["Build React static assets"]
        ReactBuild --> FastAPI["FastAPI serves API + frontend"]
        FastAPI --> OpenAI["OpenAI gpt-4.1-mini"]
    end

    subgraph Local["Local reviewer machine"]
        LocalReact["Vite frontend"] --> LocalAPI["FastAPI backend"]
        LocalAPI --> LocalOpenAI["OpenAI gpt-4.1-mini"]
        LocalAPI --> LocalOllama["Ollama qwen3:14b / llama3.1"]
    end
```

Render should use OpenAI. Local reviewers can use OpenAI or Ollama.

## Accuracy Approach

Evidence Alpha uses a conservative RAG pattern:

1. Search all indexed filings.
2. Select the best evidence chunks.
3. Include current-chat context only for follow-up interpretation.
4. Ask the LLM to answer in strict JSON.
5. Require the answer to cite evidence.
6. Decline when evidence is insufficient.

The production upgrade path should add table-aware extraction, hybrid search, embeddings, reranking, and a second verifier pass that checks numbers against citations.
