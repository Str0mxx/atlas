"""Girdi temizleme yoneticisi.

Girdi temizleme, kacis dizileri,
kodlama duzeltme ve dogrulama.
"""

import html
import logging
import re
import time
from typing import Any
from uuid import uuid4

from app.models.injectionprotect_models import (
    SanitizeResult,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 10000
_MAX_HISTORY = 10000

# Temizleme kurallari
_SANITIZE_RULES: list[dict[str, Any]] = [
    {
        "name": "null_bytes",
        "pattern": r"\x00|%00|\\x00|\\u0000",
        "replacement": "",
        "description": "Null byte temizleme",
    },
    {
        "name": "sql_comments",
        "pattern": r"/\*.*?\*/|--[^\n]*",
        "replacement": "",
        "description": "SQL yorum temizleme",
    },
    {
        "name": "html_tags",
        "pattern": r"<[^>]+>",
        "replacement": "",
        "description": "HTML etiket temizleme",
    },
    {
        "name": "script_tags",
        "pattern": r"<\s*script[^>]*>.*?</\s*script\s*>",
        "replacement": "",
        "description": "Script etiket temizleme",
    },
    {
        "name": "command_separators",
        "pattern": r"[;&|`](?=\s*(cat|ls|rm|wget|curl|nc|bash|sh|python))",
        "replacement": " ",
        "description": "Komut ayirici temizleme",
    },
    {
        "name": "path_traversal",
        "pattern": r"\.\.(/|\\|%2f|%5c)",
        "replacement": "",
        "description": "Dizin gezinme temizleme",
    },
    {
        "name": "crlf_injection",
        "pattern": r"%0d%0a|%0a|%0d|\r\n",
        "replacement": "\n",
        "description": "CRLF injection temizleme",
    },
]

# Kodlama duzeltme kaliplari
_ENCODING_FIXES: list[dict[str, Any]] = [
    {
        "name": "double_url_encode",
        "pattern": r"%25([0-9a-fA-F]{2})",
        "replacement": r"%\1",
        "description": "Cift URL kodlama",
    },
    {
        "name": "unicode_escape",
        "pattern": r"\\u([0-9a-fA-F]{4})",
        "replacement": "",
        "description": "Unicode kacis",
    },
    {
        "name": "hex_escape",
        "pattern": r"\\x([0-9a-fA-F]{2})",
        "replacement": "",
        "description": "Hex kacis",
    },
]


class InputSanitizer:
    """Girdi temizleme yoneticisi.

    Girdi temizleme, kacis dizileri,
    kodlama duzeltme ve dogrulama.

    Attributes:
        _records: Temizleme sonuc deposu.
    """

    def __init__(
        self,
        max_input_length: int = 10000,
        strip_html: bool = True,
        fix_encoding: bool = True,
    ) -> None:
        """InputSanitizer baslatir.

        Args:
            max_input_length: Maks girdi uzunlugu.
            strip_html: HTML temizle.
            fix_encoding: Kodlama duzelt.
        """
        self._records: dict[
            str, SanitizeResult
        ] = {}
        self._record_order: list[str] = []
        self._max_length = max_input_length
        self._strip_html = strip_html
        self._fix_encoding = fix_encoding
        self._rules: list[
            dict[str, Any]
        ] = list(_SANITIZE_RULES)
        self._encoding_fixes: list[
            dict[str, Any]
        ] = list(_ENCODING_FIXES)
        self._compiled_rules: list[
            dict[str, Any]
        ] = []
        self._compiled_encoding: list[
            dict[str, Any]
        ] = []
        self._total_ops: int = 0
        self._total_sanitized: int = 0
        self._total_threats_removed: int = 0
        self._total_encoding_fixed: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

        self._compile_rules()

        logger.info(
            "InputSanitizer baslatildi "
            "max_length=%d rules=%d",
            self._max_length,
            len(self._rules),
        )

    # ---- Derleme ----

    def _compile_rules(self) -> None:
        """Kurallari derler."""
        self._compiled_rules.clear()
        for rule in self._rules:
            try:
                compiled = re.compile(
                    rule["pattern"],
                    re.IGNORECASE | re.DOTALL,
                )
                self._compiled_rules.append({
                    "name": rule["name"],
                    "regex": compiled,
                    "replacement": (
                        rule["replacement"]
                    ),
                })
            except re.error:
                logger.warning(
                    "Kural derlenemedi: %s",
                    rule["name"],
                )

        self._compiled_encoding.clear()
        for fix in self._encoding_fixes:
            try:
                compiled = re.compile(
                    fix["pattern"],
                    re.IGNORECASE,
                )
                self._compiled_encoding.append({
                    "name": fix["name"],
                    "regex": compiled,
                    "replacement": (
                        fix["replacement"]
                    ),
                })
            except re.error:
                pass

    # ---- Temizleme ----

    def sanitize(
        self,
        text: str,
    ) -> SanitizeResult:
        """Girdiyi temizler.

        Args:
            text: Temizlenecek metin.

        Returns:
            Temizleme sonucu.
        """
        if len(self._records) >= _MAX_RECORDS:
            self._rotate()

        result_id = str(uuid4())[:8]
        now = time.time()
        self._total_sanitized += 1
        self._total_ops += 1

        original = text
        changes: list[str] = []
        threat_removed = False
        encoding_fixed = False

        # Uzunluk sinirla
        if len(text) > self._max_length:
            text = text[: self._max_length]
            changes.append(
                f"truncated to "
                f"{self._max_length} chars",
            )

        # Kural tabanli temizleme
        for rule in self._compiled_rules:
            regex = rule["regex"]
            if regex.search(text):
                text = regex.sub(
                    rule["replacement"], text,
                )
                changes.append(rule["name"])
                threat_removed = True

        # Kodlama duzeltme
        if self._fix_encoding:
            for fix in self._compiled_encoding:
                regex = fix["regex"]
                if regex.search(text):
                    text = regex.sub(
                        fix["replacement"], text,
                    )
                    changes.append(
                        f"encoding:{fix['name']}",
                    )
                    encoding_fixed = True

        # HTML temizleme
        if self._strip_html:
            decoded = html.unescape(text)
            if decoded != text:
                changes.append("html_unescape")
                text = decoded

        # Fazla bosluk temizle
        cleaned = re.sub(
            r"\s+", " ", text,
        ).strip()
        if cleaned != text:
            changes.append("whitespace_normalize")
            text = cleaned

        if threat_removed:
            self._total_threats_removed += 1
        if encoding_fixed:
            self._total_encoding_fixed += 1

        result = SanitizeResult(
            result_id=result_id,
            original=original[:500],
            sanitized=text[:500],
            changes_made=changes,
            threat_removed=threat_removed,
            encoding_fixed=encoding_fixed,
            timestamp=now,
        )

        self._records[result_id] = result
        self._record_order.append(result_id)

        self._record_history(
            "sanitize",
            result_id,
            f"changes={len(changes)} "
            f"threat={threat_removed}",
        )

        return result

    def validate_input(
        self,
        text: str,
        allowed_chars: str = "",
        max_length: int = 0,
    ) -> dict[str, Any]:
        """Girdiyi dogrular.

        Args:
            text: Dogrulanacak metin.
            allowed_chars: Izin verilen karakterler.
            max_length: Maks uzunluk.

        Returns:
            Dogrulama sonucu.
        """
        issues: list[str] = []
        max_len = max_length or self._max_length

        if len(text) > max_len:
            issues.append(
                f"length exceeds {max_len}",
            )

        if allowed_chars:
            invalid = set(text) - set(
                allowed_chars,
            )
            if invalid:
                issues.append(
                    f"invalid chars: "
                    f"{','.join(sorted(invalid)[:5])}",
                )

        # Null byte kontrolu
        if "\x00" in text or "%00" in text:
            issues.append("contains null bytes")

        # Kontrol karakter kontrolu
        control_chars = sum(
            1 for c in text
            if ord(c) < 32
            and c not in "\n\r\t"
        )
        if control_chars > 0:
            issues.append(
                f"control chars: {control_chars}",
            )

        self._total_ops += 1

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "length": len(text),
            "max_length": max_len,
        }

    def escape_for_output(
        self,
        text: str,
        context: str = "html",
    ) -> str:
        """Cikis icin metin kacislar.

        Args:
            text: Kacirilacak metin.
            context: Cikis baglami.

        Returns:
            Kacirilmis metin.
        """
        if context == "html":
            return html.escape(text)
        elif context == "sql":
            return text.replace("'", "''")
        elif context == "shell":
            return re.sub(
                r"[;&|`$(){}]", "", text,
            )
        return text

    def batch_sanitize(
        self,
        texts: list[str],
    ) -> list[SanitizeResult]:
        """Toplu temizleme.

        Args:
            texts: Metin listesi.

        Returns:
            Sonuc listesi.
        """
        return [self.sanitize(t) for t in texts]

    # ---- Kural Yonetimi ----

    def add_rule(
        self,
        name: str,
        pattern: str,
        replacement: str = "",
    ) -> bool:
        """Kural ekler.

        Args:
            name: Kural adi.
            pattern: Regex kalibi.
            replacement: Degistirme metni.

        Returns:
            Basarili ise True.
        """
        try:
            compiled = re.compile(
                pattern,
                re.IGNORECASE | re.DOTALL,
            )
        except re.error:
            return False

        self._rules.append({
            "name": name,
            "pattern": pattern,
            "replacement": replacement,
        })
        self._compiled_rules.append({
            "name": name,
            "regex": compiled,
            "replacement": replacement,
        })
        self._total_ops += 1
        return True

    def remove_rule(
        self,
        name: str,
    ) -> bool:
        """Kural siler.

        Args:
            name: Kural adi.

        Returns:
            Basarili ise True.
        """
        before = len(self._rules)
        self._rules = [
            r for r in self._rules
            if r["name"] != name
        ]
        self._compiled_rules = [
            r for r in self._compiled_rules
            if r["name"] != name
        ]
        removed = before - len(self._rules)
        if removed > 0:
            self._total_ops += 1
        return removed > 0

    def list_rules(
        self,
    ) -> list[dict[str, Any]]:
        """Kurallari listeler.

        Returns:
            Kural listesi.
        """
        return list(self._rules)

    # ---- Sorgulama ----

    def get_result(
        self,
        result_id: str,
    ) -> SanitizeResult | None:
        """Sonuc dondurur.

        Args:
            result_id: Sonuc ID.

        Returns:
            Sonuc veya None.
        """
        return self._records.get(result_id)

    def list_results(
        self,
        threats_only: bool = False,
        limit: int = 50,
    ) -> list[SanitizeResult]:
        """Sonuclari listeler.

        Args:
            threats_only: Sadece tehdit iceren.
            limit: Maks sayi.

        Returns:
            Sonuc listesi.
        """
        ids = list(
            reversed(self._record_order),
        )
        result: list[SanitizeResult] = []

        for rid in ids:
            r = self._records.get(rid)
            if not r:
                continue
            if (
                threats_only
                and not r.threat_removed
            ):
                continue
            result.append(r)
            if len(result) >= limit:
                break

        return result

    # ---- Gosterim ----

    def format_result(
        self,
        result_id: str,
    ) -> str:
        """Sonucu formatlar.

        Args:
            result_id: Sonuc ID.

        Returns:
            Formatlenmis metin.
        """
        r = self._records.get(result_id)
        if not r:
            return ""

        parts = [
            f"Sanitize ID: {r.result_id}",
            f"Changes: "
            f"{', '.join(r.changes_made)}",
            f"Threat Removed: "
            f"{r.threat_removed}",
            f"Encoding Fixed: "
            f"{r.encoding_fixed}",
        ]
        return "\n".join(parts)

    # ---- Temizlik ----

    def clear_results(self) -> int:
        """Sonuclari temizler.

        Returns:
            Silinen sayi.
        """
        count = len(self._records)
        self._records.clear()
        self._record_order.clear()
        self._total_ops += 1
        return count

    # ---- Dahili ----

    def _rotate(self) -> int:
        """Eski kayitlari temizler."""
        keep = _MAX_RECORDS // 2
        if len(self._record_order) <= keep:
            return 0

        to_remove = self._record_order[:-keep]
        for rid in to_remove:
            self._records.pop(rid, None)

        self._record_order = (
            self._record_order[-keep:]
        )
        return len(to_remove)

    def _record_history(
        self,
        action: str,
        record_id: str,
        detail: str,
    ) -> None:
        """Aksiyonu kaydeder."""
        self._history.append({
            "action": action,
            "record_id": record_id,
            "detail": detail,
            "timestamp": time.time(),
        })
        if len(self._history) > _MAX_HISTORY:
            self._history = (
                self._history[-5000:]
            )

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gecmisi dondurur."""
        return list(
            reversed(
                self._history[-limit:],
            ),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur."""
        return {
            "total_records": len(
                self._records,
            ),
            "total_sanitized": (
                self._total_sanitized
            ),
            "total_threats_removed": (
                self._total_threats_removed
            ),
            "total_encoding_fixed": (
                self._total_encoding_fixed
            ),
            "max_length": self._max_length,
            "rule_count": len(self._rules),
            "total_ops": self._total_ops,
        }
