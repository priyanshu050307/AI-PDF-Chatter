import uuid
import pytest
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentChunk
from app.models.conversation import Conversation, ChatMode
from app.services.rag_service import RAGService
from app.services.embedding_service import MockEmbeddingService
from app.core.errors import ValidationError, NotFoundError


@pytest.mark.asyncio
async def test_rag_document_not_ready_refusal(db_session):
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    user = User(id=user_id, email="unready_user@example.com", password_hash="hash", full_name="Unready User")
    doc = Document(
        id=doc_id, user_id=user_id, title="Processing Doc", original_filename="p.pdf",
        storage_key="k", file_size_bytes=100, page_count=5, processing_status=DocumentStatus.PROCESSING
    )
    conv = Conversation(id=conv_id, user_id=user_id, document_id=doc_id, title="Chat", mode=ChatMode.RAG_CHAT)
    db_session.add_all([user, doc, conv])
    await db_session.commit()

    rag_service = RAGService(db_session)
    with pytest.raises(ValidationError) as exc:
        await rag_service.execute_rag_completion(user, conv_id, "What is in this document?")

    assert "still being prepared" in str(exc.value)


@pytest.mark.asyncio
async def test_rag_completion_and_citations(db_session):
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    user = User(id=user_id, email="rag_user@example.com", password_hash="hash", full_name="RAG User")
    doc = Document(
        id=doc_id, user_id=user_id, title="Ready Doc", original_filename="r.pdf",
        storage_key="k", file_size_bytes=100, page_count=5, processing_status=DocumentStatus.COMPLETED
    )
    conv = Conversation(id=conv_id, user_id=user_id, document_id=doc_id, title="Chat", mode=ChatMode.RAG_CHAT)
    db_session.add_all([user, doc, conv])
    await db_session.commit()

    embedder = MockEmbeddingService(dimension=1536)
    vecs = await embedder.generate_embeddings(["The protocol mandates TLS 1.3 encryption across all network sockets."])

    chunk = DocumentChunk(
        id=uuid.uuid4(), document_id=doc_id, page_start=5, page_end=6,
        chapter_title="Protocols", section_title="TLS Standard",
        content="The protocol mandates TLS 1.3 encryption across all network sockets.", token_count=50, embedding=vecs[0]
    )
    db_session.add(chunk)
    await db_session.commit()

    rag_service = RAGService(db_session)
    msg = await rag_service.execute_rag_completion(user, conv_id, "What encryption protocol is mandated?")

    assert msg.sender == "assistant"
    assert msg.content is not None
    assert len(msg.citations) == 1
    assert msg.citations[0]["page_start"] == 5
    assert msg.citations[0]["page_end"] == 6
    assert msg.citations[0]["chapter_title"] == "Protocols"
