from fastapi import FastAPI
from src.database import conv_engine, ConvBase

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router

# Setup routes
app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(llm_router, prefix="/llm", tags=["llm"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


# Setup database
def init_db():
    ConvBase.metadata.create_all(bind=conv_engine)


if __name__ == "__main__":
    init_db()
