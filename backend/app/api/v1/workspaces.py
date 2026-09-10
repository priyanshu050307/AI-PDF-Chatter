import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_async_db
from app.models.user import User
from app.models.document import Document
from app.models.workspace import Workspace, WorkspaceDocument
from app.api.deps import get_current_user
from app.services.multi_doc_service import MultiDocService
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.services.context_builder import ContextBuilder, StructuredContext
from app.services.ai_service import get_ai_service
from app.services.agent.agent_router import AgentRouter
from app.core.logging import logger


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class WorkspaceCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class AddDocumentSchema(BaseModel):
    document_id: uuid.UUID


class WorkspaceDocumentSchema(BaseModel):
    document_id: uuid.UUID
    title: str
    original_filename: str
    page_count: int
    added_at: str


class WorkspaceResponseSchema(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    created_at: str
    updated_at: str
    documents_count: int
    documents: Optional[List[WorkspaceDocumentSchema]] = None


class MultiDocQuerySchema(BaseModel):
    query: str = Field(..., min_length=1)
    selected_document_ids: Optional[List[uuid.UUID]] = None
    mode: str = Field("auto", description="Query mode: 'auto', 'normal', 'agentic'")


class CompareRequestSchema(BaseModel):
    selected_document_ids: List[uuid.UUID]
    topic: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper: Verify Workspace Ownership
# ---------------------------------------------------------------------------
async def get_user_workspace(workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Workspace:
    stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == user_id)
    res = await db.execute(stmt)
    ws = res.scalars().first()
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found or access denied.")
    return ws


# ---------------------------------------------------------------------------
# Workspace CRUD Endpoints
# ---------------------------------------------------------------------------
@router.post("", response_model=WorkspaceResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = Workspace(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=payload.title,
        description=payload.description
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)

    return WorkspaceResponseSchema(
        id=ws.id,
        title=ws.title,
        description=ws.description,
        created_at=ws.created_at.isoformat(),
        updated_at=ws.updated_at.isoformat(),
        documents_count=0,
        documents=[]
    )


@router.get("", response_model=List[WorkspaceResponseSchema])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    stmt = select(Workspace).where(Workspace.user_id == current_user.id).order_by(Workspace.updated_at.desc())
    res = await db.execute(stmt)
    workspaces = res.scalars().all()

    result = []
    for ws in workspaces:
        # count documents
        doc_count_res = await db.execute(
            select(WorkspaceDocument).where(WorkspaceDocument.workspace_id == ws.id)
        )
        count = len(doc_count_res.scalars().all())
        result.append(
            WorkspaceResponseSchema(
                id=ws.id,
                title=ws.title,
                description=ws.description,
                created_at=ws.created_at.isoformat(),
                updated_at=ws.updated_at.isoformat(),
                documents_count=count
            )
        )
    return result


@router.get("/{workspace_id}", response_model=WorkspaceResponseSchema)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)

    # Fetch attached documents with document details
    stmt = (
        select(WorkspaceDocument, Document)
        .join(Document, WorkspaceDocument.document_id == Document.id)
        .where(WorkspaceDocument.workspace_id == ws.id)
    )
    res = await db.execute(stmt)
    rows = res.all()

    doc_schemas = []
    for ws_doc, doc in rows:
        doc_schemas.append(
            WorkspaceDocumentSchema(
                document_id=doc.id,
                title=doc.title,
                original_filename=doc.original_filename,
                page_count=doc.page_count or 0,
                added_at=ws_doc.added_at.isoformat()
            )
        )

    return WorkspaceResponseSchema(
        id=ws.id,
        title=ws.title,
        description=ws.description,
        created_at=ws.created_at.isoformat(),
        updated_at=ws.updated_at.isoformat(),
        documents_count=len(doc_schemas),
        documents=doc_schemas
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponseSchema)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)

    if payload.title is not None:
        ws.title = payload.title
    if payload.description is not None:
        ws.description = payload.description

    await db.commit()
    await db.refresh(ws)

    return WorkspaceResponseSchema(
        id=ws.id,
        title=ws.title,
        description=ws.description,
        created_at=ws.created_at.isoformat(),
        updated_at=ws.updated_at.isoformat(),
        documents_count=0
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)
    await db.delete(ws)
    await db.commit()


# ---------------------------------------------------------------------------
# Workspace Document Management (Attachment / Detachment)
# ---------------------------------------------------------------------------
@router.post("/{workspace_id}/documents", status_code=status.HTTP_201_CREATED)
async def add_document_to_workspace(
    workspace_id: uuid.UUID,
    payload: AddDocumentSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)

    # Ownership check on Document: MUST belong to current_user
    stmt = select(Document).where(Document.id == payload.document_id, Document.user_id == current_user.id)
    doc_res = await db.execute(stmt)
    doc = doc_res.scalars().first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document not found or unauthorized to attach this document."
        )

    # Check if already added
    existing_stmt = select(WorkspaceDocument).where(
        WorkspaceDocument.workspace_id == ws.id,
        WorkspaceDocument.document_id == doc.id
    )
    ex_res = await db.execute(existing_stmt)
    if ex_res.scalars().first():
        return {"message": "Document is already attached to workspace."}

    ws_doc = WorkspaceDocument(workspace_id=ws.id, document_id=doc.id)
    db.add(ws_doc)
    await db.commit()
    return {"message": f"Document '{doc.title}' successfully added to workspace."}


@router.delete("/{workspace_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document_from_workspace(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)
    await db.execute(
        delete(WorkspaceDocument).where(
            WorkspaceDocument.workspace_id == ws.id,
            WorkspaceDocument.document_id == document_id
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Multi-Document RAG & Cross-Document Querying
# ---------------------------------------------------------------------------
@router.post("/{workspace_id}/query")
async def query_workspace(
    workspace_id: uuid.UUID,
    payload: MultiDocQuerySchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)

    # Fetch attached workspace documents
    stmt = (
        select(WorkspaceDocument, Document)
        .join(Document, WorkspaceDocument.document_id == Document.id)
        .where(WorkspaceDocument.workspace_id == ws.id)
    )
    res = await db.execute(stmt)
    ws_docs = [doc for _, doc in res.all()]
    all_ws_doc_ids = {doc.id for doc in ws_docs}
    doc_title_map = {doc.id: doc.title for doc in ws_docs}

    # Resolve target document scope
    if payload.selected_document_ids:
        target_ids = [d for d in payload.selected_document_ids if d in all_ws_doc_ids]
        if not target_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected document IDs do not belong to this workspace.")
    else:
        target_ids = list(all_ws_doc_ids)

    if not target_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents available in workspace to query.")

    # Classify route
    router_service = AgentRouter()
    route, is_agentic = router_service.route_query(payload.query, mode_override=payload.mode, is_multi_doc=True)

    # Multi-Document Retrieval
    pipeline = HybridRetrievalPipeline(db)
    evidence_results, telemetry = await pipeline.execute_pipeline(
        document_ids=target_ids,
        query=payload.query,
        top_k=8
    )

    # Format chunks with document title for ContextBuilder
    chunks_for_context = []
    for item in evidence_results:
        d_uuid = uuid.UUID(item.document_id)
        d_title = doc_title_map.get(d_uuid, "Unknown PDF")
        chunks_for_context.append({
            "chunk_id": item.chunk_id,
            "document_id": item.document_id,
            "document_title": d_title,
            "page_start": item.page_start,
            "page_end": item.page_end,
            "chapter_title": item.chapter_title,
            "section_title": item.section_title,
            "content": item.content,
            "score": item.rerank_score or item.fused_score or item.dense_score,
        })

    context_builder = ContextBuilder()
    struct_ctx = StructuredContext(retrieved_chunks=chunks_for_context)
    sys_prompt, snapshot, citations = context_builder.build_system_prompt_and_snapshot(payload.query, struct_ctx)

    ai_service = get_ai_service()
    llm_res = await ai_service.generate_answer(
        system_prompt=sys_prompt,
        messages=[{"role": "user", "content": payload.query}]
    )
    answer = llm_res.get("content", "")

    return {

        "workspace_id": str(ws.id),
        "route": route.value if hasattr(route, "value") else str(route),
        "is_agentic": is_agentic,
        "query": payload.query,
        "answer": answer,
        "citations": citations,
        "telemetry": telemetry.model_dump()
    }


# ---------------------------------------------------------------------------
# Structured Multi-Doc Intelligence Endpoints
# ---------------------------------------------------------------------------
@router.post("/{workspace_id}/compare")
async def compare_workspace_documents(
    workspace_id: uuid.UUID,
    payload: CompareRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)
    service = MultiDocService(db)
    res = await service.compare_documents(user=current_user, selected_document_ids=payload.selected_document_ids, topic=payload.topic)
    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 400), detail=res["error"])
    return res


@router.post("/{workspace_id}/agreements")
async def find_workspace_agreements(
    workspace_id: uuid.UUID,
    payload: CompareRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)
    service = MultiDocService(db)
    res = await service.find_common_claims(user=current_user, selected_document_ids=payload.selected_document_ids, topic=payload.topic)
    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 400), detail=res["error"])
    return res


@router.post("/{workspace_id}/conflicts")
async def find_workspace_conflicts(
    workspace_id: uuid.UUID,
    payload: CompareRequestSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    ws = await get_user_workspace(workspace_id, current_user.id, db)
    service = MultiDocService(db)
    res = await service.find_conflicting_claims(user=current_user, selected_document_ids=payload.selected_document_ids, topic=payload.topic)
    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 400), detail=res["error"])
    return res
