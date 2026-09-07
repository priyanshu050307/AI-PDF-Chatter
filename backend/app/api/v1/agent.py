import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.agent import AgentRun, AgentStep
from app.services.document_service import DocumentService
from app.services.agent.agent_controller import AgentController
from app.core.errors import NotFoundError, ForbiddenError


router = APIRouter()


class AgentAskRequest(BaseModel):
    query: str = Field(..., description="User query or multi-step investigation request")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Optional persistent conversation thread ID")
    mode: str = Field("auto", description="Routing mode: auto, agentic, normal")
    current_page: Optional[int] = Field(None, description="Active user reading page number")
    spoiler_mode: str = Field("spoiler_free", description="Spoiler control: spoiler_free, current_position, full_book")


class AgentStepResponse(BaseModel):
    step: int
    tool: str
    description: str
    status: str
    duration_ms: Optional[float] = None


class AgentAskResponse(BaseModel):
    run_id: str
    query: str
    answer: str
    route: str
    state: str
    steps: List[AgentStepResponse]
    citations: List[Dict[str, Any]]
    latency_ms: Optional[float] = None


@router.post("/documents/{document_id}/agent/ask", response_model=AgentAskResponse)
async def ask_agentic_question(
    document_id: uuid.UUID,
    req: AgentAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Execute Bounded Agentic AI Multi-Step Document Reasoning."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    controller = AgentController(db)
    res = await controller.run_investigation(
        user=current_user,
        document_id=document_id,
        query=req.query,
        conversation_id=req.conversation_id,
        mode=req.mode,
        current_page=req.current_page,
        spoiler_mode=req.spoiler_mode
    )

    return AgentAskResponse(
        run_id=res["run_id"],
        query=res["query"],
        answer=res["answer"],
        route=res["route"],
        state=res["state"],
        steps=[
            AgentStepResponse(
                step=s["step"],
                tool=s["tool"],
                description=s["description"],
                status=s["status"],
                duration_ms=s.get("duration_ms")
            )
            for s in res["steps"]
        ],
        citations=res["citations"],
        latency_ms=res.get("latency_ms")
    )


@router.get("/documents/{document_id}/agent/runs/{run_id}")
async def get_agent_run_telemetry(
    document_id: uuid.UUID,
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get high-level agent run status, telemetry, and step history."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    q = select(AgentRun).where(
        AgentRun.id == run_id,
        AgentRun.document_id == document_id,
        AgentRun.user_id == current_user.id
    )
    res = await db.execute(q)
    run = res.scalars().first()
    if not run:
        raise NotFoundError(message=f"AgentRun '{run_id}' not found.")

    return {
        "run_id": str(run.id),
        "document_id": str(run.document_id),
        "query": run.query,
        "state": run.state,
        "route": run.route,
        "step_count": run.step_count,
        "latency_ms": run.latency_ms,
        "steps": [
            {
                "step_index": s.step_index,
                "action_type": s.action_type,
                "tool_name": s.tool_name,
                "status": s.status,
                "duration_ms": s.duration_ms
            }
            for s in run.steps
        ],
        "telemetry": run.telemetry_json
    }
