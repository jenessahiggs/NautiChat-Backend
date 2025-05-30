from fastapi import Depends, FastAPI
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import (
    CreateUserRequest,
    Token,
    User,
    UserInDB,
)
from typing import Annotated, List, Optional
from src.llm.router import router as llm_router

app = FastAPI()
app.include_router(llm_router, prefix="/llm")



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
