from __future__ import annotations

import json
import os

from openai import OpenAI, OpenAIError

from .indexer import Chunk, concise_evidence


DEFAULT_PROVIDER = "openai"
DEFAULT_MODELS = {
    "openai": "gpt-4.1-mini",
    "groq": "qwen/qwen3.8-27b",
    "openrouter": "openrouter/free",
}


def provider_name() -> str:
    return os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).lower()


def llm_enabled() -> bool:
    return os.getenv("USE_LLM", "true").lower() in {"1", "true", "yes", "on"}


def model_name() -> str:
    return os.getenv("LLM_MODEL", DEFAULT_MODELS.get(provider_name(), DEFAULT_MODELS["groq"]))


def api_key_name() -> str:
    provider = provider_name()
    if provider == "groq":
        return "GROQ_API_KEY"
    if provider == "openrouter":
        return "OPENROUTER_API_KEY"
    return "OPENAI_API_KEY"


def client_for_provider() -> OpenAI:
    provider = provider_name()
    api_key = os.getenv(api_key_name())
    if provider == "groq":
        return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    if provider == "openrouter":
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": os.getenv("APP_URL", "http://localhost:5173"),
                "X-Title": "Evidence Alpha",
            },
        )
    return OpenAI(api_key=api_key)


def build_evidence(results: list[tuple[Chunk, float]]) -> list[dict]:
    evidence = []
    for index, (chunk, score) in enumerate(results, start=1):
        evidence.append(
            {
                "id": index,
                "doc_name": chunk.doc_name,
                "page_num": chunk.page_num,
                "score": score,
                "text": concise_evidence(chunk.text, max_chars=1800),
            }
        )
    return evidence


def answer_with_llm(question: str, results: list[tuple[Chunk, float]]) -> dict:
    if not results:
        return {
            "status": "not_found",
            "answer": "Not found in this filing.",
            "confidence": 0.0,
            "calculation": None,
        }

    key_name = api_key_name()
    if not os.getenv(key_name):
        return {
            "status": "not_found",
            "answer": f"LLM is enabled, but {key_name} is not set. Add the key and restart the backend.",
            "confidence": 0.0,
            "calculation": None,
        }

    evidence = build_evidence(results)
    prompt = {
        "question": question,
        "evidence": evidence,
        "instructions": [
            "Answer only from the supplied evidence.",
            "If the evidence does not directly support the answer, return status not_found.",
            "Do not use outside knowledge.",
            "For numbers, preserve units and explain any calculation briefly.",
            "Return valid JSON only.",
        ],
        "schema": {
            "status": "answered or not_found",
            "answer": "short analyst-ready answer",
            "confidence": "number between 0 and 1",
            "evidence_id": "id of strongest evidence item, or null",
            "calculation": "brief calculation or null",
        },
    }

    try:
        client = client_for_provider()
        response = client.chat.completions.create(
            model=model_name(),
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Evidence Alpha, a careful financial analyst assistant. "
                        "You answer SEC filing questions only when cited evidence proves the answer. "
                        "When evidence is weak or absent, say not_found."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
    except (OpenAIError, json.JSONDecodeError) as exc:
        return {
            "status": "not_found",
            "answer": f"LLM answer generation failed: {exc}",
            "confidence": 0.0,
            "calculation": None,
        }

    status = parsed.get("status")
    if status not in {"answered", "not_found"}:
        status = "not_found"

    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "status": status,
        "answer": parsed.get("answer") or "Not found in this filing.",
        "confidence": max(0.0, min(confidence, 1.0)),
        "evidence_id": parsed.get("evidence_id"),
        "calculation": parsed.get("calculation"),
    }
