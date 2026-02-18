"""
Gizli sizinti tarayici modulu.

Kod tarama, log tarama,
oruntu tespiti, uyari uretimi,
duzeltme.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SecretLeakScanner:
    """Gizli sizinti tarayici.

    Attributes:
        _patterns: Tarama oruntuleri.
        _scans: Tarama kayitlari.
        _alerts: Uyarilar.
        _stats: Istatistikler.
    """

    DEFAULT_PATTERNS: list[dict] = [
        {
            "name": "api_key",
            "pattern": (
                r"(?i)(api[_-]?key|apikey)"
                r"\s*[=:]\s*['\"]?"
                r"[a-zA-Z0-9]{20,}"
            ),
            "severity": "high",
        },
        {
            "name": "password",
            "pattern": (
                r"(?i)(password|passwd|pwd)"
                r"\s*[=:]\s*['\"]?"
                r"[^\s'\"]{8,}"
            ),
            "severity": "critical",
        },
        {
            "name": "token",
            "pattern": (
                r"(?i)(token|bearer)"
                r"\s*[=:]\s*['\"]?"
                r"[a-zA-Z0-9_\-.]{20,}"
            ),
            "severity": "high",
        },
        {
            "name": "private_key",
            "pattern": (
                r"-----BEGIN\s+"
                r"(RSA\s+)?PRIVATE\s+KEY-----"
            ),
            "severity": "critical",
        },
        {
            "name": "connection_string",
            "pattern": (
                r"(?i)(mongodb|postgres|mysql|"
                r"redis)://[^\s]+"
            ),
            "severity": "high",
        },
    ]

    def __init__(self) -> None:
        """Tarayiciyi baslatir."""
        self._patterns: list[dict] = list(
            self.DEFAULT_PATTERNS
        )
        self._scans: list[dict] = []
        self._alerts: list[dict] = []
        self._stats: dict[str, int] = {
            "scans_done": 0,
            "leaks_found": 0,
            "alerts_generated": 0,
        }
        logger.info(
            "SecretLeakScanner baslatildi"
        )

    @property
    def scan_count(self) -> int:
        """Tarama sayisi."""
        return len(self._scans)

    def add_pattern(
        self,
        name: str = "",
        pattern: str = "",
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Oruntu ekler.

        Args:
            name: Oruntu adi.
            pattern: Regex deseni.
            severity: Ciddiyet.

        Returns:
            Ekleme bilgisi.
        """
        try:
            re.compile(pattern)
            self._patterns.append({
                "name": name,
                "pattern": pattern,
                "severity": severity,
            })

            return {
                "name": name,
                "added": True,
            }

        except re.error as e:
            return {
                "added": False,
                "error": f"Gecersiz regex: {e}",
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def scan_content(
        self,
        content: str = "",
        source: str = "unknown",
        source_type: str = "code",
    ) -> dict[str, Any]:
        """Icerik tarar.

        Args:
            content: Taranacak icerik.
            source: Kaynak.
            source_type: Kaynak turu.

        Returns:
            Tarama bilgisi.
        """
        try:
            sid = f"sn_{uuid4()!s:.8}"
            findings = []

            for p in self._patterns:
                matches = re.findall(
                    p["pattern"], content
                )
                if matches:
                    findings.append({
                        "pattern_name": p[
                            "name"
                        ],
                        "severity": p[
                            "severity"
                        ],
                        "match_count": len(
                            matches
                        ),
                    })

            scan = {
                "scan_id": sid,
                "source": source,
                "source_type": source_type,
                "findings_count": len(
                    findings
                ),
                "findings": findings,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._scans.append(scan)
            self._stats["scans_done"] += 1
            self._stats[
                "leaks_found"
            ] += len(findings)

            if findings:
                self._generate_alerts(
                    sid, source, findings
                )

            return {
                "scan_id": sid,
                "leak_detected": len(
                    findings
                )
                > 0,
                "findings": findings,
                "scanned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def _generate_alerts(
        self,
        scan_id: str,
        source: str,
        findings: list[dict],
    ) -> None:
        """Uyari uretir."""
        for f in findings:
            self._alerts.append({
                "alert_id": (
                    f"al_{uuid4()!s:.8}"
                ),
                "scan_id": scan_id,
                "source": source,
                "pattern_name": f[
                    "pattern_name"
                ],
                "severity": f["severity"],
                "resolved": False,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            self._stats[
                "alerts_generated"
            ] += 1

    def scan_log(
        self,
        log_content: str = "",
        log_source: str = "",
    ) -> dict[str, Any]:
        """Log tarar.

        Args:
            log_content: Log icerigi.
            log_source: Log kaynagi.

        Returns:
            Tarama bilgisi.
        """
        return self.scan_content(
            content=log_content,
            source=log_source,
            source_type="log",
        )

    def get_alerts(
        self,
        severity: str = "",
        resolved: bool | None = None,
    ) -> dict[str, Any]:
        """Uyarilari getirir.

        Args:
            severity: Ciddiyet filtresi.
            resolved: Cozulmus filtresi.

        Returns:
            Uyari bilgisi.
        """
        try:
            alerts = [
                a
                for a in self._alerts
                if (
                    not severity
                    or a["severity"]
                    == severity
                )
                and (
                    resolved is None
                    or a["resolved"]
                    == resolved
                )
            ]

            return {
                "alerts": alerts,
                "count": len(alerts),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def resolve_alert(
        self,
        alert_id: str = "",
        remediation: str = "",
    ) -> dict[str, Any]:
        """Uyariyi cozer.

        Args:
            alert_id: Uyari ID.
            remediation: Duzeltme.

        Returns:
            Cozum bilgisi.
        """
        try:
            for a in self._alerts:
                if a["alert_id"] == alert_id:
                    a["resolved"] = True
                    a[
                        "remediation"
                    ] = remediation
                    a[
                        "resolved_at"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    return {
                        "alert_id": alert_id,
                        "resolved": True,
                    }

            return {
                "resolved": False,
                "error": "Bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def get_scan_summary(
        self,
    ) -> dict[str, Any]:
        """Tarama ozeti getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            total_findings = sum(
                s["findings_count"]
                for s in self._scans
            )
            critical = sum(
                1
                for a in self._alerts
                if a["severity"] == "critical"
                and not a["resolved"]
            )
            high = sum(
                1
                for a in self._alerts
                if a["severity"] == "high"
                and not a["resolved"]
            )
            unresolved = sum(
                1
                for a in self._alerts
                if not a["resolved"]
            )

            return {
                "total_scans": len(
                    self._scans
                ),
                "total_findings": (
                    total_findings
                ),
                "unresolved_alerts": (
                    unresolved
                ),
                "critical_alerts": critical,
                "high_alerts": high,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
