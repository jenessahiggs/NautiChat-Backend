import os
import pytest
import asyncio
import pytest_asyncio

from datetime import timedelta
from typing import AsyncIterator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import StaticPool

# Set up test DB URL
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
DATABASE_URL = os.environ["DATABASE_URL"]

# Must be imported after setting DATABASE_URL
from src.database import sessionmanager, Base, get_db_session
from src.auth import models
from src.auth.service import create_access_token
from src.main import create_app


@pytest_asyncio.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest_asyncio.fixture()
async def async_session() -> AsyncIterator[AsyncSession]:
    """Return the async test db session created for each test"""
    engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

@pytest_asyncio.fixture()
async def client(async_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Return a test client which can be used to send api requests"""

    async def override_get_db():
        yield async_session

    test_app = create_app()

    # Disable middleware unless @pytest.mark.use_middleware
    if request.node.get_closest_marker("use_middleware") is None:
        test_app.user_middleware = []

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture()
async def user_headers(async_session: AsyncSession):
    """Return headers for a simple user"""

    test_user = models.User(
        username="testuser", hashed_password="nothashedpassword", onc_token="onctoken", is_admin=False
    )

    async_session.add(test_user)
    await async_session.commit()
    await async_session.refresh(test_user)

    settings = get_settings()
    token = create_access_token(test_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)

    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture()
async def admin_headers(async_session: AsyncSession):
    """Return headers for an admin user"""

    admin_user = models.User(
        username="admin", hashed_password="nothashedpassword", onc_token="admintoken", is_admin=True
    )

    async_session.add(admin_user)
    await async_session.commit()
    await async_session.refresh(admin_user)

    settings = get_settings()
    token = create_access_token(admin_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)

    return {"Authorization": f"Bearer {token}"}

