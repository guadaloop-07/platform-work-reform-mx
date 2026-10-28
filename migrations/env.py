"""Run online migrations using only the project's validated configuration."""

from alembic import context
from sqlalchemy import URL, create_engine, text
from sqlalchemy.pool import NullPool

from platform_work_reform.config import Settings

settings = context.config.attributes.get("settings") or Settings.from_env()
url = URL.create(
    "postgresql+psycopg",
    username=settings.user,
    password=settings.password,
    host=settings.host,
    port=settings.port,
    database=settings.database,
)
engine = create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 5})
try:
    with engine.begin() as connection:
        # Bootstrap the namespace that holds Alembic's own revision table.
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS meta"))
        context.configure(connection=connection, version_table_schema="meta")
        with context.begin_transaction():
            context.run_migrations()
finally:
    engine.dispose()
