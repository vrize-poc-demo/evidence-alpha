from pydantic import BaseModel


class FilingSummary(BaseModel):
    doc_name: str
    file_name: str
    company: str | None = None
    doc_type: str | None = None
    doc_period: str | None = None
    status: str = "indexed"
    chunk_count: int = 0


class Evidence(BaseModel):
    doc_name: str
    page_num: int | None
    text: str
    score: float


class AskRequest(BaseModel):
    question: str
    doc_name: str | None = None


class AskResponse(BaseModel):
    status: str
    answer: str
    confidence: float
    model_used: str | None = None
    document: str | None = None
    page: int | None = None
    evidence: list[Evidence] = []
    calculation: str | None = None


class UploadResponse(BaseModel):
    doc_name: str
    status: str
    chunk_count: int
