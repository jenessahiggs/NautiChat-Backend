def test_create_converstation(client, user_headers):
    # Payload for creating a conversation
    payload = {"title": "Test Conversation"}
    response = client.post("/llm/conversations", params=payload, headers=user_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Conversation"
    assert "conversation_id" in data
    assert isinstance(data["conversation_id"], int)


def test_get_conversations_empty(client, user_headers):
    response = client.get("/llm/conversations", headers=user_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_single_conversation(client, user_headers):
    # Create a conversation
    post_response = client.post("/llm/conversations", params={"title": "Conversation 1"}, headers=user_headers)
    conv_id = post_response.json()["conversation_id"]

    # Retrieve Conversation
    get_response = client.get(f"/llm/conversations/{conv_id}", headers=user_headers)
    assert get_response.status_code == 200
    assert get_response.json()["conversation_id"] == conv_id
    assert get_response.json()["title"] == "Conversation 1"


def test_get_single_conversation_unauthorized(client, user_headers):
    # Create user1 conversation
    response = client.post("/llm/conversations", params={"title": "Conversation 2"}, headers=user_headers)
    conv_id = response.json()["conversation_id"]

    response2 = client.post(
        "/auth/register", json={"username": "otheruser", "password": "pass", "onc_token": "abcdlmnop"}
    )
    token2 = response2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User2 tries to access user1's conversation
    response = client.get(f"/llm/conversations/{conv_id}", headers=headers2)
    assert response.status_code == 404


def test_generate_response(client, user_headers):
    # Create conversation
    response = client.post("/llm/conversations", params={"title": "Chatting"}, headers=user_headers)
    conv_id = response.json()["conversation_id"]

    # Send message
    payload = {"input": "Hello ChatBot", "conversation_id": conv_id}
    response = client.post("/llm/messages", params=payload, headers=user_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["input"] == "Hello ChatBot"
    assert "LLM Response for" in data["response"]


def test_get_message(client, user_headers):
    # Create a Conversation + message
    conversation = client.post("/llm/conversations", params={"title": "Get Message"}, headers=user_headers).json()
    msg = client.post(
        "/llm/messages",
        params={"input": "What is the weather?", "conversation_id": conversation["conversation_id"]},
        headers=user_headers,
    ).json()

    # Get message
    response = client.get(f"/llm/messages/{msg['message_id']}", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["message_id"] == msg["message_id"]


def test_feedback_create_and_update(client, user_headers):
    # Create conversation + message
    conversation = client.post("/llm/conversations", params={"title": "Feedback Test"}, headers=user_headers).json()
    msg = client.post(
        "/llm/messages",
        params={
            "input": "What is the temperature of Cambridge Bay?",
            "conversation_id": conversation["conversation_id"],
        },
        headers=user_headers,
    ).json()

    # Submit feedback
    fb = {"rating": 5, "comment": "Great response!"}
    response = client.patch(f"/llm/messages/{msg['message_id']}/feedback", json=fb, headers=user_headers)
    assert response.status_code == 200

    # Update feedback
    updated_fb = {"rating": 1, "comment": "Actually not helpful."}
    response = client.patch(f"/llm/messages/{msg['message_id']}/feedback", json=updated_fb, headers=user_headers)
    assert response.status_code == 200
