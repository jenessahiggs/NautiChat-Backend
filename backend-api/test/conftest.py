from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from src.auth import models
from src.auth.dependencies import get_settings
from src.auth.service import create_access_token
from src.database import Base, get_db
from src.main import app
from typing import Iterator


@pytest.fixture()
def session() -> Iterator[Session]:
    """Return the test db session created for each test"""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(session) -> Iterator[TestClient]:
    """Return a test client which can be used to send api requests"""

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user_headers(session):
    """Return headers for a simple user"""

    test_user = models.User(
        username="testuser", hashed_password="nothashedpassword", onc_token="onctoken", is_admin=False
    )
    session.add(test_user)
    session.commit()
    session.refresh(test_user)

    settings = get_settings()
    token = create_access_token(test_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(session):
    """Return headers for an admin user"""

    admin_user = models.User(
        username="admin", hashed_password="nothashedpassword", onc_token="admintoken", is_admin=True
    )
    session.add(admin_user)
    session.commit()
    session.refresh(admin_user)

    settings = get_settings()
    token = create_access_token(admin_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings)
    return {"Authorization": f"Bearer {token}"}
