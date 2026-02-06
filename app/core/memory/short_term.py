"""ATLAS kisa sureli hafiza modulu (Redis).

Aktif gorev durumlari, oturum cache'i ve gecici verileri yonetir.
"""

import json
import logging
from typing import Any

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

# Varsayilan TTL degerleri (saniye)
DEFAULT_SESSION_TTL = 3600   # 1 saat
DEFAULT_TASK_TTL = 86400     # 24 saat


class ShortTermMemory:
    """Redis tabanli kisa sureli hafiza sinifi.

    Aktif gorev durumlarini, oturum verilerini ve gecici cache'i yonetir.

    Attributes:
        prefix: Redis anahtar on eki (namespace).
        redis: Async Redis istemcisi.
    """

    def __init__(self, prefix: str = "atlas") -> None:
        """ShortTermMemory'yi baslatir.

        Args:
            prefix: Redis anahtar on eki. Tum anahtarlar bu on ek ile baslar.
        """
        self.prefix = prefix
        self.redis: Redis | None = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        """Redis baglantisini kurar."""
        self.redis = Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
        # Baglanti testi
        await self.redis.ping()
        logger.info("Redis baglantisi kuruldu: %s", settings.redis_url.split("@")[-1])

    async def close(self) -> None:
        """Redis baglantisini kapatir."""
        if self.redis is not None:
            await self.redis.close()
            self.redis = None
            logger.info("Redis baglantisi kapatildi")

    def _ensure_connected(self) -> Redis:  # type: ignore[type-arg]
        """Baglantinin aktif oldugunu dogrular.

        Returns:
            Aktif Redis istemcisi.

        Raises:
            RuntimeError: Baglanti kurulmamissa.
        """
        if self.redis is None:
            raise RuntimeError("Redis baglantisi kurulmamis. Once connect() cagiriniz.")
        return self.redis

    def _key(self, *parts: str) -> str:
        """Prefixed Redis anahtari olusturur.

        Args:
            parts: Anahtar parcalari.

        Returns:
            Formatlanmis anahtar (ornek: 'atlas:task:abc123').
        """
        return ":".join([self.prefix, *parts])

    # === Aktif gorev durum yonetimi ===

    async def store_task_status(
        self,
        task_id: str,
        status: dict[str, Any],
        ttl: int = DEFAULT_TASK_TTL,
    ) -> None:
        """Aktif gorev durumunu Redis'e kaydeder.

        Args:
            task_id: Gorev kimlik numarasi.
            status: Gorev durum bilgisi (JSON-serializable dict).
            ttl: Yasam suresi (saniye).
        """
        r = self._ensure_connected()
        key = self._key("task", task_id)
        await r.set(key, json.dumps(status, default=str), ex=ttl)
        logger.debug("Gorev durumu kaydedildi: %s", task_id)

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Aktif gorev durumunu getirir.

        Args:
            task_id: Gorev kimlik numarasi.

        Returns:
            Gorev durum bilgisi veya None (bulunamazsa).
        """
        r = self._ensure_connected()
        key = self._key("task", task_id)
        data = await r.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def delete_task_status(self, task_id: str) -> bool:
        """Aktif gorev durumunu siler.

        Args:
            task_id: Gorev kimlik numarasi.

        Returns:
            Silme basarili mi (anahtar var miydi).
        """
        r = self._ensure_connected()
        key = self._key("task", task_id)
        deleted = await r.delete(key)
        logger.debug("Gorev durumu silindi: %s (sonuc=%d)", task_id, deleted)
        return deleted > 0

    async def get_active_tasks(self) -> list[dict[str, Any]]:
        """Tum aktif gorev durumlarini listeler.

        Returns:
            Aktif gorev durumlari listesi.
        """
        r = self._ensure_connected()
        pattern = self._key("task", "*")
        tasks: list[dict[str, Any]] = []
        async for key in r.scan_iter(match=pattern):
            data = await r.get(key)
            if data is not None:
                tasks.append(json.loads(data))
        return tasks

    # === Oturum cache yonetimi ===

    async def store_session(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int = DEFAULT_SESSION_TTL,
    ) -> None:
        """Oturum verisini cache'e kaydeder.

        Args:
            session_id: Oturum kimlik numarasi.
            data: Oturum verisi (JSON-serializable dict).
            ttl: Yasam suresi (saniye).
        """
        r = self._ensure_connected()
        key = self._key("session", session_id)
        await r.set(key, json.dumps(data, default=str), ex=ttl)
        logger.debug("Oturum kaydedildi: %s (TTL=%ds)", session_id, ttl)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Oturum verisini getirir.

        Args:
            session_id: Oturum kimlik numarasi.

        Returns:
            Oturum verisi veya None (bulunamazsa veya suresi dolmussa).
        """
        r = self._ensure_connected()
        key = self._key("session", session_id)
        data = await r.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def delete_session(self, session_id: str) -> bool:
        """Oturum verisini siler.

        Args:
            session_id: Oturum kimlik numarasi.

        Returns:
            Silme basarili mi.
        """
        r = self._ensure_connected()
        key = self._key("session", session_id)
        deleted = await r.delete(key)
        return deleted > 0

    # === Genel cache yonetimi ===

    async def cache_set(
        self,
        key_name: str,
        value: Any,
        ttl: int = DEFAULT_SESSION_TTL,
    ) -> None:
        """Genel amacli cache kaydi.

        Args:
            key_name: Cache anahtari.
            value: Kaydedilecek deger (JSON-serializable).
            ttl: Yasam suresi (saniye).
        """
        r = self._ensure_connected()
        key = self._key("cache", key_name)
        await r.set(key, json.dumps(value, default=str), ex=ttl)

    async def cache_get(self, key_name: str) -> Any | None:
        """Genel amacli cache okuma.

        Args:
            key_name: Cache anahtari.

        Returns:
            Saklanan deger veya None.
        """
        r = self._ensure_connected()
        key = self._key("cache", key_name)
        data = await r.get(key)
        if data is None:
            return None
        return json.loads(data)

    async def cache_delete(self, key_name: str) -> bool:
        """Genel amacli cache silme.

        Args:
            key_name: Cache anahtari.

        Returns:
            Silme basarili mi.
        """
        r = self._ensure_connected()
        key = self._key("cache", key_name)
        deleted = await r.delete(key)
        return deleted > 0
