"""ATLAS Girdi Dogrulayici modulu.

SQL injection, XSS, command injection,
path traversal onleme ve girdi
temizleme.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class InputValidator:
    """Girdi dogrulayici.

    Zararli girdileri tespit eder
    ve temizler.

    Attributes:
        _rules: Dogrulama kurallari.
        _violations: Ihlal kayitlari.
        _sanitize_map: Temizleme haritasi.
    """

    def __init__(self) -> None:
        """Girdi dogrulayiciyi baslatir."""
        self._rules: dict[str, dict[str, Any]] = {
            "sql_injection": {
                "patterns": [
                    r"('\s*(OR|AND)\s+')",
                    r"(;\s*(DROP|DELETE|UPDATE|INSERT))",
                    r"(UNION\s+SELECT)",
                    r"(1\s*=\s*1)",
                    r"('?\s*--)",
                    r"(/\*.*?\*/)",
                ],
                "enabled": True,
            },
            "xss": {
                "patterns": [
                    r"(<\s*script)",
                    r"(javascript\s*:)",
                    r"(on\w+\s*=)",
                    r"(<\s*iframe)",
                    r"(eval\s*\()",
                    r"(document\.\w+)",
                ],
                "enabled": True,
            },
            "command_injection": {
                "patterns": [
                    r"(;\s*\w+\s)",
                    r"(\|\s*\w+)",
                    r"(&&\s*\w+)",
                    r"(\$\()",
                    r"(`[^`]+`)",
                ],
                "enabled": True,
            },
            "path_traversal": {
                "patterns": [
                    r"(\.\./)",
                    r"(\.\.\\)",
                    r"(%2e%2e)",
                    r"(/etc/(passwd|shadow))",
                    r"(C:\\Windows)",
                ],
                "enabled": True,
            },
        }
        self._violations: list[dict[str, Any]] = []
        self._sanitize_map: dict[str, str] = {
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;",
            "&": "&amp;",
        }

        logger.info("InputValidator baslatildi")

    def validate(
        self,
        input_data: str,
        checks: list[str] | None = None,
    ) -> dict[str, Any]:
        """Girdi dogrular.

        Args:
            input_data: Girdi verisi.
            checks: Kontrol listesi.

        Returns:
            Dogrulama sonucu.
        """
        if checks is None:
            checks = list(self._rules.keys())

        violations: list[dict[str, Any]] = []

        for check_name in checks:
            rule = self._rules.get(check_name)
            if not rule or not rule["enabled"]:
                continue

            for pattern in rule["patterns"]:
                if re.search(pattern, input_data, re.IGNORECASE):
                    violation = {
                        "type": check_name,
                        "pattern": pattern,
                        "input_preview": input_data[:50],
                    }
                    violations.append(violation)
                    self._violations.append(violation)
                    break

        is_safe = len(violations) == 0
        return {
            "safe": is_safe,
            "violations": violations,
            "checks_performed": len(checks),
        }

    def sanitize(
        self,
        input_data: str,
    ) -> str:
        """Girdiyi temizler (HTML escape).

        Args:
            input_data: Ham girdi.

        Returns:
            Temizlenmis girdi.
        """
        result = input_data
        for char, replacement in self._sanitize_map.items():
            result = result.replace(char, replacement)
        return result

    def sanitize_sql(
        self,
        input_data: str,
    ) -> str:
        """SQL icin girdiyi temizler.

        Args:
            input_data: Ham girdi.

        Returns:
            Temizlenmis girdi.
        """
        # Tek tirnaklari escape et
        result = input_data.replace("'", "''")
        # Yorumlari kaldir
        result = re.sub(r"--.*$", "", result)
        result = re.sub(r"/\*.*?\*/", "", result)
        return result.strip()

    def sanitize_path(
        self,
        input_data: str,
    ) -> str:
        """Dosya yolu icin girdiyi temizler.

        Args:
            input_data: Ham yol.

        Returns:
            Temizlenmis yol.
        """
        result = input_data.replace("..", "")
        result = result.replace("~", "")
        result = re.sub(r"[<>|:*?\"\\]", "", result)
        return result

    def validate_email(
        self,
        email: str,
    ) -> bool:
        """E-posta dogrular.

        Args:
            email: E-posta adresi.

        Returns:
            Gecerli ise True.
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def validate_url(
        self,
        url: str,
    ) -> bool:
        """URL dogrular.

        Args:
            url: URL.

        Returns:
            Gecerli ise True.
        """
        pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        return bool(re.match(pattern, url))

    def add_rule(
        self,
        name: str,
        patterns: list[str],
    ) -> None:
        """Dogrulama kurali ekler.

        Args:
            name: Kural adi.
            patterns: Regex desenleri.
        """
        self._rules[name] = {
            "patterns": patterns,
            "enabled": True,
        }

    def disable_rule(self, name: str) -> bool:
        """Kurali devre disi birakir.

        Args:
            name: Kural adi.

        Returns:
            Basarili ise True.
        """
        if name in self._rules:
            self._rules[name]["enabled"] = False
            return True
        return False

    def enable_rule(self, name: str) -> bool:
        """Kurali etkinlestirir.

        Args:
            name: Kural adi.

        Returns:
            Basarili ise True.
        """
        if name in self._rules:
            self._rules[name]["enabled"] = True
            return True
        return False

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def violation_count(self) -> int:
        """Ihlal sayisi."""
        return len(self._violations)
