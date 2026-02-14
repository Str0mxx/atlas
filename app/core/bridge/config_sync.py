"""ATLAS Konfigurasyon Senkronizasyonu modulu.

Paylasilan konfigurasyon, yayilim, sicak yukleme,
tutarlilik kontrolu ve geri alma.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ConfigSync:
    """Konfigurasyon senkronizasyonu.

    Sistemler arasi konfigurasyon paylasimi,
    yayilimi ve tutarliligi yonetir.

    Attributes:
        _shared_config: Paylasilan konfigurasyonlar.
        _system_configs: Sistem bazli konfigurasyonlar.
        _history: Degisiklik gecmisi.
        _listeners: Degisiklik dinleyicileri.
    """

    def __init__(self) -> None:
        """Konfigurasyon senkronizasyonunu baslatir."""
        self._shared_config: dict[str, Any] = {}
        self._system_configs: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._listeners: dict[str, list] = {}
        self._snapshots: list[dict[str, Any]] = []

        logger.info("ConfigSync baslatildi")

    def set_shared(
        self,
        key: str,
        value: Any,
        source: str = "",
    ) -> None:
        """Paylasilan konfigurasyon ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
            source: Degistiren sistem.
        """
        old_value = self._shared_config.get(key)
        self._shared_config[key] = value

        # Gecmise kaydet
        self._history.append({
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Dinleyicileri bilgilendir
        for listener in self._listeners.get(key, []):
            try:
                listener(key, value, old_value)
            except Exception as e:
                logger.error("Listener hatasi: %s", e)

    def get_shared(self, key: str, default: Any = None) -> Any:
        """Paylasilan konfigurasyon getirir.

        Args:
            key: Anahtar.
            default: Varsayilan deger.

        Returns:
            Deger.
        """
        return self._shared_config.get(key, default)

    def get_all_shared(self) -> dict[str, Any]:
        """Tum paylasilan konfigurasyonlari getirir.

        Returns:
            Konfigurasyon sozlugu.
        """
        return dict(self._shared_config)

    def set_system_config(
        self,
        system_id: str,
        config: dict[str, Any],
    ) -> None:
        """Sistem konfigurasyonu ayarlar.

        Args:
            system_id: Sistem ID.
            config: Konfigurasyon.
        """
        self._system_configs[system_id] = config

    def get_system_config(
        self,
        system_id: str,
    ) -> dict[str, Any]:
        """Sistem konfigurasyonunu getirir.

        Args:
            system_id: Sistem ID.

        Returns:
            Konfigurasyon sozlugu.
        """
        return dict(self._system_configs.get(system_id, {}))

    def propagate(
        self,
        key: str,
        systems: list[str] | None = None,
    ) -> int:
        """Konfigurasyonu sistemlere yayar.

        Args:
            key: Anahtar.
            systems: Hedef sistemler (None=tumu).

        Returns:
            Guncellenen sistem sayisi.
        """
        value = self._shared_config.get(key)
        if value is None:
            return 0

        targets = systems or list(self._system_configs.keys())
        updated = 0

        for system_id in targets:
            config = self._system_configs.get(system_id, {})
            config[key] = value
            self._system_configs[system_id] = config
            updated += 1

        return updated

    def add_listener(
        self,
        key: str,
        listener: Any,
    ) -> None:
        """Degisiklik dinleyici ekler.

        Args:
            key: Izlenecek anahtar.
            listener: Dinleyici (key, new, old) -> None.
        """
        self._listeners.setdefault(key, []).append(listener)

    def remove_listener(
        self,
        key: str,
        listener: Any,
    ) -> bool:
        """Dinleyici kaldirir.

        Args:
            key: Anahtar.
            listener: Dinleyici.

        Returns:
            Basarili ise True.
        """
        listeners = self._listeners.get(key, [])
        if listener in listeners:
            listeners.remove(listener)
            return True
        return False

    def check_consistency(self) -> list[dict[str, Any]]:
        """Tutarlilik kontrolu yapar.

        Returns:
            Tutarsizlik listesi.
        """
        inconsistencies: list[dict[str, Any]] = []

        for key, shared_value in self._shared_config.items():
            for system_id, config in self._system_configs.items():
                if key in config and config[key] != shared_value:
                    inconsistencies.append({
                        "key": key,
                        "system_id": system_id,
                        "shared_value": shared_value,
                        "system_value": config[key],
                    })

        return inconsistencies

    def create_snapshot(self) -> str:
        """Konfigurasyon snapshot'i olusturur.

        Returns:
            Snapshot ID.
        """
        snapshot_id = f"snap-{len(self._snapshots)}"
        self._snapshots.append({
            "snapshot_id": snapshot_id,
            "shared": dict(self._shared_config),
            "systems": {
                k: dict(v) for k, v in self._system_configs.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return snapshot_id

    def rollback(self, snapshot_id: str) -> bool:
        """Snapshot'a geri doner.

        Args:
            snapshot_id: Snapshot ID.

        Returns:
            Basarili ise True.
        """
        for snap in self._snapshots:
            if snap["snapshot_id"] == snapshot_id:
                self._shared_config = dict(snap["shared"])
                self._system_configs = {
                    k: dict(v) for k, v in snap["systems"].items()
                }
                return True
        return False

    def get_history(
        self,
        key: str = "",
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Degisiklik gecmisini getirir.

        Args:
            key: Anahtar filtresi.
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        history = list(self._history)
        if key:
            history = [h for h in history if h["key"] == key]
        if limit > 0:
            history = history[-limit:]
        return history

    @property
    def shared_count(self) -> int:
        """Paylasilan konfigurasyon sayisi."""
        return len(self._shared_config)

    @property
    def system_count(self) -> int:
        """Konfigure edilen sistem sayisi."""
        return len(self._system_configs)

    @property
    def snapshot_count(self) -> int:
        """Snapshot sayisi."""
        return len(self._snapshots)
