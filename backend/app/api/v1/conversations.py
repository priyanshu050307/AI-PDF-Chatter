import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ChatMessageResponse,
    PaginatedMessagesResponse,
    SendMessageRequest
)
from app.services.rag_service import RAGService
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.core.errors import NotFoundError, ValidationError

router = APIRouter()


def _to_conversation_dict(conv) -> dict:
    """Helper to convert Conversation ORM model to dictionary avoiding lazy loading."""
    msgs = []
    if "messages" in conv.__dict__ and conv.__dict__["messages"]:
        for m in conv.__dict__["messages"]:
            msgs.append({
                "id": m.id,
                "conversation_id": m.conversation_id,
                "sender": m.sender,
                "content": m.content,
                "citations": m.citations or [],
                "context_snapshot": m.context_snapshot or {},
                "token_usage": m.token_usage or {},
                "created_at": m.created_at
            })

    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "document_id": conv.document_id,
        "title": conv.title,
        "mode": conv.mode.value if hasattr(conv.mode, "value") else str(conv.mode),
        "summary": conv.summary,
        "summary_updated_at": conv.summary_updated_at,
        "summary_message_count": conv.summary_message_count or 0,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "messages": msgs
    }


@router.post("/documents/{document_id}/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    document_id: uuid.UUID,
    body: ConversationCreate = ConversationCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_user_id(document_id, current_user.id)
    if not doc:
        raise NotFoundError(message=f"Document with ID {document_id} not found.")

    conv_repo = ConversationRepository(db)
    title = body.title or f"Chat on {doc.title[:30]}"
    conv = await conv_repo.create_conversation(current_user.id, document_id, title=title)
    return _to_conversation_dict(conv)


@router.get("/documents/{document_id}/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id_and_user_id(document_id, current_user.id)
    if not doc:
        raise NotFoundError(message=f"Document with ID {document_id} not found.")

    conv_repo = ConversationRepository(db)
    convs = await conv_repo.list_by_document_and_user(document_id, current_user.id)
    return [_to_conversation_dict(c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id_and_user_id(conversation_id, current_user.id)
    if not conv:
        raise NotFoundError(message=f"Conversation with ID {conversation_id} not found.")
    return _to_conversation_dict(conv)


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if not body.title or not body.title.strip():
        raise ValidationError(message="Title cannot be empty.")

    conv_repo = ConversationRepository(db)
    conv = await conv_repo.update_title(conversation_id, current_user.id, body.title.strip())
    if not conv:
        raise NotFoundError(message=f"Conversation with ID {conversation_id} not found.")
    return _to_conversation_dict(conv)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    conv_repo = ConversationRepository(db)
    deleted = await conv_repo.delete_conversation(conversation_id, current_user.id)
    if not deleted:
        raise NotFoundError(message=f"Conversation with ID {conversation_id} not found.")
    return None


@router.get("/conversations/{conversation_id}/messages", response_model=PaginatedMessagesResponse)
async def get_paginated_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[uuid.UUID] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    conv_repo = ConversationRepository(db)
    items, total, has_more, next_cursor = await conv_repo.get_paginated_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
        limit=limit,
        before_id=before
    )

    formatted_items = []
    for m in items:
        formatted_items.append({
            "id": m.id,
            "conversation_id": m.conversation_id,
            "sender": m.sender,
            "content": m.content,
            "citations": m.citations or [],
            "context_snapshot": m.context_snapshot or {},
            "token_usage": m.token_usage or {},
            "created_at": m.created_at
        })

    return {
        "items": formatted_items,
        "total": total,
        "has_more": has_more,
        "next_cursor": next_cursor
    }


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    if not body.content or not body.content.strip():
        raise ValidationError(message="Message content cannot be empty.")

    rag_service = RAGService(db)
    assistant_msg = await rag_service.execute_rag_completion(
        current_user=current_user,
        conversation_id=conversation_id,
        user_query=body.content.strip(),
        context_snapshot_req=body.context_snapshot,
        intent_req=body.intent
    )

    return {
        "id": assistant_msg.id,
        "conversation_id": assistant_msg.conversation_id,
        "sender": assistant_msg.sender,
        "content": assistant_msg.content,
        "citations": assistant_msg.citations or [],
        "context_snapshot": assistant_msg.context_snapshot or {},
        "token_usage": assistant_msg.token_usage or {},
        "created_at": assistant_msg.created_at
    }
