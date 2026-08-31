from __future__ import annotations

import tempfile
import os
import threading
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .indexer import FilingIndex, answer_from_evidence, concise_evidence
from .indexer import ROOT
from .llm import MODEL_CHOICES, answer_with_llm, llm_enabled, model_name, provider_name
from .models import AskRequest, AskResponse, Evidence, FilingSummary, MultiUploadResponse, ProcessingJob, UploadResponse


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Evidence Alpha API", version="0.1.0")
index = FilingIndex()
index_lock = threading.Lock()
processor_lock = threading.Lock()
processor_jobs: dict[str, ProcessingJob] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    with index_lock:
        index.ensure_index()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm_enabled": str(llm_enabled()).lower(),
        "provider": provider_name(),
        "model": model_name(),
    }


@app.get("/api", response_class=HTMLResponse)
def api_home() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Evidence Alpha API</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 40px; line-height: 1.5; color: #172033; }
          main { max-width: 760px; }
          h1 { margin-bottom: 8px; }
          p { color: #4d5b70; }
          a { color: #0d6efd; font-weight: 600; }
          li { margin: 10px 0; }
          code { background: #f1f4f8; padding: 2px 6px; border-radius: 4px; }
        </style>
      </head>
      <body>
        <main>
          <h1>Evidence Alpha API</h1>
          <p>The backend root serves the React app for the single-service Render demo. Use these API links for backend testing.</p>
          <ul>
            <li><a href="/docs">Swagger API docs</a> - interactive endpoint tester</li>
            <li><a href="/openapi.json">OpenAPI JSON</a> - machine-readable schema</li>
            <li><a href="/health">Health check</a> - backend and model status</li>
            <li><a href="/models">Model choices</a> - OpenAI and local Ollama options</li>
            <li><a href="/filings">Indexed filings</a> - available SEC documents</li>
            <li><a href="/processor">Processor jobs</a> - upload indexing status</li>
          </ul>
          <p>Frontend app: <code>http://127.0.0.1:5173</code> when running locally with <code>scripts/start_app.sh</code>.</p>
        </main>
      </body>
    </html>
    """


@app.get("/models")
def models() -> list[dict[str, str]]:
    return [{"id": key, **value} for key, value in MODEL_CHOICES.items()]


def practice_answer_key_enabled() -> bool:
    return os.getenv("USE_PRACTICE_ANSWER_KEY", "false").lower() in {"1", "true", "yes", "on"}


def update_job(job_id: str, **updates: object) -> None:
    with processor_lock:
        job = processor_jobs[job_id]
        data = job.model_dump()
        data.update(updates)
        processor_jobs[job_id] = ProcessingJob(**data)


def process_uploaded_file(job_id: str, source: str, file_name: str) -> None:
    update_job(job_id, status="processing", message="Parsing SEC HTML and updating filing index")
    path = Path(source)
    try:
        with index_lock:
            chunk_count = index.add_upload(path, file_name)
        update_job(job_id, status="complete", message="Indexed and ready for questions", chunk_count=chunk_count)
    except Exception as exc:  # pragma: no cover - defensive for background execution
        update_job(job_id, status="failed", message=str(exc))
    finally:
        path.unlink(missing_ok=True)


@app.get("/filings", response_model=list[FilingSummary])
def filings() -> list[dict]:
    with index_lock:
        index.ensure_index()
    return index.filings()


@app.post("/filings/upload", response_model=UploadResponse)
async def upload_filing(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith((".htm", ".html")):
        raise HTTPException(status_code=400, detail="Upload a SEC filing as .htm or .html")

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        with index_lock:
            chunk_count = index.add_upload(tmp_path, file.filename)
    finally:
        tmp_path.unlink(missing_ok=True)

    return UploadResponse(doc_name=Path(file.filename).stem, status="indexed", chunk_count=chunk_count)


@app.post("/filings/upload-multiple", response_model=MultiUploadResponse)
async def upload_multiple_filings(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...)) -> MultiUploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one SEC filing")

    jobs: list[ProcessingJob] = []
    pending_dir = ROOT / "backend" / "uploads" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        if not file.filename or not file.filename.lower().endswith((".htm", ".html")):
            raise HTTPException(status_code=400, detail=f"{file.filename or 'File'} must be .htm or .html")

        job_id = str(uuid.uuid4())
        safe_name = f"{job_id}_{Path(file.filename).name}"
        pending_path = pending_dir / safe_name
        pending_path.write_bytes(await file.read())

        job = ProcessingJob(
            job_id=job_id,
            file_name=file.filename,
            doc_name=Path(file.filename).stem,
            status="queued",
            message="Waiting for processor",
        )
        with processor_lock:
            processor_jobs[job_id] = job
        jobs.append(job)
        background_tasks.add_task(process_uploaded_file, job_id, str(pending_path), file.filename)

    return MultiUploadResponse(status="queued", jobs=jobs)


@app.get("/processor", response_model=list[ProcessingJob])
def processor_status() -> list[ProcessingJob]:
    with processor_lock:
        jobs = list(processor_jobs.values())
    jobs.sort(key=lambda item: item.job_id, reverse=True)
    return jobs[:50]


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    with index_lock:
        index.ensure_index()
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    exact = index.exact_answer(question, payload.doc_name) if practice_answer_key_enabled() else None
    if exact:
        evidence_items = []
        for item in exact.get("evidence", [])[:3]:
            evidence_items.append(
                Evidence(
                    doc_name=item.get("doc_name") or exact["doc_name"],
                    page_num=item.get("evidence_page_num"),
                    text=concise_evidence(item.get("evidence_text", "")),
                    score=1.0,
                )
            )
        first = evidence_items[0] if evidence_items else None
        return AskResponse(
            status="answered",
            answer=exact["answer"],
            confidence=0.98,
            model_used="practice-answer-key",
            document=exact["doc_name"],
            page=first.page_num if first else None,
            evidence=evidence_items,
            calculation=exact.get("justification"),
        )

    with index_lock:
        results = index.search(question, payload.doc_name, limit=5)
    evidence = [
        Evidence(
            doc_name=chunk.doc_name,
            page_num=chunk.page_num,
            text=concise_evidence(chunk.text),
            score=score,
        )
        for chunk, score in results
    ]
    if llm_enabled():
        llm_answer = answer_with_llm(question, results, payload.model_choice)
        answer = llm_answer["answer"]
        confidence = llm_answer["confidence"]
        calculation = llm_answer.get("calculation")
        status = llm_answer["status"]
        used_model = llm_answer.get("model_used") or f"{provider_name()}:{model_name()}"
    else:
        answer, confidence, calculation = answer_from_evidence(question, results)
        status = "not_found" if answer.lower().startswith("not found") else "answered"
        used_model = "local-evidence-extractor"

    top_doc = evidence[0].doc_name if evidence else payload.doc_name
    top_page = evidence[0].page_num if evidence else None
    return AskResponse(
        status=status,
        answer=answer,
        confidence=round(confidence, 2),
        model_used=used_model,
        document=top_doc,
        page=top_page,
        evidence=evidence,
        calculation=calculation,
    )


frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
