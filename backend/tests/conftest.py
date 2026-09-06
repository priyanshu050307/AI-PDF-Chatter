import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: Register all ORM models with Base.metadata
from app.main import app
from app.core.database import Base, get_async_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(autouse=True)
async def setup_test_db():
    """Create fresh tables for every test."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_async_db] = override_get_async_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def user_a_headers(client: AsyncClient) -> dict:
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": "usera@example.com",
        "password": "Password123!",
        "full_name": "User A"
    })
    token = signup_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def user_b_headers(client: AsyncClient) -> dict:
    signup_res = await client.post("/api/v1/auth/signup", json={
        "email": "userb@example.com",
        "password": "Password123!",
        "full_name": "User B"
    })
    token = signup_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
