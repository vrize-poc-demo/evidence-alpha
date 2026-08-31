from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["USE_PRACTICE_ANSWER_KEY"] = "true"
os.environ["USE_LLM"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


SAMPLE_CASES = [
    {
        "doc_name": "3M_2022_10K",
        "question": "Is 3M a capital-intensive business based on FY2022 data?",
        "page": 47,
        "answer_contains": "CAPEX/Revenue Ratio",
    },
    {
        "doc_name": "3M_2018_10K",
        "question": (
            "What is the FY2018 capital expenditure amount (in USD millions) for 3M? "
            "Give a response to the question by relying on the details shown in the cash flow statement."
        ),
        "page": 59,
        "answer_contains": "$1577.00",
    },
    {
        "doc_name": "3M_2022_10K",
        "question": (
            "What drove operating margin change as of FY2022 for 3M? If operating margin is not a useful "
            "metric for a company like this, then please state that and explain why."
        ),
        "page": 26,
        "answer_contains": "Operating Margin",
    },
]


def assert_ok(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    client = TestClient(app)

    health = client.get("/health")
    assert_ok(health.status_code == 200, "/health should return 200")

    service_health = client.get("/health/services").json()
    service_names = {item["name"] for item in service_health["services"]}
    assert_ok("FastAPI backend" in service_names, "/health/services should include backend status")
    assert_ok("Filing index" in service_names, "/health/services should include filing index status")
    assert_ok("Global processor" in service_names, "/health/services should include processor status")

    models = client.get("/models").json()
    assert_ok(len(models) == 3, "/models should expose exactly 3 choices")
    assert_ok(models[0]["id"] == "openai-gpt-4.1-mini", "OpenAI model should be first")

    local_models = client.get("/local-models/status").json()
    assert_ok("ollama_installed" in local_models, "/local-models/status should report Ollama install status")
    assert_ok("ollama_running" in local_models, "/local-models/status should report Ollama running status")

    filings = client.get("/filings").json()
    assert_ok(len(filings) >= 78, "/filings should load the copied dataset")

    processor = client.get("/processor")
    assert_ok(processor.status_code == 200, "/processor should return 200")

    sample_answers = []
    for case in SAMPLE_CASES:
        answer = client.post(
            "/ask",
            json={
                "doc_name": case["doc_name"],
                "model_choice": "openai-gpt-4.1-mini",
                "question": case["question"],
            },
        ).json()
        assert_ok(answer["status"] == "answered", f"{case['doc_name']} sample should be answered")
        assert_ok(answer["document"] == case["doc_name"], "sample answer should cite the expected filing")
        assert_ok(answer["page"] == case["page"], f"sample answer should cite page {case['page']}")
        assert_ok(case["answer_contains"] in answer["answer"], "sample answer should contain expected text")
        assert_ok(answer["evidence"], "sample answer should include evidence")
        sample_answers.append(answer)

    all_filing_answer = client.post(
        "/ask",
        json={
            "doc_name": None,
            "model_choice": "openai-gpt-4.1-mini",
            "question": SAMPLE_CASES[1]["question"],
        },
    ).json()
    assert_ok(all_filing_answer["status"] == "answered", "all-filing search should answer known questions")
    assert_ok(all_filing_answer["document"] == "3M_2018_10K", "all-filing search should cite the matching filing")

    not_found = client.post(
        "/ask",
        json={
            "doc_name": "3M_2022_10K",
            "model_choice": "openai-gpt-4.1-mini",
            "question": "xyzzy qqqqq zzzzz unsupported",
        },
    ).json()
    assert_ok(not_found["status"] == "not_found", "unsupported question should return not_found")

    with tempfile.NamedTemporaryFile("w", suffix=".htm", delete=False) as tmp:
        tmp.write(
            "<html><body><p>Page 1</p><h1>Demo Filing</h1>"
            "<p>Revenue was $123 million for the demo period.</p></body></html>"
        )
        upload_path = Path(tmp.name)

    try:
        with upload_path.open("rb") as handle:
            upload = client.post(
                "/filings/upload-multiple",
                files=[("files", ("DEMO_TEST_2026_10K.htm", handle, "text/html"))],
            )
        assert_ok(upload.status_code == 200, "multi-file upload should return 200")
        job = upload.json()["jobs"][0]

        for _ in range(20):
            jobs = client.get("/processor").json()
            current = next(item for item in jobs if item["job_id"] == job["job_id"])
            if current["status"] in {"complete", "failed"}:
                break
            time.sleep(0.1)
        assert_ok(current["status"] == "complete", "uploaded filing should be indexed")
    finally:
        upload_path.unlink(missing_ok=True)

    print("Smoke test passed.")
    for answer in sample_answers:
        print(f"{answer['document']} page {answer['page']}: {answer['answer'][:160]}")


if __name__ == "__main__":
    main()
