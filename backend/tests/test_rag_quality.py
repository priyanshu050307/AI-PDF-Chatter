import uuid
import pytest
from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentChunk
from app.models.conversation import Conversation, ChatMode
from app.services.rag_service import RAGService
from app.services.embedding_service import MockEmbeddingService


@pytest.mark.asyncio
async def test_rag_quality_sanity_dataset(db_session):
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    user = User(id=user_id, email="benchmark_rag@example.com", password_hash="hash", full_name="Sanity User")
    doc = Document(
        id=doc_id, user_id=user_id, title="System Spec Doc", original_filename="spec.pdf",
        storage_key="k_spec", file_size_bytes=5000, page_count=20, processing_status=DocumentStatus.COMPLETED
    )
    conv = Conversation(id=conv_id, user_id=user_id, document_id=doc_id, title="Sanity Chat", mode=ChatMode.RAG_CHAT)
    db_session.add_all([user, doc, conv])
    await db_session.commit()

    embedder = MockEmbeddingService(dimension=1536)

    text_memory = "The maximum memory footprint limit per worker node is configured to 16 Gigabytes of RAM."
    text_ha = "High availability clustering uses active-passive failover nodes with heartbeats synchronized every 500 milliseconds."
    text_sec32 = "Section 3.2 describes database connection pooling boundaries using PgBouncer."

    v_memory = await embedder.generate_embeddings([text_memory])
    v_ha = await embedder.generate_embeddings([text_ha])
    v_sec32 = await embedder.generate_embeddings([text_sec32])

    c1 = DocumentChunk(
        id=uuid.uuid4(), document_id=doc_id, page_start=4, page_end=4,
        chapter_title="Chapter 2: Hardware Requirements", section_title="Memory Allocations",
        content=text_memory, token_count=45, embedding=v_memory[0]
    )
    c2 = DocumentChunk(
        id=uuid.uuid4(), document_id=doc_id, page_start=8, page_end=9,
        chapter_title="Chapter 4: Architecture", section_title="High Availability",
        content=text_ha, token_count=55, embedding=v_ha[0]
    )
    c3 = DocumentChunk(
        id=uuid.uuid4(), document_id=doc_id, page_start=12, page_end=12,
        chapter_title="Chapter 5: Database", section_title="3.2 PgBouncer Pooling",
        content=text_sec32, token_count=40, embedding=v_sec32[0]
    )
    db_session.add_all([c1, c2, c3])
    await db_session.commit()

    rag_service = RAGService(db_session)

    # 1. Direct Lookup Query
    res_direct = await rag_service.execute_rag_completion(user, conv_id, text_memory)
    assert res_direct.content is not None
    assert any(cit["page_start"] == 4 for cit in res_direct.citations)

    # 2. Conceptual Query
    res_concept = await rag_service.execute_rag_completion(user, conv_id, text_ha)
    assert res_concept.sender == "assistant"
    assert any(cit["page_start"] == 8 for cit in res_concept.citations)

    # 3. Page-Specific Query
    res_sec = await rag_service.execute_rag_completion(user, conv_id, text_sec32)
    assert any(cit["page_start"] == 12 for cit in res_sec.citations)
