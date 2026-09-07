"""FastAPI router for Operational Monitoring & Infrastructure Metrics."""

import time
import os
try:
    import psutil
except ImportError:
    psutil = None
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
START_TIME = time.time()


@router.get("/health", summary="Get operational infrastructure monitoring metrics")
async def get_operational_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns operational metrics including uptime, CPU/RAM usage, DB pool status, and Redis connection state."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    
    if psutil:
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            sys_resources = {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "process_memory_mb": round(mem_info.rss / (1024 * 1024), 2),
                "system_memory_percent": psutil.virtual_memory().percent
            }
        except Exception:
            sys_resources = {"cpu_percent": 0.0, "process_memory_mb": 0.0, "system_memory_percent": 0.0}
    else:
        sys_resources = {"cpu_percent": 0.0, "process_memory_mb": 0.0, "system_memory_percent": 0.0}

    # DB Pool Check
    db_ok = False
    try:
        res = await db.execute(text("SELECT 1"))
        db_ok = (res.scalar() == 1)
    except Exception:
        db_ok = False

    # Redis Ping Check
    redis_ok = False
    try:
        from app.core.rate_limit import get_redis_client
        redis = await get_redis_client()
        if redis:
            redis_ok = await redis.ping()
    except Exception:
        redis_ok = False

    return {
        "status": "operational" if db_ok else "degraded",
        "uptime_seconds": uptime_seconds,
        "environment": settings.APP_ENV,
        "system_resources": sys_resources,
        "infrastructure": {
            "database_connected": db_ok,
            "redis_connected": redis_ok,
            "storage_backend": settings.STORAGE_BACKEND,
            "llm_provider": settings.LLM_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER
        }
    }
