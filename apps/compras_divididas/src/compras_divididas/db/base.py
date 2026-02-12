"""SQLAlchemy base metadata and model registration utilities."""

from importlib import import_module

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""


def import_orm_models() -> None:
    """Import ORM models so metadata is fully populated."""

    modules = (
        "compras_divididas.db.models.participant",
        "compras_divididas.db.models.financial_movement",
        "compras_divididas.db.models.recurrence_rule",
        "compras_divididas.db.models.recurrence_occurrence",
        "compras_divididas.db.models.recurrence_event",
    )
    for module_name in modules:
        import_module(module_name)
