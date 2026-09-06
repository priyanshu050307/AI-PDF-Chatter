import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter


def generate_test_pdf_bytes(num_pages: int = 10) -> bytes:
    """Utility helper to generate test PDF bytes with arbitrary page counts."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_large_page_count_pdf(client: AsyncClient, user_a_headers: dict):
    """Verify that documents with high page counts (e.g. 100 pages) are accepted without arbitrary page limits."""
    pdf_bytes = generate_test_pdf_bytes(num_pages=100)

    response = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("large_100_pages.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "large_100_pages.pdf"
    assert data["page_count"] == 100
    assert data["processing_status"] in ["PENDING", "COMPLETED", "PROCESSING"]


@pytest.mark.asyncio
async def test_upload_corrupt_pdf_returns_400(client: AsyncClient, user_a_headers: dict):
    """Verify corrupted PDF bytes return a clear HTTP 400 validation error rather than unhandled 500."""
    corrupt_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ncorrupt garbage bytes metadata..."

    response = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("corrupt.pdf", corrupt_bytes, "application/pdf")}
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_upload_non_pdf_magic_bytes_returns_400(client: AsyncClient, user_a_headers: dict):
    """Verify files without %PDF magic bytes return a clean HTTP 400 validation error."""
    invalid_bytes = b"NOT_A_PDF_HEADER_DATA"

    response = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("invalid.pdf", invalid_bytes, "application/pdf")}
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
