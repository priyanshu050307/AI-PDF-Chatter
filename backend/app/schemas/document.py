import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import DocumentStatus
from app.schemas.reading_progress import ReadingProgressResponse


class DocumentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    original_filename: str
    file_size_bytes: int
    page_count: int
    processing_status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    progress: Optional[ReadingProgressResponse] = None

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    storage_key: str
