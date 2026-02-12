from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path
from typing import TYPE_CHECKING

from alembic import context
from sqlalchemy import engine_from_config, pool

if TYPE_CHECKING:
    from sqlalchemy import MetaData

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _load_target_metadata() -> tuple[MetaData, str]:
    from compras_divididas.core.settings import get_settings
    from compras_divididas.db.base import Base, import_orm_models

    import_orm_models()
    return Base.metadata, get_settings().database_url


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata, default_database_url = _load_target_metadata()


def _resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    return default_database_url


config.set_main_option("sqlalchemy.url", _resolve_database_url())


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
