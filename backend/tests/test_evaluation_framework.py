import pytest
import uuid
from sqlalchemy import select

from app.models.user import User
from app.models.evaluation import EvalRun, EvalCaseResult, EvalHumanReview
from app.core.security import get_password_hash
from app.eval.datasets import get_dataset, list_datasets
from app.eval.metrics import (
    calculate_retrieval_metrics,
    calculate_generation_metrics,
    calculate_citation_metrics,
    calculate_context_spoiler_metrics,
    calculate_agent_metrics,
    calculate_percentile_latencies,
    check_quality_gates,
    calculate_run_metrics
)
from app.eval.runner import EvaluationRunner
from app.services.eval_service import EvalService


# ---------------------------------------------------------------------------
# 1. Dataset Registry & Versioning Tests
# ---------------------------------------------------------------------------
def test_dataset_registry_and_versioning():
    datasets = list_datasets()
    assert len(datasets) >= 7
    versions = {d["dataset_version"] for d in datasets}
    assert "retrieval-v1" in versions
    assert "agent-v1" in versions
    assert "narrative-v1" in versions
    assert "multidoc-v1" in versions
    assert "multimodal-v1" in versions
    assert "tutor-v1" in versions
    assert "hallucination-v1" in versions

    ret_dataset = get_dataset("retrieval-v1")
    assert ret_dataset is not None
    assert len(ret_dataset["cases"]) >= 4


# ---------------------------------------------------------------------------
# 2. Metric Calculations & Percentiles Tests
# ---------------------------------------------------------------------------
def test_metric_calculations():
    # Retrieval
    retrieved = [{"content": "AES-256 key length details."}]
    expected = [{"keywords": ["AES-256", "key length"]}]
    ret_m = calculate_retrieval_metrics(retrieved, expected, top_k=5)
    assert ret_m["recall_at_k"] == 1.0
    assert ret_m["precision_at_k"] == 1.0
    assert ret_m["mrr"] == 1.0

    # Generation
    gen_m = calculate_generation_metrics("AES-256 specifies a 256-bit key length.", retrieved, {"required_terms": ["AES-256"]})
    assert gen_m["answer_relevance"] == 1.0
    assert gen_m["groundedness"] > 0.5

    # Citations
    cits = [{"document_title": "Paper_A.pdf", "page_number": 1}]
    cit_m = calculate_citation_metrics(cits, [{"page_start": 1}])
    assert cit_m["citation_present"] == 1.0
    assert cit_m["citation_precision"] == 1.0

    # Spoiler Leakage
    spoiler_chunks = [{"page_start": 10}]
    sp_m = calculate_context_spoiler_metrics(spoiler_chunks, current_page=5, spoiler_free=True)
    assert sp_m["spoiler_leakage_rate"] == 1.0

    # Percentiles
    lats = [10.0, 20.0, 30.0, 40.0, 50.0, 100.0, 200.0]
    p_stats = calculate_percentile_latencies(lats)
    assert p_stats["sample_size"] == 7
    assert p_stats["p50"] > 0.0
    assert p_stats["p95"] > 0.0


# ---------------------------------------------------------------------------
# 3. Quality Gates Check Tests
# ---------------------------------------------------------------------------
def test_quality_gates_checker():
    metrics = {"recall_at_k": 0.95, "citation_correctness": 0.92, "spoiler_leakage_rate": 0.0}
    latency = {"p95": 1200.0}
    reliability = {"failure_rate": 0.01}

    gate_res = check_quality_gates(metrics, latency, reliability)
    assert gate_res["passed"] is True
    assert gate_res["gates"]["MIN_RECALL_AT_5"]["passed"] is True


# ---------------------------------------------------------------------------
# 4. Evaluation Runner & DB Persistence Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_runner_and_persistence(db_session):
    user = User(
        id=uuid.uuid4(),
        email="eval_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Eval User"
    )
    db_session.add(user)
    await db_session.commit()

    runner = EvaluationRunner(db_session=db_session)
    run_res = await runner.run_evaluation(
        dataset_version="retrieval-v1",
        run_name="Test Retrieval Run",
        limit=2,
        user_id=user.id
    )

    assert run_res["id"] is not None
    assert run_res["dataset_version"] == "retrieval-v1"
    assert len(run_res["case_results"]) == 2

    # Verify DB persistence
    res = await db_session.execute(select(EvalRun).where(EvalRun.id == uuid.UUID(run_res["id"])))
    fetched_run = res.scalars().first()
    assert fetched_run is not None
    assert fetched_run.run_name == "Test Retrieval Run"


# ---------------------------------------------------------------------------
# 5. API Endpoints & Human Review Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_api_and_human_review(client, user_a_headers):
    # 1. Trigger evaluation run via API
    res_run = await client.post(
        "/api/v1/evaluations/run",
        json={"dataset_version": "retrieval-v1", "run_name": "API Eval Run", "limit": 2},
        headers=user_a_headers
    )
    assert res_run.status_code == 201
    run_id = res_run.json()["id"]

    # 2. List evaluation runs
    res_list = await client.get("/api/v1/evaluations", headers=user_a_headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Get run details
    res_details = await client.get(f"/api/v1/evaluations/{run_id}", headers=user_a_headers)
    assert res_details.status_code == 200
    assert res_details.json()["id"] == run_id

    # 4. Get run cases
    res_cases = await client.get(f"/api/v1/evaluations/{run_id}/cases", headers=user_a_headers)
    assert res_cases.status_code == 200
    cases = res_cases.json()
    assert len(cases) >= 1
    case_id = cases[0]["id"]

    # 5. Submit Human Review
    res_review = await client.post(
        f"/api/v1/evaluations/cases/{case_id}/review",
        json={"label": "CORRECT", "notes": "Verified accurate citation and evidence."},
        headers=user_a_headers
    )
    assert res_review.status_code == 200
    assert res_review.json()["human_review_status"] == "CORRECT"
