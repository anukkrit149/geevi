from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


@lru_cache
def get_engine():
    settings = get_settings()
    if settings.serverless:
        # No server-side prepared statements: they do not survive a transaction-mode connection pooler.
        return create_engine(settings.database_url, poolclass=NullPool, connect_args={"prepare_threshold": None})
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker():
    return sessionmaker(get_engine(), expire_on_commit=False, autoflush=True)


def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
