import asyncio
import uuid
import pytest
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.services.retrieval.graph_retriever import EntityRetriever
from tests.conftest import TestingSessionLocal, engine_test
from app.core.database import Base
from app.core.security import get_password_hash

async def main():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        user = User(
            id=uuid.uuid4(),
            email="rel_debug_user@example.com",
            password_hash=get_password_hash("Password123!"),
            full_name="Rel User"
        )
        session.add(user)
        await session.commit()

        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            user_id=user.id,
            title="rel_test.pdf",
            original_filename="rel_test.pdf",
            storage_key="rel_test_key",
            file_size_bytes=100,
            processing_status=DocumentStatus.COMPLETED,
            page_count=120
        )
        session.add(doc)
        await session.commit()

        e1 = Entity(id=uuid.uuid4(), document_id=doc_id, name="Alice Vance", entity_type="PERSON", first_appeared_page=20)
        e2 = Entity(id=uuid.uuid4(), document_id=doc_id, name="Bob Sterling", entity_type="PERSON", first_appeared_page=20)
        session.add_all([e1, e2])
        await session.commit()

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
        session.add_all([rel_p20, rel_p100])
        await session.commit()

        retriever = EntityRetriever(session)

        # Query at Page 50
        subgraph_p50 = await retriever.get_bounded_subgraph(doc_id, query="Alice Vance", max_page=50)
        p50_rels = subgraph_p50["relationships"]
        print("P50 rels count:", len(p50_rels), [r["relationship_type"] for r in p50_rels])

        # Query at Page 120
        subgraph_p120 = await retriever.get_bounded_subgraph(doc_id, query="Alice Vance", max_page=120)
        p120_rels = subgraph_p120["relationships"]
        print("P120 rels count:", len(p120_rels), [r["relationship_type"] for r in p120_rels])

    await drop_test_db()

if __name__ == "__main__":
    asyncio.run(main())
