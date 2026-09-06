import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ReadingProgressCreate(BaseModel):
    current_page: int = Field(1, ge=1, description="1-indexed current reading page")
    scroll_position_pct: float = Field(0.0, ge=0.0, le=100.0, description="Vertical scroll percentage (0 to 100)")


class ReadingProgressResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    current_page: int
    scroll_position_pct: float
    last_opened_at: datetime

    model_config = {"from_attributes": True}
