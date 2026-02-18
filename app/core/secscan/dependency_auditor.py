"""
Bagimlilik denetcisi modulu.

Paket tarama, guncel olmayan tespit,
zafiyetli surumler, guncelleme onerileri,
lisans uyumlulugu.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DependencyAuditor:
    """Bagimlilik denetcisi.

    Attributes:
        _packages: Paket kayitlari.
        _audits: Denetim kayitlari.
        _licenses: Lisans kayitlari.
        _stats: Istatistikler.
    """

    ALLOWED_LICENSES: list[str] = [
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "PSF-2.0",
    ]

    def __init__(self) -> None:
        """Denetciyi baslatir."""
        self._packages: list[dict] = []
        self._audits: list[dict] = []
        self._licenses: dict[str, str] = {}
        self._stats: dict[str, int] = {
            "packages_scanned": 0,
            "vulnerabilities_found": 0,
            "outdated_found": 0,
        }
        logger.info(
            "DependencyAuditor baslatildi"
        )

    @property
    def package_count(self) -> int:
        """Paket sayisi."""
        return len(self._packages)

    def add_package(
        self,
        name: str = "",
        version: str = "",
        latest_version: str = "",
        license_type: str = "",
        source: str = "pip",
    ) -> dict[str, Any]:
        """Paket ekler.

        Args:
            name: Paket adi.
            version: Mevcut surum.
            latest_version: Son surum.
            license_type: Lisans turu.
            source: Kaynak (pip/npm).

        Returns:
            Ekleme bilgisi.
        """
        try:
            pid = f"pk_{uuid4()!s:.8}"
            outdated = (
                latest_version != ""
                and version != latest_version
            )

            pkg = {
                "package_id": pid,
                "name": name,
                "version": version,
                "latest_version": (
                    latest_version or version
                ),
                "license": license_type,
                "source": source,
                "outdated": outdated,
                "vulnerable": False,
                "vulnerabilities": [],
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._packages.append(pkg)

            if license_type:
                self._licenses[name] = (
                    license_type
                )

            if outdated:
                self._stats[
                    "outdated_found"
                ] += 1

            return {
                "package_id": pid,
                "name": name,
                "outdated": outdated,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def report_vulnerability(
        self,
        package_name: str = "",
        cve_id: str = "",
        severity: str = "high",
        description: str = "",
        fixed_version: str = "",
    ) -> dict[str, Any]:
        """Zafiyet bildirir.

        Args:
            package_name: Paket adi.
            cve_id: CVE ID.
            severity: Ciddiyet.
            description: Aciklama.
            fixed_version: Duzeltilmis surum.

        Returns:
            Bildirim bilgisi.
        """
        try:
            for pkg in self._packages:
                if pkg["name"] == package_name:
                    vuln = {
                        "cve_id": cve_id,
                        "severity": severity,
                        "description": description,
                        "fixed_version": (
                            fixed_version
                        ),
                    }
                    pkg["vulnerabilities"].append(
                        vuln
                    )
                    pkg["vulnerable"] = True
                    self._stats[
                        "vulnerabilities_found"
                    ] += 1

                    return {
                        "package": package_name,
                        "cve_id": cve_id,
                        "reported": True,
                    }

            return {
                "reported": False,
                "error": "Paket bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reported": False,
                "error": str(e),
            }

    def audit_packages(
        self,
    ) -> dict[str, Any]:
        """Paketleri denetler.

        Returns:
            Denetim bilgisi.
        """
        try:
            aid = f"au_{uuid4()!s:.8}"
            outdated = [
                p
                for p in self._packages
                if p["outdated"]
            ]
            vulnerable = [
                p
                for p in self._packages
                if p["vulnerable"]
            ]

            audit = {
                "audit_id": aid,
                "total_packages": len(
                    self._packages
                ),
                "outdated_count": len(outdated),
                "vulnerable_count": len(
                    vulnerable
                ),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._audits.append(audit)
            self._stats[
                "packages_scanned"
            ] += len(self._packages)

            return {
                "audit_id": aid,
                "total": len(self._packages),
                "outdated": len(outdated),
                "vulnerable": len(vulnerable),
                "audited": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "audited": False,
                "error": str(e),
            }

    def get_update_recommendations(
        self,
    ) -> dict[str, Any]:
        """Guncelleme onerileri getirir.

        Returns:
            Oneri bilgisi.
        """
        try:
            recs = []
            for pkg in self._packages:
                if pkg["outdated"]:
                    priority = "low"
                    if pkg["vulnerable"]:
                        priority = "critical"
                    recs.append({
                        "name": pkg["name"],
                        "current": pkg[
                            "version"
                        ],
                        "latest": pkg[
                            "latest_version"
                        ],
                        "vulnerable": pkg[
                            "vulnerable"
                        ],
                        "priority": priority,
                    })

            recs.sort(
                key=lambda x: (
                    x["priority"] == "critical"
                ),
                reverse=True,
            )

            return {
                "recommendations": recs,
                "count": len(recs),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def check_license_compliance(
        self,
        allowed: list[str] | None = None,
    ) -> dict[str, Any]:
        """Lisans uyumlulugu kontrol eder.

        Args:
            allowed: Izin verilen lisanslar.

        Returns:
            Uyumluluk bilgisi.
        """
        try:
            ok_licenses = (
                allowed or self.ALLOWED_LICENSES
            )
            violations = []
            for pkg in self._packages:
                lic = pkg["license"]
                if lic and lic not in ok_licenses:
                    violations.append({
                        "name": pkg["name"],
                        "license": lic,
                    })

            return {
                "compliant": len(violations)
                == 0,
                "violations": violations,
                "violation_count": len(
                    violations
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_vulnerable_packages(
        self,
    ) -> dict[str, Any]:
        """Zafiyetli paketleri getirir.

        Returns:
            Paket bilgisi.
        """
        try:
            vulns = [
                {
                    "name": p["name"],
                    "version": p["version"],
                    "vulnerabilities": p[
                        "vulnerabilities"
                    ],
                }
                for p in self._packages
                if p["vulnerable"]
            ]

            return {
                "packages": vulns,
                "count": len(vulns),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
