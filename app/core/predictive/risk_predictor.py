"""ATLAS Risk Tahmini modulu.

Basarisizlik olasiligi, risk faktor agirliklama,
erken uyari sinyalleri, azaltma onerileri ve etki degerlendirmesi.
"""

import logging
import math
from typing import Any

from app.models.predictive import (
    DataPoint,
    RiskAssessment,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# Risk faktor agirliklari
_DEFAULT_FACTOR_WEIGHTS: dict[str, float] = {
    "severity": 0.3,
    "frequency": 0.25,
    "detectability": 0.2,
    "impact": 0.25,
}

# Erken uyari sinyal esikleri
_WARNING_THRESHOLDS: dict[str, float] = {
    "critical": 0.8,
    "high": 0.6,
    "moderate": 0.4,
    "low": 0.2,
}

# Risk azaltma sablonlari
_MITIGATION_TEMPLATES: dict[str, list[str]] = {
    "system_failure": [
        "Yedekleme sistemini kontrol edin",
        "Failover mekanizmasini aktifle",
        "Kaynak kapasitesini artirin",
    ],
    "security": [
        "Guvenlik yamalarini guncelleyin",
        "Erisim kontrollerini sikila",
        "Log izlemeyi artirin",
    ],
    "performance": [
        "Cache stratejisini optimize edin",
        "Veritabani indekslerini kontrol edin",
        "Yuk dengelemeyi yapilandirin",
    ],
    "business": [
        "Risk fonunu gozden gecirin",
        "Alternatif tedarikcileri belirleyin",
        "Sigorta kapsamini kontrol edin",
    ],
    "default": [
        "Durumu yakindan izleyin",
        "Yedek plan hazirlayin",
        "Ilgili ekibi bilgilendirin",
    ],
}


class RiskPredictor:
    """Risk tahmin sistemi.

    Basarisizlik olasiliklarini hesaplar, risk faktorlerini
    agirliklandirir, erken uyari sinyalleri uretir ve
    azaltma onerileri sunar.

    Attributes:
        _factor_weights: Risk faktor agirliklari.
        _history: Risk degerlendirme gecmisi.
        _warning_history: Uyari gecmisi.
    """

    def __init__(self, factor_weights: dict[str, float] | None = None) -> None:
        """Risk tahmin sistemini baslatir.

        Args:
            factor_weights: Ozel risk faktor agirliklari.
        """
        self._factor_weights = factor_weights or dict(_DEFAULT_FACTOR_WEIGHTS)
        self._history: list[RiskAssessment] = []
        self._warning_history: list[dict[str, Any]] = []

        logger.info("RiskPredictor baslatildi (faktor_sayisi=%d)", len(self._factor_weights))

    def calculate_failure_probability(self, data: list[DataPoint], threshold: float = 0.0) -> float:
        """Basarisizlik olasligini hesaplar.

        Verinin esik altina dusme olasligini tahmin eder.

        Args:
            data: Metrik veri noktalari.
            threshold: Basarisizlik esigi.

        Returns:
            Olasilik degeri (0.0-1.0).
        """
        values = [d.value for d in data]
        if not values:
            return 0.5

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values) if len(values) > 1 else 0.0
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0 if mean > threshold else 1.0

        # Z-score ile normal dagilim tahmini
        z = (threshold - mean) / std_dev

        # Sigmoid yaklasimi (CDF yakinsama)
        prob = 1.0 / (1.0 + math.exp(-1.7 * z))

        # Trend etkisi
        if len(values) >= 3:
            recent = values[-3:]
            trend = (recent[-1] - recent[0]) / max(abs(recent[0]), 1e-10)
            if trend < 0:  # Dusus trendi riski arttirir
                prob = min(1.0, prob + abs(trend) * 0.2)

        return max(0.0, min(1.0, prob))

    def weight_risk_factors(self, factors: dict[str, float]) -> float:
        """Risk faktorlerini agirliklandirir.

        Args:
            factors: Faktor adi -> deger (0.0-1.0) eslesmesi.

        Returns:
            Agirlikli risk skoru (0.0-1.0).
        """
        if not factors:
            return 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for name, value in factors.items():
            weight = self._factor_weights.get(name, 0.1)
            weighted_sum += max(0.0, min(1.0, value)) * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def detect_early_warnings(self, data: list[DataPoint], baseline: float | None = None) -> list[str]:
        """Erken uyari sinyallerini tespit eder.

        Args:
            data: Metrik veri noktalari.
            baseline: Referans deger. None ise ortalama kullanilir.

        Returns:
            Uyari mesajlari listesi.
        """
        values = [d.value for d in data]
        if len(values) < 3:
            return []

        mean = baseline if baseline is not None else sum(values) / len(values)
        warnings: list[str] = []

        # Son deger sapmasi
        last_val = values[-1]
        deviation = abs(last_val - mean) / max(abs(mean), 1e-10)
        if deviation > 0.5:
            warnings.append(f"Son deger referanstan %{deviation * 100:.0f} sapiyor")

        # Ardisik dusus trendi
        consecutive_drops = 0
        for i in range(len(values) - 1, 0, -1):
            if values[i] < values[i - 1]:
                consecutive_drops += 1
            else:
                break
        if consecutive_drops >= 3:
            warnings.append(f"Ardisik {consecutive_drops} donemdir dusus var")

        # Volatilite artisi
        if len(values) >= 6:
            first_half = values[: len(values) // 2]
            second_half = values[len(values) // 2 :]
            vol1 = math.sqrt(sum((v - sum(first_half) / len(first_half)) ** 2 for v in first_half) / len(first_half))
            vol2 = math.sqrt(sum((v - sum(second_half) / len(second_half)) ** 2 for v in second_half) / len(second_half))
            if vol1 > 0 and vol2 / vol1 > 2.0:
                warnings.append("Volatilite son donemde 2 kattan fazla artti")

        # Hizli degisim
        if len(values) >= 2:
            pct_change = abs(values[-1] - values[-2]) / max(abs(values[-2]), 1e-10)
            if pct_change > 0.3:
                warnings.append(f"Son donemde %{pct_change * 100:.0f} hizli degisim")

        for w in warnings:
            self._warning_history.append({"warning": w, "values": values[-3:]})

        return warnings

    def suggest_mitigations(self, risk_category: str, risk_level: RiskLevel) -> list[str]:
        """Risk azaltma onerileri sunar.

        Args:
            risk_category: Risk kategorisi.
            risk_level: Risk seviyesi.

        Returns:
            Oneri listesi.
        """
        templates = _MITIGATION_TEMPLATES.get(risk_category, _MITIGATION_TEMPLATES["default"])

        if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            return templates  # Tum onerileri ver
        elif risk_level == RiskLevel.MODERATE:
            return templates[:2]
        else:
            return templates[:1]

    def assess_impact(self, probability: float, severity: float) -> float:
        """Etki degerlendirmesi yapar.

        Args:
            probability: Olasilik (0.0-1.0).
            severity: Siddet (0.0-1.0).

        Returns:
            Etki skoru (0.0-1.0).
        """
        return max(0.0, min(1.0, probability * severity))

    def assess_risk(
        self,
        data: list[DataPoint],
        factors: dict[str, float] | None = None,
        category: str = "default",
        threshold: float = 0.0,
    ) -> RiskAssessment:
        """Kapsamli risk degerlendirmesi yapar.

        Args:
            data: Metrik veri noktalari.
            factors: Risk faktorleri.
            category: Risk kategorisi.
            threshold: Basarisizlik esigi.

        Returns:
            RiskAssessment nesnesi.
        """
        probability = self.calculate_failure_probability(data, threshold)

        if factors:
            factor_score = self.weight_risk_factors(factors)
            # Faktor skoru ile olasiligi birlestir
            combined = probability * 0.6 + factor_score * 0.4
        else:
            combined = probability
            factors = {}

        impact = self.assess_impact(combined, factors.get("severity", 0.5))

        # Risk skoru
        risk_score = max(0.0, min(1.0, combined * 0.7 + impact * 0.3))

        # Risk seviyesi
        if risk_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MODERATE
        elif risk_score >= 0.2:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NEGLIGIBLE

        # Uyarilar
        warnings = self.detect_early_warnings(data)

        # Azaltma onerileri
        mitigations = self.suggest_mitigations(category, risk_level)

        assessment = RiskAssessment(
            risk_level=risk_level,
            probability=probability,
            impact=impact,
            risk_score=risk_score,
            factors=factors,
            warnings=warnings,
            mitigations=mitigations,
        )
        self._history.append(assessment)

        logger.info(
            "Risk degerlendirmesi: seviye=%s, skor=%.2f, olasilik=%.2f",
            risk_level.value, risk_score, probability,
        )
        return assessment

    @property
    def history(self) -> list[RiskAssessment]:
        """Risk degerlendirme gecmisi."""
        return list(self._history)

    @property
    def warning_count(self) -> int:
        """Toplam uyari sayisi."""
        return len(self._warning_history)
