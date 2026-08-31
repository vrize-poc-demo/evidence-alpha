from __future__ import annotations

import tempfile
import os
import json
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .indexer import FilingIndex, answer_from_evidence, concise_evidence
from .indexer import ROOT
from .llm import MODEL_CHOICES, answer_with_llm, llm_enabled, model_name, provider_name, resolve_model_choice
from .models import (
    AskRequest,
    AskResponse,
    DeleteDocumentsRequest,
    DeleteDocumentsResponse,
    Evidence,
    FilingSummary,
    LocalModelActionRequest,
    LocalModelJob,
    LocalModelStatusResponse,
    MultiUploadResponse,
    ProcessingJob,
    ServiceHealthItem,
    ServiceHealthResponse,
    UploadResponse,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Evidence Alpha API", version="0.1.0")
index = FilingIndex()
index_lock = threading.Lock()
processor_lock = threading.Lock()
processor_jobs: dict[str, ProcessingJob] = {}
local_model_lock = threading.Lock()
local_model_jobs: dict[str, LocalModelJob] = {}
ollama_process: subprocess.Popen | None = None
LOCAL_MODEL_CHOICES = {
    "local-qwen3-14b": "qwen3:14b",
    "local-llama3.1": "llama3.1",
}

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


def service_item(name: str, status: str, message: str, detail: str | None = None) -> ServiceHealthItem:
    return ServiceHealthItem(name=name, status=status, message=message, detail=detail)


def ollama_root_url() -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    return base_url[:-3] if base_url.endswith("/v1") else base_url


def ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def ollama_tags() -> tuple[bool, list[str]]:
    root_url = ollama_root_url()
    try:
        with urllib.request.urlopen(f"{root_url}/api/tags", timeout=1.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
                return True, models
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, []
    return False, []


def ollama_health(model_choice: str | None = None) -> ServiceHealthItem:
    root_url = ollama_root_url()
    installed = ollama_installed()
    running, models = ollama_tags()
    selected_model = LOCAL_MODEL_CHOICES.get(model_choice or "", "")
    selected_label = MODEL_CHOICES.get(model_choice or "", {}).get("label", "Local Ollama")
    if running:
        if selected_model:
            installed_model = any(item == selected_model or item.startswith(f"{selected_model}:") for item in models)
            if installed_model:
                return service_item(selected_label, "ok", "Ollama running and selected model is downloaded", root_url)
            return service_item(selected_label, "warning", "Ollama is running, but this model is not downloaded yet", root_url)
        model_count = len(models)
        return service_item("Local Ollama", "ok", f"Reachable with {model_count} local model(s)", root_url)
    if installed:
        return service_item(selected_label, "warning", "Installed but not running. Use Health details to start it.", root_url)
    return service_item(selected_label, "warning", "Not installed. Use Health details to download Ollama.", root_url)


def selected_model_health(model_choice: str | None) -> ServiceHealthItem:
    provider, selected_model, label = resolve_model_choice(model_choice)
    if provider == "ollama":
        return ollama_health(model_choice)
    if not llm_enabled():
        return service_item("LLM generation", "warning", "USE_LLM is disabled", "Evidence retrieval still works")
    if os.getenv("OPENAI_API_KEY"):
        return service_item(label, "ok", "API key configured", selected_model)
    return service_item(label, "warning", "OPENAI_API_KEY is not set", selected_model)


def set_local_model_job(model_choice: str, model: str, status: str, message: str) -> LocalModelJob:
    job = LocalModelJob(model_choice=model_choice, model=model, status=status, message=message)
    with local_model_lock:
        local_model_jobs[model_choice] = job
    return job


def pull_local_model(model_choice: str, model: str) -> None:
    set_local_model_job(model_choice, model, "working", f"Downloading {model}. This can take several minutes.")
    try:
        completed = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except subprocess.TimeoutExpired:
        set_local_model_job(model_choice, model, "error", f"Download timed out for {model}.")
        return
    except OSError as exc:
        set_local_model_job(model_choice, model, "error", f"Could not run ollama pull: {exc}")
        return

    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode == 0:
        set_local_model_job(model_choice, model, "complete", f"{model} is downloaded and ready.")
    else:
        set_local_model_job(model_choice, model, "error", output[-260:] or f"Download failed for {model}.")


def ensure_ollama_model_choice(model_choice: str) -> str:
    model = LOCAL_MODEL_CHOICES.get(model_choice)
    if not model:
        raise HTTPException(status_code=400, detail="Choose qwen3:14b local or llama3.1 local.")
    return model


@app.get("/local-models/status", response_model=LocalModelStatusResponse)
def local_model_status() -> LocalModelStatusResponse:
    running, models = ollama_tags()
    with local_model_lock:
        jobs = list(local_model_jobs.values())
    return LocalModelStatusResponse(
        ollama_installed=ollama_installed(),
        ollama_running=running,
        installed_models=models,
        jobs=jobs,
    )


@app.post("/local-models/start")
def start_ollama() -> dict[str, str]:
    global ollama_process
    if not ollama_installed():
        raise HTTPException(status_code=400, detail="Ollama is not installed. Download it first from https://ollama.com/download")

    running, _ = ollama_tags()
    if running:
        return {"status": "ok", "message": "Ollama is already running."}

    try:
        ollama_process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not start Ollama: {exc}") from exc

    time.sleep(1)
    running, _ = ollama_tags()
    return {
        "status": "ok" if running else "starting",
        "message": "Ollama started." if running else "Ollama start requested. Refresh health in a few seconds.",
    }


@app.post("/local-models/pull", response_model=LocalModelJob)
def pull_ollama_model(payload: LocalModelActionRequest, background_tasks: BackgroundTasks) -> LocalModelJob:
    model = ensure_ollama_model_choice(payload.model_choice)
    if not ollama_installed():
        raise HTTPException(status_code=400, detail="Ollama is not installed. Download it first from https://ollama.com/download")

    running, models = ollama_tags()
    if not running:
        raise HTTPException(status_code=400, detail="Ollama is not running. Start Ollama first.")
    if any(item == model or item.startswith(f"{model}:") for item in models):
        return set_local_model_job(payload.model_choice, model, "complete", f"{model} is already downloaded.")

    job = set_local_model_job(payload.model_choice, model, "queued", f"Queued download for {model}.")
    background_tasks.add_task(pull_local_model, payload.model_choice, model)
    return job


@app.get("/health/services", response_model=ServiceHealthResponse)
def service_health(model_choice: str | None = None) -> ServiceHealthResponse:
    with index_lock:
        index.ensure_index()
        filing_count = len(index.filings())
        chunk_count = len(index.chunks)
    with processor_lock:
        jobs = list(processor_jobs.values())

    active_jobs = [job for job in jobs if job.status in {"queued", "processing"}]
    failed_jobs = [job for job in jobs if job.status == "failed"]
    services = [
        service_item("FastAPI backend", "ok", "Running", "http://127.0.0.1:8000"),
        service_item(
            "Filing index",
            "ok" if filing_count else "warning",
            f"{filing_count} filing(s), {chunk_count} evidence chunk(s)",
            "Loaded from data/filings and uploaded files",
        ),
        service_item(
            "Global processor",
            "working" if active_jobs else ("error" if failed_jobs else "ok"),
            f"{len(active_jobs)} active, {len(failed_jobs)} failed, {len(jobs)} recent job(s)",
            "Polls upload indexing jobs",
        ),
    ]

    services.append(selected_model_health(model_choice))

    if any(item.status == "error" for item in services):
        overall = "error"
    elif any(item.status in {"warning", "working"} for item in services):
        overall = "warning"
    else:
        overall = "ok"
    return ServiceHealthResponse(status=overall, services=services)


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
            <li><a href="/local-models/status">Local model status</a> - Ollama install, running, and download jobs</li>
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


def clean_chat_context(payload: AskRequest) -> list[dict[str, str]]:
    context = []
    for item in payload.chat_context[-8:]:
        role = item.role if item.role in {"user", "assistant"} else "user"
        text = item.text.strip()
        if text:
            context.append({"role": role, "text": text[:900]})
    return context


def contextual_search_question(question: str, chat_context: list[dict[str, str]]) -> str:
    if not chat_context:
        return question
    prior = " ".join(item["text"] for item in chat_context[-4:])
    return f"{prior} {question}"


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


@app.post("/documents/delete-all", response_model=DeleteDocumentsResponse)
def delete_all_documents(payload: DeleteDocumentsRequest) -> DeleteDocumentsResponse:
    if payload.confirmation != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm document deletion")

    with index_lock:
        deleted_documents, deleted_chunks = index.clear_documents()
    with processor_lock:
        processor_jobs.clear()

    return DeleteDocumentsResponse(
        status="deleted",
        deleted_documents=deleted_documents,
        deleted_chunks=deleted_chunks,
        message="All indexed documents and uploaded files were deleted from the active app index.",
    )


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
    with index_lock:
        index.ensure_index()
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    chat_context = clean_chat_context(payload)

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
        results = index.search(contextual_search_question(question, chat_context), payload.doc_name, limit=5)
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
        llm_answer = answer_with_llm(question, results, payload.model_choice, chat_context)
        answer = llm_answer["answer"]
        confidence = llm_answer["confidence"]
        calculation = llm_answer.get("calculation")
        status = llm_answer["status"]
        used_model = llm_answer.get("model_used") or f"{provider_name()}:{model_name()}"
        evidence_id = llm_answer.get("evidence_id")
    else:
        answer, confidence, calculation = answer_from_evidence(question, results)
        status = "not_found" if answer.lower().startswith("not found") else "answered"
        used_model = "local-evidence-extractor"
        evidence_id = None

    cited_evidence = evidence[0] if evidence else None
    try:
        evidence_index = int(evidence_id) if evidence_id is not None else 0
    except (TypeError, ValueError):
        evidence_index = 0
    if 1 <= evidence_index <= len(evidence):
        cited_evidence = evidence[evidence_index - 1]
    top_doc = cited_evidence.doc_name if cited_evidence else payload.doc_name
    top_page = cited_evidence.page_num if cited_evidence else None
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
