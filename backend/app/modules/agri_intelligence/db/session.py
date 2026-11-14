from sqlalchemy.orm import sessionmaker
from .engine import get_engine

# Session factory; callers should use `with Session() as session:`
SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)

def get_session():
    """Convenient dependency for FastAPI (if needed later)."""
    return SessionLocal()
