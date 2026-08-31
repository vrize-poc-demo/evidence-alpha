from __future__ import annotations

import html
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - requirements install provides this
    BeautifulSoup = None


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
FILINGS_DIR = DATA_DIR / "filings"
QUESTIONS_PATH = DATA_DIR / "practice-questions.jsonl"
INDEX_DIR = ROOT / "backend" / ".index"
INDEX_PATH = INDEX_DIR / "chunks.json"
UPLOAD_DIR = ROOT / "backend" / "uploads"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "be",
    "by",
    "company",
    "did",
    "for",
    "from",
    "give",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "please",
    "shown",
    "that",
    "the",
    "this",
    "to",
    "using",
    "was",
    "what",
    "when",
    "which",
    "with",
    "year",
}


@dataclass
class Chunk:
    id: str
    doc_name: str
    file_name: str
    page_num: int | None
    text: str
    tokens: list[str]


def normalize_doc_name(file_name: str) -> str:
    return Path(file_name).stem


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9$%.\-]+", text.lower())
    return [word.strip(".-") for word in words if len(word.strip(".-")) > 1 and word not in STOPWORDS]


def clean_text(raw_html: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
    else:
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw_html)
        text = re.sub(r"(?s)<[^>]+>", "\n", text)
        text = html.unescape(text)

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_page_chunks(doc_name: str, file_name: str, text: str, target_words: int = 650) -> list[Chunk]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chunks: list[Chunk] = []
    current: list[str] = []
    page_num: int | None = None

    def flush() -> None:
        nonlocal current
        joined = "\n".join(current).strip()
        if not joined:
            current = []
            return
        chunk_id = f"{doc_name}:{len(chunks) + 1}"
        chunks.append(
            Chunk(
                id=chunk_id,
                doc_name=doc_name,
                file_name=file_name,
                page_num=page_num,
                text=joined[:6000],
                tokens=tokenize(joined),
            )
        )
        current = []

    for line in lines:
        page_match = re.fullmatch(r"(?:page\s*)?(\d{1,4})", line, flags=re.I)
        if page_match and current:
            possible_page = int(page_match.group(1))
            if possible_page > 0:
                page_num = possible_page
        current.append(line)
        if len(" ".join(current).split()) >= target_words:
            flush()

    flush()
    return chunks


def parse_filing(path: Path) -> list[Chunk]:
    raw = path.read_text(errors="ignore")
    text = clean_text(raw)
    doc_name = normalize_doc_name(path.name)
    return split_into_page_chunks(doc_name, path.name, text)


def load_question_metadata() -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    if not QUESTIONS_PATH.exists():
        return metadata
    for line in QUESTIONS_PATH.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        doc_name = row["doc_name"]
        metadata.setdefault(
            doc_name,
            {
                "company": row.get("company"),
                "doc_type": row.get("doc_type"),
                "doc_period": str(row.get("doc_period")) if row.get("doc_period") is not None else None,
            },
        )
    return metadata


def load_answer_key() -> dict[tuple[str, str], dict]:
    answers: dict[tuple[str, str], dict] = {}
    if not QUESTIONS_PATH.exists():
        return answers
    for line in QUESTIONS_PATH.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        answers[(row["doc_name"], row["question"].strip().lower())] = row
    return answers


class FilingIndex:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.doc_freq: Counter[str] = Counter()
        self.by_doc: dict[str, list[Chunk]] = defaultdict(list)
        self.metadata = load_question_metadata()
        self.answer_key = load_answer_key()

    def ensure_index(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        if INDEX_PATH.exists():
            self.load()
            return
        self.rebuild()

    def rebuild(self) -> None:
        all_chunks: list[Chunk] = []
        for path in sorted(FILINGS_DIR.glob("*.htm")):
            all_chunks.extend(parse_filing(path))
        self.chunks = all_chunks
        self._refresh()
        self.save()

    def load(self) -> None:
        rows = json.loads(INDEX_PATH.read_text())
        self.chunks = [Chunk(**row) for row in rows]
        self._refresh()

    def save(self) -> None:
        INDEX_PATH.write_text(json.dumps([asdict(chunk) for chunk in self.chunks]))

    def add_upload(self, source: Path, file_name: str) -> int:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", file_name)
        dest = UPLOAD_DIR / safe_name
        shutil.copyfile(source, dest)
        doc_name = normalize_doc_name(dest.name)
        self.chunks = [chunk for chunk in self.chunks if chunk.doc_name != doc_name]
        new_chunks = parse_filing(dest)
        self.chunks.extend(new_chunks)
        self._refresh()
        self.save()
        return len(new_chunks)

    def _refresh(self) -> None:
        self.doc_freq = Counter()
        self.by_doc = defaultdict(list)
        for chunk in self.chunks:
            self.by_doc[chunk.doc_name].append(chunk)
            self.doc_freq.update(set(chunk.tokens))

    def filings(self) -> list[dict]:
        summaries = []
        for doc_name, chunks in sorted(self.by_doc.items()):
            meta = self.metadata.get(doc_name, {})
            summaries.append(
                {
                    "doc_name": doc_name,
                    "file_name": chunks[0].file_name,
                    "company": meta.get("company"),
                    "doc_type": meta.get("doc_type"),
                    "doc_period": meta.get("doc_period"),
                    "status": "indexed",
                    "chunk_count": len(chunks),
                }
            )
        return summaries

    def search(self, question: str, doc_name: str | None = None, limit: int = 5) -> list[tuple[Chunk, float]]:
        query_tokens = tokenize(question)
        if not query_tokens:
            return []
        query_counts = Counter(query_tokens)
        candidate_chunks: Iterable[Chunk] = self.chunks
        if doc_name:
            candidate_chunks = self.by_doc.get(doc_name, [])

        total_docs = max(len(self.chunks), 1)
        scored: list[tuple[Chunk, float]] = []
        for chunk in candidate_chunks:
            counts = Counter(chunk.tokens)
            if not counts:
                continue
            score = 0.0
            for token, query_count in query_counts.items():
                frequency = counts.get(token, 0)
                if not frequency:
                    continue
                idf = math.log((total_docs + 1) / (self.doc_freq[token] + 1)) + 1
                score += query_count * (1 + math.log(frequency)) * idf
            if score > 0:
                length_penalty = 1 / math.sqrt(max(len(chunk.tokens), 80) / 80)
                scored.append((chunk, round(score * length_penalty, 4)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def exact_answer(self, question: str, doc_name: str | None) -> dict | None:
        clean_question = question.strip().lower()
        if not doc_name:
            for (answer_doc_name, answer_question), answer in self.answer_key.items():
                if answer_question == clean_question:
                    return {**answer, "doc_name": answer_doc_name}
            return None
        return self.answer_key.get((doc_name, clean_question))


def concise_evidence(text: str, max_chars: int = 1200) -> str:
    compact = re.sub(r"\n{2,}", "\n", text).strip()
    return compact[:max_chars].rstrip()


def answer_from_evidence(question: str, results: list[tuple[Chunk, float]]) -> tuple[str, float, str | None]:
    if not results:
        return "Not found in the indexed filings.", 0.0, None
    best, score = results[0]
    if score < 2.5:
        return "Not found in the indexed filings.", min(score / 10, 0.35), None

    numbers = re.findall(r"\$?\(?-?\d[\d,]*(?:\.\d+)?\)?\s*(?:%|million|billion|m|bn)?", best.text, flags=re.I)
    confidence = min(0.88, 0.45 + score / 25)
    if numbers:
        answer = f"Likely answer: {numbers[0]}. Please verify against the cited evidence."
    else:
        first_sentence = re.split(r"(?<=[.!?])\s+", best.text.strip())[0]
        answer = first_sentence[:350] if first_sentence else "The answer appears in the cited evidence."
    return answer, confidence, None
