"""
Database engine and session management.

Usage in FastAPI endpoints::

    from db import get_db
    from sqlalchemy.orm import Session
    from fastapi import Depends

    @app.post("/example")
    def handler(db: Session = Depends(get_db)):
        ...
"""

import logging
import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine construction
# ---------------------------------------------------------------------------

def _build_database_url() -> str:
    """Resolve the database URL.

    Priority:
      1. DATABASE_URL environment variable (for containers / tests)
      2. database.url from the active YAML config
      3. Fallback to a local SQLite file
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        logger.info("Database URL sourced from DATABASE_URL env var.")
        return env_url

    try:
        from configs.getConfig import getConfig
        config = getConfig()
        url = config.get("database", {}).get("url")
        if url:
            logger.info(f"Database URL sourced from config.")
            return url
    except FileNotFoundError:
        logger.warning("Config file not found — falling back to SQLite default.")

    fallback = "sqlite:///./promptprop_dev.db"
    logger.warning(f"No database URL configured. Using fallback: {fallback}")
    return fallback


def _create_engine_for_url(url: str) -> Engine:
    """Create a SQLAlchemy engine with dialect-appropriate settings."""
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )


database_url = _build_database_url()
engine = _create_engine_for_url(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# SQLite: enforce foreign keys (disabled by default)
# ---------------------------------------------------------------------------

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session, closing it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
