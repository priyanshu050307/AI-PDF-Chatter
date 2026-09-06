import json
import uuid
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class ChatIntent(str, Enum):
    QUESTION = "QUESTION"
    EXPLAIN = "EXPLAIN"
    SIMPLIFY = "SIMPLIFY"
    EXAMPLE = "EXAMPLE"


class SelectionContextSchema(BaseModel):
    selected_text: str
    page_number: int
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    bounding_box: Optional[Dict[str, float]] = None


class ContextSnapshotSchema(BaseModel):
    document_id: uuid.UUID
    page_number: int
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    selection: Optional[SelectionContextSchema] = None
    intent: Optional[ChatIntent] = ChatIntent.QUESTION


class CitationSchema(BaseModel):
    chunk_id: str
    page_start: int
    page_end: int
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: str
    content: str
    citations: Optional[List[CitationSchema]] = []
    context_snapshot: Optional[Dict[str, Any]] = {}
    token_usage: Optional[Dict[str, Any]] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("citations", mode="before")
    def parse_citations(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("context_snapshot", "token_usage", mode="before")
    def parse_json_dict(cls, v):
        if v is None:
            return {}
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class ConversationCreate(BaseModel):
    title: Optional[str] = "Document Chat"


class ConversationUpdate(BaseModel):
    title: str


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    title: str
    mode: str
    summary: Optional[str] = None
    summary_updated_at: Optional[datetime] = None
    summary_message_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("messages", mode="before")
    def parse_messages(cls, v):
        if v is None:
            return []
        return v


class PaginatedMessagesResponse(BaseModel):
    items: List[ChatMessageResponse]
    total: int
    has_more: bool
    next_cursor: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str
    context_snapshot: Optional[ContextSnapshotSchema] = None
    intent: Optional[ChatIntent] = ChatIntent.QUESTION
    stream: Optional[bool] = False
