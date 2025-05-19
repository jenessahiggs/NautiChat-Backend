from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Annotated, List, Optional

app = FastAPI()

# These routes acting as the server scaffolding, since they generate documentation automatically
# To be split into separate files later and actually implemented

############################################################
# LLM API
############################################################


class Feedback(BaseModel):
    rating: Annotated[int, Field(strict=True, ge=1, le=5)]
    response: str


class LLMResponse(BaseModel):
    response_id: int
    user_id: int
    input: str
    response: str
    feedback: Optional[Feedback] = None


@app.get("/responses/generate")
def generate_response(input: str):
    """Get a response from the LLM"""
    # Might have to return some kind of id for a response so that it can be referred to for feedback
    return {"id": 1, "response": f"Response for: {input}"}


@app.get("/responses")
def get_responses(user_id: Optional[int] = None) -> List[LLMResponse]:
    """Get a list of responses"""
    # If we are a normal user, we should only be able to see our own responses
    # Admin might want to be able to see all responses
    sample_feedback = Feedback(rating=5, response="Great response!")
    return [
        LLMResponse(
            response_id=1,
            user_id=1,
            input="Sample input",
            response="Sample response",
            feedback=sample_feedback,
        ),
        LLMResponse(
            response_id=2,
            user_id=2,
            input="Another input",
            response="Another response",
            feedback=sample_feedback,
        ),
    ]


@app.post("/responses/{response_id}/feedback")
def post_feedback(response_id: int, feedback: Feedback):
    """Post feedback for a response"""
    # Save the feedback to the database
    return {"message": "Feedback received", "feedback": feedback}


############################################################
# Users / authentication
############################################################


class User(BaseModel):
    id: int
    username: str
    onc_token: str
    hashed_password: str
    is_admin: bool = False


class CreateUserRequest(BaseModel):
    username: str
    password: str
    onc_token: Optional[str] = None


@app.post("/register")
def register_user(user: CreateUserRequest):
    """Register a new user"""
    # Save the user to the database
    return {"message": "User registered"}


# login and token endpoints if we are using JWT. return a JWT to the user on authorization and then require that for endpoints

# also need rate limiting
