from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session

from src.llm import models, schemas
from typing import List


def test_admin_endpoint_unauthenticated(client: TestClient):
    response = client.get("/admin/messages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_endpoint_as_user(client: TestClient, user_headers):
    response = client.get("/admin/messages", headers=user_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_endpoint_as_admin(client: TestClient, session: Session, admin_headers):
    # add 2 conversations
    conv1 = models.Conversation(user_id=1, title="conv 1")
    conv2 = models.Conversation(user_id=2, title="conv 2")
    session.add_all([conv1, conv2])
    session.commit()
    session.refresh(conv1)
    session.refresh(conv2)

    message1 = models.Message(conversation_id=1, user_id=1, input="hello from 1", response="response 1")
    message2 = models.Message(conversation_id=2, user_id=2, input="hello from 2", response="response 2")
    session.add_all([message1, message2])
    session.commit()

    response = client.get("/admin/messages", headers=admin_headers)
    assert response.status_code == 200
    data: List = response.json()
    assert len(data) == 2
    assert schemas.Message.model_validate(data[0]).user_id == 2
    assert schemas.Message.model_validate(data[1]).user_id == 1
