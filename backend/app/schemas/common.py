from typing import Optional, Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    database: str = "connected"


class StatusResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None
