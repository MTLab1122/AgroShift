import pytest
from backend.app.modules.agri_intelligence.db.engine import get_engine
from backend.app.modules.agri_intelligence.db.base import Base
from alembic.config import Config

def test_engine_can_connect(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    engine = get_engine()
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()

def test_alembic_configuration_loads():
    cfg = Config("alembic.ini")
    # Verify that the URL from the ini matches the default we set
    assert cfg.get_main_option("sqlalchemy.url") == "sqlite:///./agri_intelligence.db"
    # Ensure metadata is importable (env.py would import Base)
    assert Base.metadata is not None
