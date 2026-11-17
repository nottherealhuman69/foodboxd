"""Alembic runtime: picks the database and runs the migrations.

The URL comes from backend/.env:
  - default:           DATABASE_URL       (the real database)
  - `-x db=test`:      TEST_DATABASE_URL  (the local test database)
  - code (the tests):  config.attributes["url"]
Migrations are plain SQL (op.execute), so no SQLAlchemy models are involved.
"""
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def database_url() -> str:
    if config.attributes.get("url"):
        return config.attributes["url"]
    target = context.get_x_argument(as_dictionary=True).get("db", "main")
    if target not in ("main", "test"):
        raise SystemExit(f"Unknown -x db={target!r}; use db=test or leave it out.")
    name = "TEST_DATABASE_URL" if target == "test" else "DATABASE_URL"
    url = os.getenv(name)
    if not url:
        raise SystemExit(f"{name} is not set (backend/.env).")
    # SQLAlchemy only accepts the postgresql:// spelling
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(url=database_url(), literal_binds=True, transaction_per_migration=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        # each migration runs in its own transaction: it either fully applies or not at all
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
