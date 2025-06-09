from pydantic import BaseModel, ConfigDict


# Data safe to return to user
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    onc_token: str
    is_admin: bool = False


class CreateUserRequest(BaseModel):
    username: str
    password: str
    onc_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
