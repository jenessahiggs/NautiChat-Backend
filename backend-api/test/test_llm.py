import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.llm.models import Conversation, Message
from src.llm.utils import get_context


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, user_headers):
    # Payload for creating a conversation
    payload = {"title": "Test Conversation"}
    response = await client.post("/llm/conversations", json=payload, headers=user_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "conversation_id" in data
    assert isinstance(data["conversation_id"], int)


@pytest.mark.asyncio
async def test_get_conversations_empty(client: AsyncClient, user_headers):
    response = await client.get("/llm/conversations", headers=user_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_single_conversation(client: AsyncClient, user_headers):
    # Create a conversation
    post_response = await client.post("/llm/conversations", json={"title": "Conversation 1"}, headers=user_headers)
    conv_id = post_response.json()["conversation_id"]

    # Retrieve Conversation
    get_response = await client.get(f"/llm/conversations/{conv_id}", headers=user_headers)
    assert get_response.status_code == 200
    assert get_response.json()["conversation_id"] == conv_id
    assert get_response.json()["title"] == "Conversation 1"


@pytest.mark.asyncio
async def test_get_single_conversation_unauthorized(client: AsyncClient, user_headers):
    # Create user1 conversation
    response = await client.post("/llm/conversations", json={"title": "Conversation 2"}, headers=user_headers)
    conv_id = response.json()["conversation_id"]

    response2 = await client.post(
        "/auth/register", json={"username": "otheruser", "password": "pass", "onc_token": "abcdlmnop"}
    )
    token2 = response2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User2 tries to access user1's conversation
    response = await client.get(f"/llm/conversations/{conv_id}", headers=headers2)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_response(client: AsyncClient, user_headers):
    # Create conversation
    response = await client.post("/llm/conversations", json={"title": "Chatting"}, headers=user_headers)
    conv_id = response.json()["conversation_id"]

    # Send message
    payload = {"input": "Hello ChatBot", "conversation_id": conv_id}
    response = await client.post("/llm/messages", json=payload, headers=user_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["input"] == "Hello ChatBot"
    assert "LLM Response for" in data["response"]


@pytest.mark.asyncio
async def test_get_message(client: AsyncClient, user_headers):
    # Create a Conversation + message
    conversation = await client.post("/llm/conversations", json={"title": "Get Message"}, headers=user_headers)
    msg = await client.post(
        "/llm/messages",
        json={"input": "What is the weather?", "conversation_id": conversation.json()["conversation_id"]},
        headers=user_headers,
    )

    # Get message
    response = await client.get(f"/llm/messages/{msg.json()['message_id']}", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["message_id"] == msg.json()["message_id"]


@pytest.mark.asyncio
async def test_feedback_create_and_update(client: AsyncClient, user_headers):
    # Create conversation + message
    conversation = await client.post("/llm/conversations", json={"title": "Feedback Test"}, headers=user_headers)
    msg = await client.post(
        "/llm/messages",
        json={
            "input": "What is the temperature of Cambridge Bay?",
            "conversation_id": conversation.json()["conversation_id"],
        },
        headers=user_headers,
    )

    # Submit feedback
    fb = {"rating": 5, "comment": "Great response!"}
    response = await client.patch(f"/llm/messages/{msg.json()['message_id']}/feedback", json=fb, headers=user_headers)
    assert response.status_code == 200

    # Update feedback
    updated_fb = {"rating": 1, "comment": "Actually not helpful."}
    response = await client.patch(
        f"/llm/messages/{msg.json()['message_id']}/feedback", json=updated_fb, headers=user_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_context_no_messages(async_session: AsyncSession, user_headers):
    # When no messages in db, should return empty list

    # Add conversation
    users = await async_session.execute(select(User))
    user_in_db = users.scalars().first()
    assert user_in_db is not None
    new_conversation = Conversation(user_id=user_in_db.id)

    async_session.add(new_conversation)
    await async_session.commit()
    await async_session.refresh(new_conversation)

    context = await get_context(new_conversation.conversation_id, 500, async_session)
    assert len(context) == 0


@pytest.mark.asyncio
async def test_get_context(async_session: AsyncSession, user_headers):
    # Add conversation
    users = await async_session.execute(select(User))
    user_in_db = users.scalars().first()
    assert user_in_db is not None
    new_conversation = Conversation(user_id=user_in_db.id)

    async_session.add(new_conversation)
    await async_session.commit()
    await async_session.refresh(new_conversation)

    content_8 = "one two three four five six seven eight"
    content_3 = "one two three"

    message_20 = Message(
        conversation_id=new_conversation.conversation_id, user_id=user_in_db.id, input=content_8, response=content_8
    )  # 4 + 8 + 8 = 20 words
    message_15 = Message(
        conversation_id=new_conversation.conversation_id, user_id=user_in_db.id, input=content_8, response=content_3
    )  # 4 + 8 + 3 = 15 words

    async_session.add(message_20)
    async_session.add(message_15)
    await async_session.commit()
    await async_session.refresh(message_20)
    await async_session.refresh(message_15)
    await async_session.refresh(new_conversation)

    context_1 = await get_context(new_conversation.conversation_id, 30, async_session)
    assert len(context_1) == 2  # 1 for input and 1 for response

    context_2 = await get_context(new_conversation.conversation_id, 100, async_session)
    assert len(context_2) == 4
    assert isinstance(context_2[0]["role"], str)
    # most recent message should be returned first
    assert context_2[0]["role"] == "user"
    assert context_2[0]["content"] == message_15.input
    assert context_2[1]["role"] == "system"
    assert context_2[1]["content"] == message_15.response
