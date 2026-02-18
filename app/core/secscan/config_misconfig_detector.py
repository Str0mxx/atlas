"""
Konfigurasyon hatasi tespitcisi modulu.

Config analizi, guvenlik en iyi uygulamalari,
varsayilan kimlik bilgileri, acik gizli bilgiler,
gucklendirme onerileri.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ConfigMisconfigDetector:
    """Konfigurasyon hatasi tespitcisi.

    Attributes:
        _checks: Kontrol kayitlari.
        _findings: Bulgu kayitlari.
        _rules: Kural kayitlari.
        _stats: Istatistikler.
    """

    DEFAULT_RULES: list[dict] = [
        {
            "name": "debug_enabled",
            "pattern": (
                r"(?i)(debug|DEBUG)\s*"
                r"[=:]\s*(true|True|1|yes)"
            ),
            "severity": "high",
            "suggestion": (
                "Disable debug in production"
            ),
        },
        {
            "name": "default_password",
            "pattern": (
                r"(?i)(password|passwd)\s*"
                r"[=:]\s*['\"]?"
                r"(admin|password|123456|root)"
            ),
            "severity": "critical",
            "suggestion": (
                "Change default passwords"
            ),
        },
        {
            "name": "exposed_port",
            "pattern": (
                r"(?i)(bind|host)\s*[=:]\s*"
                r"['\"]?0\.0\.0\.0"
            ),
            "severity": "medium",
            "suggestion": (
                "Bind to specific interface"
            ),
        },
        {
            "name": "no_ssl",
            "pattern": (
                r"(?i)(ssl|tls|https)\s*"
                r"[=:]\s*(false|False|0|no)"
            ),
            "severity": "high",
            "suggestion": (
                "Enable SSL/TLS encryption"
            ),
        },
        {
            "name": "weak_secret",
            "pattern": (
                r"(?i)secret[_-]?key\s*[=:]\s*"
                r"['\"]?.{1,8}['\"]?"
            ),
            "severity": "critical",
            "suggestion": (
                "Use strong secret keys"
            ),
        },
    ]

    def __init__(self) -> None:
        """Tespitciyi baslatir."""
        self._checks: list[dict] = []
        self._findings: list[dict] = []
        self._rules: list[dict] = list(
            self.DEFAULT_RULES
        )
        self._stats: dict[str, int] = {
            "checks_done": 0,
            "issues_found": 0,
            "issues_resolved": 0,
        }
        logger.info(
            "ConfigMisconfigDetector baslatildi"
        )

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return len(self._checks)

    def add_rule(
        self,
        name: str = "",
        pattern: str = "",
        severity: str = "medium",
        suggestion: str = "",
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            name: Kural adi.
            pattern: Regex deseni.
            severity: Ciddiyet.
            suggestion: Oneri.

        Returns:
            Ekleme bilgisi.
        """
        try:
            re.compile(pattern)
            self._rules.append({
                "name": name,
                "pattern": pattern,
                "severity": severity,
                "suggestion": suggestion,
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

    def check_config(
        self,
        config_content: str = "",
        source: str = "",
        config_type: str = "general",
    ) -> dict[str, Any]:
        """Konfigurasyon kontrol eder.

        Args:
            config_content: Config icerigi.
            source: Kaynak dosya.
            config_type: Config turu.

        Returns:
            Kontrol bilgisi.
        """
        try:
            cid = f"cc_{uuid4()!s:.8}"
            issues: list[dict] = []

            for rule in self._rules:
                matches = re.findall(
                    rule["pattern"],
                    config_content,
                )
                if matches:
                    iid = f"ci_{uuid4()!s:.8}"
                    issue = {
                        "issue_id": iid,
                        "rule": rule["name"],
                        "severity": rule[
                            "severity"
                        ],
                        "suggestion": rule[
                            "suggestion"
                        ],
                        "match_count": len(
                            matches
                        ),
                        "source": source,
                        "resolved": False,
                    }
                    issues.append(issue)
                    self._findings.append(issue)

            check = {
                "check_id": cid,
                "source": source,
                "config_type": config_type,
                "issues_count": len(issues),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._checks.append(check)
            self._stats["checks_done"] += 1
            self._stats[
                "issues_found"
            ] += len(issues)

            return {
                "check_id": cid,
                "issues": issues,
                "total_issues": len(issues),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def resolve_issue(
        self,
        issue_id: str = "",
        resolution: str = "",
    ) -> dict[str, Any]:
        """Sorunu cozer.

        Args:
            issue_id: Sorun ID.
            resolution: Cozum.

        Returns:
            Cozum bilgisi.
        """
        try:
            for f in self._findings:
                if f["issue_id"] == issue_id:
                    f["resolved"] = True
                    f["resolution"] = resolution
                    f[
                        "resolved_at"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    self._stats[
                        "issues_resolved"
                    ] += 1
                    return {
                        "issue_id": issue_id,
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

    def get_hardening_suggestions(
        self,
    ) -> dict[str, Any]:
        """Guclendirme onerileri getirir.

        Returns:
            Oneri bilgisi.
        """
        try:
            unresolved = [
                {
                    "rule": f["rule"],
                    "severity": f["severity"],
                    "suggestion": f[
                        "suggestion"
                    ],
                    "source": f["source"],
                }
                for f in self._findings
                if not f["resolved"]
            ]

            return {
                "suggestions": unresolved,
                "count": len(unresolved),
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
            unresolved = [
                f
                for f in self._findings
                if not f["resolved"]
            ]
            critical = sum(
                1
                for f in unresolved
                if f["severity"] == "critical"
            )

            return {
                "total_checks": len(
                    self._checks
                ),
                "total_issues": len(
                    self._findings
                ),
                "unresolved": len(unresolved),
                "critical": critical,
                "resolved": self._stats[
                    "issues_resolved"
                ],
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
