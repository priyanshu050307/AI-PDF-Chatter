import uuid
import abc
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.document import Document, DocumentChunk, DocumentPage
from app.models.annotation import Highlight
from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.services.retrieval.graph_retriever import EntityRetriever
from app.repositories.document_repository import DocumentRepository
from app.core.errors import NotFoundError, ValidationError, ForbiddenError


# ---------------------------------------------------------------------------
# Base Agent Tool Abstraction
# ---------------------------------------------------------------------------
class BaseAgentTool(abc.ABC):
    name: str
    description: str
    input_schema: Type[BaseModel]
    timeout_seconds: float = 10.0

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, user: User, document_id: uuid.UUID, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schema & execute tool within user and document security scope."""
        validated = self.input_schema.model_validate(tool_input)
        return await self._execute(user=user, document_id=document_id, params=validated)

    @abc.abstractmethod
    async def _execute(self, user: User, document_id: uuid.UUID, params: BaseModel) -> Dict[str, Any]:
        pass


# ---------------------------------------------------------------------------
# 1. search_evidence (Hybrid Retrieval Pipeline Tool)
# ---------------------------------------------------------------------------
class SearchEvidenceInput(BaseModel):
    query: str = Field(..., description="Search query string")
    top_k: int = Field(5, ge=1, le=10, description="Max evidence chunks to retrieve")
    max_page: Optional[int] = Field(None, description="Optional page limit for spoiler protection")


class SearchEvidenceTool(BaseAgentTool):
    name = "search_evidence"
    description = "Executes hybrid vector + lexical search with reranking to retrieve authoritative document evidence passages."
    input_schema = SearchEvidenceInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: SearchEvidenceInput) -> Dict[str, Any]:
        pipeline = HybridRetrievalPipeline(self.db)
        results, telemetry = await pipeline.execute_pipeline(
            document_id=document_id,
            query=params.query,
            top_k=params.top_k
        )

        if params.max_page is not None:
            results = [r for r in results if r.page_start <= params.max_page]

        evidence = [
            {
                "chunk_id": str(r.chunk_id),
                "page_start": r.page_start,
                "page_end": r.page_end,
                "content": r.content,
                "chapter_title": r.chapter,
                "section_title": r.section,
                "score": r.rerank_score or r.fused_score or r.dense_score,
                "element_type": (r.metadata_json or {}).get("element_type", "text")
            }
            for r in results
        ]

        return {
            "query": params.query,
            "evidence_count": len(evidence),
            "evidence": evidence
        }


# ---------------------------------------------------------------------------
# 2. search_document (Direct Text Search Tool)
# ---------------------------------------------------------------------------
class SearchDocumentInput(BaseModel):
    keyword: str = Field(..., description="Keyword or phrase to locate in document chunks")
    max_page: Optional[int] = Field(None, description="Optional max page cap")


class SearchDocumentTool(BaseAgentTool):
    name = "search_document"
    description = "Searches for exact keyword or text phrase occurrences across document pages."
    input_schema = SearchDocumentInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: SearchDocumentInput) -> Dict[str, Any]:
        q = select(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.content.ilike(f"%{params.keyword}%")
        )
        if params.max_page is not None:
            q = q.where(DocumentChunk.page_start <= params.max_page)

        q = q.limit(5)
        res = await self.db.execute(q)
        chunks = list(res.scalars().all())

        return {
            "keyword": params.keyword,
            "matches_count": len(chunks),
            "matches": [
                {
                    "chunk_id": str(c.id),
                    "page_number": c.page_start,
                    "content_snippet": c.content[:300]
                }
                for c in chunks
            ]
        }


# ---------------------------------------------------------------------------
# 3. get_page (Page Content Tool)
# ---------------------------------------------------------------------------
class GetPageInput(BaseModel):
    page_number: int = Field(..., ge=1, description="1-indexed target page number")


class GetPageTool(BaseAgentTool):
    name = "get_page"
    description = "Retrieves full authoritative text content and metadata of a specific document page."
    input_schema = GetPageInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetPageInput) -> Dict[str, Any]:
        repo = DocumentRepository(self.db)
        page = await repo.get_page(document_id, params.page_number)
        if not page:
            return {"page_number": params.page_number, "found": False, "content": None}

        return {
            "page_number": page.page_number,
            "found": True,
            "char_count": len(page.content or ""),
            "page_type": page.page_type,
            "content": page.content
        }


# ---------------------------------------------------------------------------
# 4. get_document_structure (Table of Contents / Section Hierarchy Tool)
# ---------------------------------------------------------------------------
class GetDocumentStructureInput(BaseModel):
    pass


class GetDocumentStructureTool(BaseAgentTool):
    name = "get_document_structure"
    description = "Retrieves the structural hierarchy, chapter titles, and section titles of the document."
    input_schema = GetDocumentStructureInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetDocumentStructureInput) -> Dict[str, Any]:
        res = await self.db.execute(
            select(DocumentChunk.chapter_title, DocumentChunk.section_title, DocumentChunk.page_start)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.page_start.asc())
        )
        rows = res.all()

        chapters = {}
        for ch, sec, p in rows:
            c_name = ch or "Main Document"
            if c_name not in chapters:
                chapters[c_name] = {"start_page": p, "sections": set()}
            if sec:
                chapters[c_name]["sections"].add(sec)

        structure = [
            {
                "chapter_title": k,
                "start_page": v["start_page"],
                "sections": sorted(list(v["sections"]))
            }
            for k, v in chapters.items()
        ]

        return {"document_id": str(document_id), "structure": structure}


# ---------------------------------------------------------------------------
# 5. find_entity (Narrative Entity Lookup Tool)
# ---------------------------------------------------------------------------
class FindEntityInput(BaseModel):
    name_or_alias: str = Field(..., description="Character name, alias, or location string")


class FindEntityTool(BaseAgentTool):
    name = "find_entity"
    description = "Finds narrative characters, organizations, or locations matching a name or alias."
    input_schema = FindEntityInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: FindEntityInput) -> Dict[str, Any]:
        retriever = EntityRetriever(self.db)
        matches = await retriever.find_matching_entities(document_id, params.name_or_alias)

        return {
            "query": params.name_or_alias,
            "count": len(matches),
            "entities": [
                {
                    "entity_id": str(e.id),
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "first_appeared_page": e.first_appeared_page,
                    "aliases": e.attributes.get("aliases", []) if e.attributes else [],
                    "importance": e.attributes.get("importance", "minor") if e.attributes else "minor"
                }
                for e in matches
            ]
        }


# ---------------------------------------------------------------------------
# 6. get_entity_profile (Character Profile & Graph Tool)
# ---------------------------------------------------------------------------
class GetEntityProfileInput(BaseModel):
    entity_id_or_name: str = Field(..., description="Entity UUID or canonical name")
    max_page: Optional[int] = Field(None, description="Optional spoiler protection page limit")


class GetEntityProfileTool(BaseAgentTool):
    name = "get_entity_profile"
    description = "Retrieves full character profile, relationship graph, and plot events centered on an entity."
    input_schema = GetEntityProfileInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetEntityProfileInput) -> Dict[str, Any]:
        retriever = EntityRetriever(self.db)
        profile = await retriever.get_character_profile(
            document_id=document_id,
            entity_id_or_name=params.entity_id_or_name,
            max_page=params.max_page
        )
        if not profile:
            return {"entity_id_or_name": params.entity_id_or_name, "found": False}

        return {"found": True, "profile": profile}


# ---------------------------------------------------------------------------
# 7. find_relationships (Entity Relationship Graph Tool)
# ---------------------------------------------------------------------------
class FindRelationshipsInput(BaseModel):
    entity_a: str = Field(..., description="First character name or entity ID")
    entity_b: Optional[str] = Field(None, description="Second character name or entity ID")
    max_page: Optional[int] = Field(None, description="Optional max page cap")


class FindRelationshipsTool(BaseAgentTool):
    name = "find_relationships"
    description = "Retrieves observed relationships and interactions between characters up to an optional page."
    input_schema = FindRelationshipsInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: FindRelationshipsInput) -> Dict[str, Any]:
        retriever = EntityRetriever(self.db)
        subgraph = await retriever.get_bounded_subgraph(
            document_id=document_id,
            query=params.entity_a,
            max_hops=2,
            max_page=params.max_page
        )

        rels = subgraph.get("relationships", [])
        if params.entity_b:
            b_lower = params.entity_b.lower()
            rels = [
                r for r in rels
                if b_lower in r.get("source_entity_name", "").lower() or b_lower in r.get("target_entity_name", "").lower()
            ]

        return {
            "entity_a": params.entity_a,
            "entity_b": params.entity_b,
            "relationships_count": len(rels),
            "relationships": rels
        }


# ---------------------------------------------------------------------------
# 8. get_character_timeline (Character Event Timeline Tool)
# ---------------------------------------------------------------------------
class GetCharacterTimelineInput(BaseModel):
    character_name: str = Field(..., description="Character name")
    max_page: Optional[int] = Field(None, description="Optional page limit for spoiler protection")


class GetCharacterTimelineTool(BaseAgentTool):
    name = "get_character_timeline"
    description = "Retrieves narrative plot events involving a specific character ordered by page number."
    input_schema = GetCharacterTimelineInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetCharacterTimelineInput) -> Dict[str, Any]:
        retriever = EntityRetriever(self.db)
        subgraph = await retriever.get_bounded_subgraph(
            document_id=document_id,
            query=params.character_name,
            max_hops=1,
            max_page=params.max_page
        )

        return {
            "character_name": params.character_name,
            "events_count": len(subgraph.get("events", [])),
            "events": subgraph.get("events", [])
        }


# ---------------------------------------------------------------------------
# 9. find_events (Narrative Events Search Tool)
# ---------------------------------------------------------------------------
class FindEventsInput(BaseModel):
    event_type: Optional[str] = Field(None, description="Event type (meeting, conflict, discovery, betrayal, decision, departure, revelation, death)")
    keyword: Optional[str] = Field(None, description="Event title or description keyword")
    max_page: Optional[int] = Field(None, description="Optional page limit for spoiler protection")


class FindEventsTool(BaseAgentTool):
    name = "find_events"
    description = "Searches narrative plot events by event type, keyword, or page range."
    input_schema = FindEventsInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: FindEventsInput) -> Dict[str, Any]:
        q = select(NarrativeEvent).where(NarrativeEvent.document_id == document_id)
        if params.event_type:
            q = q.where(NarrativeEvent.event_type.ilike(f"%{params.event_type}%"))
        if params.keyword:
            q = q.where(
                (NarrativeEvent.title.ilike(f"%{params.keyword}%")) | (NarrativeEvent.description.ilike(f"%{params.keyword}%"))
            )
        if params.max_page is not None:
            q = q.where(NarrativeEvent.page_number <= params.max_page)

        q = q.order_by(NarrativeEvent.page_number.asc()).limit(10)
        res = await self.db.execute(q)
        evts = list(res.scalars().all())

        return {
            "events_count": len(evts),
            "events": [
                {
                    "event_id": str(e.id),
                    "title": e.title,
                    "event_type": e.event_type,
                    "description": e.description,
                    "page_number": e.page_number,
                    "participants": (e.participants_json or {}).get("participants", [])
                }
                for e in evts
            ]
        }


# ---------------------------------------------------------------------------
# 10. get_my_annotations (User Annotations & Notes Tool)
# ---------------------------------------------------------------------------
class GetMyAnnotationsInput(BaseModel):
    keyword: Optional[str] = Field(None, description="Optional keyword in note text or highlighted text")


class GetMyAnnotationsTool(BaseAgentTool):
    name = "get_my_annotations"
    description = "Retrieves user's personal highlights, notes, and annotations for the document."
    input_schema = GetMyAnnotationsInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetMyAnnotationsInput) -> Dict[str, Any]:
        q = select(Highlight).where(
            Highlight.user_id == user.id,
            Highlight.document_id == document_id
        )
        if params.keyword:
            q = q.where(
                (Highlight.selected_text.ilike(f"%{params.keyword}%")) | (Highlight.note_text.ilike(f"%{params.keyword}%"))
            )

        res = await self.db.execute(q)
        highlights = list(res.scalars().all())

        return {
            "user_id": str(user.id),
            "annotations_count": len(highlights),
            "annotations": [
                {
                    "annotation_id": str(h.id),
                    "page_number": h.page_number,
                    "selected_text": h.selected_text,
                    "note_text": h.note_text,
                    "color": h.color
                }
                for h in highlights
            ]
        }


# ---------------------------------------------------------------------------
# 11. compare_entities (Structured Entity Comparison Tool)
# ---------------------------------------------------------------------------
class CompareEntitiesInput(BaseModel):
    entity_a_name: str = Field(..., description="First character or entity name")
    entity_b_name: str = Field(..., description="Second character or entity name")
    max_page: Optional[int] = Field(None, description="Optional page limit for spoiler protection")


class CompareEntitiesTool(BaseAgentTool):
    name = "compare_entities"
    description = "Performs a structured side-by-side comparison of two entities (attributes, shared relationships, key events)."
    input_schema = CompareEntitiesInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: CompareEntitiesInput) -> Dict[str, Any]:
        retriever = EntityRetriever(self.db)
        prof_a = await retriever.get_character_profile(document_id, params.entity_a_name, max_page=params.max_page)
        prof_b = await retriever.get_character_profile(document_id, params.entity_b_name, max_page=params.max_page)

        if not prof_a or not prof_b:
            return {
                "entity_a": params.entity_a_name,
                "entity_b": params.entity_b_name,
                "found_a": bool(prof_a),
                "found_b": bool(prof_b),
                "comparison": None
            }

        rel_tool = FindRelationshipsTool(self.db)
        shared_rels = await rel_tool.run(
            user=user,
            document_id=document_id,
            tool_input={"entity_a": params.entity_a_name, "entity_b": params.entity_b_name, "max_page": params.max_page}
        )

        return {
            "entity_a": prof_a["entity"],
            "entity_b": prof_b["entity"],
            "shared_relationships": shared_rels.get("relationships", []),
            "events_a_count": len(prof_a.get("events", [])),
            "events_b_count": len(prof_b.get("events", []))
        }


# ---------------------------------------------------------------------------
# 12. get_source (Evidence Provenance Navigation Tool)
# ---------------------------------------------------------------------------
class GetSourceInput(BaseModel):
    chunk_id: str = Field(..., description="Document chunk UUID string")


class GetSourceTool(BaseAgentTool):
    name = "get_source"
    description = "Retrieves exact document chunk provenance details (page range, chapter, section, content)."
    input_schema = GetSourceInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetSourceInput) -> Dict[str, Any]:
        try:
            c_uuid = uuid.UUID(params.chunk_id)
        except ValueError:
            raise ValidationError(message=f"Invalid chunk_id '{params.chunk_id}'")

        res = await self.db.execute(
            select(DocumentChunk).where(
                DocumentChunk.id == c_uuid,
                DocumentChunk.document_id == document_id
            )
        )
        chunk = res.scalars().first()
        if not chunk:
            raise NotFoundError(message=f"Chunk '{params.chunk_id}' not found for document.")

        return {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "chapter_title": chunk.chapter_title,
            "section_title": chunk.section_title,
            "content": chunk.content,
            "metadata": chunk.metadata_json
        }


# ---------------------------------------------------------------------------
# 13. search_workspace (Multi-Document Search Tool)
# ---------------------------------------------------------------------------
class SearchWorkspaceInput(BaseModel):
    query: str = Field(..., description="Search query string across workspace documents")
    document_ids: List[str] = Field(..., description="List of document UUIDs to search")
    top_k: int = Field(5, ge=1, le=10, description="Max candidate passages per retrieval")


class SearchWorkspaceTool(BaseAgentTool):
    name = "search_workspace"
    description = "Searches across multiple selected workspace documents with document-balanced hybrid retrieval."
    input_schema = SearchWorkspaceInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: SearchWorkspaceInput) -> Dict[str, Any]:
        doc_uuids = [uuid.UUID(d) for d in params.document_ids]
        # Security check: User must own all requested documents
        res = await self.db.execute(
            select(Document).where(Document.id.in_(doc_uuids), Document.user_id == user.id)
        )
        owned_docs = list(res.scalars().all())
        if len(owned_docs) != len(doc_uuids):
            raise ForbiddenError(message="Unauthorized access to one or more selected workspace documents.")

        pipeline = HybridRetrievalPipeline(self.db)
        results, _telemetry = await pipeline.execute_pipeline(
            document_ids=doc_uuids,
            query=params.query,
            top_k=params.top_k
        )
        return {
            "query": params.query,
            "document_count": len(doc_uuids),
            "evidence_count": len(results),
            "evidence": [
                {
                    "chunk_id": str(r.chunk_id),
                    "document_id": str(r.document_id),
                    "page_start": r.page_start,
                    "page_end": r.page_end,
                    "content": r.content,
                    "score": r.rerank_score or r.fused_score or r.dense_score
                }
                for r in results
            ]
        }


# ---------------------------------------------------------------------------
# 14. compare_documents (Cross-Document Comparison Tool)
# ---------------------------------------------------------------------------
class CompareDocumentsInput(BaseModel):
    document_ids: List[str] = Field(..., description="List of document UUIDs to compare")
    topic: Optional[str] = Field(None, description="Topic or aspect to compare")


class CompareDocumentsTool(BaseAgentTool):
    name = "compare_documents"
    description = "Executes structured side-by-side comparison across selected workspace documents."
    input_schema = CompareDocumentsInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: CompareDocumentsInput) -> Dict[str, Any]:
        from app.services.multi_doc_service import MultiDocService
        doc_uuids = [uuid.UUID(d) for d in params.document_ids]
        service = MultiDocService(self.db)
        return await service.compare_documents(user=user, selected_document_ids=doc_uuids, topic=params.topic)


# ---------------------------------------------------------------------------
# 15. find_common_claims (Agreement Detection Tool)
# ---------------------------------------------------------------------------
class FindCommonClaimsInput(BaseModel):
    document_ids: List[str] = Field(..., description="List of document UUIDs to evaluate")
    topic: Optional[str] = Field(None, description="Topic of interest")


class FindCommonClaimsTool(BaseAgentTool):
    name = "find_common_claims"
    description = "Identifies common findings and agreed-upon claims across selected documents."
    input_schema = FindCommonClaimsInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: FindCommonClaimsInput) -> Dict[str, Any]:
        from app.services.multi_doc_service import MultiDocService
        doc_uuids = [uuid.UUID(d) for d in params.document_ids]
        service = MultiDocService(self.db)
        return await service.find_common_claims(user=user, selected_document_ids=doc_uuids, topic=params.topic)


# ---------------------------------------------------------------------------
# 16. find_conflicting_claims (Contradiction Detection Tool)
# ---------------------------------------------------------------------------
class FindConflictingClaimsInput(BaseModel):
    document_ids: List[str] = Field(..., description="List of document UUIDs to evaluate")
    topic: Optional[str] = Field(None, description="Topic of interest")


class FindConflictingClaimsTool(BaseAgentTool):
    name = "find_conflicting_claims"
    description = "Detects candidate contradictions and disagreement points across selected documents while preserving qualifiers."
    input_schema = FindConflictingClaimsInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: FindConflictingClaimsInput) -> Dict[str, Any]:
        from app.services.multi_doc_service import MultiDocService
        doc_uuids = [uuid.UUID(d) for d in params.document_ids]
        service = MultiDocService(self.db)
        return await service.find_conflicting_claims(user=user, selected_document_ids=doc_uuids, topic=params.topic)


# ---------------------------------------------------------------------------
# 17. get_document_evidence (Document-Specific Evidence Tool)
# ---------------------------------------------------------------------------
class GetDocumentEvidenceInput(BaseModel):
    target_document_id: str = Field(..., description="Target document UUID string")
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, ge=1, le=10, description="Max passages")


class GetDocumentEvidenceTool(BaseAgentTool):
    name = "get_document_evidence"
    description = "Retrieves authoritative evidence passages specifically from one specified document."
    input_schema = GetDocumentEvidenceInput

    async def _execute(self, user: User, document_id: uuid.UUID, params: GetDocumentEvidenceInput) -> Dict[str, Any]:
        target_uuid = uuid.UUID(params.target_document_id)
        # Security check: User must own target document
        res = await self.db.execute(
            select(Document).where(Document.id == target_uuid, Document.user_id == user.id)
        )
        doc = res.scalars().first()
        if not doc:
            raise ForbiddenError(message=f"Unauthorized or non-existent document '{params.target_document_id}'")

        pipeline = HybridRetrievalPipeline(self.db)
        results, _ = await pipeline.execute_pipeline(
            document_id=target_uuid,
            query=params.query,
            top_k=params.top_k
        )
        return {
            "document_id": str(target_uuid),
            "document_title": doc.title,
            "evidence_count": len(results),
            "evidence": [
                {
                    "chunk_id": str(r.chunk_id),
                    "page_start": r.page_start,
                    "page_end": r.page_end,
                    "content": r.content,
                    "score": r.rerank_score or r.fused_score or r.dense_score
                }
                for r in results
            ]
        }


# ---------------------------------------------------------------------------
# Tool Registry Factory
# ---------------------------------------------------------------------------
def get_agent_tools(db: AsyncSession) -> Dict[str, BaseAgentTool]:
    """Instantiate all available agent tools mapped by tool name."""
    tools: List[BaseAgentTool] = [
        SearchEvidenceTool(db),
        SearchDocumentTool(db),
        GetPageTool(db),
        GetDocumentStructureTool(db),
        FindEntityTool(db),
        GetEntityProfileTool(db),
        FindRelationshipsTool(db),
        GetCharacterTimelineTool(db),
        FindEventsTool(db),
        GetMyAnnotationsTool(db),
        CompareEntitiesTool(db),
        GetSourceTool(db),
        SearchWorkspaceTool(db),
        CompareDocumentsTool(db),
        FindCommonClaimsTool(db),
        FindConflictingClaimsTool(db),
        GetDocumentEvidenceTool(db),
    ]
    return {t.name: t for t in tools}

