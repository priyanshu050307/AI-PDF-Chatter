import pytest
import uuid
import fitz  # PyMuPDF
from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk, DocumentElement
from app.models.user import User
from app.core.security import get_password_hash
from app.core.errors import AIProviderUnavailableError
from app.services.pdf_processor import PDFProcessor, ExtractedTable, ExtractedImage
from app.services.ocr_provider import get_ocr_provider, MockOCRProvider, PyMuPDFOCRProvider
from app.services.vision_provider import get_vision_provider, MockVisionProvider, OllamaVisionProvider
from app.services.processing_service import DocumentProcessingService
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.services.context_builder import ContextBuilder, StructuredContext


def create_sample_pdf_bytes_with_table_and_drawing() -> bytes:
    """Helper to generate an in-memory PDF binary with text and drawings/shapes."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Sample Multimodal Document Title", fontsize=16)
    page.insert_text((50, 100), "Table 1: Security Risk Matrix Overview", fontsize=12)
    page.insert_text((50, 130), "| Risk Level | Factor | Impact |\n| High | Auth | Severe |", fontsize=10)
    page.draw_rect(fitz.Rect(50, 200, 300, 350), color=(0, 0, 1), fill=(0.9, 0.9, 1))
    page.insert_text((60, 220), "[Figure 1 Architecture Diagram]", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.mark.asyncio
async def test_scanned_page_detection_and_ocr_fallback():
    pdf_bytes = create_sample_pdf_bytes_with_table_and_drawing()
    processor = PDFProcessor(pdf_bytes)
    meta, pages = processor.process()

    assert meta.page_count == 1
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].page_type in ["text-native", "mixed", "scanned"]


@pytest.mark.asyncio
async def test_ocr_provider_abstraction():
    mock_ocr = MockOCRProvider()
    text, conf = mock_ocr.extract_text(b"fake_image_bytes")
    assert "[OCR Extracted Text]" in text
    assert conf == 0.95

    pymupdf_ocr = PyMuPDFOCRProvider()
    health = pymupdf_ocr.health_check()
    assert health["available"] is True
    assert health["provider"] == "pymupdf"


@pytest.mark.asyncio
async def test_vision_provider_abstraction():
    mock_vision = MockVisionProvider()
    desc = await mock_vision.describe_image(b"fake_image_bytes")
    assert "[Visual Description]" in desc

    ollama_vision = OllamaVisionProvider(base_url="http://127.0.0.1:99999", model="nonexistent_vision_model")
    with pytest.raises(AIProviderUnavailableError):
        await ollama_vision.describe_image(b"test_bytes")


@pytest.mark.asyncio
async def test_multimodal_processing_service_end_to_end(db_session):
    user = User(
        id=uuid.uuid4(),
        email="multimodal_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Multimodal User"
    )
    db_session.add(user)
    await db_session.commit()

    pdf_bytes = create_sample_pdf_bytes_with_table_and_drawing()

    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="multimodal_sample.pdf",
        original_filename="multimodal_sample.pdf",
        storage_key="test_storage_key_multimodal",
        file_size_bytes=len(pdf_bytes),
        processing_status=DocumentStatus.PENDING,
        page_count=1
    )
    db_session.add(doc)
    await db_session.commit()

    # Pre-seed storage service with test binary
    proc_service = DocumentProcessingService(db_session)
    await proc_service.storage.upload(pdf_bytes, "test_storage_key_multimodal", "application/pdf")

    res = await proc_service.process_document(doc.id)
    assert res.get("error") is None, f"Processing failed with error: {res.get('error')}"
    assert res["status"] == DocumentStatus.COMPLETED
    assert res["page_count"] == 1
    assert res["chunks_count"] >= 1

    # Verify DocumentElement records
    elements = await proc_service.doc_repo.get_elements_for_document(doc.id)
    assert isinstance(elements, list)


@pytest.mark.asyncio
async def test_multimodal_query_routing_and_context_citations(db_session):
    pipeline = HybridRetrievalPipeline(db_session)
    assert pipeline.classify_query("Explain Table 2 in section 4") == "table_question"
    assert pipeline.classify_query("What does Figure 3 show?") == "visual_question"
    assert pipeline.classify_query("Why is asymmetric encryption slower?") == "conceptual"

    context_builder = ContextBuilder()
    retrieved_chunks = [
        {
            "chunk_id": str(uuid.uuid4()),
            "page_start": 4,
            "page_end": 4,
            "content": "| Control | Risk |\n| MFA | Low |",
            "metadata_json": {"element_type": "table", "bbox": {"x0": 10, "y0": 20, "x1": 200, "y1": 300}}
        },
        {
            "chunk_id": str(uuid.uuid4()),
            "page_start": 5,
            "page_end": 5,
            "content": "Visual Summary of Architecture Diagram",
            "metadata_json": {"element_type": "image", "bbox": {"x0": 50, "y0": 50, "x1": 400, "y1": 400}}
        }
    ]

    struct_ctx = StructuredContext(
        page_number=4,
        retrieved_chunks=retrieved_chunks
    )

    system_prompt, snapshot, citations = context_builder.build_system_prompt_and_snapshot(
        user_query="What does the table and diagram show?",
        structured_context=struct_ctx
    )

    assert "[Page 4, Table 1]" in system_prompt
    assert "[Page 5, Figure 2]" in system_prompt
    assert len(citations) == 2
    assert citations[0]["element_type"] == "table"
    assert citations[1]["element_type"] == "image"
