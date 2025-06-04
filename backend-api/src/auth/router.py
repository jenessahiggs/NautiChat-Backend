from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from . import config, service
from .dependencies import get_current_user, get_settings
from .schemas import CreateUserRequest, Token, User

router = APIRouter()


@router.post("/login")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Annotated[config.Settings, Depends(get_settings)],
) -> Token:
    return service.login_user(form_data, settings)


@router.post("/register")
def register_user(
    user: CreateUserRequest, settings: Annotated[config.Settings, Depends(get_settings)]
) -> Token:
    return service.register_user(user, settings)


@router.get("/me")
def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get the current user"""
    # get_current_user is called automatically because of the Depends()
    return user
