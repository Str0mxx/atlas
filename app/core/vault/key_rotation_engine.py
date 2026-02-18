"""
Anahtar rotasyon motoru modulu.

Otomatik rotasyon, zamanlanmis rotasyon,
manuel tetikleme, surum takibi,
geri alma destegi.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class KeyRotationEngine:
    """Anahtar rotasyon motoru.

    Attributes:
        _keys: Anahtar kayitlari.
        _schedules: Zamanlama kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._keys: dict[str, dict] = {}
        self._schedules: dict[str, dict] = {}
        self._stats: dict[str, int] = {
            "keys_created": 0,
            "rotations_done": 0,
            "rollbacks_done": 0,
        }
        logger.info(
            "KeyRotationEngine baslatildi"
        )

    @property
    def key_count(self) -> int:
        """Anahtar sayisi."""
        return len(self._keys)

    def _generate_key(self) -> str:
        """Yeni anahtar uretir."""
        raw = secrets.token_bytes(32)
        return hashlib.sha256(raw).hexdigest()

    def create_key(
        self,
        key_name: str = "",
        algorithm: str = "AES-256",
        rotation_days: int = 90,
        owner: str = "",
    ) -> dict[str, Any]:
        """Anahtar olusturur.

        Args:
            key_name: Anahtar adi.
            algorithm: Algoritma.
            rotation_days: Rotasyon gunu.
            owner: Sahip.

        Returns:
            Olusturma bilgisi.
        """
        try:
            kid = f"ky_{uuid4()!s:.8}"
            key_value = self._generate_key()
            now = datetime.now(
                timezone.utc
            ).isoformat()

            self._keys[key_name] = {
                "key_id": kid,
                "key_name": key_name,
                "current_key": key_value,
                "algorithm": algorithm,
                "version": 1,
                "versions": [
                    {
                        "version": 1,
                        "key_hash": hashlib
                        .sha256(
                            key_value.encode()
                        )
                        .hexdigest()[:16],
                        "created_at": now,
                        "active": True,
                    }
                ],
                "owner": owner,
                "created_at": now,
                "last_rotated": now,
                "active": True,
            }

            self._schedules[key_name] = {
                "rotation_days": rotation_days,
                "auto_rotate": True,
                "last_rotated": now,
            }

            self._stats["keys_created"] += 1

            return {
                "key_id": kid,
                "key_name": key_name,
                "version": 1,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def rotate_key(
        self,
        key_name: str = "",
        reason: str = "scheduled",
    ) -> dict[str, Any]:
        """Anahtari dondurur.

        Args:
            key_name: Anahtar adi.
            reason: Neden.

        Returns:
            Rotasyon bilgisi.
        """
        try:
            if key_name not in self._keys:
                return {
                    "rotated": False,
                    "error": "Bulunamadi",
                }

            key = self._keys[key_name]
            old_version = key["version"]
            new_key = self._generate_key()
            now = datetime.now(
                timezone.utc
            ).isoformat()

            for v in key["versions"]:
                v["active"] = False

            key["version"] += 1
            key["current_key"] = new_key
            key["last_rotated"] = now
            key["versions"].append({
                "version": key["version"],
                "key_hash": hashlib.sha256(
                    new_key.encode()
                ).hexdigest()[:16],
                "created_at": now,
                "active": True,
                "reason": reason,
            })

            if key_name in self._schedules:
                self._schedules[key_name][
                    "last_rotated"
                ] = now

            self._stats[
                "rotations_done"
            ] += 1

            return {
                "key_name": key_name,
                "old_version": old_version,
                "new_version": key["version"],
                "reason": reason,
                "rotated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rotated": False,
                "error": str(e),
            }

    def schedule_rotation(
        self,
        key_name: str = "",
        rotation_days: int = 90,
        auto_rotate: bool = True,
    ) -> dict[str, Any]:
        """Rotasyon zamanlar.

        Args:
            key_name: Anahtar adi.
            rotation_days: Gun sayisi.
            auto_rotate: Otomatik mi.

        Returns:
            Zamanlama bilgisi.
        """
        try:
            if key_name not in self._keys:
                return {
                    "scheduled": False,
                    "error": "Bulunamadi",
                }

            self._schedules[key_name] = {
                "rotation_days": rotation_days,
                "auto_rotate": auto_rotate,
                "last_rotated": self._keys[
                    key_name
                ]["last_rotated"],
            }

            return {
                "key_name": key_name,
                "rotation_days": rotation_days,
                "auto_rotate": auto_rotate,
                "scheduled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scheduled": False,
                "error": str(e),
            }

    def get_key_info(
        self,
        key_name: str = "",
    ) -> dict[str, Any]:
        """Anahtar bilgisi getirir.

        Args:
            key_name: Anahtar adi.

        Returns:
            Anahtar bilgisi.
        """
        try:
            if key_name not in self._keys:
                return {
                    "found": False,
                    "retrieved": True,
                }

            key = self._keys[key_name]
            schedule = self._schedules.get(
                key_name, {}
            )

            return {
                "key_name": key_name,
                "algorithm": key["algorithm"],
                "version": key["version"],
                "total_versions": len(
                    key["versions"]
                ),
                "owner": key["owner"],
                "created_at": key["created_at"],
                "last_rotated": key[
                    "last_rotated"
                ],
                "rotation_days": schedule.get(
                    "rotation_days", 0
                ),
                "auto_rotate": schedule.get(
                    "auto_rotate", False
                ),
                "active": key["active"],
                "found": True,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_version_history(
        self,
        key_name: str = "",
    ) -> dict[str, Any]:
        """Surum gecmisini getirir.

        Args:
            key_name: Anahtar adi.

        Returns:
            Gecmis bilgisi.
        """
        try:
            if key_name not in self._keys:
                return {
                    "versions": [],
                    "retrieved": True,
                }

            versions = self._keys[key_name][
                "versions"
            ]

            return {
                "key_name": key_name,
                "versions": versions,
                "total": len(versions),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def rollback_key(
        self,
        key_name: str = "",
        target_version: int = 0,
    ) -> dict[str, Any]:
        """Anahtari geri alir.

        Args:
            key_name: Anahtar adi.
            target_version: Hedef surum.

        Returns:
            Geri alma bilgisi.
        """
        try:
            if key_name not in self._keys:
                return {
                    "rolled_back": False,
                    "error": "Bulunamadi",
                }

            key = self._keys[key_name]
            target = None
            for v in key["versions"]:
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

            old_version = key["version"]
            for v in key["versions"]:
                v["active"] = (
                    v["version"]
                    == target_version
                )

            key["version"] = target_version
            self._stats["rollbacks_done"] += 1

            return {
                "key_name": key_name,
                "old_version": old_version,
                "restored_version": (
                    target_version
                ),
                "rolled_back": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rolled_back": False,
                "error": str(e),
            }

    def check_rotation_due(
        self,
    ) -> dict[str, Any]:
        """Rotasyon gereken anahtarlari bulur.

        Returns:
            Rotasyon bilgisi.
        """
        try:
            due = []
            for kn, sched in (
                self._schedules.items()
            ):
                if not sched.get(
                    "auto_rotate", False
                ):
                    continue
                due.append({
                    "key_name": kn,
                    "rotation_days": sched[
                        "rotation_days"
                    ],
                    "last_rotated": sched[
                        "last_rotated"
                    ],
                })

            return {
                "due_keys": due,
                "count": len(due),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }
