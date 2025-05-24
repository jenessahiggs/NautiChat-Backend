from pydantic import BaseModel, Field
from typing import Annotated, Optional

############################################################
# Users / authentication
############################################################


# Data safe to return to user
class User(BaseModel):
    id: int
    username: str
    onc_token: str
    is_admin: bool = False


class UserInDB(User):
    hashed_password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    onc_token: str


class Token(BaseModel):
    access_token: str
    token_type: str


############################################################
# LLM
############################################################


class Feedback(BaseModel):
    rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    response: Optional[str] = None


class Message(BaseModel):
    response_id: int
    conversation_id: int
    user_id: int
    input: str
    response: str
    feedback: Optional[Feedback] = None


class Conversation(BaseModel):
    conversation_id: int
    user_id: int
    title: Optional[str] = None
    messages: list[Message] = []
