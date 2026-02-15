"""ATLAS IaC Durum Yoneticisi modulu.

Durum depolama, kilitleme,
surumle, uzak durum
ve iceeri/disari aktarma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IaCStateManager:
    """IaC durum yoneticisi.

    Altyapi durumunu yonetir.

    Attributes:
        _state: Mevcut durum.
        _versions: Surum gecmisi.
    """

    def __init__(
        self,
        backend: str = "local",
    ) -> None:
        """Yoneticiyi baslatir.

        Args:
            backend: Arka uc tipi.
        """
        self._backend = backend
        self._state: dict[
            str, dict[str, Any]
        ] = {}
        self._versions: list[
            dict[str, Any]
        ] = []
        self._locks: dict[
            str, dict[str, Any]
        ] = {}
        self._serial = 0

        logger.info(
            "IaCStateManager baslatildi: %s",
            backend,
        )

    def set_resource(
        self,
        resource_key: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Kaynak durumunu ayarlar.

        Args:
            resource_key: Kaynak anahtari.
            state: Durum.

        Returns:
            Durum bilgisi.
        """
        self._state[resource_key] = {
            **state,
            "updated_at": time.time(),
        }

        return {
            "key": resource_key,
            "status": "updated",
        }

    def get_resource(
        self,
        resource_key: str,
    ) -> dict[str, Any] | None:
        """Kaynak durumunu getirir.

        Args:
            resource_key: Kaynak anahtari.

        Returns:
            Durum veya None.
        """
        return self._state.get(resource_key)

    def remove_resource(
        self,
        resource_key: str,
    ) -> bool:
        """Kaynak durumunu kaldirir.

        Args:
            resource_key: Kaynak anahtari.

        Returns:
            Basarili mi.
        """
        if resource_key in self._state:
            del self._state[resource_key]
            return True
        return False

    def save_version(
        self,
        message: str = "",
    ) -> dict[str, Any]:
        """Durum surumunu kaydeder.

        Args:
            message: Surum mesaji.

        Returns:
            Surum bilgisi.
        """
        self._serial += 1
        version = {
            "serial": self._serial,
            "message": message,
            "resource_count": len(self._state),
            "state_snapshot": {
                k: dict(v)
                for k, v in self._state.items()
            },
            "timestamp": time.time(),
        }

        self._versions.append(version)

        return {
            "serial": self._serial,
            "resources": len(self._state),
        }

    def get_version(
        self,
        serial: int,
    ) -> dict[str, Any] | None:
        """Surumu getirir.

        Args:
            serial: Surum numarasi.

        Returns:
            Surum bilgisi veya None.
        """
        for v in self._versions:
            if v["serial"] == serial:
                return v
        return None

    def restore_version(
        self,
        serial: int,
    ) -> dict[str, Any]:
        """Surumu geri yukler.

        Args:
            serial: Surum numarasi.

        Returns:
            Geri yukleme bilgisi.
        """
        version = self.get_version(serial)
        if not version:
            return {"error": "version_not_found"}

        self._state = {
            k: dict(v)
            for k, v
            in version["state_snapshot"].items()
        }

        return {
            "restored_serial": serial,
            "resources": len(self._state),
        }

    def lock(
        self,
        lock_id: str,
        owner: str = "",
    ) -> dict[str, Any]:
        """Durumu kilitler.

        Args:
            lock_id: Kilit ID.
            owner: Kilit sahibi.

        Returns:
            Kilit bilgisi.
        """
        if lock_id in self._locks:
            return {
                "error": "already_locked",
                "owner": (
                    self._locks[lock_id]["owner"]
                ),
            }

        self._locks[lock_id] = {
            "owner": owner,
            "locked_at": time.time(),
        }

        return {
            "lock_id": lock_id,
            "status": "locked",
        }

    def unlock(
        self,
        lock_id: str,
        owner: str = "",
    ) -> dict[str, Any]:
        """Kilidi acar.

        Args:
            lock_id: Kilit ID.
            owner: Kilit sahibi.

        Returns:
            Acma bilgisi.
        """
        lock = self._locks.get(lock_id)
        if not lock:
            return {"error": "not_locked"}

        if owner and lock["owner"] != owner:
            return {"error": "wrong_owner"}

        del self._locks[lock_id]
        return {
            "lock_id": lock_id,
            "status": "unlocked",
        }

    def is_locked(
        self,
        lock_id: str,
    ) -> bool:
        """Kilitli mi kontrol eder.

        Args:
            lock_id: Kilit ID.

        Returns:
            Kilitli mi.
        """
        return lock_id in self._locks

    def export_state(self) -> dict[str, Any]:
        """Durumu disari aktarir.

        Returns:
            Aktarilmis durum.
        """
        return {
            "backend": self._backend,
            "serial": self._serial,
            "resources": {
                k: dict(v)
                for k, v in self._state.items()
            },
            "exported_at": time.time(),
        }

    def import_state(
        self,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Durumu iceri aktarir.

        Args:
            data: Aktarilacak veri.

        Returns:
            Aktarma bilgisi.
        """
        resources = data.get("resources", {})
        imported = 0

        for key, state in resources.items():
            self._state[key] = dict(state)
            imported += 1

        return {
            "imported": imported,
            "total": len(self._state),
        }

    def list_resources(self) -> list[str]:
        """Kaynak anahtarlarini listeler.

        Returns:
            Anahtar listesi.
        """
        return list(self._state.keys())

    def get_versions(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Surumleri getirir.

        Args:
            limit: Limit.

        Returns:
            Surum listesi.
        """
        return [
            {
                "serial": v["serial"],
                "message": v["message"],
                "resource_count": (
                    v["resource_count"]
                ),
                "timestamp": v["timestamp"],
            }
            for v in self._versions[-limit:]
        ]

    @property
    def resource_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._state)

    @property
    def version_count(self) -> int:
        """Surum sayisi."""
        return len(self._versions)

    @property
    def lock_count(self) -> int:
        """Kilit sayisi."""
        return len(self._locks)

    @property
    def serial(self) -> int:
        """Mevcut seri numarasi."""
        return self._serial

    @property
    def backend(self) -> str:
        """Arka uc tipi."""
        return self._backend
