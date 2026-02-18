"""
CVE takipci modulu.

CVE izleme, etki degerlendirmesi,
etkilenen sistemler, yama takibi,
bildirimler.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CVETracker:
    """CVE takipci.

    Attributes:
        _cves: CVE kayitlari.
        _systems: Sistem kayitlari.
        _notifications: Bildirim kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._cves: list[dict] = []
        self._systems: list[dict] = []
        self._notifications: list[dict] = []
        self._stats: dict[str, int] = {
            "cves_tracked": 0,
            "systems_registered": 0,
            "patches_applied": 0,
        }
        logger.info(
            "CVETracker baslatildi"
        )

    @property
    def cve_count(self) -> int:
        """CVE sayisi."""
        return len(self._cves)

    def add_cve(
        self,
        cve_id: str = "",
        description: str = "",
        severity: str = "high",
        cvss_score: float = 0.0,
        affected_software: str = "",
        published_date: str = "",
    ) -> dict[str, Any]:
        """CVE ekler.

        Args:
            cve_id: CVE ID.
            description: Aciklama.
            severity: Ciddiyet.
            cvss_score: CVSS puani.
            affected_software: Etkilenen.
            published_date: Yayin tarihi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            for c in self._cves:
                if c["cve_id"] == cve_id:
                    return {
                        "added": False,
                        "error": "CVE zaten var",
                    }

            cve = {
                "cve_id": cve_id,
                "description": description,
                "severity": severity,
                "cvss_score": cvss_score,
                "affected_software": (
                    affected_software
                ),
                "published_date": (
                    published_date
                    or datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "patched": False,
                "patch_version": "",
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._cves.append(cve)
            self._stats["cves_tracked"] += 1

            return {
                "cve_id": cve_id,
                "severity": severity,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def register_system(
        self,
        name: str = "",
        software: str = "",
        version: str = "",
    ) -> dict[str, Any]:
        """Sistem kayit eder.

        Args:
            name: Sistem adi.
            software: Yazilim.
            version: Surum.

        Returns:
            Kayit bilgisi.
        """
        try:
            sid = f"sy_{uuid4()!s:.8}"
            system = {
                "system_id": sid,
                "name": name,
                "software": software,
                "version": version,
                "registered_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._systems.append(system)
            self._stats[
                "systems_registered"
            ] += 1

            return {
                "system_id": sid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def assess_impact(
        self,
        cve_id: str = "",
    ) -> dict[str, Any]:
        """Etki degerlendirir.

        Args:
            cve_id: CVE ID.

        Returns:
            Degerlendirme bilgisi.
        """
        try:
            cve = None
            for c in self._cves:
                if c["cve_id"] == cve_id:
                    cve = c
                    break

            if not cve:
                return {
                    "assessed": False,
                    "error": "CVE bulunamadi",
                }

            affected = [
                s
                for s in self._systems
                if cve["affected_software"]
                in s["software"]
            ]

            impact = "low"
            if cve["cvss_score"] >= 9.0:
                impact = "critical"
            elif cve["cvss_score"] >= 7.0:
                impact = "high"
            elif cve["cvss_score"] >= 4.0:
                impact = "medium"

            return {
                "cve_id": cve_id,
                "impact": impact,
                "affected_systems": len(
                    affected
                ),
                "cvss_score": cve[
                    "cvss_score"
                ],
                "assessed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def get_affected_systems(
        self,
        cve_id: str = "",
    ) -> dict[str, Any]:
        """Etkilenen sistemleri getirir.

        Args:
            cve_id: CVE ID.

        Returns:
            Sistem bilgisi.
        """
        try:
            cve = None
            for c in self._cves:
                if c["cve_id"] == cve_id:
                    cve = c
                    break

            if not cve:
                return {
                    "retrieved": False,
                    "error": "CVE bulunamadi",
                }

            affected = [
                {
                    "name": s["name"],
                    "software": s[
                        "software"
                    ],
                    "version": s["version"],
                }
                for s in self._systems
                if cve["affected_software"]
                in s["software"]
            ]

            return {
                "cve_id": cve_id,
                "systems": affected,
                "count": len(affected),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def mark_patched(
        self,
        cve_id: str = "",
        patch_version: str = "",
    ) -> dict[str, Any]:
        """CVE yamali isaretler.

        Args:
            cve_id: CVE ID.
            patch_version: Yama surumu.

        Returns:
            Isaret bilgisi.
        """
        try:
            for c in self._cves:
                if c["cve_id"] == cve_id:
                    c["patched"] = True
                    c[
                        "patch_version"
                    ] = patch_version
                    c[
                        "patched_at"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    self._stats[
                        "patches_applied"
                    ] += 1
                    return {
                        "cve_id": cve_id,
                        "patched": True,
                    }

            return {
                "patched": False,
                "error": "CVE bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "patched": False,
                "error": str(e),
            }

    def send_notification(
        self,
        cve_id: str = "",
        channel: str = "telegram",
        recipients: list[str] | None = None,
    ) -> dict[str, Any]:
        """Bildirim gonderir.

        Args:
            cve_id: CVE ID.
            channel: Kanal.
            recipients: Alicilar.

        Returns:
            Bildirim bilgisi.
        """
        try:
            nid = f"cn_{uuid4()!s:.8}"
            notif = {
                "notification_id": nid,
                "cve_id": cve_id,
                "channel": channel,
                "recipients": (
                    recipients or []
                ),
                "sent_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._notifications.append(notif)

            return {
                "notification_id": nid,
                "cve_id": cve_id,
                "sent": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "sent": False,
                "error": str(e),
            }

    def get_unpatched_cves(
        self,
    ) -> dict[str, Any]:
        """Yamasiz CVE'leri getirir.

        Returns:
            CVE bilgisi.
        """
        try:
            unpatched = [
                {
                    "cve_id": c["cve_id"],
                    "severity": c["severity"],
                    "cvss_score": c[
                        "cvss_score"
                    ],
                    "affected_software": c[
                        "affected_software"
                    ],
                }
                for c in self._cves
                if not c["patched"]
            ]

            return {
                "cves": unpatched,
                "count": len(unpatched),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            unpatched = [
                c
                for c in self._cves
                if not c["patched"]
            ]
            critical = sum(
                1
                for c in unpatched
                if c["severity"] == "critical"
            )

            return {
                "total_cves": len(
                    self._cves
                ),
                "unpatched": len(unpatched),
                "critical": critical,
                "systems": len(
                    self._systems
                ),
                "patches_applied": self._stats[
                    "patches_applied"
                ],
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
