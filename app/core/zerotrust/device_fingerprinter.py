"""
Cihaz parmak izi modulu.

Cihaz tanimlama, parmak izi uretimi,
degisiklik tespiti, guven puanlama,
cihaz kaydi.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DeviceFingerprinter:
    """Cihaz parmak izi.

    Attributes:
        _devices: Cihaz kayitlari.
        _fingerprints: Parmak izleri.
        _changes: Degisiklik gecmisi.
        _stats: Istatistikler.
    """

    COMPONENTS: list[str] = [
        "user_agent",
        "screen_resolution",
        "timezone",
        "language",
        "platform",
        "plugins",
        "canvas_hash",
        "webgl_hash",
    ]

    def __init__(self) -> None:
        """Parmak izi baslatir."""
        self._devices: dict[
            str, dict
        ] = {}
        self._fingerprints: dict[
            str, str
        ] = {}
        self._changes: list[dict] = []
        self._stats: dict[str, int] = {
            "devices_registered": 0,
            "fingerprints_generated": 0,
            "changes_detected": 0,
            "trust_scores_calculated": 0,
        }
        logger.info(
            "DeviceFingerprinter "
            "baslatildi"
        )

    @property
    def device_count(self) -> int:
        """Cihaz sayisi."""
        return len(self._devices)

    def register_device(
        self,
        device_id: str = "",
        user_id: str = "",
        components: dict | None = None,
    ) -> dict[str, Any]:
        """Cihaz kaydeder.

        Args:
            device_id: Cihaz ID.
            user_id: Kullanici ID.
            components: Cihaz bilesenleri.

        Returns:
            Kayit bilgisi.
        """
        try:
            comps = components or {}
            fp = self._generate_fingerprint(
                comps
            )

            self._devices[device_id] = {
                "device_id": device_id,
                "user_id": user_id,
                "components": comps,
                "fingerprint": fp,
                "trust_score": 0.5,
                "seen_count": 1,
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._fingerprints[
                device_id
            ] = fp
            self._stats[
                "devices_registered"
            ] += 1

            return {
                "device_id": device_id,
                "fingerprint": fp,
                "trust_score": 0.5,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def _generate_fingerprint(
        self,
        components: dict,
    ) -> str:
        """Parmak izi uretir."""
        self._stats[
            "fingerprints_generated"
        ] += 1
        parts = sorted(
            f"{k}={v}"
            for k, v in components.items()
        )
        raw = "|".join(parts)
        return hashlib.sha256(
            raw.encode()
        ).hexdigest()[:32]

    def generate_fingerprint(
        self,
        components: dict | None = None,
    ) -> dict[str, Any]:
        """Parmak izi uretir (public).

        Args:
            components: Bilesenleri.

        Returns:
            Parmak izi bilgisi.
        """
        try:
            comps = components or {}
            fp = self._generate_fingerprint(
                comps
            )
            return {
                "fingerprint": fp,
                "components_used": len(
                    comps
                ),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def check_device(
        self,
        device_id: str = "",
        components: dict | None = None,
    ) -> dict[str, Any]:
        """Cihaz kontrol eder.

        Args:
            device_id: Cihaz ID.
            components: Guncel bilesenler.

        Returns:
            Kontrol bilgisi.
        """
        try:
            dev = self._devices.get(
                device_id
            )
            if not dev:
                return {
                    "known": False,
                    "error": (
                        "Cihaz bulunamadi"
                    ),
                }

            comps = components or {}
            new_fp = (
                self._generate_fingerprint(
                    comps
                )
            )
            old_fp = dev["fingerprint"]
            changed = new_fp != old_fp

            if changed:
                self._stats[
                    "changes_detected"
                ] += 1
                changes = (
                    self._detect_changes(
                        dev["components"],
                        comps,
                    )
                )
                self._changes.append({
                    "device_id": device_id,
                    "changes": changes,
                    "old_fp": old_fp,
                    "new_fp": new_fp,
                    "detected_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                })
            else:
                changes = []

            dev["seen_count"] += 1

            return {
                "device_id": device_id,
                "known": True,
                "fingerprint_match": (
                    not changed
                ),
                "changes": changes,
                "trust_score": dev[
                    "trust_score"
                ],
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _detect_changes(
        self,
        old: dict,
        new: dict,
    ) -> list[str]:
        """Degisiklikleri tespit eder."""
        changes: list[str] = []
        all_keys = set(old) | set(new)
        for k in all_keys:
            if old.get(k) != new.get(k):
                changes.append(k)
        return changes

    def calculate_trust(
        self,
        device_id: str = "",
    ) -> dict[str, Any]:
        """Guven puani hesaplar.

        Args:
            device_id: Cihaz ID.

        Returns:
            Guven bilgisi.
        """
        try:
            self._stats[
                "trust_scores_calculated"
            ] += 1
            dev = self._devices.get(
                device_id
            )
            if not dev:
                return {
                    "calculated": False,
                    "error": (
                        "Cihaz bulunamadi"
                    ),
                }

            score = 0.5
            seen = dev["seen_count"]
            if seen >= 10:
                score += 0.3
            elif seen >= 5:
                score += 0.2
            elif seen >= 2:
                score += 0.1

            device_changes = [
                c
                for c in self._changes
                if c["device_id"]
                == device_id
            ]
            if device_changes:
                score -= (
                    len(device_changes) * 0.1
                )

            score = max(0.0, min(1.0, score))
            dev["trust_score"] = round(
                score, 2
            )

            level = "high"
            if score < 0.3:
                level = "low"
            elif score < 0.6:
                level = "medium"

            return {
                "device_id": device_id,
                "trust_score": round(
                    score, 2
                ),
                "trust_level": level,
                "seen_count": seen,
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def revoke_device(
        self,
        device_id: str = "",
    ) -> dict[str, Any]:
        """Cihazi iptal eder.

        Args:
            device_id: Cihaz ID.

        Returns:
            Iptal bilgisi.
        """
        try:
            dev = self._devices.get(
                device_id
            )
            if not dev:
                return {
                    "revoked": False,
                    "error": (
                        "Cihaz bulunamadi"
                    ),
                }

            dev["trust_score"] = 0.0
            dev["revoked"] = True
            return {
                "device_id": device_id,
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_devices": len(
                    self._devices
                ),
                "total_changes": len(
                    self._changes
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
