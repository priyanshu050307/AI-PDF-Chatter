import uuid
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation, ChatMessage, ChatMode
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Conversation, db)

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        title: str = "Document Chat",
        mode: ChatMode = ChatMode.RAG_CHAT
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            document_id=document_id,
            title=title,
            mode=mode
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_by_id_and_user_id(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Conversation]:
        """Fetch conversation by ID ensuring ownership, preloading chat messages."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalars().first()

    async def list_by_document_and_user(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[Conversation]:
        """List user conversations for a given document ordered by latest update."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.document_id == document_id, Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update_title(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str
    ) -> Optional[Conversation]:
        """Rename conversation title with strict ownership verification."""
        conv = await self.get_by_id_and_user_id(conversation_id, user_id)
        if not conv:
            return None

        conv.title = title
        conv.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """Delete conversation and cascading messages with strict ownership check."""
        conv = await self.get_by_id_and_user_id(conversation_id, user_id)
        if not conv:
            return False

        await self.db.delete(conv)
        await self.db.commit()
        return True

    async def get_paginated_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        before_id: Optional[uuid.UUID] = None
    ) -> Tuple[List[ChatMessage], int, bool, Optional[str]]:
        """
        Fetch paginated messages for a conversation ensuring ownership.
        Returns: (items, total_count, has_more, next_cursor)
        """
        conv = await self.get_by_id_and_user_id(conversation_id, user_id)
        if not conv:
            return [], 0, False, None

        # Total count query
        total_stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        total_res = await self.db.execute(total_stmt)
        total = total_res.scalar() or 0

        # Query messages
        query = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)

        if before_id:
            # Find timestamp of before_id message
            before_msg_res = await self.db.execute(
                select(ChatMessage.created_at).where(ChatMessage.id == before_id)
            )
            before_time = before_msg_res.scalar()
            if before_time:
                query = query.where(ChatMessage.created_at < before_time)

        # Fetch newest first then reverse for chronological order
        query = query.order_by(ChatMessage.created_at.desc()).limit(limit + 1)
        res = await self.db.execute(query)
        fetched_msgs = list(res.scalars().all())

        has_more = len(fetched_msgs) > limit
        if has_more:
            items = fetched_msgs[:limit]
        else:
            items = fetched_msgs

        # Chronological order
        items.reverse()
        next_cursor = str(items[0].id) if items and has_more else None

        return items, total, has_more, next_cursor

    async def update_summary(
        self,
        conversation_id: uuid.UUID,
        summary: str,
        summary_message_count: int
    ) -> bool:
        """
        Update conversation rolling summary atomically.
        Guarantees that a stale summary update (representing fewer messages)
        will not overwrite a newer summary (optimistic concurrency check).
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.summary_message_count <= summary_message_count
            )
            .values(
                summary=summary,
                summary_updated_at=now,
                summary_message_count=summary_message_count,
                updated_at=now
            )
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def add_message(
        self,
        conversation_id: uuid.UUID,
        sender: str,
        content: str,
        citations: Optional[list] = None,
        context_snapshot: Optional[dict] = None,
        token_usage: Optional[dict] = None
    ) -> ChatMessage:
        """Append a message to a conversation and touch conversation updated_at timestamp."""
        msg = ChatMessage(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            citations=citations or [],
            context_snapshot=context_snapshot or {},
            token_usage=token_usage or {}
        )
        self.db.add(msg)
        
        # Touch conversation updated_at
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
        return msg
