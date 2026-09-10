import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.annotation import ReadingProgress
from app.repositories.base import BaseRepository


class ReadingProgressRepository(BaseRepository[ReadingProgress]):
    def __init__(self, db: AsyncSession):
        super().__init__(ReadingProgress, db)

    async def get_by_user_and_doc(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Optional[ReadingProgress]:
        """Fetch reading progress record for specific user and document."""
        result = await self.db.execute(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.document_id == document_id
            )
        )
        return result.scalars().first()

    async def upsert_progress(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        current_page: int,
        scroll_position_pct: float
    ) -> ReadingProgress:
        """Create or update reading progress position."""
        progress = await self.get_by_user_and_doc(user_id, document_id)
        now = datetime.now(timezone.utc)

        if progress:
            progress.current_page = current_page
            progress.scroll_position_pct = scroll_position_pct
            progress.last_opened_at = now
        else:
            progress = ReadingProgress(
                user_id=user_id,
                document_id=document_id,
                current_page=current_page,
                scroll_position_pct=scroll_position_pct,
                last_opened_at=now
            )
            self.db.add(progress)

        await self.db.flush()
        return progress
