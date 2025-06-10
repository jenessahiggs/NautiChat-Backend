from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth.dependencies import get_admin_user
from src.auth.schemas import UserOut
from src.database import get_db
from src.llm import models, schemas

router = APIRouter()


@router.get("/messages")
def get_all_messages(
    _: Annotated[UserOut, Depends(get_admin_user)], db: Annotated[Session, Depends(get_db)]
) -> List[schemas.Message]:
    """Get all messages"""
    # TODO: add pagination to this in case there are tons of messages

    return db.query(models.Message).order_by(models.Message.message_id.desc()).all()  # type: ignore
