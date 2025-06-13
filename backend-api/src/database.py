from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from src.settings import get_settings


engine = create_engine(
    get_settings().SUPABASE_DB_URL,
    poolclass=NullPool,
    connect_args={"sslmode": "require"},  # Required for Supabase Postgres
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Get a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
