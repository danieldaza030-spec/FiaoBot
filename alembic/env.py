"""Alembic environment for fiadobot database migrations."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from importlib import import_module

from sqlalchemy import engine_from_config, pool
from alembic import context

# Alembic's runtime context exposes members dynamically.
# The migration bootstrap also resembles model declarations enough to trigger
# duplicate-code false positives.
# pylint: disable=no-member,duplicate-code

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

Base = import_module("fiadobot.db.base").Base
import_module("fiadobot.models")

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url"),
    ),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
