from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from openai import OpenAI, OpenAIError

from .indexer import Chunk, concise_evidence


DEFAULT_PROVIDER = "openai"
DEFAULT_MODELS = {"openai": "gpt-4.1-mini", "ollama": "qwen3:14b"}
MODEL_CHOICES = {
    "openai-gpt-4.1-mini": {"provider": "openai", "model": "gpt-4.1-mini", "label": "OpenAI ChatGPT 4.1-mini"},
    "local-qwen3-14b": {"provider": "ollama", "model": "qwen3:14b", "label": "qwen3:14b local"},
    "local-llama3.1": {"provider": "ollama", "model": "llama3.1", "label": "llama3.1 local"},
}


def provider_name() -> str:
    return os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).lower()


def llm_enabled() -> bool:
    return os.getenv("USE_LLM", "true").lower() in {"1", "true", "yes", "on"}


def model_name() -> str:
    return os.getenv("LLM_MODEL", DEFAULT_MODELS.get(provider_name(), DEFAULT_MODELS["openai"]))


def resolve_model_choice(model_choice: str | None) -> tuple[str, str, str]:
    if model_choice and model_choice in MODEL_CHOICES:
        choice = MODEL_CHOICES[model_choice]
        return choice["provider"], choice["model"], choice["label"]
    provider = provider_name()
    model = model_name()
    return provider, model, f"{provider}:{model}"


def api_key_name(provider: str | None = None) -> str | None:
    provider = provider or provider_name()
    if provider == "ollama":
        return None
    return "OPENAI_API_KEY"


def client_for_provider(provider: str) -> OpenAI:
    if provider == "ollama":
        return OpenAI(
            api_key=os.getenv("OLLAMA_API_KEY", "ollama"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        )
    api_key = os.getenv(api_key_name(provider) or "")
    return OpenAI(api_key=api_key)


def ollama_root_url() -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    return base_url[:-3] if base_url.endswith("/v1") else base_url


def ollama_model_available(model: str) -> tuple[bool, bool]:
    try:
        with urllib.request.urlopen(f"{ollama_root_url()}/api/tags", timeout=1.5) as response:
            if response.status != 200:
                return False, False
            data = json.loads(response.read().decode("utf-8"))
            models = [item.get("name", "") for item in data.get("models", []) if item.get("name")]
            return True, any(item == model or item.startswith(f"{model}:") for item in models)
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, False


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


def answer_with_llm(
    question: str,
    results: list[tuple[Chunk, float]],
    model_choice: str | None = None,
    chat_context: list[dict[str, str]] | None = None,
) -> dict:
    if not results:
        return {
            "status": "not_found",
            "answer": "Not found in the indexed filings.",
            "confidence": 0.0,
            "calculation": None,
        }

    provider, selected_model, label = resolve_model_choice(model_choice)
    key_name = api_key_name(provider)
    if key_name and not os.getenv(key_name):
        return {
            "status": "not_found",
            "answer": f"LLM is enabled, but {key_name} is not set. Add the key and restart the backend.",
            "confidence": 0.0,
            "model_used": label,
            "calculation": None,
        }
    if provider == "ollama":
        ollama_running, model_available = ollama_model_available(selected_model)
        if not ollama_running:
            return {
                "status": "not_found",
                "answer": (
                    f"{label} is selected, but Ollama is not reachable. "
                    "Open Service Health, start Ollama, then ask again."
                ),
                "confidence": 0.0,
                "model_used": label,
                "calculation": None,
            }
        if not model_available:
            return {
                "status": "not_found",
                "answer": (
                    f"{label} is selected, but {selected_model} is not downloaded. "
                    "Open Service Health and click Download for the selected model."
                ),
                "confidence": 0.0,
                "model_used": label,
                "calculation": None,
            }

    evidence = build_evidence(results)
    prompt = {
        "question": question,
        "chat_context": chat_context or [],
        "evidence": evidence,
        "instructions": [
            "Use chat_context only to understand follow-up references such as 'it', 'that company', or 'same year'.",
            "Answer only from the supplied evidence.",
            "If the evidence does not directly support the answer, return status not_found.",
            "Do not use outside knowledge.",
            "Do not answer from chat_context alone; cited evidence must prove the answer.",
            "For numbers, preserve units and explain any calculation briefly.",
            (
                "For capital-intensive questions, calculate and reason from ratios such as capex/revenue, "
                "fixed assets/total assets, and return on assets when the evidence provides them. "
                "Do not conclude that a company is capital intensive merely because it has PP&E or capital spending."
            ),
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
        client = client_for_provider(provider)
        response = client.chat.completions.create(
            model=selected_model,
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
        if provider == "ollama":
            message = (
                f"{label} is selected, but Ollama is not reachable. "
                "Start Ollama locally and pull the selected model before asking again."
            )
        else:
            message = f"LLM answer generation failed: {exc}"
        return {
            "status": "not_found",
            "answer": message,
            "confidence": 0.0,
            "model_used": label,
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
        "answer": parsed.get("answer") or "Not found in the indexed filings.",
        "confidence": max(0.0, min(confidence, 1.0)),
        "model_used": label,
        "evidence_id": parsed.get("evidence_id"),
        "calculation": parsed.get("calculation"),
    }
