import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.reading_progress import ReadingProgressCreate, ReadingProgressResponse
from app.services.reading_progress_service import ReadingProgressService

router = APIRouter()
logger = logging.getLogger("pdfchatter")


@router.get("/{document_id}/progress", response_model=ReadingProgressResponse)
async def get_reading_progress(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Retrieve current reading progress for a document."""
    service = ReadingProgressService(db)
    try:
        return await service.get_progress(current_user, document_id)
    except Exception as e:
        logger.warning(f"Failed to fetch reading progress for doc {document_id}: {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        return ReadingProgressResponse(
            id=uuid.uuid4(),
            user_id=current_user.id,
            document_id=document_id,
            current_page=1,
            scroll_position_pct=0.0,
            last_opened_at=datetime.now(timezone.utc),
        )


@router.post("/{document_id}/progress", response_model=ReadingProgressResponse)
async def update_reading_progress(
    document_id: uuid.UUID,
    progress_in: ReadingProgressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update reading position for a document. Non-critical — never returns 500."""
    service = ReadingProgressService(db)
    try:
        return await service.save_progress(current_user, document_id, progress_in)
    except OperationalError as e:
        # SQLite may be busy/locked when concurrent requests fire simultaneously
        logger.warning(f"Reading progress save skipped (DB busy): {e}")
        try:
            await db.rollback()
        except Exception:
            pass
        try:
            return await service.get_progress(current_user, document_id)
        except Exception:
            try:
                await db.rollback()
            except Exception:
                pass
            return ReadingProgressResponse(
                id=uuid.uuid4(),
                user_id=current_user.id,
                document_id=document_id,
                current_page=progress_in.current_page,
                scroll_position_pct=progress_in.scroll_position_pct,
                last_opened_at=datetime.now(timezone.utc),
            )
    except Exception as e:
        logger.error(f"Reading progress save failed unexpectedly: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        return ReadingProgressResponse(
            id=uuid.uuid4(),
            user_id=current_user.id,
            document_id=document_id,
            current_page=progress_in.current_page,
            scroll_position_pct=progress_in.scroll_position_pct,
            last_opened_at=datetime.now(timezone.utc),
        )



