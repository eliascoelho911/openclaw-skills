"""SQLAlchemy engine and session bootstrap."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from compras_divididas.infrastructure.settings import AppSettings


class Base(DeclarativeBase):
    """Base declarative class for ORM models."""


def create_db_engine(settings: AppSettings) -> Engine:
    """Build a SQLAlchemy engine from application settings."""
    return create_engine(settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create the SQLAlchemy session factory."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional session scope."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
