"""ATLAS Hata Analizcisi modulu.

Hata kalibi tanima, kok neden analizi,
hata korelasyonu, etki degerlendirmesi
ve siklik takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import ErrorRecord, ErrorSeverity

logger = logging.getLogger(__name__)


class ErrorAnalyzer:
    """Hata analizcisi.

    Hatalari analiz eder, kok nedenleri
    bulur ve korelasyonlari tespit eder.

    Attributes:
        _errors: Hata kayitlari.
        _patterns: Hata kaliplari.
        _correlations: Korelasyon kayitlari.
        _frequency_map: Siklik haritasi.
    """

    def __init__(self) -> None:
        """Hata analizcisini baslatir."""
        self._errors: list[ErrorRecord] = []
        self._patterns: dict[str, dict[str, Any]] = {}
        self._correlations: list[dict[str, Any]] = []
        self._frequency_map: dict[str, int] = {}
        self._root_cause_rules: dict[str, str] = {
            "timeout": "Agir is yuku veya ag gecikmesi",
            "connection": "Servis erisim sorunu",
            "memory": "Bellek yetersizligi",
            "permission": "Yetki yapılandirma hatasi",
            "validation": "Gecersiz veri girisi",
            "database": "Veritabani baglanti sorunu",
        }

        logger.info("ErrorAnalyzer baslatildi")

    def record_error(
        self,
        error_type: str,
        message: str,
        component: str = "",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> ErrorRecord:
        """Hata kaydeder.

        Args:
            error_type: Hata turu.
            message: Hata mesaji.
            component: Bilesen.
            severity: Ciddiyet.

        Returns:
            ErrorRecord nesnesi.
        """
        # Siklik guncelle
        key = f"{error_type}:{component}"
        self._frequency_map[key] = self._frequency_map.get(key, 0) + 1

        record = ErrorRecord(
            error_type=error_type,
            message=message,
            severity=severity,
            component=component,
            frequency=self._frequency_map[key],
        )
        self._errors.append(record)

        # Kalip kontrol
        self._check_pattern(record)

        logger.info(
            "Hata kaydedildi: %s (%s) - siklik: %d",
            error_type, component, self._frequency_map[key],
        )
        return record

    def analyze_root_cause(
        self,
        error_id: str,
    ) -> dict[str, Any]:
        """Kok neden analizi yapar.

        Args:
            error_id: Hata ID.

        Returns:
            Analiz sonucu.
        """
        target = None
        for e in self._errors:
            if e.error_id == error_id:
                target = e
                break

        if not target:
            return {"found": False, "reason": "Hata bulunamadi"}

        root_cause = self._determine_root_cause(target)
        target.root_cause = root_cause

        return {
            "found": True,
            "error_id": error_id,
            "error_type": target.error_type,
            "root_cause": root_cause,
            "component": target.component,
            "severity": target.severity.value,
        }

    def find_correlations(
        self,
        time_window_seconds: int = 60,
    ) -> list[dict[str, Any]]:
        """Hata korelasyonlarini bulur.

        Args:
            time_window_seconds: Zaman penceresi.

        Returns:
            Korelasyon listesi.
        """
        new_correlations: list[dict[str, Any]] = []

        for i, err1 in enumerate(self._errors):
            for err2 in self._errors[i + 1:]:
                diff = abs(
                    (err2.timestamp - err1.timestamp).total_seconds(),
                )
                if diff <= time_window_seconds and err1.component != err2.component:
                    corr = {
                        "error_1": err1.error_id,
                        "error_2": err2.error_id,
                        "component_1": err1.component,
                        "component_2": err2.component,
                        "time_diff": round(diff, 2),
                        "possible_cascade": err1.severity.value in (
                            "high", "critical",
                        ),
                    }
                    new_correlations.append(corr)

        self._correlations.extend(new_correlations)
        return new_correlations

    def assess_impact(
        self,
        error_id: str,
    ) -> dict[str, Any]:
        """Etki degerlendirmesi yapar.

        Args:
            error_id: Hata ID.

        Returns:
            Etki degerlendirmesi.
        """
        target = None
        for e in self._errors:
            if e.error_id == error_id:
                target = e
                break

        if not target:
            return {"assessed": False}

        severity_weight = {
            ErrorSeverity.LOW: 0.2,
            ErrorSeverity.MEDIUM: 0.5,
            ErrorSeverity.HIGH: 0.8,
            ErrorSeverity.CRITICAL: 1.0,
        }

        impact_score = severity_weight.get(target.severity, 0.5)
        freq_factor = min(1.0, target.frequency / 10)
        overall = round(impact_score * 0.7 + freq_factor * 0.3, 3)

        return {
            "assessed": True,
            "error_id": error_id,
            "severity_impact": impact_score,
            "frequency_factor": round(freq_factor, 3),
            "overall_impact": overall,
            "requires_immediate": overall > 0.7,
        }

    def get_error_patterns(self) -> dict[str, dict[str, Any]]:
        """Hata kaliplarini getirir.

        Returns:
            Kalip sozlugu.
        """
        return dict(self._patterns)

    def get_frequent_errors(
        self,
        min_frequency: int = 3,
    ) -> list[dict[str, Any]]:
        """Sik hatalari getirir.

        Args:
            min_frequency: Min siklik.

        Returns:
            Sik hata listesi.
        """
        frequent = []
        for key, count in self._frequency_map.items():
            if count >= min_frequency:
                parts = key.split(":", 1)
                frequent.append({
                    "error_type": parts[0],
                    "component": parts[1] if len(parts) > 1 else "",
                    "frequency": count,
                })
        frequent.sort(key=lambda x: x["frequency"], reverse=True)
        return frequent

    def get_errors_by_component(
        self,
        component: str,
    ) -> list[ErrorRecord]:
        """Bilesene gore hatalari getirir.

        Args:
            component: Bilesen adi.

        Returns:
            Hata listesi.
        """
        return [e for e in self._errors if e.component == component]

    def get_errors_by_severity(
        self,
        severity: ErrorSeverity,
    ) -> list[ErrorRecord]:
        """Ciddiyete gore hatalari getirir.

        Args:
            severity: Ciddiyet.

        Returns:
            Hata listesi.
        """
        return [e for e in self._errors if e.severity == severity]

    def add_root_cause_rule(
        self,
        keyword: str,
        cause: str,
    ) -> None:
        """Kok neden kurali ekler.

        Args:
            keyword: Anahtar kelime.
            cause: Kok neden.
        """
        self._root_cause_rules[keyword] = cause

    def _determine_root_cause(self, error: ErrorRecord) -> str:
        """Kok nedeni belirler.

        Args:
            error: Hata kaydi.

        Returns:
            Kok neden metni.
        """
        combined = f"{error.error_type} {error.message}".lower()
        for keyword, cause in self._root_cause_rules.items():
            if keyword in combined:
                return cause
        return "Bilinmeyen kok neden"

    def _check_pattern(self, error: ErrorRecord) -> None:
        """Kalip kontrolu.

        Args:
            error: Hata kaydi.
        """
        key = f"{error.error_type}:{error.component}"
        if key not in self._patterns:
            self._patterns[key] = {
                "error_type": error.error_type,
                "component": error.component,
                "count": 0,
                "severities": [],
                "first_seen": error.timestamp.isoformat(),
            }
        self._patterns[key]["count"] += 1
        self._patterns[key]["severities"].append(error.severity.value)
        self._patterns[key]["last_seen"] = error.timestamp.isoformat()

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return len(self._errors)

    @property
    def pattern_count(self) -> int:
        """Kalip sayisi."""
        return len(self._patterns)

    @property
    def correlation_count(self) -> int:
        """Korelasyon sayisi."""
        return len(self._correlations)
