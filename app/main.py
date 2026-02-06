"""ATLAS FastAPI ana uygulama modulu."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Uygulama yasam dongusu yoneticisi.

    Baslangicta servisleri baslatir, kapanista temizlik yapar.
    """
    # --- Baslangic ---
    _setup_logging()
    logger.info("ATLAS baslatiliyor... ortam=%s", settings.app_env)

    # Redis baglantisi
    from app.core.memory.short_term import ShortTermMemory

    short_term: ShortTermMemory | None = ShortTermMemory()
    try:
        await short_term.connect()
        logger.info("Redis baglantisi hazir")
    except Exception as exc:
        logger.error("Redis baglanti hatasi: %s", exc)
        short_term = None

    # Veritabani baglantisi
    from app.core.database import close_db, create_tables, init_db
    from app.core.memory.long_term import LongTermMemory

    try:
        await init_db()
        if settings.app_debug:
            await create_tables()
        logger.info("Veritabani baglantisi hazir")
    except Exception as exc:
        logger.error("Veritabani baglanti hatasi: %s", exc)

    # Hafiza nesnelerini app.state'e kaydet
    app.state.short_term_memory = short_term
    app.state.long_term_memory = LongTermMemory()

    # TODO: Telegram bot baslat
    # TODO: Master Agent baslat

    logger.info("ATLAS hazir.")
    yield

    # --- Kapanis ---
    logger.info("ATLAS kapatiliyor...")

    if short_term is not None:
        await short_term.close()

    await close_db()

    logger.info("ATLAS kapatildi.")


app = FastAPI(
    title="ATLAS",
    description="Autonomous AI Partner System",
    version="0.1.0",
    lifespan=lifespan,
)


def _setup_logging() -> None:
    """Loglama yapilandirmasini kurar."""
    logging.basicConfig(
        level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# === Saglik kontrol endpoint'leri ===


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Sistem saglik kontrolu."""
    return {"status": "ok", "service": "atlas"}


@app.get("/status")
async def system_status() -> dict[str, object]:
    """Detayli sistem durumu."""
    return {
        "service": "atlas",
        "version": "0.1.0",
        "environment": settings.app_env,
        "debug": settings.app_debug,
        "agents": {
            "master": "idle",
            # Diger agent durumlari buraya eklenecek
        },
    }


# === Gorev endpoint'leri ===


@app.post("/tasks")
async def create_task(payload: dict[str, object]) -> JSONResponse:
    """Yeni gorev olusturur ve Master Agent'a iletir.

    Args:
        payload: Gorev detaylarini iceren sozluk.

    Returns:
        Olusturulan gorev bilgisi.
    """
    logger.info("Yeni gorev alindi: %s", payload.get("description", "tanimsiz"))

    # TODO: Master Agent'a yonlendir
    task_id = "task_placeholder"

    return JSONResponse(
        status_code=201,
        content={
            "task_id": task_id,
            "status": "queued",
            "message": "Gorev kuyruga eklendi",
        },
    )
