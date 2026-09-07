import uuid
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentPage, DocumentChunk, DocumentElement
from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, db: AsyncSession):
        super().__init__(Document, db)

    async def get_by_id_and_user_id(self, document_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Document]:
        """Fetch document by ID ensuring strict ownership matching user_id."""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id, Document.user_id == user_id)
            .options(selectinload(Document.reading_progresses))
        )
        return result.scalars().first()

    async def get_by_user_id_with_progress(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Document]:
        """Fetch documents belonging to user, ordered by creation date, with reading progress preloaded."""
        result = await self.db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .options(selectinload(Document.reading_progresses))
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_by_id_and_user_id(self, document_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete document record if user owns it."""
        doc = await self.get_by_id_and_user_id(document_id, user_id)
        if doc:
            await self.db.delete(doc)
            await self.db.flush()
            return True
        return False

    async def clear_pages_and_chunks(self, document_id: uuid.UUID) -> None:
        """Idempotency helper: delete existing pages, chunks, elements, entities, relationships, and events prior to re-ingestion."""
        await self.db.execute(delete(NarrativeEvent).where(NarrativeEvent.document_id == document_id))
        await self.db.execute(delete(EntityRelationship).where(EntityRelationship.document_id == document_id))
        await self.db.execute(delete(Entity).where(Entity.document_id == document_id))
        await self.db.execute(delete(DocumentElement).where(DocumentElement.document_id == document_id))
        await self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        await self.db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
        await self.db.flush()

    async def bulk_create_pages(self, pages: List[DocumentPage], batch_size: int = 50) -> None:
        """Bulk insert DocumentPage entities in batches to prevent SQL parameter limits."""
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i + batch_size]
            self.db.add_all(batch)
            await self.db.flush()

    async def bulk_create_chunks(self, chunks: List[DocumentChunk], batch_size: int = 50) -> None:
        """Bulk insert DocumentChunk entities in batches to prevent SQL parameter limits."""
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            self.db.add_all(batch)
            await self.db.flush()

    async def bulk_create_elements(self, elements: List[DocumentElement], batch_size: int = 50) -> None:
        """Bulk insert DocumentElement entities in batches."""
        for i in range(0, len(elements), batch_size):
            batch = elements[i:i + batch_size]
            self.db.add_all(batch)
            await self.db.flush()

    async def get_elements_for_document(self, document_id: uuid.UUID, element_type: Optional[str] = None) -> List[DocumentElement]:
        """Fetch elements for a document with optional element_type filtering."""
        query = select(DocumentElement).where(DocumentElement.document_id == document_id)
        if element_type:
            query = query.where(DocumentElement.element_type == element_type)
        query = query.order_by(DocumentElement.page_number.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_chunks_for_document(self, document_id: uuid.UUID) -> List[DocumentChunk]:
        """Fetch all chunks for a document ordered by page_start."""
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.page_start.asc())
        )
        return list(result.scalars().all())

    async def get_page_by_number(self, document_id: uuid.UUID, page_number: int) -> Optional[DocumentPage]:
        """Fetch a specific page by document_id and page_number."""
        result = await self.db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id, DocumentPage.page_number == page_number)
        )
        return result.scalars().first()

    async def get_chunks_for_page(self, document_id: uuid.UUID, page_number: int) -> List[DocumentChunk]:
        """Fetch chunks spanning a given page_number."""
        result = await self.db.execute(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.page_start <= page_number,
                DocumentChunk.page_end >= page_number
            )
        )
        return list(result.scalars().all())

    async def get_entities_for_document(self, document_id: uuid.UUID) -> List[Entity]:
        """Fetch all entities for a document."""
        result = await self.db.execute(
            select(Entity)
            .where(Entity.document_id == document_id)
            .order_by(Entity.first_appeared_page.asc().nulls_last())
        )
        return list(result.scalars().all())

    async def get_relationships_for_document(self, document_id: uuid.UUID) -> List[EntityRelationship]:
        """Fetch all entity relationships for a document."""
        result = await self.db.execute(
            select(EntityRelationship)
            .where(EntityRelationship.document_id == document_id)
            .order_by(EntityRelationship.observed_page.asc().nulls_last())
        )
        return list(result.scalars().all())

    async def get_events_for_document(self, document_id: uuid.UUID) -> List[NarrativeEvent]:
        """Fetch all narrative events for a document ordered by page_number."""
        result = await self.db.execute(
            select(NarrativeEvent)
            .where(NarrativeEvent.document_id == document_id)
            .order_by(NarrativeEvent.page_number.asc())
        )
        return list(result.scalars().all())


