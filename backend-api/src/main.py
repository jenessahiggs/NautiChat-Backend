from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from .models import (
    CreateUserRequest,
    Message,
    Token,
    User,
    UserInDB,
    Conversation,
    Feedback,
)
from typing import Annotated, List, Optional

app = FastAPI()

# These routes acting as the server scaffolding, since they generate documentation automatically
# To be split into separate files later and actually implemented

############################################################
# Users / authentication
############################################################

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

FAKE_USER = UserInDB(
    user_id=1,
    username="account1",
    hashed_password="password1",
    onc_token="fakeONCtoken",
    is_admin=True,
)


def fake_decode_token(_token) -> UserInDB:
    return FAKE_USER


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    # For now always return a fake user
    user = fake_decode_token(token)
    return user


def get_admin_user(token: Annotated[str, Depends(oauth2_scheme)]) -> UserInDB:
    # For now always return an "admin user"
    user = fake_decode_token(token)
    return user


@app.post("/auth/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Login and return a token"""
    # Validate the user and return a token
    # For now just return a fake token every time
    return Token(access_token=form_data.username, token_type="bearer")


@app.post("/auth/register")
def register_user(user: CreateUserRequest) -> Token:
    """Register a new user"""
    # Save the user to the database
    # Do nothing right now because we allow all logins anyways
    return Token(access_token=user.username, token_type="bearer")


@app.get("/auth/me")
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get the current user"""
    # get_current_user is called automatically because of the Depends()
    return user


############################################################
# LLM API
############################################################


@app.post("/conversations", status_code=201)
def create_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    title: Optional[str] = None,
) -> Conversation:
    """Create a new conversation"""
    return Conversation(
        conversation_id=1, user_id=current_user.user_id, title=title, messages=[]
    )


@app.get("/conversations")
def get_conversations(
    current_user: Annotated[User, Depends(get_current_user)],
) -> List[Conversation]:
    """Get a list of the users conversations"""
    return [
        Conversation(
            conversation_id=1,
            user_id=current_user.user_id,
            title="Conversation 1",
            messages=[],
        ),
        Conversation(
            conversation_id=2,
            user_id=current_user.user_id,
            title="Conversation 2",
            messages=[],
        ),
    ]


@app.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Conversation:
    """Get a conversation"""
    return Conversation(
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        messages=[],
    )


@app.post("/messages")
def generate_response(
    input: str,
    conversation_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Message:
    """Get a response from the LLM"""
    return Message(
        message_id=1,
        conversation_id=conversation_id,
        user_id=current_user.user_id,
        input=input,
        response=f"Response for: {input}",
    )


@app.get("/messages/{message_id}")
def get_message(
    message_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Message:
    """Get a message"""
    return Message(
        message_id=message_id,
        conversation_id=1,
        user_id=current_user.user_id,
        input=f"Input for message {message_id}",
        response=f"Response for message {message_id}",
    )


@app.post("/messages/{message_id}/feedback")
def submit_feedback(
    message_id: int,
    feedback: Feedback,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Message:
    """Submit feedback for a message"""
    return Message(
        message_id=message_id,
        conversation_id=1,
        user_id=current_user.user_id,
        input=f"Input for message {message_id}",
        response=f"Response for message {message_id}",
        feedback=feedback,
    )


@app.get("/admin/messages")
def get_all_messages(
    current_user: Annotated[User, Depends(get_admin_user)],
) -> List[Message]:
    """Get all messages"""
    return [
        Message(
            message_id=1,
            conversation_id=1,
            user_id=current_user.user_id,
            input="Input for message 1",
            response="Response for message 1",
        ),
        Message(
            message_id=2,
            conversation_id=2,
            user_id=current_user.user_id,
            input="Input for message 2",
            response="Response for message 2",
        ),
    ]
