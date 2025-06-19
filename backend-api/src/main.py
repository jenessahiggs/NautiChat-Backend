import asyncio
import logging
from contextlib import asynccontextmanager  # Used to manage async app startup/shutdown events

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Enables frontend-backend communications via CORS

# Need to import the models in the same module that Base is defined to ensure they are registered with SQLAlchemy
from src.auth import models  # noqa
from src.llm import models  # noqa

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router
from src.database import Base, DatabaseSessionManager, init_redis
from src.middleware import RateLimitMiddleware  # Custom middleware for rate limiting
from src.settings import get_settings  # Settings management for environment variables


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create tables on startup using async engine
    try:
        async with asyncio.timeout(20):
            logger.info("Initializing database session manager...")
            session_manager = DatabaseSessionManager(get_settings().SUPABASE_DB_URL)
            app.state.session_manager = session_manager
            assert session_manager._engine is not None, "Session manager engine is not initialized"
            async with session_manager.connect() as conn:
                await conn.run_sync(Base.metadata.create_all)
        # Initialize Redis client
        async with asyncio.timeout(20):
            logger.info("Initializing Redis client...")
            app.state.redis_client = await init_redis()

        yield
    finally:
        # Close connection to database and Redis Connection
        if hasattr(app.state, "session_manager"):
            logger.info("Closing database session manager...")
            await app.state.session_manager.close()
        if hasattr(app.state, "redis_client"):
            logger.info("Closing Redis client...")
            await app.state.redis_client.aclose()


def create_app():
    app = FastAPI(lifespan=lifespan)

    # TODO: add frontend url to origins
    origins = ["http://localhost:3000"]

    # Add CORS and Rate Limit Middleware
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routes from modules (auth, llm, admin)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(llm_router, prefix="/llm", tags=["llm"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])

    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok"}
