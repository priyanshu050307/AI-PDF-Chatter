import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.reading_progress import ReadingProgressCreate, ReadingProgressResponse
from app.repositories.document_repository import DocumentRepository
from app.repositories.reading_progress_repository import ReadingProgressRepository
from app.core.errors import NotFoundError, ValidationError


class ReadingProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.progress_repo = ReadingProgressRepository(db)

    async def save_progress(
        self,
        user: User,
        document_id: uuid.UUID,
        progress_in: ReadingProgressCreate
    ) -> ReadingProgressResponse:
        """Save reading progress position after verifying document ownership."""
        doc = await self.doc_repo.get_by_id_and_user_id(document_id, user.id)
        if not doc:
            raise NotFoundError(message="Document not found.")

        if progress_in.current_page > doc.page_count:
            raise ValidationError(message=f"Current page cannot exceed document total page count ({doc.page_count}).")

        progress = await self.progress_repo.upsert_progress(
            user_id=user.id,
            document_id=document_id,
            current_page=progress_in.current_page,
            scroll_position_pct=progress_in.scroll_position_pct
        )
        await self.db.commit()
        return ReadingProgressResponse.model_validate(progress)

    async def get_progress(self, user: User, document_id: uuid.UUID) -> ReadingProgressResponse:
        """Fetch reading progress position for authenticated user."""
        doc = await self.doc_repo.get_by_id_and_user_id(document_id, user.id)
        if not doc:
            raise NotFoundError(message="Document not found.")

        progress = await self.progress_repo.get_by_user_and_doc(user.id, document_id)
        if not progress:
            # Default to page 1 if no saved progress exists yet
            progress = await self.progress_repo.upsert_progress(
                user_id=user.id,
                document_id=document_id,
                current_page=1,
                scroll_position_pct=0.0
            )
            await self.db.commit()

        return ReadingProgressResponse.model_validate(progress)
