from fastapi import FastAPI

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router
from src.database import Base, engine

from src.llm import models  # noqa
from src.auth import models  # noqa


app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])

Base.metadata.create_all(bind=engine)
