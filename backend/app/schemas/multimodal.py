from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MultimodalEvidence(BaseModel):
    """Typed representation of retrieved multimodal evidence (text, table, image, ocr_text)."""

    element_id: Optional[str] = None
    type: str = Field(..., description="Modality type: text, table, image, ocr_text")
    document_id: str
    page_number: int
    bbox: Optional[Dict[str, float]] = None
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    image_storage_key: Optional[str] = None
    ocr_confidence: Optional[float] = None
    score: float = 0.0


class DocumentElementResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    element_type: str
    bbox_json: Optional[Dict[str, float]] = None
    content: str
    structured_data: Optional[Dict[str, Any]] = None
    image_storage_key: Optional[str] = None
    ocr_confidence: Optional[float] = None
    created_at: str
