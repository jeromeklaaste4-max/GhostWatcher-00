"""SQLAlchemy database engine, session factory, and declarative base.

GhostWatcher uses synchronous SQLAlchemy on purpose: SQLite writes are
fast, single-file, and the webhook workload is low-volume, so a simple
thread-safe synchronous session keeps the codebase easy to reason about.
Endpoints that touch the database offload the call to a worker thread via
``starlette.concurrency.run_in_threadpool`` so the event loop is never
blocked.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

_connect_args = {}
if settings.database_url.startswith("sqlite"):
    # Needed because SQLite objects created in one thread may be used in
    # another when FastAPI offloads sync work to the threadpool.
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def init_db() -> None:
    """Create all tables that do not yet exist.

    Safe to call on every application startup; it is a no-op for tables
    that already exist.
    """
    # Import models here (not at module load time) to avoid circular
    # imports between database.py and models that import Base from here.
    from app.models import alert  # noqa: F401  (ensures model is registered)

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager that yields a database session and always closes it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per-request."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

