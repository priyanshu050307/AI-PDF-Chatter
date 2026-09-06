import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter


def create_sample_pdf_bytes(num_pages: int = 3) -> bytes:
    """Utility helper to generate valid PDF byte content for testing."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_pdf_upload_and_metadata(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=5)

    response = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("test_doc.pdf", pdf_bytes, "application/pdf")}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "test_doc.pdf"
    assert data["page_count"] == 5
    assert data["file_size_bytes"] == len(pdf_bytes)
    assert data["processing_status"] in ["PENDING", "COMPLETED", "PROCESSING"]


@pytest.mark.asyncio
async def test_get_document_by_id(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("sample.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=user_a_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_list_user_documents(client: AsyncClient, user_a_headers: dict):
    pdf1 = create_sample_pdf_bytes(1)
    pdf2 = create_sample_pdf_bytes(2)

    await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("doc1.pdf", pdf1, "application/pdf")})
    await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("doc2.pdf", pdf2, "application/pdf")})

    list_res = await client.get("/api/v1/documents", headers=user_a_headers)
    assert list_res.status_code == 200
    docs = list_res.json()
    assert len(docs) >= 2


@pytest.mark.asyncio
async def test_download_document_file(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=3)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("download_test.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    file_res = await client.get(f"/api/v1/documents/{doc_id}/file", headers=user_a_headers)
    assert file_res.status_code == 200
    assert file_res.headers["content-type"] == "application/pdf"
    assert len(file_res.content) == len(pdf_bytes)


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=1)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("delete_me.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=user_a_headers)
    assert del_res.status_code == 200

    get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=user_a_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_isolation(client: AsyncClient, user_a_headers: dict, user_b_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("user_a_private.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # User B tries to read User A's document
    get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=user_b_headers)
    assert get_res.status_code == 404

    # User B tries to download User A's document file
    file_res = await client.get(f"/api/v1/documents/{doc_id}/file", headers=user_b_headers)
    assert file_res.status_code == 404

    # User B tries to delete User A's document
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=user_b_headers)
    assert del_res.status_code == 404


@pytest.mark.asyncio
async def test_upload_non_pdf_fails(client: AsyncClient, user_a_headers: dict):
    invalid_file = b"Hello, this is a plain text file"
    response = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("invalid.txt", invalid_file, "text/plain")}
    )
    assert response.status_code == 400
