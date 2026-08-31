from __future__ import annotations

import tempfile
import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .indexer import FilingIndex, answer_from_evidence, concise_evidence
from .indexer import ROOT
from .llm import answer_with_llm, llm_enabled, model_name, provider_name
from .models import AskRequest, AskResponse, Evidence, FilingSummary, UploadResponse


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Evidence Alpha API", version="0.1.0")
index = FilingIndex()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    index.ensure_index()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "llm_enabled": str(llm_enabled()).lower(),
        "provider": provider_name(),
        "model": model_name(),
    }


def practice_answer_key_enabled() -> bool:
    return os.getenv("USE_PRACTICE_ANSWER_KEY", "false").lower() in {"1", "true", "yes", "on"}


@app.get("/filings", response_model=list[FilingSummary])
def filings() -> list[dict]:
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
        chunk_count = index.add_upload(tmp_path, file.filename)
    finally:
        tmp_path.unlink(missing_ok=True)

    return UploadResponse(doc_name=Path(file.filename).stem, status="indexed", chunk_count=chunk_count)


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest) -> AskResponse:
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
        llm_answer = answer_with_llm(question, results)
        answer = llm_answer["answer"]
        confidence = llm_answer["confidence"]
        calculation = llm_answer.get("calculation")
        status = llm_answer["status"]
        used_model = f"{provider_name()}:{model_name()}"
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
