import asyncio
import logging
from contextlib import asynccontextmanager  # Used to manage async app startup/shutdown events

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Enables frontend-backend communications via CORS

from sqlalchemy import text

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

    # Connect to Supabase Postgres as async engine
    try:
        # async with asyncio.timeout(20):
        logger.info("Initializing database session manager...")
        session_manager = DatabaseSessionManager(get_settings().SUPABASE_DB_URL)
        app.state.session_manager = session_manager
        
        if session_manager._engine is None:
            raise RuntimeError("Session manager engine is not initialized")
        
        # Database connectivity check
        try:
            async with session_manager.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                scalar_result = result.scalar_one_or_none()
                if scalar_result != 1:
                    raise RuntimeError("Unexpected DB result")
                logger.info("Database connectivity check passed.")
        except Exception as e:
            logger.error(f"Database connectivity check failed: {e}")
            raise
        
        # Initialize Redis client
        # async with asyncio.timeout(20):
        logger.info("Initializing Redis client...")
        app.state.redis_client = await init_redis()

        yield

        logger.info("App startup complete")
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
