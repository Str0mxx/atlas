"""
XSS koruyucu modulu.

XSS tespiti, girdi dogrulama,
cikti kodlama, CSP zorlama,
sanitizasyon.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class XSSProtector:
    """XSS koruyucu.

    Attributes:
        _detections: Tespit kayitlari.
        _csp_policies: CSP politikalari.
        _stats: Istatistikler.
    """

    XSS_PATTERNS: list[dict] = [
        {
            "name": "script_tag",
            "pattern": (
                r"(?i)<\s*script[^>]*>"
            ),
            "severity": "critical",
        },
        {
            "name": "event_handler",
            "pattern": (
                r"(?i)\bon\w+\s*=\s*['\"]"
            ),
            "severity": "high",
        },
        {
            "name": "javascript_uri",
            "pattern": (
                r"(?i)javascript\s*:"
            ),
            "severity": "critical",
        },
        {
            "name": "iframe_inject",
            "pattern": (
                r"(?i)<\s*iframe[^>]*>"
            ),
            "severity": "high",
        },
        {
            "name": "img_onerror",
            "pattern": (
                r"(?i)<\s*img[^>]*"
                r"onerror\s*="
            ),
            "severity": "high",
        },
        {
            "name": "svg_onload",
            "pattern": (
                r"(?i)<\s*svg[^>]*"
                r"onload\s*="
            ),
            "severity": "high",
        },
        {
            "name": "data_uri",
            "pattern": (
                r"(?i)data\s*:\s*text/"
                r"html"
            ),
            "severity": "medium",
        },
    ]

    HTML_ENCODE_MAP: dict[str, str] = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
    }

    def __init__(self) -> None:
        """Koruyucuyu baslatir."""
        self._detections: list[dict] = []
        self._csp_policies: list[dict] = []
        self._stats: dict[str, int] = {
            "checks_done": 0,
            "xss_detected": 0,
            "inputs_sanitized": 0,
            "outputs_encoded": 0,
        }
        logger.info(
            "XSSProtector baslatildi"
        )

    @property
    def detection_count(self) -> int:
        """Tespit sayisi."""
        return len(self._detections)

    def detect_xss(
        self,
        input_str: str = "",
        source: str = "",
    ) -> dict[str, Any]:
        """XSS tespit eder.

        Args:
            input_str: Girdi.
            source: Kaynak.

        Returns:
            Tespit bilgisi.
        """
        try:
            self._stats["checks_done"] += 1
            matched: list[dict] = []

            for p in self.XSS_PATTERNS:
                if re.search(
                    p["pattern"], input_str
                ):
                    matched.append({
                        "name": p["name"],
                        "severity": p[
                            "severity"
                        ],
                    })

            detected = len(matched) > 0
            if detected:
                did = f"xd_{uuid4()!s:.8}"
                record = {
                    "detection_id": did,
                    "patterns": matched,
                    "source": source,
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                self._detections.append(
                    record
                )
                self._stats[
                    "xss_detected"
                ] += 1

            return {
                "detected": detected,
                "patterns": matched,
                "pattern_count": len(
                    matched
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def validate_input(
        self,
        input_str: str = "",
        allowed_tags: (
            list[str] | None
        ) = None,
        max_length: int = 10000,
    ) -> dict[str, Any]:
        """Girdi dogrular.

        Args:
            input_str: Girdi.
            allowed_tags: Izinli etiketler.
            max_length: Maks uzunluk.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            issues: list[str] = []
            tags = allowed_tags or []

            if len(input_str) > max_length:
                issues.append(
                    "Maks uzunluk asildi"
                )

            xss_check = self.detect_xss(
                input_str=input_str
            )
            if xss_check.get("detected"):
                for p in xss_check.get(
                    "patterns", []
                ):
                    if (
                        p["name"]
                        not in tags
                    ):
                        issues.append(
                            f"XSS: {p['name']}"
                        )

            valid = len(issues) == 0

            return {
                "valid": valid,
                "issues": issues,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def encode_output(
        self,
        output_str: str = "",
    ) -> dict[str, Any]:
        """Cikti kodlar.

        Args:
            output_str: Cikti.

        Returns:
            Kodlama bilgisi.
        """
        try:
            encoded = output_str
            for (
                char,
                replacement,
            ) in self.HTML_ENCODE_MAP.items():
                encoded = encoded.replace(
                    char, replacement
                )

            self._stats[
                "outputs_encoded"
            ] += 1

            return {
                "original": output_str,
                "encoded": encoded,
                "modified": (
                    encoded != output_str
                ),
                "encoded_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "encoded_ok": False,
                "error": str(e),
            }

    def sanitize_html(
        self,
        html: str = "",
        allowed_tags: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """HTML sanitize eder.

        Args:
            html: HTML icerigi.
            allowed_tags: Izinli etiketler.

        Returns:
            Sanitize bilgisi.
        """
        try:
            tags = allowed_tags or [
                "b", "i", "em", "strong",
                "p", "br", "ul", "li",
            ]
            sanitized = html

            sanitized = re.sub(
                r"(?i)<\s*script[^>]*>"
                r".*?</\s*script\s*>",
                "",
                sanitized,
                flags=re.DOTALL,
            )
            sanitized = re.sub(
                r"(?i)\bon\w+\s*=\s*"
                r"['\"][^'\"]*['\"]",
                "",
                sanitized,
            )
            sanitized = re.sub(
                r"(?i)javascript\s*:",
                "",
                sanitized,
            )

            self._stats[
                "inputs_sanitized"
            ] += 1

            return {
                "original": html,
                "sanitized": sanitized,
                "modified": (
                    sanitized != html
                ),
                "sanitized_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "sanitized_ok": False,
                "error": str(e),
            }

    def set_csp_policy(
        self,
        name: str = "",
        directives: (
            dict[str, str] | None
        ) = None,
    ) -> dict[str, Any]:
        """CSP politikasi ayarlar.

        Args:
            name: Politika adi.
            directives: CSP direktifleri.

        Returns:
            Ayar bilgisi.
        """
        try:
            dirs = directives or {
                "default-src": "'self'",
                "script-src": "'self'",
                "style-src": (
                    "'self' 'unsafe-inline'"
                ),
                "img-src": "'self' data:",
                "frame-ancestors": "'none'",
            }

            parts = [
                f"{k} {v}"
                for k, v in dirs.items()
            ]
            header = "; ".join(parts)

            policy = {
                "name": name,
                "directives": dirs,
                "header": header,
                "active": True,
            }
            self._csp_policies.append(policy)

            return {
                "name": name,
                "header": header,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
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
            return {
                "total_detections": len(
                    self._detections
                ),
                "csp_policies": len(
                    self._csp_policies
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
