import uuid
import pytest

from app.models.user import User
from app.models.document import Document, DocumentStatus, DocumentChunk
from app.services.retrieval_service import PgVectorRetrievalService
from app.services.embedding_service import MockEmbeddingService


@pytest.mark.asyncio
async def test_vector_retrieval_document_scoping_and_ordering(db_session):
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    other_doc_id = uuid.uuid4()

    user = User(id=user_id, email="retrieval_user@example.com", password_hash="hash", full_name="Retrieval User")
    doc1 = Document(
        id=doc_id, user_id=user_id, title="Doc 1", original_filename="d1.pdf",
        storage_key="k1", file_size_bytes=100, page_count=5, processing_status=DocumentStatus.COMPLETED
    )
    doc2 = Document(
        id=other_doc_id, user_id=user_id, title="Doc 2", original_filename="d2.pdf",
        storage_key="k2", file_size_bytes=100, page_count=5, processing_status=DocumentStatus.COMPLETED
    )
    db_session.add_all([user, doc1, doc2])
    await db_session.commit()

    embedder = MockEmbeddingService(dimension=1536)
    c1_text = "Cybersecurity firewall configuration guidelines."
    c2_text = "Cooking recipes for authentic pasta carbonara."
    c3_text = "Zero trust network architecture policies."

    c1_vecs = await embedder.generate_embeddings([c1_text])
    c2_vecs = await embedder.generate_embeddings([c2_text])
    c3_vecs = await embedder.generate_embeddings([c3_text])

    chunk1 = DocumentChunk(
        id=uuid.uuid4(), document_id=doc_id, page_start=1, page_end=2,
        chapter_title="Security", section_title="Firewalls",
        content=c1_text, token_count=50, embedding=c1_vecs[0]
    )
    chunk2 = DocumentChunk(
        id=uuid.uuid4(), document_id=other_doc_id, page_start=1, page_end=1,
        content=c2_text, token_count=40, embedding=c2_vecs[0]
    )
    chunk3 = DocumentChunk(
        id=uuid.uuid4(), document_id=doc_id, page_start=3, page_end=4,
        chapter_title="Security", section_title="Zero Trust",
        content=c3_text, token_count=60, embedding=c3_vecs[0]
    )
    db_session.add_all([chunk1, chunk2, chunk3])
    await db_session.commit()

    retriever = PgVectorRetrievalService(db_session)
    results = await retriever.retrieve_relevant_chunks(
        document_id=doc_id,
        query=c1_text,
        top_k=5
    )

    # Scoping check: should only return chunks belonging to doc_id
    assert len(results) == 2
    returned_doc_ids = {r["document_id"] for r in results}
    assert returned_doc_ids == {str(doc_id)}

    # Highest similarity score should be top result
    assert results[0]["chunk_id"] == str(chunk1.id)
    assert results[0]["score"] > 0.0
    assert results[0]["page_start"] == 1
    assert results[0]["chapter_title"] == "Security"
