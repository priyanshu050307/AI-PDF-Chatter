import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: Register all ORM models with Base.metadata
import app.core.database as app_db
import app.api.v1.documents as app_docs
import app.workers.tasks as app_tasks
from app.main import app
from app.core.database import Base, get_async_db
from app.core.config import settings
from app.workers.celery_app import celery_app

# Force mock providers for automated unit tests unless overridden
settings.EMBEDDING_PROVIDER = "mock"
settings.LLM_PROVIDER = "mock"
settings.VISION_PROVIDER = "mock"
settings.OCR_PROVIDER = "mock"
celery_app.conf.task_always_eager = True

from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_suite.db"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    poolclass=NullPool,
)


@event.listens_for(engine_test.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.close()

TestingSessionLocal = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Patch AsyncSessionLocal so background processing tasks run against the test SQLite DB
app_db.AsyncSessionLocal = TestingSessionLocal
app_docs.AsyncSessionLocal = TestingSessionLocal
app_tasks.AsyncSessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Create fresh tables and clear data between tests."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


async def override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_async_db] = override_get_async_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def user_a_headers(client: AsyncClient) -> dict:
    email = "usera@example.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "User A"
    })
    if signup_res.status_code == 201:
        token = signup_res.json()["access_token"]
    else:
        login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"})
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_b_headers(client: AsyncClient) -> dict:
    email = "userb@example.com"
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": "Password123!",
        "full_name": "User B"
    })
    if signup_res.status_code == 201:
        token = signup_res.json()["access_token"]
    else:
        login_res = await client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"})
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
