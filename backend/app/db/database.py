from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _default_sqlite_path() -> str:
    # backend/data/ardhiq.sqlite
    here = Path(__file__).resolve()
    backend_root = here.parents[2]
    data_dir = backend_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "ardhiq.sqlite")


DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite+pysqlite:///{_default_sqlite_path()}"

# For SQLite, need check_same_thread False for FastAPI.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
