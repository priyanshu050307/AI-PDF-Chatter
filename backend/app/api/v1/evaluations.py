"""FastAPI router for Phase 13 Unified Evaluation & Quality Engineering endpoints."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.services.eval_service import EvalService
from app.eval.datasets import list_datasets

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class RunEvaluationRequest(BaseModel):
    dataset_version: str = Field("retrieval-v1", description="Dataset version (e.g. retrieval-v1, agent-v1, multidoc-v1)")
    run_name: Optional[str] = Field(None, description="Optional custom name for run")
    llm_provider: str = Field("ollama", description="LLM provider name")
    llm_model: str = Field("qwen3:4b-instruct", description="LLM model identifier")
    embedding_provider: str = Field("ollama", description="Embedding provider name")
    embedding_model: str = Field("embeddinggemma", description="Embedding model identifier")
    embedding_dimension: int = Field(768, description="Embedding vector dimension")
    limit: Optional[int] = Field(None, description="Optional limit on cases to run")


class HumanReviewRequest(BaseModel):
    label: str = Field(..., description="Label choice: CORRECT, PARTIALLY_CORRECT, INCORRECT, CITATION_CORRECT, CITATION_INCORRECT")
    notes: Optional[str] = Field(None, description="Optional review notes")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/datasets", summary="List available benchmark evaluation datasets")
async def get_benchmark_datasets(current_user: User = Depends(get_current_user)):
    return list_datasets()


@router.post("/run", status_code=status.HTTP_201_CREATED, summary="Trigger an async evaluation run")
async def trigger_evaluation_run(
    req: RunEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    try:
        results = await service.run_evaluation(
            user=current_user,
            dataset_version=req.dataset_version,
            run_name=req.run_name,
            llm_provider=req.llm_provider,
            llm_model=req.llm_model,
            embedding_provider=req.embedding_provider,
            embedding_model=req.embedding_model,
            embedding_dimension=req.embedding_dimension,
            limit=req.limit
        )
        return results
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute evaluation run: {str(e)}")


@router.get("", summary="List evaluation runs")
async def list_evaluation_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    return await service.list_runs(user=current_user, limit=limit, offset=offset)


@router.get("/compare", summary="Compare two evaluation runs side-by-side")
async def compare_evaluation_runs(
    run_id_a: uuid.UUID = Query(..., description="First evaluation run ID"),
    run_id_b: uuid.UUID = Query(..., description="Second evaluation run ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    comparison = await service.compare_runs(run_id_a, run_id_b, current_user)
    if not comparison:
        raise HTTPException(status_code=404, detail="One or both evaluation runs not found.")
    return comparison


@router.get("/{id}", summary="Get specific evaluation run details")
async def get_evaluation_run_details(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    run_details = await service.get_run_details(id, current_user)
    if not run_details:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return run_details


@router.get("/{id}/cases", summary="List sample-level debugging cases for an evaluation run")
async def get_evaluation_run_cases(
    id: uuid.UUID,
    category: Optional[str] = Query(None),
    passed: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    run_details = await service.get_run_details(id, current_user)
    if not run_details:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")

    return await service.get_run_cases(
        run_id=id,
        category=category,
        passed_filter=passed,
        limit=limit,
        offset=offset
    )


@router.post("/cases/{case_id}/review", summary="Record human review label for a sample case")
async def submit_human_review(
    case_id: uuid.UUID,
    req: HumanReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    res = await service.record_human_review(
        case_result_id=case_id,
        user=current_user,
        label=req.label,
        notes=req.notes
    )
    if not res:
        raise HTTPException(status_code=404, detail="Evaluation case result not found.")
    return res


@router.get("/{id}/report", summary="Download evaluation run report")
async def download_evaluation_report(
    id: uuid.UUID,
    format: str = Query("markdown", regex="^(markdown|json)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    service = EvalService(db)
    try:
        report_str = await service.export_report(id, current_user, format_type=format)
        if format == "json":
            return JSONResponse(content=json.loads(report_str))
        return PlainTextResponse(content=report_str, media_type="text/markdown")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
