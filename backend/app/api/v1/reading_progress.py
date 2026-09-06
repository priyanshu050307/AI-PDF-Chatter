import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.reading_progress import ReadingProgressCreate, ReadingProgressResponse
from app.services.reading_progress_service import ReadingProgressService

router = APIRouter()


@router.get("/{document_id}/progress", response_model=ReadingProgressResponse)
async def get_reading_progress(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Retrieve current reading progress for a document."""
    service = ReadingProgressService(db)
    return await service.get_progress(current_user, document_id)


@router.post("/{document_id}/progress", response_model=ReadingProgressResponse)
async def update_reading_progress(
    document_id: uuid.UUID,
    progress_in: ReadingProgressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update reading position for a document."""
    service = ReadingProgressService(db)
    return await service.save_progress(current_user, document_id, progress_in)
