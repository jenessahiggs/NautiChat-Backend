from typing import List

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.auth.models import User
from src.llm import schemas
from src.llm.models import Conversation, Message


def test_admin_endpoint_unauthenticated(client: TestClient):
    response = client.get("/admin/messages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_endpoint_as_user(client: TestClient, user_headers):
    response = client.get("/admin/messages", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_endpoint_as_admin(client: TestClient, session: Session, admin_headers):
    # add 2 users
    user1 = User(username="user1", hashed_password="hpw1", onc_token="token1")
    user2 = User(username="user2", hashed_password="hpw2", onc_token="token2")
    session.add_all([user1, user2])
    session.commit()
    session.refresh(user1)
    session.refresh(user2)

    # add 2 conversations
    conv1 = Conversation(user=user1, title="conv 1")
    conv2 = Conversation(user=user2, title="conv 2")
    session.add_all([conv1, conv2])
    session.commit()
    session.refresh(conv1)
    session.refresh(conv2)

    # add 2 messages
    message1 = Message(conversation=conv1, user_id=user1.id, input="hello from 1", response="response 1")
    message2 = Message(conversation=conv2, user_id=user2.id, input="hello from 2", response="response 2")
    session.add_all([message1, message2])
    session.commit()
    session.refresh(message1)
    session.refresh(message2)

    response = client.get("/admin/messages", headers=admin_headers)
    assert response.status_code == 200
    data: List = response.json()
    assert len(data) == 2
    # recent messages first
    assert schemas.Message.model_validate(data[0]).conversation_id == message2.conversation_id
    assert schemas.Message.model_validate(data[1]).conversation_id == message1.conversation_id
