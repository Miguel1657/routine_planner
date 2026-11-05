"""SQLite engine/session setup. Swappable for Postgres later (just the URL)."""
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import DATABASE_PATH
from src.models import Base


def make_engine(database_path=DATABASE_PATH):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{database_path}", future=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)


def init_db(engine_=engine) -> None:
    Base.metadata.create_all(engine_)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
