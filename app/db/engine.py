"""Database engine and session management."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_DB_DIR = Path(os.environ.get("SPOOL_STATION_DATA", Path.home() / ".spool-station"))
_DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _DB_DIR / "spool_station.db"

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
_SessionFactory = sessionmaker(bind=_engine)


def get_engine():
    """Return the SQLAlchemy engine."""
    return _engine


def get_session() -> Session:
    """Create a new database session."""
    return _SessionFactory()


def init_db():
    """Create all tables if they don't exist, then add any missing columns."""
    from app.db.models import Base  # noqa: F811

    Base.metadata.create_all(_engine)
    _migrate_add_columns(Base)


def _migrate_add_columns(Base):
    """Add columns that may be missing from older databases."""
    import sqlalchemy as sa

    with _engine.connect() as conn:
        inspector = sa.inspect(_engine)
        for table_name, table in Base.metadata.tables.items():
            if not inspector.has_table(table_name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table_name)}
            for col in table.columns:
                if col.name not in existing:
                    col_type = col.type.compile(_engine.dialect)
                    conn.execute(
                        sa.text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}")
                    )
        conn.commit()
