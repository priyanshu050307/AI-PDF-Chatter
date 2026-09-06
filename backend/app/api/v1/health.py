from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_async_db)):
    """Health check endpoint verifying API service and database connectivity."""
    db_status = "disconnected"
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=db_status
    )


@router.get("/ai/health")
async def ai_health_check():
    """Health check endpoint verifying configured LLM and Embedding provider availability."""
    from app.services.ai_service import get_ai_service
    from app.services.embedding_service import get_embedding_service
    from app.core.config import settings

    ai_service = get_ai_service()
    embedding_service = get_embedding_service()

    ai_health = await ai_service.health_check()
    emb_health = await embedding_service.health_check()

    is_healthy = ai_health.get("available", False) and emb_health.get("available", False)

    return {
        "status": "healthy" if is_healthy else "degraded",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "llm_health": ai_health,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
        "embedding_health": emb_health,
    }

