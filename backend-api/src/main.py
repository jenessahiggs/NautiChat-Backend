import traceback
from contextlib import asynccontextmanager # Used to manage async app startup/shutdown events

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Enables frontend-backend communications via CORS

from src.database import sessionmanager, Base, init_redis

from src.auth import models  # noqa
from src.llm import models  # noqa

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.llm.router import router as llm_router
from src.middleware import RateLimitMiddleware # Custom middleware for rate limiting


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("Initializing DB...")
        # Create tables on startup using async engine
        async with sessionmanager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("DB is ready")
    except Exception as e:
        print("DB error:", e)
        traceback.print_exc()

    try:
        print("Initializing Redis...")
        # Initialize Redis Client
        app.state.redis_client = init_redis()
        print("Redis is ready")
    except Exception as e:
        print(f"Redis error: {e}")
        print("Redis error:", e)
        traceback.print_exc()
    
    yield
    # Close connection to database and Redis Connection
    # TODO? Add try/except if an exception prevents cleanup
    await sessionmanager.close()
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

