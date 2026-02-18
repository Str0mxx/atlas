"""
Kimlik sizinti tespitcisi modulu.

Acik kaynak kontrolu, Git gecmisi tarama,
dark web izleme, uyari uretimi,
otomatik iptal.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CredentialLeakDetector:
    """Kimlik sizinti tespitcisi.

    Attributes:
        _patterns: Tespit kaliplari.
        _scans: Tarama kayitlari.
        _leaks: Sizinti kayitlari.
        _alerts: Uyari kayitlari.
        _stats: Istatistikler.
    """

    LEAK_SOURCES: list[str] = [
        "github_public",
        "git_history",
        "dark_web",
        "paste_site",
        "log_file",
        "config_file",
        "environment",
    ]

    SEVERITY_LEVELS: list[str] = [
        "info",
        "warning",
        "critical",
        "emergency",
    ]

    def __init__(
        self,
        auto_revoke: bool = True,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            auto_revoke: Otomatik iptal.
        """
        self._auto_revoke = auto_revoke
        self._patterns: list[dict] = []
        self._scans: list[dict] = []
        self._leaks: list[dict] = []
        self._alerts: list[dict] = []
        self._monitored_keys: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "patterns_registered": 0,
            "scans_run": 0,
            "leaks_detected": 0,
            "alerts_generated": 0,
            "auto_revocations": 0,
        }
        self._init_default_patterns()
        logger.info(
            "CredentialLeakDetector "
            "baslatildi"
        )

    def _init_default_patterns(
        self,
    ) -> None:
        """Varsayilan kaliplari yukler."""
        defaults = [
            {
                "name": "api_key_pattern",
                "pattern": (
                    r"(?:api[_-]?key|"
                    r"apikey)\s*[:=]\s*"
                    r"['\"]?[\w\-]{20,}"
                ),
                "severity": "critical",
            },
            {
                "name": "aws_key_pattern",
                "pattern": (
                    r"AKIA[0-9A-Z]{16}"
                ),
                "severity": "emergency",
            },
            {
                "name": "jwt_pattern",
                "pattern": (
                    r"eyJ[A-Za-z0-9_-]+"
                    r"\.eyJ[A-Za-z0-9_-]+"
                ),
                "severity": "critical",
            },
            {
                "name": "password_pattern",
                "pattern": (
                    r"(?:password|passwd"
                    r"|pwd)\s*[:=]\s*"
                    r"['\"]?[^\s'\"]{8,}"
                ),
                "severity": "critical",
            },
            {
                "name": "private_key",
                "pattern": (
                    r"-----BEGIN\s+"
                    r"(?:RSA\s+)?PRIVATE"
                    r"\s+KEY-----"
                ),
                "severity": "emergency",
            },
        ]
        for d in defaults:
            pid = f"pt_{uuid4()!s:.8}"
            d["pattern_id"] = pid
            self._patterns.append(d)
            self._stats[
                "patterns_registered"
            ] += 1

    @property
    def leak_count(self) -> int:
        """Sizinti sayisi."""
        return len(self._leaks)

    def register_pattern(
        self,
        name: str = "",
        pattern: str = "",
        severity: str = "critical",
        description: str = "",
    ) -> dict[str, Any]:
        """Tespit kalibi ekler.

        Args:
            name: Kalip adi.
            pattern: Regex kalibi.
            severity: Ciddiyet.
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        try:
            if (
                severity
                not in self.SEVERITY_LEVELS
            ):
                return {
                    "registered": False,
                    "error": (
                        f"Gecersiz: "
                        f"{severity}"
                    ),
                }

            pid = f"pt_{uuid4()!s:.8}"
            self._patterns.append({
                "pattern_id": pid,
                "name": name,
                "pattern": pattern,
                "severity": severity,
                "description": description,
            })
            self._stats[
                "patterns_registered"
            ] += 1

            return {
                "pattern_id": pid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def monitor_key(
        self,
        key_id: str = "",
        key_prefix: str = "",
        key_hash: str = "",
        service: str = "",
    ) -> dict[str, Any]:
        """Anahtari izlemeye alir.

        Args:
            key_id: Anahtar ID.
            key_prefix: Anahtar oneki.
            key_hash: Anahtar hash.
            service: Servis adi.

        Returns:
            Izleme bilgisi.
        """
        try:
            kh = key_hash or (
                hashlib.sha256(
                    key_prefix.encode()
                ).hexdigest()[:16]
            )
            self._monitored_keys[key_id] = {
                "key_id": key_id,
                "key_prefix": key_prefix,
                "key_hash": kh,
                "service": service,
                "monitored_since": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "status": "monitoring",
            }

            return {
                "key_id": key_id,
                "key_hash": kh,
                "monitoring": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "monitoring": False,
                "error": str(e),
            }

    def scan_content(
        self,
        content: str = "",
        source: str = "unknown",
        source_url: str = "",
    ) -> dict[str, Any]:
        """Icerigi tarar.

        Args:
            content: Taranacak icerik.
            source: Kaynak.
            source_url: Kaynak URL.

        Returns:
            Tarama sonucu.
        """
        try:
            self._stats["scans_run"] += 1
            findings: list[dict] = []

            for pat in self._patterns:
                try:
                    matches = re.findall(
                        pat["pattern"],
                        content,
                        re.IGNORECASE,
                    )
                    if matches:
                        findings.append({
                            "pattern_name": (
                                pat["name"]
                            ),
                            "severity": (
                                pat["severity"]
                            ),
                            "match_count": (
                                len(matches)
                            ),
                            "sample": (
                                matches[0][:20]
                                + "..."
                            ),
                        })
                except re.error:
                    continue

            # Monitored key kontrolu
            for kid, mk in (
                self._monitored_keys.items()
            ):
                prefix = mk["key_prefix"]
                if prefix and (
                    prefix in content
                ):
                    findings.append({
                        "pattern_name": (
                            "monitored_key"
                        ),
                        "severity": (
                            "emergency"
                        ),
                        "key_id": kid,
                        "match_count": 1,
                    })

            # Sizinti kaydi
            for f in findings:
                lid = f"lk_{uuid4()!s:.8}"
                leak = {
                    "leak_id": lid,
                    "source": source,
                    "source_url": (
                        source_url
                    ),
                    "severity": (
                        f["severity"]
                    ),
                    "pattern_name": (
                        f["pattern_name"]
                    ),
                    "detected_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "status": "detected",
                }
                self._leaks.append(leak)
                self._stats[
                    "leaks_detected"
                ] += 1

                # Uyari
                aid = f"al_{uuid4()!s:.8}"
                alert = {
                    "alert_id": aid,
                    "leak_id": lid,
                    "severity": (
                        f["severity"]
                    ),
                    "message": (
                        f"Sizinti tespit: "
                        f"{f['pattern_name']}"
                    ),
                    "source": source,
                    "auto_revoked": False,
                    "created_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                }

                # Otomatik iptal
                if (
                    self._auto_revoke
                    and f["severity"]
                    in (
                        "critical",
                        "emergency",
                    )
                ):
                    alert[
                        "auto_revoked"
                    ] = True
                    leak["status"] = (
                        "auto_revoked"
                    )
                    self._stats[
                        "auto_revocations"
                    ] += 1

                self._alerts.append(alert)
                self._stats[
                    "alerts_generated"
                ] += 1

            scan = {
                "source": source,
                "findings": len(findings),
                "leaks": findings,
                "scanned": True,
            }
            self._scans.append(scan)

            return scan

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def scan_git_history(
        self,
        commits: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Git gecmisini tarar.

        Args:
            commits: Commit listesi.

        Returns:
            Tarama sonucu.
        """
        try:
            clist = commits or []
            total_findings = 0
            results: list[dict] = []

            for commit in clist:
                content = commit.get(
                    "diff", ""
                )
                cid = commit.get(
                    "commit_id", ""
                )
                result = self.scan_content(
                    content=content,
                    source="git_history",
                    source_url=cid,
                )
                if result.get("findings", 0):
                    total_findings += (
                        result["findings"]
                    )
                    results.append({
                        "commit_id": cid,
                        "findings": result[
                            "findings"
                        ],
                    })

            return {
                "commits_scanned": len(
                    clist
                ),
                "total_findings": (
                    total_findings
                ),
                "affected_commits": (
                    results
                ),
                "scanned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def check_dark_web(
        self,
        key_hash: str = "",
        known_breaches: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Dark web kontrolu yapar.

        Args:
            key_hash: Anahtar hash.
            known_breaches: Bilinen sizintilar.

        Returns:
            Kontrol sonucu.
        """
        try:
            breaches = (
                known_breaches or []
            )
            found: list[dict] = []

            for b in breaches:
                if key_hash in b.get(
                    "hashes", []
                ):
                    found.append({
                        "breach_name": b.get(
                            "name", ""
                        ),
                        "breach_date": b.get(
                            "date", ""
                        ),
                        "severity": (
                            "emergency"
                        ),
                    })

            if found:
                for f in found:
                    lid = (
                        f"lk_{uuid4()!s:.8}"
                    )
                    self._leaks.append({
                        "leak_id": lid,
                        "source": "dark_web",
                        "severity": (
                            "emergency"
                        ),
                        "pattern_name": (
                            f["breach_name"]
                        ),
                        "detected_at": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                        "status": "detected",
                    })
                    self._stats[
                        "leaks_detected"
                    ] += 1

            return {
                "key_hash": key_hash,
                "breaches_checked": len(
                    breaches
                ),
                "found_in_breaches": len(
                    found
                ),
                "details": found,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_alerts(
        self,
        severity: str = "",
    ) -> dict[str, Any]:
        """Uyarilari getirir.

        Args:
            severity: Filtre.

        Returns:
            Uyari listesi.
        """
        try:
            if severity:
                alerts = [
                    a for a in self._alerts
                    if a["severity"]
                    == severity
                ]
            else:
                alerts = list(self._alerts)

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

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_severity: dict[
                str, int
            ] = {}
            for leak in self._leaks:
                s = leak["severity"]
                by_severity[s] = (
                    by_severity.get(s, 0)
                    + 1
                )

            return {
                "total_patterns": len(
                    self._patterns
                ),
                "total_scans": len(
                    self._scans
                ),
                "total_leaks": len(
                    self._leaks
                ),
                "monitored_keys": len(
                    self._monitored_keys
                ),
                "by_severity": by_severity,
                "auto_revoke": (
                    self._auto_revoke
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
