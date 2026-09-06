import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

HighlightColor = Literal["yellow", "green", "blue", "pink", "purple"]


class BoundingBoxRect(BaseModel):
    x: float
    y: float
    width: float
    height: float


class BoundingBoxPayload(BaseModel):
    # Normalized page-relative coordinates (0.0 to 1.0 or page points)
    x: float
    y: float
    width: float
    height: float
    page_width: Optional[float] = None
    page_height: Optional[float] = None
    rects: Optional[List[BoundingBoxRect]] = None


class HighlightCreate(BaseModel):
    page_number: int = Field(..., ge=1, description="1-indexed PDF page number")
    selected_text: str = Field(..., min_length=1, max_length=5000, description="Selected passage text")
    start_offset: int = Field(0, ge=0, description="Character start offset")
    end_offset: int = Field(0, ge=0, description="Character end offset")
    color: HighlightColor = Field("yellow", description="Controlled highlight color")
    note_text: Optional[str] = Field(None, max_length=2000, description="Optional user note")
    bounding_box: Optional[Dict[str, Any]] = Field(None, description="Page-relative positional bounds")
    chapter_title: Optional[str] = Field(None, max_length=255)
    section_title: Optional[str] = Field(None, max_length=255)


class HighlightUpdate(BaseModel):
    color: Optional[HighlightColor] = None
    note_text: Optional[str] = Field(None, max_length=2000)


class HighlightResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    selected_text: str
    start_offset: int
    end_offset: int
    color: str
    note_text: Optional[str] = None
    bounding_box: Optional[Dict[str, Any]] = None
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HighlightListResponse(BaseModel):
    items: List[HighlightResponse]
    total: int
