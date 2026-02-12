"""ATLAS FastAPI ana uygulama modulu."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request

from app.celery_app import celery_app  # noqa: F401 — Celery worker/beat icin
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

    # Qdrant (vektor veritabani) baglantisi
    from app.core.memory.semantic import SemanticMemory

    semantic: SemanticMemory | None = SemanticMemory()
    try:
        await semantic.connect()
        logger.info("Qdrant baglantisi hazir")
    except Exception as exc:
        logger.error("Qdrant baglanti hatasi: %s", exc)
        semantic = None

    # Hafiza nesnelerini app.state'e kaydet
    app.state.short_term_memory = short_term
    app.state.long_term_memory = LongTermMemory()
    app.state.semantic_memory = semantic

    # Telegram bot baslat
    from app.tools.telegram_bot import TelegramBot

    telegram_bot: TelegramBot | None = None
    try:
        telegram_bot = TelegramBot()
        await telegram_bot.start_polling()
        logger.info("Telegram bot baslatildi")
    except Exception as exc:
        logger.error("Telegram bot baslatilamadi: %s", exc)
        telegram_bot = None

    # Master Agent baslat ve agent'lari kaydet
    from app.agents import (
        AnalysisAgent,
        CodingAgent,
        CommunicationAgent,
        CreativeAgent,
        MarketingAgent,
        ResearchAgent,
        SecurityAgent,
        ServerMonitorAgent,
    )
    from app.core.master_agent import MasterAgent

    master_agent = MasterAgent()

    for agent_cls in [
        ServerMonitorAgent,
        SecurityAgent,
        ResearchAgent,
        MarketingAgent,
        CodingAgent,
        CommunicationAgent,
        AnalysisAgent,
        CreativeAgent,
    ]:
        try:
            agent = agent_cls()
            master_agent.register_agent(agent)
        except Exception as exc:
            logger.error(
                "Agent kaydedilemedi (%s): %s",
                agent_cls.__name__,
                exc,
            )

    # Telegram <-> Master Agent baglantisi
    if telegram_bot:
        master_agent.telegram_bot = telegram_bot
        telegram_bot.master_agent = master_agent

    app.state.master_agent = master_agent
    app.state.telegram_bot = telegram_bot

    # TaskManager baslat
    from app.core.task_manager import TaskManager

    task_manager = TaskManager(
        master_agent=master_agent,
        long_term=app.state.long_term_memory,
        short_term=short_term,
        semantic=semantic,
        telegram_bot=telegram_bot,
    )
    await task_manager.start()
    app.state.task_manager = task_manager

    logger.info(
        "ATLAS hazir. Kayitli agent: %d",
        len(master_agent.agents),
    )
    yield

    # --- Kapanis ---
    logger.info("ATLAS kapatiliyor...")

    # TaskManager durdur
    if getattr(app.state, "task_manager", None):
        try:
            await app.state.task_manager.stop()
        except Exception as exc:
            logger.error("TaskManager durdurma hatasi: %s", exc)

    # Telegram bot durdur
    if getattr(app.state, "telegram_bot", None):
        try:
            await app.state.telegram_bot.stop()
        except Exception as exc:
            logger.error("Telegram bot durdurma hatasi: %s", exc)

    if semantic is not None:
        await semantic.close()

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

# Router'lari kaydet
from app.api.routes import router as api_router
from app.api.webhooks import router as webhooks_router

app.include_router(api_router)
app.include_router(webhooks_router)


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
async def system_status(request: Request) -> dict[str, object]:
    """Detayli sistem durumu."""
    master_agent = getattr(request.app.state, "master_agent", None)

    agents_info: dict[str, object] = {"master": "idle"}
    if master_agent:
        agents_info = {
            "master": master_agent.status.value,
            "registered": master_agent.get_registered_agents(),
            "count": len(master_agent.agents),
        }

    return {
        "service": "atlas",
        "version": "0.1.0",
        "environment": settings.app_env,
        "debug": settings.app_debug,
        "agents": agents_info,
    }
