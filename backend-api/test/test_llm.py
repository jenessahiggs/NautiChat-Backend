import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.auth import service
from src.database import get_conv_db, ConvBase
from src.llm.models import Conversation, Message, Feedback

import os
from pathlib import Path

############################################################
# Initial Test Database Setup
############################################################

# Get path to where this current file exists
BASE_DIR = Path(__file__).resolve().parent

TEST_DB_PATH = BASE_DIR / "test.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create Test Tables (using ConvBase we copy its tables into this new db)
ConvBase.metadata.create_all(bind=test_engine)

# Dependency Override
def override_get_conv_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_conv_db] = override_get_conv_db

client = TestClient(app)

############################################################
# Pytest Fixture Setup for all Tests
############################################################

# Automatically create and Clean-up DB before/after each test
@pytest.fixture(autouse=True)
def reset_test_db():
    ConvBase.metadata.drop_all(bind=test_engine)
    ConvBase.metadata.create_all(bind=test_engine)
    yield
    ConvBase.metadata.drop_all(bind=test_engine)

# Delete the test.db file at the end of the test session
@pytest.fixture(scope="session", autouse=True)
def delete_test_db():
    yield
    # Ensure all connections are closed
    test_engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

@pytest.fixture(autouse=True)
def clear_fake_user_db():
    service.FAKE_USERS_DB.clear()

@pytest.fixture()
def auth_headers():
    """Register and log in a test user to get a valid auth token"""
    test_user = {
        "username": "testuser",
        "password": "password1",
        "onc_token": "abcd1234"
    }

    client.post("/auth/register", json=test_user)

    # login to get token
    response = client.post(
        "/auth/login",
        data={"username": test_user["username"], "password": test_user["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

############################################################
# Endpoint Testing
############################################################

def test_create_converstation(auth_headers):

    # Payload for creating a conversation
    payload = {"title": "Test Conversation"}
    response = client.post("/llm/conversations", params=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "conversation_id" in data
    assert isinstance(data["conversation_id"], int)

def test_get_conversations_empty(auth_headers):
    response = client.get("/llm/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

def test_get_single_conversation(auth_headers):
    # Create a conversation
    post_response = client.post("/llm/conversations", params={"title": "Conversation 1"}, headers=auth_headers)
    conv_id = post_response.json()["conversation_id"]

    # Retrieve Conversation
    get_response = client.get(f"/llm/conversations/{conv_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["conversation_id"] == conv_id
    assert get_response.json()["title"] == "Conversation 1"

def test_get_single_conversation_unauthorized(auth_headers):
    # Create user1 conversation
    response = client.post("/llm/conversations", params={"title": "Conversation 2"}, headers=auth_headers)
    conv_id = response.json()["conversation_id"]

    response2 = client.post("/auth/register", json={
        "username": "otheruser",
        "password": "pass",
        "onc_token": "abcdlmnop"
    })
    token2 = response2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User2 tries to access user1's conversation
    response = client.get(f"/llm/conversations/{conv_id}", headers=headers2)
    assert response.status_code == 404

def test_generate_response(auth_headers):
    # Create conversation
    response = client.post("/llm/conversations", params={"title": "Chatting"}, headers=auth_headers)
    conv_id = response.json()["conversation_id"]

    # Send message
    payload = {"input": "Hello ChatBot", "conversation_id": conv_id}
    response = client.post("/llm/messages", params=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["input"] == "Hello ChatBot"
    assert "LLM Response for" in data["response"]

def test_get_message(auth_headers):
    # Create a Conversation + message
    conversation = client.post("/llm/conversations", params={"title": "Get Message"}, headers=auth_headers).json()
    msg = client.post("/llm/messages", params={
        "input": "What is the weather?",
        "conversation_id": conversation["conversation_id"]
    }, headers=auth_headers).json()

    # Get message
    response = client.get(f"/llm/messages/{msg['message_id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["message_id"] == msg["message_id"]

def test_feedback_create_and_update(auth_headers):
    # Create conversation + message
    conversation = client.post("/llm/conversations", params={"title": "Feedback Test"}, headers=auth_headers).json()
    msg = client.post("/llm/messages", params={
        "input": "What is the temperature of Cambridge Bay?",
        "conversation_id": conversation["conversation_id"]
    }, headers=auth_headers).json()

    # Submit feedback
    fb = {"rating": 5, "comment": "Great response!"}
    response = client.patch(f"/llm/messages/{msg['message_id']}/feedback", json=fb, headers=auth_headers)
    assert response.status_code == 200

    # Update feedback
    updated_fb = {"rating": 1, "comment": "Actually not helpful."}
    response = client.patch(f"/llm/messages/{msg['message_id']}/feedback", json=updated_fb, headers=auth_headers)
    assert response.status_code == 200