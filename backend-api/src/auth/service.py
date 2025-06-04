from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from . import config
from .schemas import CreateUserRequest, Token, UserInDB

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


FAKE_USER1 = UserInDB(
    user_id=1,
    username="user1",
    onc_token="fake_token",
    hashed_password=get_password_hash("password1"),
    is_admin=False,
)

FAKE_USER2 = UserInDB(
    user_id=2,
    username="user2",
    onc_token="fake_token2",
    hashed_password=get_password_hash("password2"),
    is_admin=True,
)

FAKE_USERS_DB = {}
FAKE_USERS_DB.update(
    {"user1": FAKE_USER1.model_dump(), "user2": FAKE_USER2.model_dump()}
)


def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)


def create_access_token(
    username: str,
    expires_delta: timedelta,
    settings: config.Settings,
) -> str:
    """Create a JWT access token for the given username with an expiration time."""
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def register_user(user_register: CreateUserRequest, settings: config.Settings) -> Token:
    """Register a new user"""

    # check that the user does not already exist
    existing_user = get_user(FAKE_USERS_DB, user_register.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # create a new user
    new_user = UserInDB(
        user_id=len(FAKE_USERS_DB) + 1,
        username=user_register.username,
        onc_token=user_register.onc_token,
        hashed_password=get_password_hash(user_register.password),
        is_admin=False,
    )
    FAKE_USERS_DB[new_user.username] = new_user.model_dump()

    token = create_access_token(
        new_user.username, timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS), settings
    )
    return Token(access_token=token, token_type="bearer")


def get_user_by_token(
    token: str,
    settings: config.Settings,
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(FAKE_USERS_DB, username)
    if user is None:
        raise credentials_exception
    return user


def login_user(
    form_data: OAuth2PasswordRequestForm,
    settings: config.Settings,
) -> Token:
    """Login and return a token"""
    invalid_credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # check that the user actually exists
    matched_user = get_user(FAKE_USERS_DB, form_data.username)
    if not matched_user:
        raise invalid_credentials_exception
    # check that the password is correct
    if not verify_password(form_data.password, matched_user.hashed_password):
        raise invalid_credentials_exception

    # create a new token
    token = create_access_token(
        matched_user.username,
        timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
        settings,
    )

    return Token(access_token=token, token_type="bearer")
