"""Prompt injection tespit yoneticisi.

Kalip esleme, sezgisel analiz,
ML tabanli tespit ve puanlama.
"""

import logging
import re
import time
from typing import Any
from uuid import uuid4

from app.models.injectionprotect_models import (
    ActionTaken,
    DetectionResult,
    SeverityLevel,
    ThreatType,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 10000
_MAX_HISTORY = 10000

# Varsayilan injection kaliplari
_DEFAULT_PATTERNS: dict[str, dict[str, Any]] = {
    "ignore_previous": {
        "pattern": r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|rules)",
        "threat_type": ThreatType.PROMPT_INJECTION,
        "severity": SeverityLevel.HIGH,
        "score": 0.9,
    },
    "system_override": {
        "pattern": r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|new\s+instructions?)",
        "threat_type": ThreatType.JAILBREAK,
        "severity": SeverityLevel.HIGH,
        "score": 0.85,
    },
    "sql_injection": {
        "pattern": r"('|\"|;)\s*(OR|AND|UNION|SELECT|DROP|DELETE|INSERT|UPDATE)\s",
        "threat_type": ThreatType.SQL_INJECTION,
        "severity": SeverityLevel.CRITICAL,
        "score": 0.95,
    },
    "command_injection": {
        "pattern": r"[;&|`]\s*(cat|ls|rm|wget|curl|nc|bash|sh|python|perl)\s",
        "threat_type": ThreatType.COMMAND_INJECTION,
        "severity": SeverityLevel.CRITICAL,
        "score": 0.95,
    },
    "xss_script": {
        "pattern": r"<\s*script[^>]*>|javascript\s*:|on(load|error|click)\s*=",
        "threat_type": ThreatType.XSS,
        "severity": SeverityLevel.HIGH,
        "score": 0.9,
    },
    "path_traversal": {
        "pattern": r"\.\./|\.\.\\|%2e%2e[/\\]",
        "threat_type": ThreatType.PATH_TRAVERSAL,
        "severity": SeverityLevel.HIGH,
        "score": 0.85,
    },
    "encoding_attack": {
        "pattern": r"(%00|%0a|%0d|\\x00|\\n.*\\n|\\u0000)",
        "threat_type": ThreatType.ENCODING_ATTACK,
        "severity": SeverityLevel.MEDIUM,
        "score": 0.7,
    },
    "data_exfil": {
        "pattern": r"(send|post|upload|exfiltrate|leak)\s+(data|info|secret|password|key|token)",
        "threat_type": ThreatType.DATA_EXFILTRATION,
        "severity": SeverityLevel.HIGH,
        "score": 0.85,
    },
    "social_engineering": {
        "pattern": r"(do\s+not\s+tell|keep\s+secret|don'?t\s+mention|hide\s+this)",
        "threat_type": ThreatType.SOCIAL_ENGINEERING,
        "severity": SeverityLevel.MEDIUM,
        "score": 0.7,
    },
    "jailbreak_dan": {
        "pattern": r"(DAN|do\s+anything\s+now|developer\s+mode|jailbreak)",
        "threat_type": ThreatType.JAILBREAK,
        "severity": SeverityLevel.HIGH,
        "score": 0.9,
    },
}

# Sezgisel sinyaller
_HEURISTIC_SIGNALS: list[dict[str, Any]] = [
    {
        "name": "excessive_instructions",
        "check": "instruction_count",
        "threshold": 5,
        "score": 0.3,
    },
    {
        "name": "role_manipulation",
        "check": "role_keywords",
        "threshold": 2,
        "score": 0.4,
    },
    {
        "name": "encoding_mix",
        "check": "encoding_variety",
        "threshold": 3,
        "score": 0.35,
    },
    {
        "name": "length_anomaly",
        "check": "text_length",
        "threshold": 5000,
        "score": 0.2,
    },
]


class InjectionDetector:
    """Prompt injection tespit yoneticisi.

    Kalip esleme, sezgisel analiz,
    ML tabanli tespit ve puanlama.

    Attributes:
        _records: Tespit sonuc deposu.
    """

    def __init__(
        self,
        detection_level: str = "medium",
        threshold: float = 0.5,
    ) -> None:
        """InjectionDetector baslatir.

        Args:
            detection_level: Tespit seviyesi.
            threshold: Tehdit esik degeri.
        """
        self._records: dict[
            str, DetectionResult
        ] = {}
        self._record_order: list[str] = []
        self._detection_level = detection_level
        self._threshold = threshold
        self._patterns: dict[
            str, dict[str, Any]
        ] = dict(_DEFAULT_PATTERNS)
        self._heuristics: list[
            dict[str, Any]
        ] = list(_HEURISTIC_SIGNALS)
        self._compiled: dict[
            str, re.Pattern[str]
        ] = {}
        self._total_ops: int = 0
        self._total_scans: int = 0
        self._total_threats: int = 0
        self._total_clean: int = 0
        self._history: list[
            dict[str, Any]
        ] = []

        self._compile_patterns()

        logger.info(
            "InjectionDetector baslatildi "
            "level=%s threshold=%.2f "
            "patterns=%d",
            self._detection_level,
            self._threshold,
            len(self._patterns),
        )

    # ---- Derleme ----

    def _compile_patterns(self) -> None:
        """Kaliplari derler."""
        self._compiled.clear()
        for name, info in self._patterns.items():
            try:
                self._compiled[name] = re.compile(
                    info["pattern"],
                    re.IGNORECASE,
                )
            except re.error:
                logger.warning(
                    "Kalip derlenemedi: %s", name,
                )

    # ---- Tespit ----

    def detect(
        self,
        text: str,
        context: str = "",
    ) -> DetectionResult:
        """Girdi metninde injection tespit eder.

        Args:
            text: Kontrol edilecek metin.
            context: Ek baglam.

        Returns:
            Tespit sonucu.
        """
        if len(self._records) >= _MAX_RECORDS:
            self._rotate()

        result_id = str(uuid4())[:8]
        now = time.time()
        self._total_scans += 1
        self._total_ops += 1

        # Kalip esleme
        matched_patterns: list[str] = []
        max_score = 0.0
        threat_type = ThreatType.OTHER
        severity = SeverityLevel.INFO

        for name, regex in self._compiled.items():
            if regex.search(text):
                info = self._patterns[name]
                matched_patterns.append(name)
                score = info.get("score", 0.5)
                if score > max_score:
                    max_score = score
                    threat_type = info["threat_type"]
                    severity = info["severity"]

        # Sezgisel analiz
        heuristic_score = self._run_heuristics(
            text,
        )
        combined_score = max(
            max_score,
            max_score * 0.7 + heuristic_score * 0.3,
        )

        # Seviye carpani
        level_mult = self._get_level_multiplier()
        final_score = min(
            combined_score * level_mult, 1.0,
        )

        is_threat = final_score >= self._threshold
        action = (
            ActionTaken.BLOCKED
            if is_threat
            else ActionTaken.ALLOWED
        )

        if is_threat:
            self._total_threats += 1
        else:
            self._total_clean += 1

        result = DetectionResult(
            result_id=result_id,
            input_text=text[:500],
            is_threat=is_threat,
            threat_type=threat_type,
            severity=severity,
            confidence=round(final_score, 4),
            patterns_matched=matched_patterns,
            details=(
                f"patterns={len(matched_patterns)} "
                f"heuristic={heuristic_score:.2f} "
                f"final={final_score:.2f}"
            ),
            action_taken=action,
            timestamp=now,
        )

        self._records[result_id] = result
        self._record_order.append(result_id)

        self._record_history(
            "detect",
            result_id,
            f"threat={is_threat} "
            f"score={final_score:.2f} "
            f"patterns={len(matched_patterns)}",
        )

        return result

    def quick_check(
        self,
        text: str,
    ) -> bool:
        """Hizli injection kontrolu.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Tehdit varsa True.
        """
        for regex in self._compiled.values():
            if regex.search(text):
                return True
        return False

    def score_text(
        self,
        text: str,
    ) -> float:
        """Metin tehdit puani dondurur.

        Args:
            text: Puanlanacak metin.

        Returns:
            Tehdit puani (0.0-1.0).
        """
        max_score = 0.0
        for name, regex in self._compiled.items():
            if regex.search(text):
                info = self._patterns[name]
                score = info.get("score", 0.5)
                if score > max_score:
                    max_score = score

        heuristic = self._run_heuristics(text)
        combined = max(
            max_score,
            max_score * 0.7 + heuristic * 0.3,
        )
        return round(
            min(
                combined
                * self._get_level_multiplier(),
                1.0,
            ),
            4,
        )

    def batch_detect(
        self,
        texts: list[str],
    ) -> list[DetectionResult]:
        """Toplu tespit yapar.

        Args:
            texts: Metin listesi.

        Returns:
            Sonuc listesi.
        """
        return [self.detect(t) for t in texts]

    # ---- Sezgisel ----

    def _run_heuristics(
        self,
        text: str,
    ) -> float:
        """Sezgisel analiz calistirir."""
        total_score = 0.0
        count = 0

        for signal in self._heuristics:
            check = signal["check"]
            threshold = signal["threshold"]
            score = signal["score"]

            if check == "instruction_count":
                keywords = [
                    "must", "should", "always",
                    "never", "do not", "ignore",
                ]
                hits = sum(
                    1 for k in keywords
                    if k in text.lower()
                )
                if hits >= threshold:
                    total_score += score
                    count += 1

            elif check == "role_keywords":
                keywords = [
                    "you are", "act as",
                    "pretend", "role",
                    "persona", "character",
                ]
                hits = sum(
                    1 for k in keywords
                    if k in text.lower()
                )
                if hits >= threshold:
                    total_score += score
                    count += 1

            elif check == "encoding_variety":
                encodings = 0
                if "%" in text:
                    encodings += 1
                if "\\x" in text:
                    encodings += 1
                if "\\u" in text:
                    encodings += 1
                if "&#" in text:
                    encodings += 1
                if encodings >= threshold:
                    total_score += score
                    count += 1

            elif check == "text_length":
                if len(text) > threshold:
                    total_score += score
                    count += 1

        return min(total_score, 1.0)

    def _get_level_multiplier(self) -> float:
        """Seviye carpanini dondurur."""
        multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.2,
            "paranoid": 1.5,
        }
        return multipliers.get(
            self._detection_level, 1.0,
        )

    # ---- Kalip Yonetimi ----

    def add_pattern(
        self,
        name: str,
        pattern: str,
        threat_type: ThreatType = ThreatType.OTHER,
        severity: SeverityLevel = (
            SeverityLevel.MEDIUM
        ),
        score: float = 0.5,
    ) -> bool:
        """Kalip ekler.

        Args:
            name: Kalip adi.
            pattern: Regex kalibi.
            threat_type: Tehdit tipi.
            severity: Ciddiyet seviyesi.
            score: Puan.

        Returns:
            Basarili ise True.
        """
        try:
            compiled = re.compile(
                pattern, re.IGNORECASE,
            )
        except re.error:
            return False

        self._patterns[name] = {
            "pattern": pattern,
            "threat_type": threat_type,
            "severity": severity,
            "score": score,
        }
        self._compiled[name] = compiled
        self._total_ops += 1
        return True

    def remove_pattern(
        self,
        name: str,
    ) -> bool:
        """Kalip siler.

        Args:
            name: Kalip adi.

        Returns:
            Basarili ise True.
        """
        if name not in self._patterns:
            return False
        del self._patterns[name]
        self._compiled.pop(name, None)
        self._total_ops += 1
        return True

    def list_patterns(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Kaliplari listeler.

        Returns:
            Kalip sozlugu.
        """
        return dict(self._patterns)

    # ---- Sorgulama ----

    def get_result(
        self,
        result_id: str,
    ) -> DetectionResult | None:
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
        threat_type: str = "",
        limit: int = 50,
    ) -> list[DetectionResult]:
        """Sonuclari listeler.

        Args:
            threats_only: Sadece tehditler.
            threat_type: Tehdit tipi filtresi.
            limit: Maks sayi.

        Returns:
            Sonuc listesi.
        """
        ids = list(
            reversed(self._record_order),
        )
        result: list[DetectionResult] = []

        for rid in ids:
            r = self._records.get(rid)
            if not r:
                continue
            if threats_only and not r.is_threat:
                continue
            if (
                threat_type
                and r.threat_type.value
                != threat_type
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

        status = (
            "THREAT" if r.is_threat else "CLEAN"
        )
        parts = [
            f"[{status}] {r.result_id}",
            f"Type: {r.threat_type.value}",
            f"Severity: {r.severity.value}",
            f"Confidence: {r.confidence}",
            f"Action: {r.action_taken.value}",
            f"Patterns: "
            f"{', '.join(r.patterns_matched)}",
        ]
        return "\n".join(parts)

    # ---- Ayarlar ----

    def set_threshold(
        self,
        threshold: float,
    ) -> None:
        """Esik degerini ayarlar.

        Args:
            threshold: Yeni esik degeri.
        """
        self._threshold = max(
            0.0, min(threshold, 1.0),
        )
        self._total_ops += 1

    def set_detection_level(
        self,
        level: str,
    ) -> None:
        """Tespit seviyesini ayarlar.

        Args:
            level: Yeni seviye.
        """
        if level in (
            "low", "medium", "high", "paranoid",
        ):
            self._detection_level = level
            self._total_ops += 1

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
            "total_threats": (
                self._total_threats
            ),
            "total_clean": self._total_clean,
            "detection_level": (
                self._detection_level
            ),
            "threshold": self._threshold,
            "pattern_count": len(
                self._patterns,
            ),
            "total_ops": self._total_ops,
        }
