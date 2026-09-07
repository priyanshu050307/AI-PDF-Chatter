import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.document_service import DocumentService
from app.services.retrieval.graph_retriever import EntityRetriever
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.services.context_builder import ContextBuilder, StructuredContext
from app.services.ai_service import get_ai_service
from app.core.errors import NotFoundError, ValidationError


router = APIRouter()


class NarrativeAskRequest(BaseModel):
    query: str = Field(..., description="Question about character, relationship, or narrative event")
    spoiler_mode: str = Field("spoiler_free", description="Spoiler control: spoiler_free, current_position, full_book")
    current_page: Optional[int] = Field(None, description="Active user reading page for spoiler capping")


class NarrativeAskResponse(BaseModel):
    query: str
    answer: str
    spoiler_mode: str
    capped_at_page: Optional[int]
    graph_context: Dict[str, Any]
    citations: List[Dict[str, Any]]


@router.get("/documents/{document_id}/narrative/entities")
async def list_narrative_entities(
    document_id: uuid.UUID,
    importance: Optional[str] = Query(None, description="Filter by importance: major, minor, background"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List characters and entities for a document with optional importance filtering."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    entities = await doc_service.repo.get_entities_for_document(document_id)
    
    result = []
    for e in entities:
        imp = e.attributes.get("importance", "minor") if e.attributes else "minor"
        if importance and imp.lower() != importance.lower():
            continue
        result.append({
            "id": str(e.id),
            "document_id": str(e.document_id),
            "name": e.name,
            "entity_type": e.entity_type,
            "description": e.description,
            "first_appeared_page": e.first_appeared_page,
            "aliases": e.attributes.get("aliases", []) if e.attributes else [],
            "importance": imp,
            "mention_count": e.attributes.get("mention_count", 1) if e.attributes else 1
        })
    return result


@router.get("/documents/{document_id}/narrative/entities/{entity_id}")
async def get_entity_profile(
    document_id: uuid.UUID,
    entity_id: str,
    max_page: Optional[int] = Query(None, description="Optional page limit for spoiler filtering"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get detailed character profile, relationship graph, and event timeline."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    retriever = EntityRetriever(db)
    profile = await retriever.get_character_profile(document_id, entity_id, max_page=max_page)
    if not profile:
        raise NotFoundError(message=f"Entity '{entity_id}' not found.")

    return profile


@router.get("/documents/{document_id}/narrative/timeline")
async def get_narrative_timeline(
    document_id: uuid.UUID,
    max_page: Optional[int] = Query(None, description="Optional max page for spoiler filtering"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get ordered narrative event timeline for document."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    events = await doc_service.repo.get_events_for_document(document_id)
    if max_page is not None:
        events = [ev for ev in events if ev.page_number <= max_page]

    return [
        {
            "id": str(ev.id),
            "document_id": str(ev.document_id),
            "title": ev.title,
            "event_type": ev.event_type,
            "description": ev.description,
            "page_number": ev.page_number,
            "participants": ev.participants_json.get("participants", []) if ev.participants_json else [],
            "location_name": ev.location_name
        }
        for ev in events
    ]


@router.post("/documents/{document_id}/narrative/ask", response_model=NarrativeAskResponse)
async def ask_narrative_question(
    document_id: uuid.UUID,
    req: NarrativeAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Execute Character/Narrative-Aware Graph RAG with Spoiler Control."""
    doc_service = DocumentService(db)
    doc = await doc_service.get_user_document(current_user, document_id)

    # Calculate max page limit based on spoiler_mode
    max_page: Optional[int] = None
    if req.spoiler_mode == "spoiler_free" and req.current_page:
        max_page = req.current_page
    elif req.spoiler_mode == "current_position":
        if doc.reading_progresses:
            max_page = max((p.current_page for p in doc.reading_progresses), default=req.current_page)
        else:
            max_page = req.current_page

    # 1. Graph Retrieval (Bounded Subgraph & Entities)
    graph_retriever = EntityRetriever(db)
    graph_context = await graph_retriever.get_bounded_subgraph(
        document_id=document_id,
        query=req.query,
        max_hops=2,
        max_page=max_page
    )

    # 2. Hybrid Text Chunk Retrieval
    pipeline = HybridRetrievalPipeline(db)
    retrieved_chunks, telemetry = await pipeline.execute_pipeline(
        document_id=document_id,
        query=req.query,
        top_k=5
    )

    # Filter text chunks by max_page if spoiler protection is active
    if max_page is not None:
        retrieved_chunks = [c for c in retrieved_chunks if c.page_start <= max_page]

    # Convert RetrievalResult to dict format for ContextBuilder
    chunk_dicts = [
        {
            "chunk_id": c.chunk_id,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "content": c.content,
            "chapter_title": c.chapter,
            "section_title": c.section,
            "score": c.rerank_score or c.fused_score or c.dense_score
        }
        for c in retrieved_chunks
    ]

    # 3. Assemble Context & Generate AI Answer
    context_builder = ContextBuilder()
    struct_ctx = StructuredContext(
        page_number=req.current_page,
        retrieved_chunks=chunk_dicts,
        narrative_context=graph_context
    )

    system_prompt, snapshot, citations = context_builder.build_system_prompt_and_snapshot(
        user_query=req.query,
        structured_context=struct_ctx
    )

    ai_service = get_ai_service()
    ai_res = await ai_service.generate_answer(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": req.query}]
    )

    return NarrativeAskResponse(
        query=req.query,
        answer=ai_res["content"],
        spoiler_mode=req.spoiler_mode,
        capped_at_page=max_page,
        graph_context=graph_context,
        citations=citations
    )
