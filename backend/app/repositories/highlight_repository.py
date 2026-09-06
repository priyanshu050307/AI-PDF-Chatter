import uuid
from typing import List, Optional
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Highlight
from app.schemas.annotation import HighlightCreate, HighlightUpdate


class HighlightRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_highlight(self, user_id: uuid.UUID, document_id: uuid.UUID, data: HighlightCreate) -> Highlight:
        highlight = Highlight(
            id=uuid.uuid4(),
            user_id=user_id,
            document_id=document_id,
            page_number=data.page_number,
            selected_text=data.selected_text,
            start_offset=data.start_offset,
            end_offset=data.end_offset,
            color=data.color,
            note_text=data.note_text,
            bounding_box=data.bounding_box,
            chapter_title=data.chapter_title,
            section_title=data.section_title
        )
        self.db.add(highlight)
        await self.db.flush()
        await self.db.commit()
        return highlight

    async def get_highlight(self, highlight_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Highlight]:
        stmt = select(Highlight).where(
            Highlight.id == highlight_id,
            Highlight.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_highlights(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        page_number: Optional[int] = None,
        color: Optional[str] = None,
        has_note: Optional[bool] = None,
        search_query: Optional[str] = None
    ) -> List[Highlight]:
        conditions = [
            Highlight.user_id == user_id,
            Highlight.document_id == document_id
        ]

        if page_number is not None:
            conditions.append(Highlight.page_number == page_number)

        if color:
            conditions.append(Highlight.color == color)

        if has_note is True:
            conditions.append(and_(Highlight.note_text.isnot(None), Highlight.note_text != ""))
        elif has_note is False:
            conditions.append(or_(Highlight.note_text.is_(None), Highlight.note_text == ""))

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            conditions.append(
                or_(
                    Highlight.selected_text.ilike(term),
                    Highlight.note_text.ilike(term)
                )
            )

        stmt = select(Highlight).where(*conditions).order_by(Highlight.page_number.asc(), Highlight.created_at.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_highlight(
        self,
        highlight_id: uuid.UUID,
        user_id: uuid.UUID,
        color: Optional[str] = None,
        note_text: Optional[str] = None
    ) -> Optional[Highlight]:
        highlight = await self.get_highlight(highlight_id, user_id)
        if not highlight:
            return None

        if color is not None:
            highlight.color = color

        # Note text can be cleared by passing empty string or None
        highlight.note_text = note_text

        await self.db.flush()
        await self.db.commit()
        return highlight

    async def delete_highlight(self, highlight_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        highlight = await self.get_highlight(highlight_id, user_id)
        if not highlight:
            return False

        await self.db.delete(highlight)
        await self.db.flush()
        await self.db.commit()
        return True
