import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config import settings

# Ensure database directory exists
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# Create engine with check_same_thread=False for SQLite concurrency
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}
engine = create_engine(db_url, connect_args=connect_args)

# Enable WAL mode and foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def configure_sqlite_pragmas(dbapi_connection, connection_record):
    if "sqlite" in db_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes all database tables defined by models."""
    import backend.models  # noqa: F401 - ensure all models are imported
    Base.metadata.create_all(bind=engine)
