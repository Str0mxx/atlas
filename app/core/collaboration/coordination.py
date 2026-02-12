"""ATLAS Agent koordinasyon modulu.

Senkronizasyon bariyerleri, paylasimli durum (blackboard)
ve karsilikli dislamali kaynak erisimi.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class Blackboard:
    """Paylasimli bilgi panosu (blackboard pattern).

    Agentlar arasi bilgi paylasimi icin merkezi depo.
    Namespace ile izole alanlar, versiyonlama ve
    degisiklik bildirimi destekler.

    Attributes:
        _data: Paylasimli veri (namespace:key -> value).
        _versions: Versiyon sayaclari (namespace:key -> versiyon).
        _watchers: Degisiklik izleyicileri (namespace:key -> [Event]).
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._versions: dict[str, int] = {}
        self._watchers: dict[str, list[asyncio.Event]] = {}
        self._history: list[dict[str, Any]] = []

    def _make_key(self, namespace: str, key: str) -> str:
        """Dahili anahtar olusturur."""
        return f"{namespace}:{key}"

    async def write(
        self,
        namespace: str,
        key: str,
        value: Any,
        author: str = "",
    ) -> int:
        """Veri yazar.

        Args:
            namespace: Alan adi.
            key: Anahtar.
            value: Deger.
            author: Yazan agent adi.

        Returns:
            Yeni versiyon numarasi.
        """
        full_key = self._make_key(namespace, key)
        version = self._versions.get(full_key, 0) + 1

        self._data[full_key] = value
        self._versions[full_key] = version

        self._history.append({
            "namespace": namespace,
            "key": key,
            "value": value,
            "author": author,
            "version": version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Izleyicileri bilgilendir
        for event in self._watchers.get(full_key, []):
            event.set()

        logger.debug(
            "Blackboard yazma: %s = %s (v%d, yazar=%s)",
            full_key,
            value,
            version,
            author,
        )
        return version

    def read(self, namespace: str, key: str) -> Any | None:
        """Veri okur.

        Args:
            namespace: Alan adi.
            key: Anahtar.

        Returns:
            Deger veya None.
        """
        full_key = self._make_key(namespace, key)
        return self._data.get(full_key)

    def read_namespace(self, namespace: str) -> dict[str, Any]:
        """Tum namespace verilerini okur.

        Args:
            namespace: Alan adi.

        Returns:
            Anahtar-deger sozlugu.
        """
        prefix = f"{namespace}:"
        result: dict[str, Any] = {}
        for full_key, value in self._data.items():
            if full_key.startswith(prefix):
                short_key = full_key[len(prefix):]
                result[short_key] = value
        return result

    def get_version(self, namespace: str, key: str) -> int:
        """Versiyon numarasini dondurur.

        Args:
            namespace: Alan adi.
            key: Anahtar.

        Returns:
            Versiyon numarasi (0 = yok).
        """
        full_key = self._make_key(namespace, key)
        return self._versions.get(full_key, 0)

    async def watch(
        self,
        namespace: str,
        key: str,
        timeout: float | None = None,
    ) -> bool:
        """Degisiklik bekler.

        Args:
            namespace: Alan adi.
            key: Anahtar.
            timeout: Bekleme suresi (saniye).

        Returns:
            Degisiklik oldu mu (False = timeout).
        """
        full_key = self._make_key(namespace, key)
        event = asyncio.Event()
        if full_key not in self._watchers:
            self._watchers[full_key] = []
        self._watchers[full_key].append(event)

        try:
            if timeout is not None:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()
            return True
        except asyncio.TimeoutError:
            return False
        finally:
            watchers = self._watchers.get(full_key, [])
            if event in watchers:
                watchers.remove(event)

    def delete(self, namespace: str, key: str) -> bool:
        """Veri siler.

        Args:
            namespace: Alan adi.
            key: Anahtar.

        Returns:
            Silme basarili mi.
        """
        full_key = self._make_key(namespace, key)
        if full_key in self._data:
            del self._data[full_key]
            self._versions.pop(full_key, None)
            return True
        return False

    def clear_namespace(self, namespace: str) -> int:
        """Namespace'i temizler.

        Args:
            namespace: Alan adi.

        Returns:
            Silinen kayit sayisi.
        """
        prefix = f"{namespace}:"
        keys_to_delete = [k for k in self._data if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._data[key]
            self._versions.pop(key, None)
        return len(keys_to_delete)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Degisiklik gecmisini dondurur.

        Args:
            limit: Maksimum kayit.

        Returns:
            Gecmis kayitlari.
        """
        return list(self._history[-limit:])


class SyncBarrier:
    """Senkronizasyon bariyeri.

    Birden fazla agent'in belirli bir noktada bulusmasini
    saglar. Tum katilimcilar gelene kadar bekler.

    Attributes:
        name: Bariyer adi.
        expected: Beklenen katilimci sayisi.
        _arrived: Gelen agentlar.
        _event: Tum katilimcilar geldiginde tetiklenir.
    """

    def __init__(self, name: str, expected: int) -> None:
        self.name = name
        self.expected = expected
        self._arrived: set[str] = set()
        self._event = asyncio.Event()

    async def arrive(self, agent_name: str) -> bool:
        """Bariyere varir.

        Args:
            agent_name: Varan agent adi.

        Returns:
            Tum katilimcilar geldi mi.
        """
        self._arrived.add(agent_name)
        logger.debug(
            "Bariyer %s: %s vardi (%d/%d)",
            self.name,
            agent_name,
            len(self._arrived),
            self.expected,
        )
        if len(self._arrived) >= self.expected:
            self._event.set()
            return True
        return False

    async def wait(self, timeout: float | None = None) -> bool:
        """Tum katilimcilari bekler.

        Args:
            timeout: Bekleme suresi (saniye).

        Returns:
            Tum katilimcilar geldi mi (False = timeout).
        """
        try:
            if timeout is not None:
                await asyncio.wait_for(self._event.wait(), timeout=timeout)
            else:
                await self._event.wait()
            return True
        except asyncio.TimeoutError:
            return False

    def reset(self) -> None:
        """Bariyeri sifirlar."""
        self._arrived.clear()
        self._event.clear()

    @property
    def arrived_count(self) -> int:
        """Gelen katilimci sayisi."""
        return len(self._arrived)

    @property
    def is_complete(self) -> bool:
        """Tum katilimcilar geldi mi."""
        return len(self._arrived) >= self.expected


class MutexLock:
    """Karsilikli dislamali kilit.

    Tek seferde sadece bir agent'in bir kaynaga
    erismesini saglar.

    Attributes:
        resource_name: Kaynak adi.
        _lock: Asyncio kilidi.
        _holder: Kilidi tutan agent adi.
    """

    def __init__(self, resource_name: str) -> None:
        self.resource_name = resource_name
        self._lock = asyncio.Lock()
        self._holder: str | None = None

    async def acquire(self, agent_name: str, timeout: float | None = None) -> bool:
        """Kilidi alir.

        Args:
            agent_name: Agent adi.
            timeout: Bekleme suresi (saniye).

        Returns:
            Kilit alindi mi.
        """
        try:
            if timeout is not None:
                acquired = await asyncio.wait_for(
                    self._lock.acquire(), timeout=timeout,
                )
            else:
                acquired = await self._lock.acquire()

            if acquired:
                self._holder = agent_name
                logger.debug("Kilit alindi: %s -> %s", agent_name, self.resource_name)
            return acquired
        except asyncio.TimeoutError:
            return False

    def release(self, agent_name: str) -> bool:
        """Kilidi serbest birakir.

        Args:
            agent_name: Agent adi.

        Returns:
            Basarili mi (sadece tutan agent serbest birakabilir).
        """
        if self._holder != agent_name:
            return False

        self._holder = None
        self._lock.release()
        logger.debug("Kilit serbest: %s -> %s", agent_name, self.resource_name)
        return True

    @property
    def holder(self) -> str | None:
        """Kilidi tutan agent."""
        return self._holder

    @property
    def is_locked(self) -> bool:
        """Kilit tutulmakta mi."""
        return self._lock.locked()
