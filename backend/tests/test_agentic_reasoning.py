import pytest
import uuid
import time
import fitz  # PyMuPDF

from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk
from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.models.annotation import Highlight
from app.models.user import User
from app.core.security import get_password_hash
from app.services.agent.tools import get_agent_tools
from app.services.agent.evidence_ledger import EvidenceLedger, EvidenceRecord
from app.services.agent.agent_router import AgentRouter, AgentRoute
from app.services.agent.agent_controller import AgentController
from tests.fixtures.gold_agent_dataset import GOLD_AGENT_DATASET


def create_agent_sample_pdf() -> bytes:
    doc = fitz.open()
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text(
        (50, 50),
        "Chapter 1: Security Architecture\n\n"
        "The system uses AES-256 encryption. Lord Edward Sterling met Lady Eleanor Vance at Sterling Manor.\n"
        "Table 1: Risk Factor Matrix\n| Factor | Impact |\n| MFA | High |",
        fontsize=11
    )
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(
        (50, 50),
        "Chapter 2: Authentication\n\n"
        "Multi-factor authentication (MFA) protects user accounts. Captain Arthur Pendelton warned Lord Sterling.",
        fontsize=11
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# 1. Agent Router Classification Tests
# ---------------------------------------------------------------------------
def test_agent_router_classification():
    router = AgentRouter()

    route1, is_agentic1 = router.route_query("What is the primary encryption standard?")
    assert route1 == AgentRoute.SIMPLE_FACTUAL
    assert is_agentic1 is False

    route2, is_agentic2 = router.route_query("Compare Lord Sterling and Lady Eleanor Vance")
    assert route2 == AgentRoute.COMPARISON
    assert is_agentic2 is True

    route3, is_agentic3 = router.route_query("How did Lord Edward Sterling and Lady Eleanor Vance's relationship evolve?")
    assert route3 == AgentRoute.CHARACTER_NARRATIVE
    assert is_agentic3 is True

    route4, is_agentic4 = router.route_query("What did I highlight about authentication security in my notes?")
    assert route4 == AgentRoute.ANNOTATION_ANALYSIS
    assert is_agentic4 is True


# ---------------------------------------------------------------------------
# 2. Evidence Ledger Deduplication Test
# ---------------------------------------------------------------------------
def test_evidence_ledger_deduplication():
    ledger = EvidenceLedger()

    r1 = EvidenceRecord(source_type="chunk", source_id="c1", document_id="doc1", content="Text 1")
    r2 = EvidenceRecord(source_type="chunk", source_id="c1", document_id="doc1", content="Text 1 Duplicate")
    r3 = EvidenceRecord(source_type="chunk", source_id="c2", document_id="doc1", content="Text 2")

    assert ledger.add_record(r1) is True
    assert ledger.add_record(r2) is False  # Deduplicated!
    assert ledger.add_record(r3) is True

    assert len(ledger.records) == 2


# ---------------------------------------------------------------------------
# 3. Tool Execution & Schema Validation Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_tools_execution_and_schema_validation(db_session):
    user = User(
        id=uuid.uuid4(),
        email="tool_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Tool User"
    )
    db_session.add(user)
    await db_session.commit()

    pdf_bytes = create_agent_sample_pdf()
    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="agent_sample.pdf",
        original_filename="agent_sample.pdf",
        storage_key="agent_sample_key",
        file_size_bytes=len(pdf_bytes),
        processing_status=DocumentStatus.COMPLETED,
        page_count=2
    )
    db_session.add(doc)

    e1 = Entity(id=uuid.uuid4(), document_id=doc.id, name="Lord Edward Sterling", entity_type="PERSON", first_appeared_page=1)
    e2 = Entity(id=uuid.uuid4(), document_id=doc.id, name="Lady Eleanor Vance", entity_type="PERSON", first_appeared_page=1)
    db_session.add_all([e1, e2])

    rel = EntityRelationship(id=uuid.uuid4(), document_id=doc.id, source_entity_id=e1.id, target_entity_id=e2.id, relationship_type="trusts", observed_page=1)
    db_session.add(rel)

    ann = Highlight(
        id=uuid.uuid4(),
        user_id=user.id,
        document_id=doc.id,
        page_number=2,
        selected_text="Multi-factor authentication",
        start_offset=0,
        end_offset=27,
        note_text="Important MFA rule",
        color="yellow"
    )
    db_session.add(ann)
    await db_session.commit()

    tools = get_agent_tools(db_session)

    # 1. get_document_structure
    res_struct = await tools["get_document_structure"].run(user, doc.id, {})
    assert "structure" in res_struct

    # 2. find_entity
    res_ent = await tools["find_entity"].run(user, doc.id, {"name_or_alias": "Lord Sterling"})
    assert res_ent["count"] >= 1

    # 3. get_entity_profile
    res_prof = await tools["get_entity_profile"].run(user, doc.id, {"entity_id_or_name": "Lord Edward Sterling"})
    assert res_prof["found"] is True

    # 4. compare_entities
    res_comp = await tools["compare_entities"].run(user, doc.id, {"entity_a_name": "Lord Edward Sterling", "entity_b_name": "Lady Eleanor Vance"})
    assert res_comp["entity_a"] is not None

    # 5. get_my_annotations
    res_ann = await tools["get_my_annotations"].run(user, doc.id, {"keyword": "MFA"})
    assert res_ann["annotations_count"] >= 1


# ---------------------------------------------------------------------------
# 4. Agent Controller End-to-End & Benchmark Evaluation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_controller_end_to_end_and_benchmark(db_session):
    user = User(
        id=uuid.uuid4(),
        email="agent_bench_user@example.com",
        password_hash=get_password_hash("Password123!"),
        full_name="Agent Bench User"
    )
    db_session.add(user)
    await db_session.commit()

    pdf_bytes = create_agent_sample_pdf()
    doc = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        title="agent_bench.pdf",
        original_filename="agent_bench.pdf",
        storage_key="agent_bench_key",
        file_size_bytes=len(pdf_bytes),
        processing_status=DocumentStatus.COMPLETED,
        page_count=2
    )
    db_session.add(doc)

    e1 = Entity(id=uuid.uuid4(), document_id=doc.id, name="Lord Edward Sterling", entity_type="PERSON", first_appeared_page=1)
    e2 = Entity(id=uuid.uuid4(), document_id=doc.id, name="Lady Eleanor Vance", entity_type="PERSON", first_appeared_page=1)
    db_session.add_all([e1, e2])

    rel = EntityRelationship(id=uuid.uuid4(), document_id=doc.id, source_entity_id=e1.id, target_entity_id=e2.id, relationship_type="trusts", observed_page=1)
    db_session.add(rel)
    await db_session.commit()

    controller = AgentController(db_session)

    # Run query
    res = await controller.run_investigation(
        user=user,
        document_id=doc.id,
        query="Compare Lord Edward Sterling and Lady Eleanor Vance",
        mode="agentic"
    )

    assert res["state"] == "COMPLETED"
    assert res["route"] in ["COMPARISON", "CHARACTER_NARRATIVE", "MULTI_STEP_INVESTIGATION"]
    assert "answer" in res
    assert len(res["steps"]) >= 1
    assert res["latency_ms"] > 0


# ---------------------------------------------------------------------------
# 5. Multi-Tenant Security Isolation Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_security_isolation(client, user_a_headers, user_b_headers):
    pdf_bytes = create_agent_sample_pdf()

    res_upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("sec_agent_doc.pdf", pdf_bytes, "application/pdf")},
        headers=user_a_headers
    )
    assert res_upload.status_code == 200
    doc_id = res_upload.json()["id"]

    # User B attempts to trigger Agentic Investigation on User A's document
    res_sec_ask = await client.post(
        f"/api/v1/documents/{doc_id}/agent/ask",
        json={"query": "Investigate encryption architecture", "mode": "agentic"},
        headers=user_b_headers
    )
    assert res_sec_ask.status_code in [403, 404]

