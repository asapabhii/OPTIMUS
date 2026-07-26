"""Alembic migration environment — standard async-compatible setup."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine, pool

# Use sync URL for Alembic migrations
DATABASE_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://optimus:optimus_dev@localhost:5432/optimus",
)


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    """Generate SQL without a database connection."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
