from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.database import engine, Base

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router

from src.llm import models  # noqa
from src.auth import models  # noqa


# Setup routes
app = FastAPI()

# TO DO: add frontend url to origins
origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])

Base.metadata.create_all(bind=engine)
