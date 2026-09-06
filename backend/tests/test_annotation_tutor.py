import pytest
from httpx import AsyncClient
from tests.test_documents import create_sample_pdf_bytes


@pytest.mark.asyncio
async def test_annotation_aware_tutor_session(client: AsyncClient, user_a_headers: dict):
    pdf_bytes = create_sample_pdf_bytes(num_pages=2)
    upload_res = await client.post("/api/v1/documents/upload", headers=user_a_headers, files={"file": ("annot_doc.pdf", pdf_bytes, "application/pdf")})
    doc_id = upload_res.json()["id"]

    # Add a user highlight & note
    hl_res = await client.post(
        f"/api/v1/documents/{doc_id}/highlights",
        headers=user_a_headers,
        json={
            "page_number": 1,
            "selected_text": "Key security principle",
            "start_offset": 0,
            "end_offset": 20,
            "color": "yellow",
            "note_text": "I think this is crucial for the exam."
        }
    )
    assert hl_res.status_code == 201

    # Create Tutor Session with HIGHLIGHTS scope
    session_res = await client.post(
        "/api/v1/tutor/sessions",
        headers=user_a_headers,
        json={
            "document_id": doc_id,
            "title": "Study Highlights Session",
            "topic_scope": {"type": "HIGHLIGHTS", "target": "User Highlights"}
        }
    )
    assert session_res.status_code == 201
    s_data = session_res.json()
    assert s_data["topic_scope"]["type"] == "HIGHLIGHTS"
