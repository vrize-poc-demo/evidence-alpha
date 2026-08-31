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
    model_choice: str | None = None


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


class ProcessingJob(BaseModel):
    job_id: str
    file_name: str
    doc_name: str
    status: str
    message: str
    chunk_count: int = 0


class MultiUploadResponse(BaseModel):
    status: str
    jobs: list[ProcessingJob]


class ServiceHealthItem(BaseModel):
    name: str
    status: str
    message: str
    detail: str | None = None


class ServiceHealthResponse(BaseModel):
    status: str
    services: list[ServiceHealthItem]
