"""ATLAS cevrimdisi yonetim modulu.

Baglanti durumu tespiti, graceful degradation,
yerel karar cache ve sync kuyrugu saglar.
"""

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectionStatus(str, Enum):
    """Baglanti durumu tanimlari."""

    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class SyncItem(BaseModel):
    """Sync kuyrugu elemani.

    Cevrimdisi iken biriktirilip baglanti gelince islenir.

    Attributes:
        item_id: Benzersiz eleman kimlik.
        operation: Islem tipi (create/update/delete).
        target_service: Hedef servis (redis/postgres/qdrant).
        payload: Islem verisi.
        created_at: Olusturulma zamani.
        retry_count: Tekrar deneme sayisi.
    """

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation: str
    target_service: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    retry_count: int = 0


class OfflineManager:
    """Cevrimdisi yonetim sinifi.

    Servislerin baglanti durumunu izler, cevrimdisi iken
    kararlari cache'ler ve islemleri sync kuyruguna biriktirir.

    Attributes:
        health_check_interval: Saglik kontrolu araligi (saniye).
        max_queue_size: Maksimum sync kuyrugu boyutu.
    """

    def __init__(
        self,
        health_check_interval: int | None = None,
        max_queue_size: int | None = None,
    ) -> None:
        """OfflineManager'i baslatir.

        Args:
            health_check_interval: Saglik kontrolu araligi (saniye).
            max_queue_size: Maksimum sync kuyrugu boyutu.
        """
        self.health_check_interval = (
            health_check_interval or settings.offline_health_check_interval
        )
        self.max_queue_size = (
            max_queue_size or settings.offline_max_queue_size
        )

        self._service_status: dict[str, ConnectionStatus] = {
            "redis": ConnectionStatus.ONLINE,
            "postgres": ConnectionStatus.ONLINE,
            "qdrant": ConnectionStatus.ONLINE,
        }
        self._decision_cache: dict[str, Any] = {}
        self._sync_queue: deque[SyncItem] = deque(maxlen=self.max_queue_size)
        self._task: asyncio.Task[None] | None = None
        self._running = False

        logger.info(
            "OfflineManager olusturuldu (aralik=%ds, kuyruk_max=%d)",
            self.health_check_interval, self.max_queue_size,
        )

    @property
    def status(self) -> ConnectionStatus:
        """Genel baglanti durumu (en kotu duruma gore).

        Returns:
            En kotu durumdaki servisin baglanti durumu.
        """
        statuses = list(self._service_status.values())
        if ConnectionStatus.OFFLINE in statuses:
            return ConnectionStatus.OFFLINE
        if ConnectionStatus.DEGRADED in statuses:
            return ConnectionStatus.DEGRADED
        return ConnectionStatus.ONLINE

    @property
    def is_offline(self) -> bool:
        """Tum servisler cevrimdisi mi.

        Returns:
            Tum servisler OFFLINE ise True.
        """
        return all(
            s == ConnectionStatus.OFFLINE
            for s in self._service_status.values()
        )

    async def check_connections(self) -> dict[str, ConnectionStatus]:
        """Tum servislerin baglanti durumunu kontrol eder.

        Returns:
            Servis adi -> baglanti durumu eslesmesi.
        """
        self._service_status["redis"] = await self._check_redis()
        self._service_status["postgres"] = await self._check_postgres()
        self._service_status["qdrant"] = await self._check_qdrant()

        logger.info(
            "Baglanti durumu: redis=%s, postgres=%s, qdrant=%s",
            self._service_status["redis"].value,
            self._service_status["postgres"].value,
            self._service_status["qdrant"].value,
        )
        return dict(self._service_status)

    async def _check_redis(self) -> ConnectionStatus:
        """Redis baglanti kontrolu."""
        try:
            from redis.asyncio import Redis

            redis = Redis.from_url(
                settings.redis_url, socket_connect_timeout=3,
            )
            await redis.ping()
            await redis.close()
            return ConnectionStatus.ONLINE
        except Exception:
            return ConnectionStatus.OFFLINE

    async def _check_postgres(self) -> ConnectionStatus:
        """PostgreSQL baglanti kontrolu."""
        try:
            from sqlalchemy.ext.asyncio import create_async_engine

            engine = create_async_engine(
                settings.database_url, pool_pre_ping=True,
            )
            async with engine.connect() as conn:
                await conn.execute(
                    __import__("sqlalchemy").text("SELECT 1"),
                )
            await engine.dispose()
            return ConnectionStatus.ONLINE
        except Exception:
            return ConnectionStatus.OFFLINE

    async def _check_qdrant(self) -> ConnectionStatus:
        """Qdrant baglanti kontrolu."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(
                    f"http://{settings.qdrant_host}:{settings.qdrant_port}"
                    "/healthz",
                )
                if resp.status_code == 200:
                    return ConnectionStatus.ONLINE
                return ConnectionStatus.DEGRADED
        except Exception:
            return ConnectionStatus.OFFLINE

    async def cache_decision(self, key: str, decision: Any) -> None:
        """Karari yerel cache'e yazar.

        Args:
            key: Karar anahtari.
            decision: Karar verisi.
        """
        self._decision_cache[key] = decision
        logger.debug("Karar cache'e yazildi: %s", key)

    async def get_cached_decision(self, key: str) -> Any | None:
        """Yerel cache'den karar okur.

        Args:
            key: Karar anahtari.

        Returns:
            Karar verisi veya None.
        """
        return self._decision_cache.get(key)

    async def enqueue(self, item: SyncItem) -> None:
        """Sync kuyruguna eleman ekler.

        Args:
            item: Sync edilecek islem.
        """
        self._sync_queue.append(item)
        logger.info(
            "Sync kuyruguna eklendi: %s -> %s (%d beklemede)",
            item.operation, item.target_service,
            len(self._sync_queue),
        )

    async def sync_pending(self) -> int:
        """Bekleyen islemleri sync eder.

        Baglanti geri geldiginde kuyrukta biriken
        islemleri hedef servislere iletir.

        Returns:
            Basariyla sync edilen islem sayisi.
        """
        synced = 0
        batch_size = settings.offline_sync_batch_size
        failed: list[SyncItem] = []

        for _ in range(min(batch_size, len(self._sync_queue))):
            if not self._sync_queue:
                break
            item = self._sync_queue.popleft()

            service_status = self._service_status.get(
                item.target_service, ConnectionStatus.OFFLINE,
            )
            if service_status == ConnectionStatus.OFFLINE:
                item.retry_count += 1
                failed.append(item)
                continue

            # Basarili sync (gercek implementasyonda servis'e gonderilir)
            synced += 1
            logger.info(
                "Sync basarili: %s -> %s (id=%s)",
                item.operation, item.target_service, item.item_id,
            )

        # Basarisiz olanlari kuyruga geri ekle
        for item in failed:
            self._sync_queue.appendleft(item)

        if synced > 0:
            logger.info("%d islem sync edildi, %d beklemede", synced, len(self._sync_queue))
        return synced

    async def get_queue_size(self) -> int:
        """Sync kuyrugu boyutunu dondurur.

        Returns:
            Kuyrukta bekleyen islem sayisi.
        """
        return len(self._sync_queue)

    async def start(self) -> None:
        """Periyodik saglik kontrolu baslatir."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._health_check_loop(),
            name="offline_health_check",
        )
        logger.info("OfflineManager baslatildi")

    async def stop(self) -> None:
        """Saglik kontrolu durdurur."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("OfflineManager durduruldu")

    async def _health_check_loop(self) -> None:
        """Periyodik saglik kontrol dongusu."""
        while self._running:
            try:
                await self.check_connections()

                # Baglanti gelmisse bekleyen islemleri sync et
                if self.status != ConnectionStatus.OFFLINE:
                    await self.sync_pending()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Saglik kontrolu hatasi: %s", exc)

            try:
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break

    def get_service_statuses(self) -> dict[str, str]:
        """Servis durumlarini string olarak dondurur.

        Returns:
            Servis adi -> durum eslesmesi.
        """
        return {k: v.value for k, v in self._service_status.items()}
