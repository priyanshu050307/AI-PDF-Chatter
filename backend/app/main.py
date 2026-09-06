from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.errors import AppException, app_exception_handler, unhandled_exception_handler
from app.api.v1 import health, auth, users, documents, reading_progress, conversations, highlights, tutor

from app.core.database import Base, engine
import app.models  # noqa: Ensure all models are registered

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode.")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info(f"Shutting down {settings.APP_NAME}.")


app = FastAPI(
    title=settings.APP_NAME,
    description="Context-Aware AI PDF Companion Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Mount API V1 routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(reading_progress.router, prefix="/api/v1/documents", tags=["Reading Progress"])
app.include_router(conversations.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(highlights.router, prefix="/api/v1", tags=["Highlights"])
app.include_router(tutor.router, prefix="/api/v1/tutor", tags=["Tutor & Study Mode"])

