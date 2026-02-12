from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from compras_divididas.db.base import Base, import_orm_models


@pytest.fixture
def sqlite_session_factory() -> Generator[sessionmaker[Session], None, None]:
    import_orm_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
