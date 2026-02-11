"""SQLAlchemy base metadata and model registration utilities."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""


def import_orm_models() -> None:
    """Import ORM models so metadata is fully populated."""

    from compras_divididas.db.models import financial_movement, participant

    _ = (financial_movement, participant)
