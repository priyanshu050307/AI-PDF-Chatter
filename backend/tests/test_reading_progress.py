import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_reading_progress_creation_and_update(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=10)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("reading_book.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # 1. Fetch default progress -> Page 1
    prog_res1 = await client.get(f"/api/v1/documents/{doc_id}/progress", headers=user_a_headers)
    assert prog_res1.status_code == 200
    assert prog_res1.json()["current_page"] == 1
    assert prog_res1.json()["scroll_position_pct"] == 0.0

    # 2. Update reading progress -> Page 5, scroll 45%
    update_res = await client.post(
        f"/api/v1/documents/{doc_id}/progress",
        headers=user_a_headers,
        json={"current_page": 5, "scroll_position_pct": 45.5}
    )
    assert update_res.status_code == 200
    assert update_res.json()["current_page"] == 5
    assert update_res.json()["scroll_position_pct"] == 45.5

    # 3. Fetch progress again -> Restores Page 5
    prog_res2 = await client.get(f"/api/v1/documents/{doc_id}/progress", headers=user_a_headers)
    assert prog_res2.status_code == 200
    assert prog_res2.json()["current_page"] == 5
    assert prog_res2.json()["scroll_position_pct"] == 45.5


@pytest.mark.asyncio
async def test_reading_progress_page_count_validation(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=3)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("short_book.pdf", pdf_bytes, "application/pdf")}
    )
    doc_id = upload_res.json()["id"]

    # Attempting to save page 10 when total is 3 pages -> Expect 400
    update_res = await client.post(
        f"/api/v1/documents/{doc_id}/progress",
        headers=user_a_headers,
        json={"current_page": 10, "scroll_position_pct": 0.0}
    )
    assert update_res.status_code == 400


@pytest.mark.asyncio
async def test_reading_progress_multi_user_isolation(
    client: AsyncClient,
    user_a_headers: dict,
    user_b_headers: dict
):
    pdf_bytes = create_sample_pdf_bytes(num_pages=5)
    upload_res = await client.post(
        "/api/v1/documents/upload",
        headers=user_a_headers,
        files={"file": ("doc_a.pdf", pdf_bytes, "application/pdf")}
    )
    doc_a_id = upload_res.json()["id"]

    # User B attempts to read/update User A's progress -> Expect 404
    get_res = await client.get(f"/api/v1/documents/{doc_a_id}/progress", headers=user_b_headers)
    assert get_res.status_code == 404

    post_res = await client.post(
        f"/api/v1/documents/{doc_a_id}/progress",
        headers=user_b_headers,
        json={"current_page": 2, "scroll_position_pct": 10.0}
    )
    assert post_res.status_code == 404
