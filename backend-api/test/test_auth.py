from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.auth import models, schemas
from src.auth.service import get_password_hash


def test_register_new_user(client: TestClient, session: Session):
    new_username = "lebron"
    new_user = schemas.CreateUserRequest(username="lebron", password="cavs", onc_token="lebrontoken")
    response = client.post("/auth/register", json=new_user.model_dump())

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)

    # get created user in db
    user_query = session.query(models.User)
    assert user_query.count() == 1
    added_user: models.User = user_query.first()
    assert added_user is not None
    assert added_user.username == new_username
    assert added_user.id == 1
    assert not added_user.is_admin


def test_register_existing_user(client: TestClient, session: Session):
    # add a user
    existing_user = models.User(username="lebron", hashed_password="cavs", onc_token="lebrontoken")
    session.add(existing_user)
    session.commit()
    session.refresh(existing_user)

    user_attempt = schemas.CreateUserRequest(
        username=existing_user.username, password="differentpassword", onc_token="differenttoken"
    )
    response = client.post("/auth/register", json=user_attempt.model_dump())

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert session.query(models.User).count() == 1, "duplicate user was added"


def test_get_me_unauthorized(client: TestClient):
    unauthenticated_response = client.get("/auth/me")
    assert unauthenticated_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_me_endpoint(client: TestClient, session: Session, user_headers):
    # at this point only one user in db, so current user should be that one
    response = client.get("/auth/me", headers=user_headers)

    assert response.status_code == status.HTTP_200_OK
    returned_user = schemas.UserOut.model_validate(response.json())

    db_user = session.query(models.User).first()
    assert db_user is not None

    # compare pydantic models
    assert returned_user == schemas.UserOut.model_validate(db_user)


def test_login_existing_user(client: TestClient, session: Session):
    # add user. since adding directly to db the password is not hashed which is easier for testing
    password = "supersecure"
    user = models.User(username="new user", hashed_password=get_password_hash(password), onc_token="newtoken")
    session.add(user)
    session.commit()
    session.refresh(user)

    response = client.post(
        "/auth/login",
        data={"username": user.username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)


def test_login_invalid_user(client: TestClient):
    # add user. since adding directly to db the password is not hashed which is easier for testing

    response = client.post(
        "/auth/login",
        data={"username": "invaliduser", "password": "somepassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
