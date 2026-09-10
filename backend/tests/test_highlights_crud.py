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
        files={"file": ("test_ann.pdf", pdf_bytes, "application/pdf")}
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_create_and_list_highlights(
    client: AsyncClient,
    user_a_headers: dict
):
    doc_id = await create_test_doc(client, user_a_headers)

    # 1. Create Highlight without Note
    res1 = await client.post(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 2,
            "selected_text": "Defense in depth uses multiple controls.",
            "start_offset": 10,
            "end_offset": 50,
            "color": "yellow",
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.05}
        }
    )
    assert res1.status_code == 201
    h1 = res1.json()
    assert h1["color"] == "yellow"
    assert h1["page_number"] == 2
    assert h1["note_text"] is None

    # 2. Create Highlight with Note & Green color
    res2 = await client.post(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 2,
            "selected_text": "Asymmetric encryption uses public and private keys.",
            "start_offset": 100,
            "end_offset": 150,
            "color": "green",
            "note_text": "Crucial concept for quiz!",
            "bounding_box": {"x": 0.1, "y": 0.3, "width": 0.6, "height": 0.05}
        }
    )
    assert res2.status_code == 201
    h2 = res2.json()
    assert h2["color"] == "green"
    assert h2["note_text"] == "Crucial concept for quiz!"

    # 3. List Highlights (No filter)
    list_res = await client.get(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers
    )
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # 4. Filter by Color
    green_res = await client.get(
        f"/api/v1/documents/{doc_id}/highlights?color=green",
        headers=user_a_headers
    )
    assert green_res.status_code == 200
    assert green_res.json()["total"] == 1
    assert green_res.json()["items"][0]["id"] == h2["id"]

    # 5. Filter by search query
    search_res = await client.get(
        f"/api/v1/documents/{doc_id}/highlights?search=quiz",
        headers=user_a_headers
    )
    assert search_res.status_code == 200
    assert search_res.json()["total"] == 1
    assert search_res.json()["items"][0]["id"] == h2["id"]


@pytest.mark.asyncio
async def test_update_and_delete_highlight(
    client: AsyncClient,
    user_a_headers: dict
):
    doc_id = await create_test_doc(client, user_a_headers)

    # Create initial highlight
    create_res = await client.post(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 1,
            "selected_text": "Original highlight text.",
            "color": "yellow"
        }
    )
    h_id = create_res.json()["id"]

    # Update color & note text
    patch_res = await client.patch(
        f"/api/v1/highlights/{h_id}",
        headers=user_a_headers,
        json={
            "color": "purple",
            "note_text": "Updated note content."
        }
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["color"] == "purple"
    assert updated["note_text"] == "Updated note content."
    assert updated["selected_text"] == "Original highlight text."

    # Delete highlight
    del_res = await client.delete(
        f"/api/v1/highlights/{h_id}",
        headers=user_a_headers
    )
    assert del_res.status_code == 204

    # Verify deletion (404)
    get_res = await client.get(
        f"/api/v1/highlights/{h_id}",
        headers=user_a_headers
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_invalid_highlight_input(
    client: AsyncClient,
    user_a_headers: dict
):
    doc_id = await create_test_doc(client, user_a_headers)

    # Page number out of bounds
    res_bad_page = await client.post(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 99,
            "selected_text": "Text on page 99",
            "color": "yellow"
        }
    )
    assert res_bad_page.status_code == 400

    # Unallowed color
    res_bad_color = await client.post(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 1,
            "selected_text": "Some text",
            "color": "neon_rainbow"
        }
    )
    assert res_bad_color.status_code == 400
