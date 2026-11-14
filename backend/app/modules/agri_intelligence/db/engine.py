import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy import event


def get_engine() -> Engine:
    """Create a SQLAlchemy Engine.
    Reads DATABASE_URL from the environment; defaults to a local SQLite file.
    The URL is "sqlite:///./agri_intelligence.db" relative to the project root.
    """
    database_url = os.getenv(
        "DATABASE_URL", "sqlite:///./agri_intelligence.db"
    )
    engine = create_engine(database_url, echo=False)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine
