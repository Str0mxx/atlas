"""ATLAS veritabani altyapi modulu.

SQLAlchemy async engine, session factory ve Base sinifi saglar.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Tum SQLAlchemy modellerinin miras alacagi temel sinif."""

    pass


# Module-level singleton'lar (init_db ile baslatilir, close_db ile kapatilir)
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Veritabani engine ve session factory'yi baslatir.

    app/main.py lifespan icerisinde cagirilir.
    """
    global engine, async_session_factory

    engine = create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_size=settings.database_pool_size,
        max_overflow=10,
        pool_pre_ping=True,
    )

    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Veritabani engine baslatildi: %s", settings.database_url.split("@")[-1])


async def close_db() -> None:
    """Veritabani engine'i kapatir.

    app/main.py lifespan kapanis asamasinda cagirilir.
    """
    global engine, async_session_factory
    if engine is not None:
        await engine.dispose()
        engine = None
        async_session_factory = None
        logger.info("Veritabani baglantisi kapatildi")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session context manager.

    FastAPI Depends ile kullanilabilir:
        session = Depends(get_session)

    Yields:
        Aktif AsyncSession.

    Raises:
        RuntimeError: Veritabani baslatilmamissa.
    """
    if async_session_factory is None:
        raise RuntimeError("Veritabani baslatilmamis. Once init_db() cagiriniz.")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Tum tablolari olusturur (gelistirme ortami icin).

    Production'da alembic kullanilmali.

    Raises:
        RuntimeError: Veritabani baslatilmamissa.
    """
    if engine is None:
        raise RuntimeError("Veritabani baslatilmamis.")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Veritabani tablolari olusturuldu")
