from enum import Enum
from typing import List

from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.llm.models import Conversation, Message


# Pydantic models for better autocomplete within this file. Could be nice for AI LLM code to also use pydantic models
class Role(str, Enum):
    user = "user"
    system = "system"


class MessageContext(BaseModel):
    role: Role
    content: str


async def get_context(conversation_id: int, max_words: int, db: Session) -> List[dict]:
    """Return a list of messages for the LLM to use as context"""

    conversation = db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()
    assert conversation, "Invalid conversation id"

    # most recent messages first
    messages: List[Message] = conversation.messages[::-1]
    context: List[MessageContext] = []

    context_words = 0

    for message in messages:
        message_words = (
            4 + len(message.input.split()) + len(message.response.split())
        )  # extra words for "role", "content"
        if context_words + message_words < max_words:
            context.append(MessageContext(role=Role.user, content=message.input))
            context.append(MessageContext(role=Role.system, content=message.response))
            context_words += message_words
        else:
            break

    return [model.model_dump(mode="json") for model in context]
