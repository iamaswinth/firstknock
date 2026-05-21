import os
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load .env file so POSTGRES_URL is available without pre-setting env vars
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# Alembic needs psycopg2 (sync). Use POSTGRES_DIRECT_URL (no pooler) for migrations.
# Pooler (PgBouncer) can break DDL statements in transaction mode.
direct_url = os.environ.get("POSTGRES_DIRECT_URL", "")
app_url = os.environ.get("POSTGRES_URL", "")

if direct_url:
    # Strip asyncpg prefix if present, keep sslmode param
    sync_url = direct_url.replace("postgresql+asyncpg://", "postgresql://")
elif app_url:
    # Fallback: derive sync URL from app URL
    sync_url = app_url.replace("postgresql+asyncpg://", "postgresql://").replace("ssl=require", "sslmode=require")
else:
    sync_url = "postgresql://firstknock:firstknock@localhost:5433/firstknock"

config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
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
