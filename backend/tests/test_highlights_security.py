import io
import pytest
from httpx import AsyncClient
from pypdf import PdfWriter


def create_sample_pdf_bytes(num_pages: int = 5) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


async def create_test_doc(client: AsyncClient, headers: dict) -> str:
    pdf_bytes = create_sample_pdf_bytes(num_pages=5)
    res = await client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("sec_ann.pdf", pdf_bytes, "application/pdf")}
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_highlights_user_isolation(
    client: AsyncClient,
    user_a_headers: dict,
    user_b_headers: dict
):
    # User A creates document & highlight
    doc_a_id = await create_test_doc(client, user_a_headers)

    create_res = await client.post(
        f"/api/v1/documents/{doc_a_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 1,
            "selected_text": "Secret note by User A",
            "color": "pink",
            "note_text": "Top secret insight"
        }
    )
    assert create_res.status_code == 201
    h_a_id = create_res.json()["id"]

    # 1. User B tries to list User A's document highlights -> 404
    list_b_res = await client.get(
        f"/api/v1/documents/{doc_a_id}/highlights",
        headers=user_b_headers
    )
    assert list_b_res.status_code == 404

    # 2. User B tries to get User A's highlight by ID -> 404
    get_b_res = await client.get(
        f"/api/v1/highlights/{h_a_id}",
        headers=user_b_headers
    )
    assert get_b_res.status_code == 404

    # 3. User B tries to patch User A's highlight -> 404
    patch_b_res = await client.patch(
        f"/api/v1/highlights/{h_a_id}",
        headers=user_b_headers,
        json={"color": "blue", "note_text": "Hacked note"}
    )
    assert patch_b_res.status_code == 404

    # 4. User B tries to delete User A's highlight -> 404
    del_b_res = await client.delete(
        f"/api/v1/highlights/{h_a_id}",
        headers=user_b_headers
    )
    assert del_b_res.status_code == 404
