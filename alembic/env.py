"""Alembic ortam yapilandirmasi.

Async SQLAlchemy destegi ile Alembic migration calistirma ortamini saglar.
Veritabani baglanti bilgisi app.config uzerinden alinir.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.core.database import Base

# Tum model modulleri import edilir ki Base.metadata tabloları icersin
from app.models.task import TaskRecord  # noqa: F401
from app.models.agent_log import AgentLogRecord  # noqa: F401
from app.models.decision import DecisionRecord  # noqa: F401
from app.models.notification import NotificationRecord  # noqa: F401

# Alembic Config nesnesi (.ini dosyasina erisim saglar)
config = context.config

# Python loglama yapilandirmasi
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate icin hedef metadata
target_metadata = Base.metadata


def get_url() -> str:
    """Veritabani URL'sini app config'den alir."""
    return settings.database_url


def run_migrations_offline() -> None:
    """Migration'lari 'offline' modda calistirir.

    Gercek bir DB baglantisi kurmadan SQL ciktilar uretir.
    Uretilenler `alembic upgrade --sql` ile gorulur.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Senkron baglanti uzerinde migration'lari calistirir."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Async engine olusturur ve migration'lari calistirir."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Migration'lari 'online' modda calistirir.

    Async engine kullanarak gercek veritabani baglantisi kurar.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
