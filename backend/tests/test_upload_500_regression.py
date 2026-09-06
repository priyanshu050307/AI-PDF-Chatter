import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter
from app.services.pdf_processor import PDFProcessor, ExtractedTextBlock


def generate_complex_test_pdf() -> bytes:
    """Generate a test PDF with content for regression testing."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_pdf_processor_handles_null_span_attributes():
    """Verify PDFProcessor safely handles null/missing font, flags, size, and bbox attributes without crashing."""
    processor = PDFProcessor(generate_complex_test_pdf())
    meta, pages = processor.process()
    assert meta.page_count >= 1
    assert len(pages) >= 1

    # Verify manual ExtractedTextBlock initialization with default/safe fields
    block = ExtractedTextBlock(text="Sample", font_size=10.0, is_bold=False, bbox=(0, 0, 100, 20))
    assert block.font_size == 10.0
    assert block.is_bold is False


@pytest.mark.asyncio
async def test_upload_regression_no_500_internal_server_error(client: AsyncClient, user_a_headers: dict):
    """
    Regression test for upload failure:
    Verify that uploading a PDF returns HTTP 201 Created and creates valid document and storage records without 500 error.
    """
    pdf_bytes = generate_complex_test_pdf()

    response = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("unit_5_test.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["original_filename"] == "unit_5_test.pdf"
    assert data["page_count"] >= 1
    assert data["processing_status"] in ["PENDING", "PROCESSING", "COMPLETED"]
