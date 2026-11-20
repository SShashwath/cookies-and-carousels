from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def make_engine(url: str):
    options = {"autocommit": False} if url.startswith("sqlite:") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=options)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.autocommit = True
            connection.execute("PRAGMA foreign_keys = ON")
            connection.autocommit = False
    return engine


engine = make_engine(settings().sqlalchemy_url)
SessionFactory = sessionmaker(engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionFactory() as db:
        yield db
