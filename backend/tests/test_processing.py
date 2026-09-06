import io
import uuid
import pytest
import fitz
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk
from app.services.processing_service import DocumentProcessingService
from app.services.pdf_processor import PDFProcessor
from app.services.chunker import ContextAwareChunker


def create_sample_text_pdf_bytes(num_pages: int = 3) -> bytes:
    """Generate a multi-page PDF containing text and chapter headings using PyMuPDF."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=612, height=792)
        page.insert_text(
            (50, 50),
            f"Chapter {i+1}: Advanced PDF Intelligence\n\n"
            f"This is section paragraph 1 for page {i+1}. Context aware chunking preserves exact page boundaries.\n\n"
            f"This is section paragraph 2 for page {i+1}. It contains detailed body content for testing.",
            fontsize=14
        )
    file_bytes = doc.tobytes()
    doc.close()
    return file_bytes


@pytest.fixture
async def user_a_headers(client: AsyncClient) -> dict:
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": "proc_user_a@example.com",
        "password": "Password123!",
        "full_name": "Proc User A"
    })
    token = signup_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_b_headers(client: AsyncClient) -> dict:
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": "proc_user_b@example.com",
        "password": "Password123!",
        "full_name": "Proc User B"
    })
    token = signup_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_pdf_processor_extraction():
    pdf_bytes = create_sample_text_pdf_bytes(num_pages=2)
    processor = PDFProcessor(pdf_bytes)
    meta, pages = processor.process()

    assert meta.page_count == 2
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Advanced PDF Intelligence" in pages[0].raw_text
    assert pages[0].page_width == 612.0
    assert pages[0].page_height == 792.0


@pytest.mark.asyncio
async def test_context_aware_chunker():
    pdf_bytes = create_sample_text_pdf_bytes(num_pages=3)
    processor = PDFProcessor(pdf_bytes)
    _, pages = processor.process()

    chunker = ContextAwareChunker(target_tokens=50, min_tokens=10)
    chunks = chunker.chunk_document(pages)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert chunk.page_start >= 1
        assert chunk.page_end >= chunk.page_start
        assert len(chunk.content) > 0
        assert chunk.token_count > 0


@pytest.mark.asyncio
async def test_end_to_end_processing_pipeline(client: AsyncClient, user_a_headers: dict, db_session: AsyncSession):
    pdf_bytes = create_sample_text_pdf_bytes(num_pages=3)

    # 1. Upload Document
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("intelligence_report.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload_res.status_code == 201
    doc_id = uuid.UUID(upload_res.json()["id"])

    # 2. Execute Processing Pipeline
    proc_service = DocumentProcessingService(db_session)
    result = await proc_service.process_document(doc_id)

    assert result["status"] == DocumentStatus.COMPLETED
    assert result["page_count"] == 3
    assert result["chunks_count"] >= 1

    # 3. Inspect Database Records
    doc_result = await db_session.execute(select(Document).where(Document.id == doc_id))
    doc = doc_result.scalars().first()
    assert doc is not None
    assert doc.processing_status == DocumentStatus.COMPLETED
    assert doc.page_count == 3

    # Check pages table
    pages_res = await db_session.execute(select(DocumentPage).where(DocumentPage.document_id == doc_id))
    pages = list(pages_res.scalars().all())
    assert len(pages) == 3

    # Check chunks table
    chunks_res = await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    chunks = list(chunks_res.scalars().all())
    assert len(chunks) >= 1

    for chunk in chunks:
        assert chunk.page_start >= 1
        assert chunk.page_end >= chunk.page_start
        assert chunk.document_id == doc_id
        assert chunk.token_count > 0


@pytest.mark.asyncio
async def test_processing_idempotency(client: AsyncClient, user_a_headers: dict, db_session: AsyncSession):
    """Verify executing process_document twice does not create duplicate pages or chunks."""
    pdf_bytes = create_sample_text_pdf_bytes(num_pages=2)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("idempotent_test.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = uuid.UUID(upload_res.json()["id"])

    proc_service = DocumentProcessingService(db_session)

    # First run
    res1 = await proc_service.process_document(doc_id)
    # Second run
    res2 = await proc_service.process_document(doc_id)

    assert res1["page_count"] == res2["page_count"]
    assert res1["chunks_count"] == res2["chunks_count"]

    pages_res = await db_session.execute(select(DocumentPage).where(DocumentPage.document_id == doc_id))
    pages = list(pages_res.scalars().all())
    assert len(pages) == 2  # Exactly 2 pages, not 4!

    chunks_res = await db_session.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc_id))
    chunks = list(chunks_res.scalars().all())
    assert len(chunks) == res1["chunks_count"]


@pytest.mark.asyncio
async def test_reprocess_endpoint_security_isolation(
    client: AsyncClient,
    user_a_headers: dict,
    user_b_headers: dict
):
    """Verify User B cannot trigger reprocessing for User A's document."""
    pdf_bytes = create_sample_text_pdf_bytes(num_pages=1)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("user_a_doc.pdf", pdf_bytes, "application/pdf")}
    )
    doc_a_id = upload_res.json()["id"]

    # User B attempts to trigger process endpoint -> Expect 404
    reproc_res = await client.post(f"/api/v1/documents/{doc_a_id}/process", headers=user_b_headers)
    assert reproc_res.status_code == 404
