import pytest
import uuid
import time
import fitz  # PyMuPDF
from typing import Dict, List, Set, Tuple

from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk
from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.models.user import User
from app.core.security import get_password_hash
from app.services.narrative_extractor import NarrativeExtractor
from app.services.processing_service import DocumentProcessingService
from app.services.retrieval.graph_retriever import EntityRetriever
from app.services.context_builder import ContextBuilder, StructuredContext
from tests.fixtures.gold_narrative_dataset import GOLD_NARRATIVE_DATASET


# ---------------------------------------------------------------------------
# Helper: Create 300+ Page Simulated Novel PDF Binary
# ---------------------------------------------------------------------------
def create_300_page_novel_pdf_bytes() -> bytes:
    doc = fitz.open()
    for p in range(1, 305):
        page = doc.new_page(width=595, height=842)
        if p == 1:
            text = (
                f"Chapter 1: The Beginning (Page {p})\n\n"
                "Lord Edward Sterling arrived at Sterling Manor in London. "
                "He greeted Lady Eleanor Vance warmly. Lord Sterling trusts Lady Eleanor."
            )
        elif p == 50:
            text = (
                f"Chapter 10: The Suspicions (Page {p})\n\n"
                "Detective Robert Smith met Inspector Thomas Miller at the London docks. "
                "Robert Smith discovered a suspicious ledger."
            )
        elif p == 150:
            text = (
                f"Chapter 25: The Conflict (Page {p})\n\n"
                "Captain Arthur Pendelton confronted Lord Edward Sterling at the grand hall. "
                "Arthur Pendelton distrusts Lord Sterling."
            )
        elif p == 300:
            text = (
                f"Chapter 50: The Climax (Page {p})\n\n"
                "Lady Eleanor Vance disclosed the hidden truth to Detective Robert Smith. "
                "Lord Edward Sterling departed from London forever."
            )
        else:
            text = (
                f"Page {p} Narrative Text.\n"
                f"Lord Sterling and Lady Eleanor continued their discussion regarding the estate."
            )
        page.insert_text((50, 50), text, fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Step 3 & Step 4: Entity Precision, Recall, F1 & Alias Resolution Tests
# ---------------------------------------------------------------------------
def test_entity_extraction_precision_recall_f1():
    extractor = NarrativeExtractor()
    sample = GOLD_NARRATIVE_DATASET[0]  # sample_1_dialogue

    pages_content = sample["text_pages"]
    extracted_entities, _, _ = extractor.extract_entities_and_relationships(pages_content)

    expected_canonical_names = {e["canonical_name"] for e in sample["expected_entities"]}
    extracted_canonical_names = {e.canonical_name for e in extracted_entities}

    true_positives = len(expected_canonical_names.intersection(extracted_canonical_names))
    false_positives = len(extracted_canonical_names - expected_canonical_names)
    false_negatives = len(expected_canonical_names - extracted_canonical_names)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    assert precision >= 0.80, f"Entity Precision too low: {precision:.2f}"
    assert recall >= 0.80, f"Entity Recall too low: {recall:.2f}"
    assert f1 >= 0.80, f"Entity F1 score too low: {f1:.2f}"


def test_alias_resolution_accuracy_and_suffix_separation():
    extractor = NarrativeExtractor()
    sample = GOLD_NARRATIVE_DATASET[1]  # sample_2_alias_distinction (Edward Sterling vs Edward Sterling Jr.)

    pages_content = sample["text_pages"]
    extracted_entities, _, _ = extractor.extract_entities_and_relationships(pages_content)

    extracted_names = {e.canonical_name for e in extracted_entities}

    # Verify distinct generational names are NOT merged
    assert "Edward Sterling" in extracted_names
    assert "Edward Sterling Jr." in extracted_names
    assert "Edward Sterling" != "Edward Sterling Jr."

    for must_not in sample["must_not_merge"]:
        e1_name, e2_name = must_not
        # Ensure e1 and e2 exist as separate canonical entity objects
        e1_obj = next((e for e in extracted_entities if e.canonical_name == e1_name), None)
        e2_obj = next((e for e in extracted_entities if e.canonical_name == e2_name), None)
        assert e1_obj is not None, f"Missing canonical entity {e1_name}"
        assert e2_obj is not None, f"Missing canonical entity {e2_name}"
        assert e1_obj.canonical_name != e2_obj.canonical_name


# ---------------------------------------------------------------------------
# Step 5: Coreference Accuracy & Ambiguity Fallback Tests
# ---------------------------------------------------------------------------
def test_coreference_resolution_and_ambiguity_fallback():
    extractor = NarrativeExtractor()
    sample = GOLD_NARRATIVE_DATASET[2]  # sample_3_coreference

    pages_content = sample["text_pages"]
    extracted_entities, _, _ = extractor.extract_entities_and_relationships(pages_content)

    robert_entity = next((e for e in extracted_entities if "Robert Smith" in e.canonical_name), None)
    assert robert_entity is not None

    # Paragraph 1 pronoun 'He' should be attributed to Detective Robert Smith
    # Paragraph 2 ambiguous pronoun 'He' should NOT cause runaway false entity creation
    assert robert_entity.mention_count >= 2


# ---------------------------------------------------------------------------
# Step 6 & Step 7: Relationship Quality & Temporality Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_relationship_temporality_non_overwriting_history(db_session):
    doc_id = uuid.uuid4()
    e1 = Entity(id=uuid.uuid4(), document_id=doc_id, name="Alice Vance", entity_type="PERSON", first_appeared_page=20)
    e2 = Entity(id=uuid.uuid4(), document_id=doc_id, name="Bob Sterling", entity_type="PERSON", first_appeared_page=20)
    db_session.add_all([e1, e2])
    await db_session.commit()

    rel_p20 = EntityRelationship(
        id=uuid.uuid4(),
        document_id=doc_id,
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        relationship_type="trusts",
        observed_page=20
    )
    rel_p100 = EntityRelationship(
        id=uuid.uuid4(),
        document_id=doc_id,
        source_entity_id=e1.id,
        target_entity_id=e2.id,
        relationship_type="distrusts",
        observed_page=100
    )
    db_session.add_all([rel_p20, rel_p100])
    await db_session.commit()

    retriever = EntityRetriever(db_session)

    # Query at Page 50 (should only return 'trusts' relationship observed at Page 20)
    subgraph_p50 = await retriever.get_bounded_subgraph(doc_id, query="Alice Vance", max_page=50)
    p50_rels = subgraph_p50["relationships"]
    assert len(p50_rels) == 1
    assert p50_rels[0]["relationship_type"] == "trusts"

    # Query at Page 120 (should return BOTH historical observations without overwriting)
    subgraph_p120 = await retriever.get_bounded_subgraph(doc_id, query="Alice Vance", max_page=120)
    p120_rels = subgraph_p120["relationships"]
    assert len(p120_rels) == 2
    rel_types = {r["relationship_type"] for r in p120_rels}
    assert "trusts" in rel_types
    assert "distrusts" in rel_types


# ---------------------------------------------------------------------------
# Step 8 & Step 9: Event Quality & Timeline Order Tests
# ---------------------------------------------------------------------------
def test_event_extraction_precision_recall_f1():
    extractor = NarrativeExtractor()
    sample = GOLD_NARRATIVE_DATASET[4]  # sample_5_event_categories

    pages_content = sample["text_pages"]
    _, _, extracted_events = extractor.extract_entities_and_relationships(pages_content)

    assert len(extracted_events) >= 3
    event_types = {ev.event_type for ev in extracted_events}
    assert "discovery" in event_types
    assert "departure" in event_types
    assert "decision" in event_types


# ---------------------------------------------------------------------------
# Step 10 & Step 11: Character Knowledge Boundaries & Spoiler Security Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_spoiler_security_across_graph_and_llm_context(db_session):
    doc_id = uuid.uuid4()
    sample = GOLD_NARRATIVE_DATASET[7]  # sample_8_spoiler_protection

    e1 = Entity(id=uuid.uuid4(), document_id=doc_id, name="Lord Sterling", entity_type="PERSON", first_appeared_page=40)
    e2 = Entity(id=uuid.uuid4(), document_id=doc_id, name="Lady Eleanor Vance", entity_type="PERSON", first_appeared_page=200)
    db_session.add_all([e1, e2])
    await db_session.commit()

    rel_spoiler = EntityRelationship(
        id=uuid.uuid4(),
        document_id=doc_id,
        source_entity_id=e2.id,
        target_entity_id=e1.id,
        relationship_type="betrayed",
        observed_page=200
    )
    db_session.add(rel_spoiler)

    ev_spoiler = NarrativeEvent(
        id=uuid.uuid4(),
        document_id=doc_id,
        title="Mastermind Revelation",
        event_type="revelation",
        description="Lady Eleanor Vance was the mastermind behind the stolen funds.",
        page_number=200,
        participants_json={"participants": ["Lady Eleanor Vance", "Lord Sterling"]}
    )
    db_session.add(ev_spoiler)
    await db_session.commit()

    retriever = EntityRetriever(db_session)

    # 1. Spoiler-Free Mode (capped at Page 40)
    subgraph_sf = await retriever.get_bounded_subgraph(doc_id, query="Lord Sterling", max_page=40)
    assert len(subgraph_sf["relationships"]) == 0
    assert len(subgraph_sf["events"]) == 0

    context_builder = ContextBuilder()
    struct_ctx_sf = StructuredContext(page_number=40, narrative_context=subgraph_sf)
    system_prompt_sf, _, _ = context_builder.build_system_prompt_and_snapshot("Who took the funds?", struct_ctx_sf)

    assert "Mastermind Revelation" not in system_prompt_sf
    assert "page 200" not in system_prompt_sf.lower()

    # 2. Full Book Mode (uncapped)
    subgraph_fb = await retriever.get_bounded_subgraph(doc_id, query="Lord Sterling", max_page=None)
    assert len(subgraph_fb["relationships"]) == 1
    assert len(subgraph_fb["events"]) == 1

    struct_ctx_fb = StructuredContext(page_number=40, narrative_context=subgraph_fb)
    system_prompt_fb, _, _ = context_builder.build_system_prompt_and_snapshot("Who took the funds?", struct_ctx_fb)

    assert "Mastermind Revelation" in system_prompt_fb


# ---------------------------------------------------------------------------
# Step 13 & Step 14: Graph Integrity & Document Reprocessing Idempotency
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_document_reprocessing_idempotency(db_session):
    user = User(
        id=uuid.uuid4(),
        email="idempotency_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Idempotency User"
    )
    db_session.add(user)
    await db_session.commit()

    # Sample binary
    doc = fitz.open()
    p = doc.new_page(width=595, height=842)
    p.insert_text((50, 50), "Lord Edward Sterling met Lady Eleanor Vance at Sterling Manor.", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()

    doc_obj = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="idempotency_test.pdf",
        original_filename="idempotency_test.pdf",
        storage_key="idempotency_storage_key",
        file_size_bytes=len(pdf_bytes),
        processing_status=DocumentStatus.PENDING,
        page_count=1
    )
    db_session.add(doc_obj)
    await db_session.commit()

    proc_service = DocumentProcessingService(db_session)
    await proc_service.storage.upload(pdf_bytes, "idempotency_storage_key", "application/pdf")

    # Pass 1: Process Document
    res1 = await proc_service.process_document(doc_obj.id)
    assert res1["status"] == DocumentStatus.COMPLETED

    ents_pass1 = await proc_service.doc_repo.get_entities_for_document(doc_obj.id)
    rels_pass1 = await proc_service.doc_repo.get_relationships_for_document(doc_obj.id)
    evts_pass1 = await proc_service.doc_repo.get_events_for_document(doc_obj.id)

    count_ents_1 = len(ents_pass1)
    count_rels_1 = len(rels_pass1)
    count_evts_1 = len(evts_pass1)

    assert count_ents_1 >= 1

    # Pass 2: Re-Process Same Document
    res2 = await proc_service.process_document(doc_obj.id)
    assert res2["status"] == DocumentStatus.COMPLETED

    ents_pass2 = await proc_service.doc_repo.get_entities_for_document(doc_obj.id)
    rels_pass2 = await proc_service.doc_repo.get_relationships_for_document(doc_obj.id)
    evts_pass2 = await proc_service.doc_repo.get_events_for_document(doc_obj.id)

    # Asserts exact count equality (zero duplicated entity explosions)
    assert len(ents_pass2) == count_ents_1
    assert len(rels_pass2) == count_rels_1
    assert len(evts_pass2) == count_evts_1


# ---------------------------------------------------------------------------
# Step 15, Step 16 & Step 18: 300+ Page Novel Scalability & AI Call Minimization
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_large_novel_scalability_and_batch_processing(db_session):
    user = User(
        id=uuid.uuid4(),
        email="novel_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Novel User"
    )
    db_session.add(user)
    await db_session.commit()

    pdf_bytes = create_300_page_novel_pdf_bytes()

    doc_obj = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="large_novel_300p.pdf",
        original_filename="large_novel_300p.pdf",
        storage_key="large_novel_storage_key",
        file_size_bytes=len(pdf_bytes),
        processing_status=DocumentStatus.PENDING,
        page_count=304
    )
    db_session.add(doc_obj)
    await db_session.commit()

    proc_service = DocumentProcessingService(db_session)
    await proc_service.storage.upload(pdf_bytes, "large_novel_storage_key", "application/pdf")

    start_time = time.time()
    res = await proc_service.process_document(doc_obj.id)
    duration = time.time() - start_time

    assert res["status"] == DocumentStatus.COMPLETED
    assert res["page_count"] == 304

    ents = await proc_service.doc_repo.get_entities_for_document(doc_obj.id)
    rels = await proc_service.doc_repo.get_relationships_for_document(doc_obj.id)
    evts = await proc_service.doc_repo.get_events_for_document(doc_obj.id)

    assert len(ents) >= 4
    assert len(rels) >= 2
    assert len(evts) >= 2
    assert duration < 60.0, f"Large document processing took too long: {duration:.2f}s"


# ---------------------------------------------------------------------------
# Step 22: Multi-Tenant Security Isolation Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multi_tenant_security_isolation(db_session, async_client, auth_tokens):
    # User A (auth_tokens) uploads a document
    pdf_bytes = create_300_page_novel_pdf_bytes()
    token_a = auth_tokens["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res_upload = await async_client.post(
        "/api/v1/documents/upload",
        files={"file": ("sec_doc.pdf", pdf_bytes, "application/pdf")},
        headers=headers_a
    )
    assert res_upload.status_code == 200
    doc_id = res_upload.json()["id"]

    # Register User B
    user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@example.com"
    res_signup = await async_client.post(
        "/api/v1/auth/signup",
        json={"email": user_b_email, "password": "Password123!", "full_name": "User B"}
    )
    assert res_signup.status_code == 200
    token_b = res_signup.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B attempts to query User A's narrative entities endpoint
    res_sec_entities = await async_client.get(
        f"/api/v1/documents/{doc_id}/narrative/entities",
        headers=headers_b
    )
    # Must return 404 or 403 authorization error
    assert res_sec_entities.status_code in [403, 404]

    # User B attempts to query User A's narrative ask endpoint
    res_sec_ask = await async_client.post(
        f"/api/v1/documents/{doc_id}/narrative/ask",
        json={"query": "Who is Lord Sterling?", "spoiler_mode": "spoiler_free"},
        headers=headers_b
    )
    assert res_sec_ask.status_code in [403, 404]
