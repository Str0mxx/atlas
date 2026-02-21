"""Cikti dogrulama yoneticisi.

Cikti tarama, hassas veri tespiti,
filtreleme ve loglama.
"""

import logging
import re
import time
from typing import Any
from uuid import uuid4

from app.models.injectionprotect_models import (
    OutputScanResult,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 10000
_MAX_HISTORY = 10000

# Hassas veri kaliplari
_SENSITIVE_PATTERNS: dict[
    str, dict[str, Any]
] = {
    "credit_card": {
        "pattern": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "mask": "****-****-****-####",
        "description": "Kredi karti numarasi",
    },
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "mask": "***@***.***",
        "description": "E-posta adresi",
    },
    "phone": {
        "pattern": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "mask": "***-***-****",
        "description": "Telefon numarasi",
    },
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "mask": "***-**-****",
        "description": "Sosyal guvenlik no",
    },
    "api_key": {
        "pattern": r"\b(sk|pk|api|key|token|secret)[-_]?[A-Za-z0-9]{16,}\b",
        "mask": "[REDACTED_KEY]",
        "description": "API anahtari",
    },
    "password": {
        "pattern": r"(password|passwd|pwd|sifre)\s*[:=]\s*\S+",
        "mask": "[REDACTED_PASSWORD]",
        "description": "Sifre",
    },
    "ip_address": {
        "pattern": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "mask": "***.***.***.***",
        "description": "IP adresi",
    },
    "tc_kimlik": {
        "pattern": r"\b[1-9]\d{10}\b",
        "mask": "***********",
        "description": "TC kimlik numarasi",
    },
}

# Injection leak kaliplari
_LEAK_PATTERNS: dict[
    str, dict[str, Any]
] = {
    "system_prompt_leak": {
        "pattern": r"(system\s+prompt|my\s+instructions?\s+(are|is)|I\s+was\s+told\s+to)",
        "description": "Sistem prompt sizintisi",
    },
    "internal_error_leak": {
        "pattern": r"(Traceback|stack\s+trace|at\s+line\s+\d+|Error:\s+\w+Error)",
        "description": "Dahili hata sizintisi",
    },
    "path_leak": {
        "pattern": r"(/home/|/var/|/etc/|C:\\\\|/usr/|/opt/)[^\s]+",
        "description": "Dosya yolu sizintisi",
    },
    "env_leak": {
        "pattern": r"(DATABASE_URL|SECRET_KEY|API_KEY|AWS_|REDIS_)\s*=\s*\S+",
        "description": "Ortam degiskeni sizintisi",
    },
}


class OutputValidator:
    """Cikti dogrulama yoneticisi.

    Cikti tarama, hassas veri tespiti,
    filtreleme ve loglama.

    Attributes:
        _records: Tarama sonuc deposu.
    """

    def __init__(
        self,
        redact_sensitive: bool = True,
        check_leaks: bool = True,
        max_output_length: int = 50000,
    ) -> None:
        """OutputValidator baslatir.

        Args:
            redact_sensitive: Hassas veri maskele.
            check_leaks: Sizinti kontrolu.
            max_output_length: Maks cikti uzunlugu.
        """
        self._records: dict[
            str, OutputScanResult
        ] = {}
        self._record_order: list[str] = []
        self._redact = redact_sensitive
        self._check_leaks = check_leaks
        self._max_length = max_output_length
        self._sensitive_patterns: dict[
            str, dict[str, Any]
        ] = dict(_SENSITIVE_PATTERNS)
        self._leak_patterns: dict[
            str, dict[str, Any]
        ] = dict(_LEAK_PATTERNS)
        self._compiled_sensitive: dict[
            str, re.Pattern[str]
        ] = {}
        self._compiled_leaks: dict[
            str, re.Pattern[str]
        ] = {}
        self._total_ops: int = 0
        self._total_scans: int = 0
        self._total_sensitive: int = 0
        self._total_leaks: int = 0
        self._total_redactions: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

        self._compile_patterns()

        logger.info(
            "OutputValidator baslatildi "
            "redact=%s check_leaks=%s",
            self._redact,
            self._check_leaks,
        )

    # ---- Derleme ----

    def _compile_patterns(self) -> None:
        """Kaliplari derler."""
        self._compiled_sensitive.clear()
        for name, info in (
            self._sensitive_patterns.items()
        ):
            try:
                self._compiled_sensitive[
                    name
                ] = re.compile(
                    info["pattern"],
                    re.IGNORECASE,
                )
            except re.error:
                logger.warning(
                    "Kalip derlenemedi: %s",
                    name,
                )

        self._compiled_leaks.clear()
        for name, info in (
            self._leak_patterns.items()
        ):
            try:
                self._compiled_leaks[
                    name
                ] = re.compile(
                    info["pattern"],
                    re.IGNORECASE,
                )
            except re.error:
                pass

    # ---- Tarama ----

    def scan_output(
        self,
        text: str,
    ) -> OutputScanResult:
        """Ciktiyi tarar.

        Args:
            text: Taranacak metin.

        Returns:
            Tarama sonucu.
        """
        if len(self._records) >= _MAX_RECORDS:
            self._rotate()

        scan_id = str(uuid4())[:8]
        now = time.time()
        self._total_scans += 1
        self._total_ops += 1

        sensitive_types: list[str] = []
        redactions = 0
        filtered = text

        # Hassas veri tarama
        for name, regex in (
            self._compiled_sensitive.items()
        ):
            matches = regex.findall(filtered)
            if matches:
                sensitive_types.append(name)
                self._total_sensitive += 1

                if self._redact:
                    mask = (
                        self._sensitive_patterns[
                            name
                        ].get(
                            "mask", "[REDACTED]",
                        )
                    )
                    filtered = regex.sub(
                        mask, filtered,
                    )
                    redactions += len(matches)

        # Sizinti kontrolu
        if self._check_leaks:
            for name, regex in (
                self._compiled_leaks.items()
            ):
                if regex.search(filtered):
                    sensitive_types.append(
                        f"leak:{name}",
                    )
                    self._total_leaks += 1

        # Uzunluk siniri
        if len(filtered) > self._max_length:
            filtered = (
                filtered[: self._max_length]
            )

        self._total_redactions += redactions
        contains_sensitive = (
            len(sensitive_types) > 0
        )

        result = OutputScanResult(
            scan_id=scan_id,
            output_text=text[:500],
            contains_sensitive=contains_sensitive,
            sensitive_types=sensitive_types,
            filtered_output=filtered[:500],
            redactions=redactions,
            timestamp=now,
        )

        self._records[scan_id] = result
        self._record_order.append(scan_id)

        self._record_history(
            "scan_output",
            scan_id,
            f"sensitive={contains_sensitive} "
            f"types={len(sensitive_types)} "
            f"redactions={redactions}",
        )

        return result

    def filter_output(
        self,
        text: str,
    ) -> str:
        """Ciktiyi filtreler.

        Args:
            text: Filtrelenecek metin.

        Returns:
            Filtrelenmis metin.
        """
        result = self.scan_output(text)
        return result.filtered_output

    def check_sensitive(
        self,
        text: str,
    ) -> list[str]:
        """Hassas veri tiplerini dondurur.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Hassas veri tipleri.
        """
        types: list[str] = []
        for name, regex in (
            self._compiled_sensitive.items()
        ):
            if regex.search(text):
                types.append(name)
        return types

    def check_leaks(
        self,
        text: str,
    ) -> list[str]:
        """Sizinti tiplerini dondurur.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Sizinti tipleri.
        """
        types: list[str] = []
        for name, regex in (
            self._compiled_leaks.items()
        ):
            if regex.search(text):
                types.append(name)
        return types

    def batch_scan(
        self,
        texts: list[str],
    ) -> list[OutputScanResult]:
        """Toplu tarama.

        Args:
            texts: Metin listesi.

        Returns:
            Sonuc listesi.
        """
        return [
            self.scan_output(t) for t in texts
        ]

    # ---- Kalip Yonetimi ----

    def add_sensitive_pattern(
        self,
        name: str,
        pattern: str,
        mask: str = "[REDACTED]",
    ) -> bool:
        """Hassas veri kalibi ekler.

        Args:
            name: Kalip adi.
            pattern: Regex kalibi.
            mask: Maskeleme metni.

        Returns:
            Basarili ise True.
        """
        try:
            compiled = re.compile(
                pattern, re.IGNORECASE,
            )
        except re.error:
            return False

        self._sensitive_patterns[name] = {
            "pattern": pattern,
            "mask": mask,
        }
        self._compiled_sensitive[name] = (
            compiled
        )
        self._total_ops += 1
        return True

    def remove_sensitive_pattern(
        self,
        name: str,
    ) -> bool:
        """Hassas veri kalibi siler.

        Args:
            name: Kalip adi.

        Returns:
            Basarili ise True.
        """
        if name not in self._sensitive_patterns:
            return False
        del self._sensitive_patterns[name]
        self._compiled_sensitive.pop(name, None)
        self._total_ops += 1
        return True

    def add_leak_pattern(
        self,
        name: str,
        pattern: str,
    ) -> bool:
        """Sizinti kalibi ekler.

        Args:
            name: Kalip adi.
            pattern: Regex kalibi.

        Returns:
            Basarili ise True.
        """
        try:
            compiled = re.compile(
                pattern, re.IGNORECASE,
            )
        except re.error:
            return False

        self._leak_patterns[name] = {
            "pattern": pattern,
        }
        self._compiled_leaks[name] = compiled
        self._total_ops += 1
        return True

    # ---- Sorgulama ----

    def get_result(
        self,
        scan_id: str,
    ) -> OutputScanResult | None:
        """Sonuc dondurur.

        Args:
            scan_id: Tarama ID.

        Returns:
            Sonuc veya None.
        """
        return self._records.get(scan_id)

    def list_results(
        self,
        sensitive_only: bool = False,
        limit: int = 50,
    ) -> list[OutputScanResult]:
        """Sonuclari listeler.

        Args:
            sensitive_only: Sadece hassas iceren.
            limit: Maks sayi.

        Returns:
            Sonuc listesi.
        """
        ids = list(
            reversed(self._record_order),
        )
        result: list[OutputScanResult] = []

        for rid in ids:
            r = self._records.get(rid)
            if not r:
                continue
            if (
                sensitive_only
                and not r.contains_sensitive
            ):
                continue
            result.append(r)
            if len(result) >= limit:
                break

        return result

    # ---- Gosterim ----

    def format_result(
        self,
        scan_id: str,
    ) -> str:
        """Sonucu formatlar.

        Args:
            scan_id: Tarama ID.

        Returns:
            Formatlenmis metin.
        """
        r = self._records.get(scan_id)
        if not r:
            return ""

        parts = [
            f"Scan ID: {r.scan_id}",
            f"Sensitive: {r.contains_sensitive}",
            f"Types: "
            f"{', '.join(r.sensitive_types)}",
            f"Redactions: {r.redactions}",
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
            "total_scans": self._total_scans,
            "total_sensitive": (
                self._total_sensitive
            ),
            "total_leaks": self._total_leaks,
            "total_redactions": (
                self._total_redactions
            ),
            "sensitive_patterns": len(
                self._sensitive_patterns,
            ),
            "leak_patterns": len(
                self._leak_patterns,
            ),
            "total_ops": self._total_ops,
        }
