import pytest
import uuid
import fitz  # PyMuPDF
from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk
from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.models.user import User
from app.core.security import get_password_hash
from app.services.narrative_extractor import NarrativeExtractor
from app.services.processing_service import DocumentProcessingService
from app.services.retrieval.graph_retriever import EntityRetriever
from app.services.context_builder import ContextBuilder, StructuredContext


def create_narrative_pdf_bytes() -> bytes:
    """Helper to generate a multi-page PDF binary containing narrative text with characters, relationships, and events."""
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text(
        (50, 50),
        "Chapter 1: The Encounter\n\n"
        "Lord Edward Sterling arrived in London yesterday. He met with Lady Eleanor Vance at the grand estate.\n"
        "Lord Sterling trusts Lady Eleanor completely. They discussed the secret treaty in detail.",
        fontsize=11
    )

    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(
        (50, 50),
        "Chapter 2: Betrayal\n\n"
        "Captain Arthur Pendelton warned Lord Sterling about the upcoming plot. Arthur Pendelton distrusts Lady Eleanor.\n"
        "Later that evening, Captain Arthur Pendelton confronted Lady Eleanor Vance at the docks.",
        fontsize=11
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_narrative_extractor_entities_aliases_coreference():
    extractor = NarrativeExtractor()
    sample_text = (
        "Lord Edward Sterling arrived in London. He spoke with Lady Eleanor Vance. "
        "Edward Sterling trusts Lady Eleanor."
    )
    res = extractor.extract(sample_text, page_number=1)

    entities = res["entities"]
    relationships = res["relationships"]
    events = res["events"]

    assert len(entities) >= 2
    entity_names = [e["name"] for e in entities]
    assert "Lord Edward Sterling" in entity_names or "Edward Sterling" in entity_names
    assert "Lady Eleanor Vance" in entity_names

    # Verify relationships
    assert len(relationships) >= 1
    rel_types = [r["relationship_type"] for r in relationships]
    assert "trusts" in rel_types or "knows" in rel_types


def test_narrative_extractor_event_creation():
    extractor = NarrativeExtractor()
    sample_text = "Captain Arthur Pendelton confronted Lady Eleanor Vance at the London docks."
    res = extractor.extract(sample_text, page_number=2)

    events = res["events"]
    assert len(events) >= 1
    assert events[0]["page_number"] == 2
    assert "confronted" in events[0]["description"].lower() or "confronted" in events[0]["title"].lower()


@pytest.mark.asyncio
async def test_entity_retriever_spoiler_filtering(db_session):
    doc_id = uuid.uuid4()

    e1 = Entity(
        id=uuid.uuid4(),
        document_id=doc_id,
        name="Lord Edward Sterling",
        entity_type="PERSON",
        first_appeared_page=1,
        attributes={"importance": "major", "aliases": ["Edward", "Sterling"]}
    )
    e2 = Entity(
        id=uuid.uuid4(),
        document_id=doc_id,
        name="Lady Eleanor Vance",
        entity_type="PERSON",
        first_appeared_page=1,
        attributes={"importance": "major", "aliases": ["Eleanor"]}
    )
    e3 = Entity(
        id=uuid.uuid4(),
        document_id=doc_id,
        name="Captain Arthur Pendelton",
        entity_type="PERSON",
        first_appeared_page=2,
        attributes={"importance": "minor", "aliases": ["Arthur"]}
    )
    db_session.add_all([e1, e2, e3])
    await db_session.commit()

    rel1 = EntityRelationship(
        id=uuid.uuid4(),
        document_id=doc_id,
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        relationship_type="trusts",
        observed_page=1
    )
    rel2 = EntityRelationship(
        id=uuid.uuid4(),
        document_id=doc_id,
        source_entity_id=e3.id,
        target_entity_id=e2.id,
        relationship_type="distrusts",
        observed_page=2
    )
    db_session.add_all([rel1, rel2])

    ev1 = NarrativeEvent(
        id=uuid.uuid4(),
        document_id=doc_id,
        title="Initial Encounter",
        event_type="MEETING",
        description="Meeting at grand estate",
        page_number=1,
        participants_json={"participants": ["Lord Edward Sterling", "Lady Eleanor Vance"]}
    )
    ev2 = NarrativeEvent(
        id=uuid.uuid4(),
        document_id=doc_id,
        title="Dock Confrontation",
        event_type="CONFRONTATION",
        description="Confrontation at the docks",
        page_number=2,
        participants_json={"participants": ["Captain Arthur Pendelton", "Lady Eleanor Vance"]}
    )
    db_session.add_all([ev1, ev2])
    await db_session.commit()

    retriever = EntityRetriever(db_session)

    # 1. Profile capped at Page 1 (Spoiler-Free mode)
    prof_p1 = await retriever.get_character_profile(doc_id, str(e2.id), max_page=1)
    assert prof_p1 is not None
    assert len(prof_p1["relationships"]) == 1
    assert prof_p1["relationships"][0]["relationship_type"] == "trusts"
    assert len(prof_p1["events"]) == 1
    assert prof_p1["events"][0]["title"] == "Initial Encounter"

    # 2. Profile with Full Book access (no max_page limit)
    prof_full = await retriever.get_character_profile(doc_id, str(e2.id), max_page=None)
    assert prof_full is not None
    assert len(prof_full["relationships"]) == 2
    assert len(prof_full["events"]) == 2


@pytest.mark.asyncio
async def test_narrative_context_builder_formatting():
    context_builder = ContextBuilder()

    graph_ctx = {
        "target_entity": {"name": "Lord Edward Sterling", "entity_type": "PERSON", "importance": "major"},
        "relationships": [
            {
                "source_entity_name": "Lord Edward Sterling",
                "target_entity_name": "Lady Eleanor Vance",
                "relationship_type": "trusts",
                "observed_page": 1,
                "description": "Expressed mutual trust in Chapter 1"
            }
        ],
        "events": [
            {
                "title": "Encounter at Estate",
                "page_number": 1,
                "description": "Discussed secret treaty"
            }
        ]
    }

    struct_ctx = StructuredContext(
        page_number=1,
        narrative_context=graph_ctx
    )

    system_prompt, snapshot, citations = context_builder.build_system_prompt_and_snapshot(
        user_query="Does Lord Sterling trust Lady Eleanor?",
        structured_context=struct_ctx
    )

    assert "LAYER 9: NARRATIVE GRAPH & CHARACTER CONTEXT" in system_prompt
    assert "Lord Edward Sterling" in system_prompt
    assert "trusts" in system_prompt
    assert "Encounter at Estate" in system_prompt


@pytest.mark.asyncio
async def test_narrative_end_to_end_ingestion_and_api(db_session, async_client, auth_tokens):
    pdf_bytes = create_narrative_pdf_bytes()

    token = auth_tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload PDF document
    response = await async_client.post(
        "/api/v1/documents/upload",
        files={"file": ("narrative_test.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 200
    doc_data = response.json()
    doc_id = doc_data["id"]

    # Process document synchronously in test environment
    proc_service = DocumentProcessingService(db_session)
    res = await proc_service.process_document(uuid.UUID(doc_id))
    assert res["status"] == DocumentStatus.COMPLETED

    # 1. GET /api/v1/documents/{doc_id}/narrative/entities
    res_ents = await async_client.get(
        f"/api/v1/documents/{doc_id}/narrative/entities",
        headers=headers
    )
    assert res_ents.status_code == 200
    entities_list = res_ents.json()
    assert isinstance(entities_list, list)
    assert len(entities_list) >= 1

    target_entity_id = entities_list[0]["id"]

    # 2. GET /api/v1/documents/{doc_id}/narrative/entities/{entity_id}
    res_prof = await async_client.get(
        f"/api/v1/documents/{doc_id}/narrative/entities/{target_entity_id}?max_page=1",
        headers=headers
    )
    assert res_prof.status_code == 200
    prof_data = res_prof.json()
    assert "entity" in prof_data
    assert "relationships" in prof_data
    assert "events" in prof_data

    # 3. GET /api/v1/documents/{doc_id}/narrative/timeline
    res_timeline = await async_client.get(
        f"/api/v1/documents/{doc_id}/narrative/timeline",
        headers=headers
    )
    assert res_timeline.status_code == 200
    timeline_data = res_timeline.json()
    assert isinstance(timeline_data, list)

    # 4. POST /api/v1/documents/{doc_id}/narrative/ask
    res_ask = await async_client.post(
        f"/api/v1/documents/{doc_id}/narrative/ask",
        json={
            "query": "Who is Lord Edward Sterling?",
            "spoiler_mode": "spoiler_free",
            "current_page": 1
        },
        headers=headers
    )
    assert res_ask.status_code == 200
    ask_data = res_ask.json()
    assert "answer" in ask_data
    assert ask_data["spoiler_mode"] == "spoiler_free"
    assert ask_data["capped_at_page"] == 1
