"""
Enjeksiyon koruyucu modulu.

SQL injection tespiti, command injection,
LDAP injection, XPath injection,
sanitizasyon.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class InjectionGuard:
    """Enjeksiyon koruyucu.

    Attributes:
        _detections: Tespit kayitlari.
        _rules: Kural kayitlari.
        _stats: Istatistikler.
    """

    SQL_PATTERNS: list[dict] = [
        {
            "name": "sql_union",
            "pattern": (
                r"(?i)\b(union\s+(all\s+)?"
                r"select)\b"
            ),
        },
        {
            "name": "sql_or_bypass",
            "pattern": (
                r"(?i)'\s*(or|and)\s+"
                r"['\d].*[=<>]"
            ),
        },
        {
            "name": "sql_comment",
            "pattern": (
                r"(--|#|/\*)"
            ),
        },
        {
            "name": "sql_drop",
            "pattern": (
                r"(?i)\b(drop|alter|"
                r"truncate)\s+table\b"
            ),
        },
        {
            "name": "sql_semicolon",
            "pattern": (
                r"(?i);\s*(select|insert|"
                r"update|delete|drop)\b"
            ),
        },
    ]

    CMD_PATTERNS: list[dict] = [
        {
            "name": "cmd_pipe",
            "pattern": r"\|.*\b(cat|ls|id|whoami)\b",
        },
        {
            "name": "cmd_semicolon",
            "pattern": (
                r";\s*(cat|ls|rm|wget|curl)\b"
            ),
        },
        {
            "name": "cmd_backtick",
            "pattern": r"`[^`]+`",
        },
        {
            "name": "cmd_subshell",
            "pattern": r"\$\([^)]+\)",
        },
    ]

    LDAP_PATTERNS: list[dict] = [
        {
            "name": "ldap_wildcard",
            "pattern": r"\(\*\)",
        },
        {
            "name": "ldap_injection",
            "pattern": (
                r"\)\s*\(\||\)\s*\(&"
            ),
        },
    ]

    XPATH_PATTERNS: list[dict] = [
        {
            "name": "xpath_or",
            "pattern": (
                r"(?i)'\s*or\s+'[^']*'\s*=\s*'"
            ),
        },
        {
            "name": "xpath_comment",
            "pattern": (
                r"(?i)'\s*\]\s*//"
            ),
        },
    ]

    def __init__(self) -> None:
        """Koruyucuyu baslatir."""
        self._detections: list[dict] = []
        self._rules: dict[
            str, list[dict]
        ] = {
            "sql": list(self.SQL_PATTERNS),
            "cmd": list(self.CMD_PATTERNS),
            "ldap": list(self.LDAP_PATTERNS),
            "xpath": list(
                self.XPATH_PATTERNS
            ),
        }
        self._stats: dict[str, int] = {
            "checks_done": 0,
            "injections_detected": 0,
            "inputs_sanitized": 0,
        }
        logger.info(
            "InjectionGuard baslatildi"
        )

    @property
    def detection_count(self) -> int:
        """Tespit sayisi."""
        return len(self._detections)

    def check_sql_injection(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """SQL injection kontrol eder.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Kontrol bilgisi.
        """
        return self._check_injection(
            input_str=input_str,
            source=source,
            injection_type="sql",
            patterns=self._rules["sql"],
        )

    def check_command_injection(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Command injection kontrol eder.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Kontrol bilgisi.
        """
        return self._check_injection(
            input_str=input_str,
            source=source,
            injection_type="cmd",
            patterns=self._rules["cmd"],
        )

    def check_ldap_injection(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """LDAP injection kontrol eder.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Kontrol bilgisi.
        """
        return self._check_injection(
            input_str=input_str,
            source=source,
            injection_type="ldap",
            patterns=self._rules["ldap"],
        )

    def check_xpath_injection(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """XPath injection kontrol eder.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Kontrol bilgisi.
        """
        return self._check_injection(
            input_str=input_str,
            source=source,
            injection_type="xpath",
            patterns=self._rules["xpath"],
        )

    def _check_injection(
        self,
        input_str: str,
        source: str,
        injection_type: str,
        patterns: list[dict],
    ) -> dict[str, Any]:
        """Enjeksiyon kontrol eder."""
        try:
            self._stats["checks_done"] += 1
            matched: list[str] = []

            for p in patterns:
                if re.search(
                    p["pattern"], input_str
                ):
                    matched.append(p["name"])

            detected = len(matched) > 0
            if detected:
                did = f"ij_{uuid4()!s:.8}"
                record = {
                    "detection_id": did,
                    "type": injection_type,
                    "patterns": matched,
                    "source": source,
                    "severity": (
                        "critical"
                        if injection_type
                        == "sql"
                        else "high"
                    ),
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                self._detections.append(
                    record
                )
                self._stats[
                    "injections_detected"
                ] += 1

            return {
                "type": injection_type,
                "detected": detected,
                "patterns": matched,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def check_all(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """Tum enjeksiyonlari kontrol eder.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Kontrol bilgisi.
        """
        try:
            results = {
                "sql": self.check_sql_injection(
                    input_str, source
                ),
                "cmd": self.check_command_injection(
                    input_str, source
                ),
                "ldap": self.check_ldap_injection(
                    input_str, source
                ),
                "xpath": self.check_xpath_injection(
                    input_str, source
                ),
            }
            total = sum(
                len(r.get("patterns", []))
                for r in results.values()
            )

            return {
                "results": results,
                "total_detections": total,
                "any_detected": total > 0,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def sanitize(
        self,
        input_str: str = "",
    ) -> dict[str, Any]:
        """Girdiyi sanitize eder.

        Args:
            input_str: Girdi.

        Returns:
            Sanitize bilgisi.
        """
        try:
            sanitized = input_str
            sanitized = sanitized.replace(
                "'", ""
            )
            sanitized = sanitized.replace(
                '"', ""
            )
            sanitized = sanitized.replace(
                ";", ""
            )
            sanitized = sanitized.replace(
                "--", ""
            )
            sanitized = sanitized.replace(
                "/*", ""
            )
            sanitized = sanitized.replace(
                "*/", ""
            )
            sanitized = re.sub(
                r"[`$|]", "", sanitized
            )

            self._stats[
                "inputs_sanitized"
            ] += 1

            return {
                "original": input_str,
                "sanitized": sanitized,
                "modified": (
                    sanitized != input_str
                ),
                "sanitized_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "sanitized_ok": False,
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
            by_type: dict[str, int] = {}
            for d in self._detections:
                t = d["type"]
                by_type[t] = (
                    by_type.get(t, 0) + 1
                )

            return {
                "total_detections": len(
                    self._detections
                ),
                "by_type": by_type,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
