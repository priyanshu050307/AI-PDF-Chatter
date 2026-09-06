import pytest
from app.services.context_builder import ContextBuilder, StructuredContext
from app.schemas.chat import ChatIntent


def test_context_builder_user_annotations_and_evidence_boundary():
    builder = ContextBuilder()

    user_annotations = [
        {
            "id": "ann-111",
            "page_number": 3,
            "color": "green",
            "selected_text": "Public key encryption relies on mathematical trapdoor functions.",
            "note_text": "Remember RSA and ECC algorithm examples for exam."
        }
    ]

    retrieved_chunks = [
        {
            "chunk_id": "chk-1",
            "page_start": 3,
            "page_end": 3,
            "chapter_title": "Cryptography",
            "section_title": "Asymmetric Algorithms",
            "content": "Asymmetric encryption uses key pairs consisting of a public key and a private key."
        }
    ]

    ctx = StructuredContext(
        page_number=3,
        user_annotations=user_annotations,
        retrieved_chunks=retrieved_chunks,
        intent=ChatIntent.QUESTION
    )

    system_prompt, snapshot, citations = builder.build_system_prompt_and_snapshot(
        user_query="What do my notes say about page 3?",
        structured_context=ctx
    )

    # 1. Verify User Annotations block is present
    assert "--- SAVED USER ANNOTATIONS & NOTES ---" in system_prompt
    assert "[User Annotation 1] (Page 3, Color: green) | User Note: \"Remember RSA and ECC algorithm examples for exam.\"" in system_prompt
    assert "Highlighted Text: \"Public key encryption relies on mathematical trapdoor functions.\"" in system_prompt

    # 2. Verify Strict Evidence Boundary Instruction
    assert "USER ASSERTIONS and NOT authoritative document text" in system_prompt
    assert "explicitly distinguish them (e.g. \"Your note states...\") from author document evidence (\"The document states...\")" in system_prompt
    assert "Do NOT create document citations from user notes" in system_prompt

    # 3. Telemetry snapshot tracking
    assert snapshot["user_annotations_count"] == 1
    assert snapshot["annotation_ids"] == ["ann-111"]
