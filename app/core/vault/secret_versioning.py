"""
Gizli versiyon yonetimi modulu.

Surum kontrolu, gecmis takibi,
fark goruntusu, geri alma,
saklama politikasi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SecretVersioning:
    """Gizli versiyon yonetimi.

    Attributes:
        _secrets: Gizli bilgi surumler.
        _policies: Saklama politikalari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Yonetimi baslatir."""
        self._secrets: dict[
            str, list[dict]
        ] = {}
        self._policies: dict[str, dict] = {}
        self._stats: dict[str, int] = {
            "versions_created": 0,
            "rollbacks_done": 0,
        }
        logger.info(
            "SecretVersioning baslatildi"
        )

    @property
    def secret_count(self) -> int:
        """Gizli bilgi sayisi."""
        return len(self._secrets)

    def create_version(
        self,
        secret_name: str = "",
        value_hash: str = "",
        author: str = "",
        change_note: str = "",
    ) -> dict[str, Any]:
        """Yeni surum olusturur.

        Args:
            secret_name: Gizli bilgi adi.
            value_hash: Deger ozeti.
            author: Yazar.
            change_note: Degisiklik notu.

        Returns:
            Surum bilgisi.
        """
        try:
            vid = f"vr_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()

            if (
                secret_name
                not in self._secrets
            ):
                self._secrets[
                    secret_name
                ] = []

            versions = self._secrets[
                secret_name
            ]
            version_num = len(versions) + 1

            versions.append({
                "version_id": vid,
                "version": version_num,
                "value_hash": value_hash,
                "author": author,
                "change_note": change_note,
                "created_at": now,
                "active": True,
            })

            for v in versions[:-1]:
                v["active"] = False

            self._stats[
                "versions_created"
            ] += 1

            return {
                "version_id": vid,
                "version": version_num,
                "secret_name": secret_name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def get_history(
        self,
        secret_name: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Gecmisi getirir.

        Args:
            secret_name: Gizli bilgi adi.
            limit: Sonuc limiti.

        Returns:
            Gecmis bilgisi.
        """
        try:
            if (
                secret_name
                not in self._secrets
            ):
                return {
                    "history": [],
                    "retrieved": True,
                }

            versions = self._secrets[
                secret_name
            ]
            history = [
                {
                    "version": v["version"],
                    "author": v["author"],
                    "change_note": v[
                        "change_note"
                    ],
                    "active": v["active"],
                    "created_at": v[
                        "created_at"
                    ],
                }
                for v in reversed(versions)
            ][:limit]

            return {
                "secret_name": secret_name,
                "history": history,
                "total_versions": len(
                    versions
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_diff(
        self,
        secret_name: str = "",
        version_a: int = 0,
        version_b: int = 0,
    ) -> dict[str, Any]:
        """Fark goruntuler.

        Args:
            secret_name: Gizli bilgi adi.
            version_a: Ilk surum.
            version_b: Ikinci surum.

        Returns:
            Fark bilgisi.
        """
        try:
            if (
                secret_name
                not in self._secrets
            ):
                return {
                    "diff": None,
                    "retrieved": True,
                }

            versions = self._secrets[
                secret_name
            ]
            va = vb = None
            for v in versions:
                if v["version"] == version_a:
                    va = v
                if v["version"] == version_b:
                    vb = v

            if not va or not vb:
                return {
                    "diff": None,
                    "error": "Surum bulunamadi",
                    "retrieved": True,
                }

            same = (
                va["value_hash"]
                == vb["value_hash"]
            )

            return {
                "secret_name": secret_name,
                "version_a": {
                    "version": va["version"],
                    "hash": va["value_hash"],
                    "author": va["author"],
                },
                "version_b": {
                    "version": vb["version"],
                    "hash": vb["value_hash"],
                    "author": vb["author"],
                },
                "identical": same,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def rollback(
        self,
        secret_name: str = "",
        target_version: int = 0,
    ) -> dict[str, Any]:
        """Geri alir.

        Args:
            secret_name: Gizli bilgi adi.
            target_version: Hedef surum.

        Returns:
            Geri alma bilgisi.
        """
        try:
            if (
                secret_name
                not in self._secrets
            ):
                return {
                    "rolled_back": False,
                    "error": "Bulunamadi",
                }

            versions = self._secrets[
                secret_name
            ]
            target = None
            for v in versions:
                if (
                    v["version"]
                    == target_version
                ):
                    target = v
                    break

            if not target:
                return {
                    "rolled_back": False,
                    "error": "Surum bulunamadi",
                }

            current = None
            for v in versions:
                if v["active"]:
                    current = v["version"]
                v["active"] = (
                    v["version"]
                    == target_version
                )

            self._stats[
                "rollbacks_done"
            ] += 1

            return {
                "secret_name": secret_name,
                "from_version": current,
                "to_version": target_version,
                "rolled_back": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rolled_back": False,
                "error": str(e),
            }

    def set_retention_policy(
        self,
        secret_name: str = "",
        max_versions: int = 10,
        min_age_days: int = 30,
    ) -> dict[str, Any]:
        """Saklama politikasi ayarlar.

        Args:
            secret_name: Gizli bilgi adi.
            max_versions: Maks surum.
            min_age_days: Min yas (gun).

        Returns:
            Politika bilgisi.
        """
        try:
            self._policies[secret_name] = {
                "max_versions": max_versions,
                "min_age_days": min_age_days,
            }

            return {
                "secret_name": secret_name,
                "max_versions": max_versions,
                "min_age_days": min_age_days,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def apply_retention(
        self,
        secret_name: str = "",
    ) -> dict[str, Any]:
        """Saklama politikasini uygular.

        Args:
            secret_name: Gizli bilgi adi.

        Returns:
            Uygulama bilgisi.
        """
        try:
            if (
                secret_name
                not in self._policies
            ):
                return {
                    "applied": False,
                    "error": "Politika yok",
                }

            policy = self._policies[
                secret_name
            ]
            max_v = policy["max_versions"]

            if (
                secret_name
                not in self._secrets
            ):
                return {
                    "purged": 0,
                    "applied": True,
                }

            versions = self._secrets[
                secret_name
            ]
            if len(versions) <= max_v:
                return {
                    "purged": 0,
                    "applied": True,
                }

            keep = versions[-max_v:]
            purged = len(versions) - max_v
            self._secrets[secret_name] = keep

            return {
                "secret_name": secret_name,
                "purged": purged,
                "remaining": len(keep),
                "applied": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "applied": False,
                "error": str(e),
            }
