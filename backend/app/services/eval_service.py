"""Evaluation Service layer handling database persistence, experiment comparison, and human reviews."""

import uuid
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.evaluation import EvalRun, EvalCaseResult, EvalHumanReview
from app.eval.runner import EvaluationRunner
from app.eval.cli import generate_markdown_report

logger = logging.getLogger(__name__)


class EvalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_evaluation(
        self,
        user: Optional[User],
        dataset_version: str = "retrieval-v1",
        run_name: Optional[str] = None,
        llm_provider: str = "ollama",
        llm_model: str = "qwen3:4b-instruct",
        embedding_provider: str = "ollama",
        embedding_model: str = "embeddinggemma",
        embedding_dimension: int = 768,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Triggers an async evaluation run and persists the results."""
        runner = EvaluationRunner(db_session=self.db)
        run_result = await runner.run_evaluation(
            dataset_version=dataset_version,
            run_name=run_name,
            llm_provider=llm_provider,
            llm_model=llm_model,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            limit=limit,
            user_id=user.id if user else None
        )
        return run_result

    async def list_runs(
        self,
        user: Optional[User] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Lists evaluation runs accessible to current user or system public benchmarks."""
        stmt = select(EvalRun).order_by(EvalRun.created_at.desc()).limit(limit).offset(offset)
        if user:
            # Allow user to see their own runs or public system runs (user_id is None)
            stmt = stmt.where((EvalRun.user_id == user.id) | (EvalRun.user_id.is_(None)))

        res = await self.db.execute(stmt)
        runs = res.scalars().all()

        return [
            {
                "id": str(r.id),
                "run_name": r.run_name,
                "dataset_name": r.dataset_name,
                "dataset_version": r.dataset_version,
                "pipeline_version": r.pipeline_version,
                "llm_provider": r.llm_provider,
                "llm_model": r.llm_model,
                "embedding_model": r.embedding_model,
                "status": r.status,
                "recall_score": r.recall_score,
                "precision_score": r.precision_score,
                "faithfulness_score": r.faithfulness_score,
                "avg_latency_ms": r.avg_latency_ms,
                "quality_gates_passed": r.quality_gates_result.get("passed", True) if r.quality_gates_result else True,
                "metrics_summary": r.metrics_summary,
                "quality_gates_result": r.quality_gates_result,
                "latency_summary": r.latency_summary,
                "reliability_summary": r.reliability_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in runs
        ]

    async def get_run_details(self, run_id: uuid.UUID, user: Optional[User] = None) -> Optional[Dict[str, Any]]:
        """Retrieves details of a specific evaluation run."""
        stmt = select(EvalRun).where(EvalRun.id == run_id)
        if user:
            stmt = stmt.where((EvalRun.user_id == user.id) | (EvalRun.user_id.is_(None)))

        res = await self.db.execute(stmt)
        r = res.scalars().first()
        if not r:
            return None

        return {
            "id": str(r.id),
            "run_name": r.run_name,
            "dataset_name": r.dataset_name,
            "dataset_version": r.dataset_version,
            "pipeline_version": r.pipeline_version,
            "prompt_version": r.prompt_version,
            "llm_provider": r.llm_provider,
            "llm_model": r.llm_model,
            "embedding_provider": r.embedding_provider,
            "embedding_model": r.embedding_model,
            "embedding_dimension": r.embedding_dimension,
            "status": r.status,
            "metrics_summary": r.metrics_summary or {},
            "quality_gates_result": r.quality_gates_result or {},
            "latency_summary": r.latency_summary or {},
            "reliability_summary": r.reliability_summary or {},
            "created_at": r.created_at.isoformat() if r.created_at else None
        }

    async def get_run_cases(
        self,
        run_id: uuid.UUID,
        category: Optional[str] = None,
        passed_filter: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves sample-level evaluation cases for debugging."""
        stmt = select(EvalCaseResult).where(EvalCaseResult.run_id == run_id)
        if category:
            stmt = stmt.where(EvalCaseResult.category == category)
        if passed_filter is not None:
            stmt = stmt.where(EvalCaseResult.passed == passed_filter)

        stmt = stmt.order_by(EvalCaseResult.created_at.asc()).limit(limit).offset(offset)
        res = await self.db.execute(stmt)
        cases = res.scalars().all()

        return [
            {
                "id": str(c.id),
                "run_id": str(c.run_id),
                "case_id": c.case_id,
                "category": c.category,
                "difficulty": c.difficulty,
                "question": c.question,
                "expected_evidence": c.expected_evidence,
                "retrieved_evidence": c.retrieved_evidence,
                "generated_answer": c.generated_answer,
                "citations": c.citations,
                "metrics": c.metrics,
                "passed": c.passed,
                "failure_reason": c.failure_reason,
                "human_review_status": c.human_review_status,
                "human_review_notes": c.human_review_notes
            }
            for c in cases
        ]

    async def compare_runs(
        self,
        run_id_a: uuid.UUID,
        run_id_b: uuid.UUID,
        user: Optional[User] = None
    ) -> Optional[Dict[str, Any]]:
        """Generates side-by-side comparison matrix and metric diffs between Model A and Model B runs."""
        run_a = await self.get_run_details(run_id_a, user)
        run_b = await self.get_run_details(run_id_b, user)

        if not run_a or not run_b:
            return None

        metrics_a = run_a.get("metrics_summary", {})
        metrics_b = run_b.get("metrics_summary", {})
        lat_a = run_a.get("latency_summary", {})
        lat_b = run_b.get("latency_summary", {})

        diff_metrics = {}
        all_metric_keys = set(metrics_a.keys()).union(set(metrics_b.keys()))
        for k in all_metric_keys:
            val_a = metrics_a.get(k, 0.0)
            val_b = metrics_b.get(k, 0.0)
            diff_metrics[k] = {
                "model_a": val_a,
                "model_b": val_b,
                "diff": round(val_b - val_a, 4)
            }

        diff_latency = {
            "p50": {"model_a": lat_a.get("p50", 0.0), "model_b": lat_b.get("p50", 0.0), "diff": round(lat_b.get("p50", 0.0) - lat_a.get("p50", 0.0), 2)},
            "p95": {"model_a": lat_a.get("p95", 0.0), "model_b": lat_b.get("p95", 0.0), "diff": round(lat_b.get("p95", 0.0) - lat_a.get("p95", 0.0), 2)},
            "p99": {"model_a": lat_a.get("p99", 0.0), "model_b": lat_b.get("p99", 0.0), "diff": round(lat_b.get("p99", 0.0) - lat_a.get("p99", 0.0), 2)},
        }

        return {
            "run_a": run_a,
            "run_b": run_b,
            "metric_comparison": diff_metrics,
            "latency_comparison": diff_latency
        }

    async def record_human_review(
        self,
        case_result_id: uuid.UUID,
        user: User,
        label: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Records human review classification label for a sample case result."""
        stmt = select(EvalCaseResult).where(EvalCaseResult.id == case_result_id)
        res = await self.db.execute(stmt)
        case_res = res.scalars().first()
        if not case_res:
            return None

        # Update case result status
        case_res.human_review_status = label
        case_res.human_review_notes = notes

        # Add human review entry
        review = EvalHumanReview(
            id=uuid.uuid4(),
            case_result_id=case_res.id,
            user_id=user.id,
            label=label,
            notes=notes
        )
        self.db.add(review)
        await self.db.commit()

        return {
            "case_result_id": str(case_res.id),
            "human_review_status": case_res.human_review_status,
            "human_review_notes": case_res.human_review_notes
        }

    async def export_report(self, run_id: uuid.UUID, user: Optional[User] = None, format_type: str = "markdown") -> str:
        """Exports evaluation run as Markdown or JSON string."""
        run_details = await self.get_run_details(run_id, user)
        if not run_details:
            raise ValueError(f"Evaluation run {run_id} not found.")

        if format_type == "json":
            return json.dumps(run_details, indent=2)

        return generate_markdown_report(run_details)
