import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.highlight_repository import HighlightRepository
from app.schemas.annotation import (
    HighlightCreate,
    HighlightUpdate,
    HighlightResponse,
    HighlightListResponse
)

router = APIRouter()


@router.post("/documents/{document_id}/highlights", response_model=HighlightResponse, status_code=status.HTTP_201_CREATED)
async def create_highlight(
    document_id: uuid.UUID,
    payload: HighlightCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_user_id(document_id, current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found or access denied."}
        )

    if doc.page_count > 0 and payload.page_number > doc.page_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAGE", "message": f"Page number {payload.page_number} exceeds document total page count {doc.page_count}."}
        )

    highlight_repo = HighlightRepository(db)
    highlight = await highlight_repo.create_highlight(
        user_id=current_user.id,
        document_id=document_id,
        data=payload
    )
    return highlight


@router.get("/documents/{document_id}/highlights", response_model=HighlightListResponse)
async def list_highlights(
    document_id: uuid.UUID,
    page_number: Optional[int] = Query(None, ge=1),
    color: Optional[str] = Query(None),
    has_note: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_user_id(document_id, current_user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found or access denied."}
        )

    highlight_repo = HighlightRepository(db)
    items = await highlight_repo.list_highlights(
        user_id=current_user.id,
        document_id=document_id,
        page_number=page_number,
        color=color,
        has_note=has_note,
        search_query=search
    )
    return HighlightListResponse(items=items, total=len(items))


@router.get("/highlights/{highlight_id}", response_model=HighlightResponse)
async def get_highlight(
    highlight_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    highlight_repo = HighlightRepository(db)
    highlight = await highlight_repo.get_highlight(highlight_id, current_user.id)
    if not highlight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HIGHLIGHT_NOT_FOUND", "message": "Highlight not found or access denied."}
        )
    return highlight


@router.patch("/highlights/{highlight_id}", response_model=HighlightResponse)
async def update_highlight(
    highlight_id: uuid.UUID,
    payload: HighlightUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    highlight_repo = HighlightRepository(db)
    highlight = await highlight_repo.update_highlight(
        highlight_id=highlight_id,
        user_id=current_user.id,
        color=payload.color,
        note_text=payload.note_text
    )
    if not highlight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HIGHLIGHT_NOT_FOUND", "message": "Highlight not found or access denied."}
        )
    return highlight


@router.delete("/highlights/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    highlight_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    highlight_repo = HighlightRepository(db)
    deleted = await highlight_repo.delete_highlight(highlight_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "HIGHLIGHT_NOT_FOUND", "message": "Highlight not found or access denied."}
        )
    return None
