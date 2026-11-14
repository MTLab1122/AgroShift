"""SQLAlchemy Database Configuration and Engine Setup for AgroShift.

Supports PostgreSQL in production and staging via psycopg 3 driver,
with graceful local SQLite fallback when DATABASE_URL is not set.

Features:
- Environment variable-driven connection URL.
- Connection pooling for PostgreSQL (pool_size=10, max_overflow=20).
- Ping-on-checkout (pool_pre_ping=True) for stale socket detection.
- Fast diagnostic connectivity check function `check_db_connection()`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

# Default SQLite path if DATABASE_URL is unset
DEFAULT_DB_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "agroshift.db"

raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# If using legacy 'postgres://' or 'postgresql://' without driver, default to psycopg 3
if raw_db_url.startswith("postgres://"):
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif raw_db_url.startswith("postgresql://") and not raw_db_url.startswith("postgresql+"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = raw_db_url

is_sqlite = DATABASE_URL.startswith("sqlite")

# Engine options
engine_kwargs: Dict[str, Any] = {
    "pool_pre_ping": True,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    engine_kwargs["pool_timeout"] = float(os.getenv("DB_POOL_TIMEOUT", "30.0"))

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency providing request-scoped database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """Inspect active database health, dialect, and connection status."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "dialect": engine.dialect.name,
            "url_masked": str(engine.url).split("@")[-1] if "@" in str(engine.url) else str(engine.url),
            "is_postgresql": engine.dialect.name == "postgresql",
        }
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", str(exc))
        return {
            "status": "error",
            "dialect": engine.dialect.name,
            "error": str(exc),
            "is_postgresql": engine.dialect.name == "postgresql",
        }
