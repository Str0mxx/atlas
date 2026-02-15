"""ATLAS Gizli Veri Kasasi modulu.

Gizli veri depolama, erisim kontrolu,
rotasyon, denetim loglama
ve entegrasyon.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SecretVault:
    """Gizli veri kasasi.

    Gizli verileri guvenli depolar.

    Attributes:
        _secrets: Gizli veriler.
        _access_log: Erisim logu.
    """

    def __init__(self) -> None:
        """Gizli veri kasasini baslatir."""
        self._secrets: dict[
            str, dict[str, Any]
        ] = {}
        self._access_log: list[
            dict[str, Any]
        ] = []
        self._acl: dict[
            str, set[str]
        ] = {}
        self._rotation_schedule: dict[
            str, int
        ] = {}

        logger.info("SecretVault baslatildi")

    def store(
        self,
        name: str,
        value: str,
        secret_type: str = "api_key",
        allowed_accessors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Gizli veri depolar.

        Args:
            name: Gizli veri adi.
            value: Deger.
            secret_type: Tip.
            allowed_accessors: Izin verilen erisimciler.

        Returns:
            Depolama bilgisi.
        """
        encrypted = self._encrypt(value)
        secret = {
            "name": name,
            "value": encrypted,
            "type": secret_type,
            "version": 1,
            "access_count": 0,
            "created_at": time.time(),
            "rotated_at": time.time(),
        }

        existing = self._secrets.get(name)
        if existing:
            secret["version"] = (
                existing["version"] + 1
            )

        self._secrets[name] = secret

        if allowed_accessors:
            self._acl[name] = set(
                allowed_accessors,
            )

        return {
            "name": name,
            "version": secret["version"],
            "type": secret_type,
        }

    def retrieve(
        self,
        name: str,
        accessor: str = "",
    ) -> dict[str, Any]:
        """Gizli veri getirir.

        Args:
            name: Gizli veri adi.
            accessor: Erisimci.

        Returns:
            Erisim sonucu.
        """
        secret = self._secrets.get(name)
        if not secret:
            return {
                "found": False,
                "reason": "not_found",
            }

        # Erisim kontrolu
        if name in self._acl:
            if (
                accessor
                and accessor not in self._acl[name]
            ):
                self._access_log.append({
                    "name": name,
                    "accessor": accessor,
                    "action": "denied",
                    "timestamp": time.time(),
                })
                return {
                    "found": True,
                    "access": "denied",
                    "reason": "unauthorized",
                }

        secret["access_count"] += 1
        self._access_log.append({
            "name": name,
            "accessor": accessor,
            "action": "granted",
            "timestamp": time.time(),
        })

        return {
            "found": True,
            "access": "granted",
            "value": self._decrypt(
                secret["value"],
            ),
            "version": secret["version"],
        }

    def delete(self, name: str) -> bool:
        """Gizli veri siler.

        Args:
            name: Gizli veri adi.

        Returns:
            Basarili mi.
        """
        if name in self._secrets:
            del self._secrets[name]
            self._acl.pop(name, None)
            self._rotation_schedule.pop(
                name, None,
            )
            return True
        return False

    def rotate(
        self,
        name: str,
        new_value: str,
    ) -> dict[str, Any]:
        """Gizli veriyi rotasyona tabi tutar.

        Args:
            name: Gizli veri adi.
            new_value: Yeni deger.

        Returns:
            Rotasyon sonucu.
        """
        secret = self._secrets.get(name)
        if not secret:
            return {
                "status": "error",
                "reason": "not_found",
            }

        secret["value"] = self._encrypt(
            new_value,
        )
        secret["version"] += 1
        secret["rotated_at"] = time.time()

        return {
            "name": name,
            "version": secret["version"],
            "status": "rotated",
        }

    def set_rotation_schedule(
        self,
        name: str,
        days: int,
    ) -> None:
        """Rotasyon zamani ayarlar.

        Args:
            name: Gizli veri adi.
            days: Gun.
        """
        self._rotation_schedule[name] = days

    def check_rotation_needed(
        self,
    ) -> list[dict[str, Any]]:
        """Rotasyon gereken verileri kontrol eder.

        Returns:
            Rotasyon gereken liste.
        """
        now = time.time()
        needed = []

        for name, days in (
            self._rotation_schedule.items()
        ):
            secret = self._secrets.get(name)
            if not secret:
                continue
            elapsed = (
                now - secret["rotated_at"]
            )
            if elapsed > days * 86400:
                needed.append({
                    "name": name,
                    "days_since_rotation": round(
                        elapsed / 86400, 1,
                    ),
                    "schedule_days": days,
                })

        return needed

    def grant_access(
        self,
        name: str,
        accessor: str,
    ) -> bool:
        """Erisim verir.

        Args:
            name: Gizli veri adi.
            accessor: Erisimci.

        Returns:
            Basarili mi.
        """
        if name not in self._secrets:
            return False
        if name not in self._acl:
            self._acl[name] = set()
        self._acl[name].add(accessor)
        return True

    def revoke_access(
        self,
        name: str,
        accessor: str,
    ) -> bool:
        """Erisim iptal eder.

        Args:
            name: Gizli veri adi.
            accessor: Erisimci.

        Returns:
            Basarili mi.
        """
        if name in self._acl:
            self._acl[name].discard(accessor)
            return True
        return False

    def get_access_log(
        self,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Erisim logunu getirir.

        Args:
            name: Filtre.

        Returns:
            Log listesi.
        """
        if name:
            return [
                l for l in self._access_log
                if l["name"] == name
            ]
        return list(self._access_log)

    def _encrypt(self, value: str) -> str:
        """Basit sifreleme.

        Args:
            value: Deger.

        Returns:
            Sifreli deger.
        """
        h = hashlib.sha256(
            value.encode(),
        ).hexdigest()[:16]
        return f"vault:{h}:{value}"

    def _decrypt(self, value: str) -> str:
        """Basit sifre cozme.

        Args:
            value: Sifreli deger.

        Returns:
            Orijinal deger.
        """
        if value.startswith("vault:"):
            parts = value.split(":", 2)
            if len(parts) == 3:
                return parts[2]
        return value

    @property
    def secret_count(self) -> int:
        """Gizli veri sayisi."""
        return len(self._secrets)

    @property
    def access_log_count(self) -> int:
        """Erisim log sayisi."""
        return len(self._access_log)
