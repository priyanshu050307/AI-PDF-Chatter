import time
import uuid
import asyncio
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

from app.models.user import User
from app.models.document import DocumentStatus
from app.models.conversation import Conversation, ChatMessage
from app.repositories.document_repository import DocumentRepository
from app.repositories.conversation_repository import ConversationRepository
from app.services.retrieval_service import PgVectorRetrievalService
from app.services.context_builder import ContextBuilder, StructuredContext
from app.services.memory_service import ConversationMemoryService
from app.services.ai_service import get_ai_service
from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import logger
from app.schemas.chat import ChatIntent, ContextSnapshotSchema, SelectionContextSchema


class RAGService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.conv_repo = ConversationRepository(db)
        self.retrieval_service = PgVectorRetrievalService(db)
        self.context_builder = ContextBuilder()
        self.memory_service = ConversationMemoryService()
        self.ai_service = get_ai_service()

    async def execute_rag_completion(
        self,
        current_user: User,
        conversation_id: uuid.UUID,
        user_query: str,
        context_snapshot_req: Optional[ContextSnapshotSchema] = None,
        intent_req: Optional[ChatIntent] = ChatIntent.QUESTION
    ) -> ChatMessage:
        """
        Execute full grounded RAG pipeline with Phase 5 Conversation Memory:
        1. Validate conversation & document ownership
        2. Validate context snapshot payload (document & page bounds)
        3. Authoritatively fetch current page content & section metadata
        4. Construct Conversation Memory (rolling summary + bounded history)
        5. Resolve ambiguous follow-up references
        6. Perform selection-aware vector retrieval
        7. Build multi-layer context & intent prompt via ContextBuilder
        8. Generate LLM completion
        9. Persist AI ChatMessage with citations & memory telemetry
        10. Auto-generate title & trigger async rolling summary update if threshold crossed
        """
        # 1. Ownership & Conversation Validation
        conv = await self.conv_repo.get_by_id_and_user_id(conversation_id, current_user.id)
        if not conv:
            raise NotFoundError(message=f"Conversation with ID {conversation_id} not found or access denied.")

        doc = await self.doc_repo.get_by_id_and_user_id(conv.document_id, current_user.id)
        if not doc:
            raise NotFoundError(message=f"Document associated with conversation not found.")

        if doc.processing_status != DocumentStatus.COMPLETED:
            raise ValidationError(
                message=f"Document '{doc.original_filename}' is still being prepared for AI search (Status: {doc.processing_status.value}). Please wait until processing finishes."
            )

        # 2. Context Snapshot Validation
        page_number: Optional[int] = None
        chapter_title: Optional[str] = None
        section_title: Optional[str] = None
        selection_text: Optional[str] = None

        if context_snapshot_req:
            # Security Validation: Document ID match
            if context_snapshot_req.document_id != doc.id:
                raise ValidationError(message="Context document_id does not match the conversation document.")

            # Page Range Validation
            if context_snapshot_req.page_number < 1 or context_snapshot_req.page_number > doc.page_count:
                raise ValidationError(message=f"Invalid context page_number {context_snapshot_req.page_number}. Must be between 1 and {doc.page_count}.")

            page_number = context_snapshot_req.page_number
            chapter_title = context_snapshot_req.chapter_title
            section_title = context_snapshot_req.section_title
            if context_snapshot_req.selection:
                selection_text = context_snapshot_req.selection.selected_text

        intent = intent_req or (context_snapshot_req.intent if context_snapshot_req else ChatIntent.QUESTION)

        # 3. Authoritative Page Data Access from Database
        page_content: Optional[str] = None
        if page_number:
            db_page = await self.doc_repo.get_page_by_number(doc.id, page_number)
            if db_page:
                page_content = db_page.raw_text
                if not chapter_title:
                    chapter_title = getattr(db_page, "chapter_title", None)
                if not section_title:
                    section_title = getattr(db_page, "section_title", None)

        start_time = time.perf_counter()

        # 4. Construct Memory & Follow-up Resolution
        existing_messages = conv.messages or []
        memory = self.memory_service.build_memory(conv, existing_messages)

        resolved_query = self.memory_service.resolve_followup_reference(
            query=user_query,
            recent_messages=memory.recent_messages,
            active_selection=selection_text
        )

        # 5. Add User Message to Database
        user_msg = None
        for attempt in range(3):
            try:
                user_msg = await self.conv_repo.add_message(
                    conversation_id=conversation_id,
                    sender="user",
                    content=user_query
                )
                break
            except OperationalError:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                if attempt == 2:
                    raise
                await asyncio.sleep(0.2 * (2 ** attempt))

        # Auto-generate title on first message if default
        if len(existing_messages) == 0 and (conv.title == "Document Chat" or conv.title.startswith("Chat on ")):
            clean_title = user_query.strip()
            if len(clean_title) > 40:
                clean_title = clean_title[:37] + "..."
            try:
                await self.conv_repo.update_title(conversation_id, current_user.id, clean_title)
            except Exception as title_exc:
                logger.warning(f"Title auto-generation update failed non-critically: {title_exc}")

        # 6. Selection-Aware Vector Retrieval
        t_retrieval_start = time.perf_counter()
        retrieved_chunks = await self.retrieval_service.retrieve_relevant_chunks(
            document_id=doc.id,
            query=resolved_query,
            top_k=settings.RAG_TOP_K,
            selected_text=selection_text
        )
        t_retrieval_end = time.perf_counter()

        # 6.b Retrieve User Annotations if requested or relevant
        user_annotations: List[Dict[str, Any]] = []
        try:
            from app.repositories.highlight_repository import HighlightRepository
            highlight_repo = HighlightRepository(self.db)
            
            query_lower = user_query.lower()
            if any(kw in query_lower for kw in ["note", "notes", "highlight", "highlights", "marked", "annotation"]):
                annotations_db = await highlight_repo.list_highlights(
                    user_id=current_user.id,
                    document_id=doc.id,
                    page_number=page_number if ("this page" in query_lower or "current page" in query_lower) else None
                )
                user_annotations = [
                    {
                        "id": str(h.id),
                        "page_number": h.page_number,
                        "selected_text": h.selected_text,
                        "note_text": h.note_text,
                        "color": h.color,
                        "chapter_title": h.chapter_title
                    }
                    for h in annotations_db
                ]
        except Exception as e:
            logger.warning(f"Failed to fetch annotations for RAG context: {e}")

        # 7. Assemble Multi-Layer Context
        structured_ctx = StructuredContext(
            selection_text=selection_text,
            page_number=page_number,
            page_content=page_content,
            chapter_title=chapter_title,
            section_title=section_title,
            retrieved_chunks=retrieved_chunks,
            history_messages=memory.recent_messages,
            summary=memory.summary,
            user_annotations=user_annotations,
            intent=intent
        )

        system_prompt, context_snapshot, citations = self.context_builder.build_system_prompt_and_snapshot(
            user_query=user_query,
            structured_context=structured_ctx
        )

        # Inject memory observability metrics
        context_snapshot["history_messages_used"] = len(memory.recent_messages)
        context_snapshot["history_tokens_used"] = memory.history_tokens

        # 8. LLM Completion
        messages_payload = memory.recent_messages + [{"role": "user", "content": resolved_query}]
        t_llm_start = time.perf_counter()
        try:
            ai_result = await self.ai_service.generate_answer(system_prompt, messages_payload)
        except Exception as llm_exc:
            logger.error(f"LLM completion error for conv={conversation_id}: {llm_exc}", exc_info=True)
            ai_result = {
                "content": f"[AI ERROR] An error occurred while generating a response: {str(llm_exc)}",
                "token_usage": {},
                "error": True
            }
        t_llm_end = time.perf_counter()

        end_time = time.perf_counter()

        retrieval_latency_ms = (t_retrieval_end - t_retrieval_start) * 1000
        llm_latency_ms = (t_llm_end - t_llm_start) * 1000
        total_latency_ms = (end_time - start_time) * 1000

        context_snapshot["retrieval_latency_ms"] = round(retrieval_latency_ms, 2)
        context_snapshot["llm_latency_ms"] = round(llm_latency_ms, 2)
        context_snapshot["total_latency_ms"] = round(total_latency_ms, 2)
        if ai_result.get("error"):
            context_snapshot["ai_error"] = True

        # 9. Persist Assistant Message
        assistant_msg = None
        for attempt in range(3):
            try:
                assistant_msg = await self.conv_repo.add_message(
                    conversation_id=conversation_id,
                    sender="assistant",
                    content=ai_result["content"],
                    citations=citations,
                    context_snapshot=context_snapshot,
                    token_usage=ai_result.get("token_usage", {})
                )
                await self.db.commit()
                break
            except OperationalError:
                try:
                    await self.db.rollback()
                except Exception:
                    pass
                if attempt == 2:
                    raise
                await asyncio.sleep(0.2 * (2 ** attempt))


        # 10. Check if Rolling Summary update is needed
        updated_total_msgs = len(existing_messages) + 2
        if updated_total_msgs - conv.summary_message_count >= settings.CONVERSATION_SUMMARY_TRIGGER_MESSAGES:
            # Trigger summary generation
            asyncio.create_task(self._trigger_background_summary(conv.id, conv.title, existing_messages + [user_msg, assistant_msg], updated_total_msgs))

        logger.info(
            f"RAG Completion [conv={conversation_id}, history={len(memory.recent_messages)} msgs, summary={bool(memory.summary)}]: "
            f"Retrieved {len(retrieved_chunks)} chunks in {retrieval_latency_ms:.1f}ms. Total: {total_latency_ms:.1f}ms."
        )

        return assistant_msg

    async def _trigger_background_summary(
        self,
        conversation_id: uuid.UUID,
        title: str,
        messages: List[ChatMessage],
        msg_count: int
    ):
        """Non-blocking background helper for rolling summary generation."""
        try:
            summary = await self.memory_service.generate_summary(title, messages)
            if summary:
                await self.conv_repo.update_summary(conversation_id, summary, msg_count)
                logger.info(f"Background rolling summary updated for conversation {conversation_id} at {msg_count} messages.")
        except Exception as e:
            logger.error(f"Failed to generate background summary for conversation {conversation_id}: {e}")
