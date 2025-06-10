from fastapi import APIRouter, Depends, HTTPException
from src.auth.dependencies import get_current_user

from sqlalchemy.orm import Session
from src.database import get_db

from typing import List, Annotated, Optional

from .schemas import Conversation, Message, Feedback
from src.auth.schemas import UserOut

from .models import Conversation as ConversationModel, Message as MessageModel, Feedback as FeedbackModel

router = APIRouter()


@router.post("/conversations", status_code=201, response_model=Conversation)
def create_conversation(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    title: Optional[str] = None,
) -> Conversation:
    """Create a new conversation"""
    conversation = ConversationModel(user_id=current_user.id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=List[Conversation])
def get_conversations(
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[Conversation]:
    """Get a list of the users conversations in descending order"""
    return (
        db.query(ConversationModel)
        .filter_by(user_id=current_user.id)
        .order_by(ConversationModel.conversation_id.desc())
        .all()
    )  # type: ignore


@router.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(
    conversation_id: int,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Conversation:
    """Get a conversation"""
    conversation = (
        db.query(ConversationModel).filter_by(user_id=current_user.id, conversation_id=conversation_id).first()
    )
    # Handle potential errors
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this conversation")
    return conversation


@router.post("/messages", status_code=201, response_model=Message)
def generate_response(
    input: str,
    conversation_id: int,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Message:
    # Validate whether converstation exists or if current user has access to conversation
    conversation = db.query(ConversationModel).filter_by(conversation_id=conversation_id).first()
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Invalid conversation access")

    """Get a response from the LLM"""
    message = MessageModel(
        conversation_id=conversation_id, user_id=current_user.id, input=input, response=f"LLM Response for: {input}"
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/messages/{message_id}", response_model=Message)
def get_message(
    message_id: int,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Message:
    """Get a message"""
    message = db.query(MessageModel).filter_by(message_id=message_id).first()
    # Handle potential errors
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this message")
    return message


@router.patch("/messages/{message_id}/feedback", response_model=Message)
def submit_feedback(
    message_id: int,
    feedback: Feedback,
    current_user: Annotated[UserOut, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Message:
    # Validate whether message exists or if current user has access to message
    message = db.query(MessageModel).filter_by(message_id=message_id).first()
    if not message or message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Invalid message access")

    """Submit feedback for a message"""
    # Check if feedback exists for this message
    existing_feedback = db.query(FeedbackModel).filter_by(message_id=message_id).first()

    if existing_feedback:
        # Update only fields that are provided in the request
        update_data = feedback.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_feedback, key, value)
    else:
        # Create new feedback entry
        new_feedback = FeedbackModel(message_id=message_id, **feedback.model_dump())
        db.add(new_feedback)

    db.commit()
    db.refresh(message)
    return message
