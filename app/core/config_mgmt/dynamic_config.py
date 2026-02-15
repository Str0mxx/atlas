"""ATLAS Dinamik Konfigurasyon modulu.

Runtime degisiklikleri, sicak yukleme,
degisiklik bildirimleri, geri alma
ve degisiklik gecmisi.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DynamicConfig:
    """Dinamik konfigurasyon yoneticisi.

    Calisma zamaninda konfigurasyon degistirir.

    Attributes:
        _configs: Dinamik konfigler.
        _watchers: Degisiklik izleyicileri.
    """

    def __init__(self) -> None:
        """Dinamik konfigurasyon baslatir."""
        self._configs: dict[
            str, dict[str, Any]
        ] = {}
        self._watchers: dict[
            str, list[Callable[..., None]]
        ] = {}
        self._change_history: list[
            dict[str, Any]
        ] = []
        self._snapshots: dict[
            str, dict[str, Any]
        ] = {}
        self._hot_reload_enabled: bool = True

        logger.info("DynamicConfig baslatildi")

    def set(
        self,
        key: str,
        value: Any,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Dinamik deger ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
            source: Kaynak.

        Returns:
            Degisiklik bilgisi.
        """
        old_value = None
        version = 1

        existing = self._configs.get(key)
        if existing:
            old_value = existing["value"]
            version = existing["version"] + 1

        entry = {
            "key": key,
            "value": value,
            "old_value": old_value,
            "version": version,
            "source": source,
            "updated_at": time.time(),
        }
        self._configs[key] = entry

        # Gecmis kaydet
        self._change_history.append({
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "version": version,
            "source": source,
            "timestamp": time.time(),
        })

        # Izleyicileri bildir
        self._notify_watchers(key, value, old_value)

        return {
            "key": key,
            "version": version,
            "changed": old_value != value,
        }

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Dinamik deger getirir.

        Args:
            key: Anahtar.
            default: Varsayilan.

        Returns:
            Deger.
        """
        entry = self._configs.get(key)
        if entry:
            return entry["value"]
        return default

    def delete(self, key: str) -> bool:
        """Dinamik deger siler.

        Args:
            key: Anahtar.

        Returns:
            Basarili mi.
        """
        if key in self._configs:
            old = self._configs[key]["value"]
            self._change_history.append({
                "key": key,
                "old_value": old,
                "new_value": None,
                "action": "delete",
                "timestamp": time.time(),
            })
            del self._configs[key]
            return True
        return False

    def watch(
        self,
        key: str,
        callback: Callable[..., None],
    ) -> bool:
        """Degisiklik izleyici ekler.

        Args:
            key: Anahtar.
            callback: Geri cagri.

        Returns:
            Basarili mi.
        """
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
        return True

    def unwatch(
        self,
        key: str,
        callback: Callable[..., None] | None = None,
    ) -> bool:
        """Izleyici kaldirir.

        Args:
            key: Anahtar.
            callback: Spesifik geri cagri (None=tumu).

        Returns:
            Basarili mi.
        """
        if key not in self._watchers:
            return False
        if callback is None:
            del self._watchers[key]
            return True
        if callback in self._watchers[key]:
            self._watchers[key].remove(callback)
            return True
        return False

    def _notify_watchers(
        self,
        key: str,
        new_value: Any,
        old_value: Any,
    ) -> int:
        """Izleyicileri bildirir.

        Args:
            key: Anahtar.
            new_value: Yeni deger.
            old_value: Eski deger.

        Returns:
            Bildirilen sayisi.
        """
        watchers = self._watchers.get(key, [])
        notified = 0
        for cb in watchers:
            try:
                cb(key, new_value, old_value)
                notified += 1
            except Exception as e:
                logger.error(
                    "Watcher hatasi %s: %s",
                    key, e,
                )
        return notified

    def rollback(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Son degisikligi geri alir.

        Args:
            key: Anahtar.

        Returns:
            Geri alma sonucu.
        """
        # Gecmiste bu anahtarin kayitlarini bul
        key_history = [
            h for h in self._change_history
            if h["key"] == key
        ]
        if len(key_history) < 1:
            return {
                "status": "error",
                "reason": "no_history",
            }

        last = key_history[-1]
        old_val = last.get("old_value")
        if old_val is None and key in self._configs:
            del self._configs[key]
            return {
                "status": "rolled_back",
                "key": key,
                "restored": None,
            }

        if old_val is not None:
            self.set(key, old_val, source="rollback")

        return {
            "status": "rolled_back",
            "key": key,
            "restored": old_val,
        }

    def create_snapshot(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Snapshot olusturur.

        Args:
            name: Snapshot adi.

        Returns:
            Snapshot bilgisi.
        """
        snapshot = {}
        for key, entry in self._configs.items():
            snapshot[key] = entry["value"]

        self._snapshots[name] = {
            "data": snapshot,
            "created_at": time.time(),
            "config_count": len(snapshot),
        }
        return {
            "name": name,
            "config_count": len(snapshot),
        }

    def restore_snapshot(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Snapshot geri yukler.

        Args:
            name: Snapshot adi.

        Returns:
            Geri yukleme sonucu.
        """
        snap = self._snapshots.get(name)
        if not snap:
            return {
                "status": "error",
                "reason": "not_found",
            }

        restored = 0
        for key, value in snap["data"].items():
            self.set(key, value, source="snapshot")
            restored += 1

        return {
            "status": "restored",
            "name": name,
            "restored_count": restored,
        }

    def get_change_history(
        self,
        key: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Degisiklik gecmisi getirir.

        Args:
            key: Filtre (None=tumu).
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        history = self._change_history
        if key:
            history = [
                h for h in history
                if h["key"] == key
            ]
        return history[-limit:]

    def set_hot_reload(
        self,
        enabled: bool,
    ) -> None:
        """Sicak yuklemeyi ayarlar.

        Args:
            enabled: Aktif mi.
        """
        self._hot_reload_enabled = enabled

    def bulk_set(
        self,
        configs: dict[str, Any],
        source: str = "bulk",
    ) -> dict[str, Any]:
        """Toplu konfigurasyon ayarlar.

        Args:
            configs: Anahtar-deger eslesmesi.
            source: Kaynak.

        Returns:
            Toplu islem sonucu.
        """
        results = []
        for key, value in configs.items():
            r = self.set(key, value, source)
            results.append(r)

        return {
            "total": len(results),
            "changed": sum(
                1 for r in results if r["changed"]
            ),
        }

    @property
    def config_count(self) -> int:
        """Konfigurasyon sayisi."""
        return len(self._configs)

    @property
    def watcher_count(self) -> int:
        """Izleyici sayisi."""
        return sum(
            len(w) for w in self._watchers.values()
        )

    @property
    def change_count(self) -> int:
        """Degisiklik sayisi."""
        return len(self._change_history)

    @property
    def snapshot_count(self) -> int:
        """Snapshot sayisi."""
        return len(self._snapshots)
