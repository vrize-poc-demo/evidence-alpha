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
}

FINANCIAL_STYLE_EXAMPLES = [
    {
        "question_pattern": "capital expenditure amount",
        "method": "Find the cash flow statement line for purchases of property, plant and equipment, capital expenditures, or PP&E purchases. Use the requested year column and keep the filing unit.",
        "answer_shape": "The requested capital expenditure amount is $X million, based on the PP&E purchases line.",
    },
    {
        "question_pattern": "net PP&E",
        "method": "Use the balance sheet line for property, plant and equipment, net. If asked in billions and the filing is in millions, divide by 1,000.",
        "answer_shape": "Year-end net PP&E is $X billion.",
    },
    {
        "question_pattern": "capital intensive",
        "method": "Do not answer from PP&E existence alone. Compute or compare capex/revenue, fixed assets/total assets, and ROA when those values are available.",
        "answer_shape": "Yes/No, because capex/revenue is X%, fixed assets/total assets is Y%, and ROA is Z%.",
    },
    {
        "question_pattern": "operating margin",
        "method": "Operating margin is operating income divided by revenue/net sales. For change questions, compare current year margin against prior year margin and explain drivers from MD&A if available.",
        "answer_shape": "Operating margin increased/decreased by X percentage points, mainly due to the cited drivers.",
    },
    {
        "question_pattern": "quick ratio",
        "method": "Quick ratio is usually (cash and equivalents + marketable securities + receivables) divided by current liabilities. Use balance sheet values for the requested period.",
        "answer_shape": "The quick ratio is about X.x, so liquidity appears healthy/weak based on the cited balance sheet values.",
    },
    {
        "question_pattern": "fixed asset turnover",
        "method": "Fixed asset turnover is revenue divided by average net PP&E across the requested year and prior year.",
        "answer_shape": "Fixed asset turnover is X.x times, calculated as revenue divided by average net PP&E.",
    },
    {
        "question_pattern": "capex as a percent of revenue",
        "method": "For each year, divide capex by revenue, then average the percentages when a multi-year average is requested.",
        "answer_shape": "The average capex as a percent of revenue is X.x%.",
    },
    {
        "question_pattern": "cash flow activity",
        "method": "Compare cash provided by or used in operating, investing, and financing activities. The activity with the highest value, or least negative value, brought in the most or lost the least cash.",
        "answer_shape": "Operating/investing/financing activities brought in the most cash at $X million.",
    },
    {
        "question_pattern": "inventory turnover",
        "method": "Inventory turnover is cost of goods sold divided by average inventory across current and prior year.",
        "answer_shape": "Inventory turnover is about X.x times.",
    },
    {
        "question_pattern": "return on assets",
        "method": "ROA is net income divided by average total assets across current and prior year.",
        "answer_shape": "ROA is about X.x%.",
    },
]


def matching_style_examples(question: str, limit: int = 4) -> list[dict[str, str]]:
    normalized = question.lower()
    matches = [example for example in FINANCIAL_STYLE_EXAMPLES if example["question_pattern"] in normalized]
    if "capex" in normalized and not any(example["question_pattern"] == "capital expenditure amount" for example in matches):
        matches.append(FINANCIAL_STYLE_EXAMPLES[0])
    if not matches:
        matches = FINANCIAL_STYLE_EXAMPLES[:2]
    return matches[:limit]


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


def build_evidence(results: list[tuple[Chunk, float]], max_chars: int = 1800) -> list[dict]:
    evidence = []
    for index, (chunk, score) in enumerate(results, start=1):
        evidence.append(
            {
                "id": index,
                "doc_name": chunk.doc_name,
                "page_num": chunk.page_num,
                "score": score,
                "text": concise_evidence(chunk.text, max_chars=max_chars),
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

    evidence = build_evidence(results, max_chars=1000 if provider == "ollama" else 1800)
    prompt = {
        "question": question,
        "chat_context": chat_context or [],
        "style_examples": matching_style_examples(question),
        "evidence": evidence,
        "instructions": [
            "Use chat_context only to understand follow-up references such as 'it', 'that company', or 'same year'.",
            "Use style_examples as reusable financial-analysis patterns only; they are not source evidence.",
            "Answer only from the supplied evidence.",
            "If the evidence does not directly support the answer, return status not_found.",
            "Do not use outside knowledge.",
            "Do not answer from chat_context alone; cited evidence must prove the answer.",
            "For numbers, preserve units and explain any calculation briefly.",
            "When a filing table is in millions and the user asks for billions, divide the cited value by 1,000.",
            (
                "For capital-intensive questions, calculate and reason from ratios such as capex/revenue, "
                "fixed assets/total assets, and return on assets when the evidence provides them. "
                "Do not conclude that a company is capital intensive merely because it has PP&E or capital spending."
            ),
            "Return valid JSON only.",
            "Keep the answer under 120 words unless the question requires a calculation list.",
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
        request_options = {
            "model": selected_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Evidence Alpha, a careful financial analyst assistant. "
                        "You answer SEC filing questions only when cited evidence proves the answer. "
                        "When evidence is weak or absent, say not_found. "
                        "For local Qwen, answer directly without extended thinking."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
        }
        if provider == "ollama":
            request_options["max_tokens"] = 450
            request_options["extra_body"] = {"options": {"num_predict": 450, "temperature": 0}}
        response = client.chat.completions.create(
            **request_options,
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
