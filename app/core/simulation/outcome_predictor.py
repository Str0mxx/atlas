"""ATLAS Sonuc Tahmincisi modulu.

Basari olasiligi, basarisizlik modlari,
kismi basari senaryolari, zincirleme etkiler ve uzun vadeli etki.
"""

import logging
from typing import Any

from app.models.simulation import (
    ActionOutcome,
    FailureMode,
    OutcomePrediction,
    OutcomeType,
    RiskLevel,
    Scenario,
)

logger = logging.getLogger(__name__)

# Aksiyon tipi -> olasi basarisizlik modlari
_FAILURE_MODES: dict[str, list[dict[str, Any]]] = {
    "deploy": [
        {"name": "Build hatasi", "probability": 0.1, "severity": "high", "mitigation": "CI/CD kontrol"},
        {"name": "Config hatasi", "probability": 0.08, "severity": "medium", "mitigation": "Config dogrulama"},
        {"name": "Kaynak yetersiz", "probability": 0.05, "severity": "high", "mitigation": "Kaynak kontrolu"},
    ],
    "migrate": [
        {"name": "Schema uyumsuzlugu", "probability": 0.12, "severity": "critical", "mitigation": "Dry-run migrasyon"},
        {"name": "Veri kaybi", "probability": 0.03, "severity": "critical", "mitigation": "Yedekleme"},
        {"name": "Timeout", "probability": 0.08, "severity": "medium", "mitigation": "Batch isleme"},
    ],
    "delete": [
        {"name": "Yanlis hedef", "probability": 0.05, "severity": "critical", "mitigation": "Onay mekanizmasi"},
        {"name": "Bagimliliklalar bozulur", "probability": 0.1, "severity": "high", "mitigation": "Bagimlilik kontrolu"},
    ],
    "restart": [
        {"name": "Servis gelmez", "probability": 0.05, "severity": "critical", "mitigation": "Health check"},
        {"name": "Port catismasi", "probability": 0.03, "severity": "medium", "mitigation": "Port kontrolu"},
    ],
    "update": [
        {"name": "Uyumsuzluk", "probability": 0.1, "severity": "medium", "mitigation": "Versiyon kontrolu"},
        {"name": "Breaking change", "probability": 0.06, "severity": "high", "mitigation": "Changelog inceleme"},
    ],
}

# Risk seviye haritasi
_RISK_MAP: dict[str, RiskLevel] = {
    "negligible": RiskLevel.NEGLIGIBLE,
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}


class OutcomePredictor:
    """Sonuc tahmin sistemi.

    Aksiyonlarin olasi sonuclarini, basarisizlik
    modlarini ve zincirleme etkilerini tahmin eder.

    Attributes:
        _predictions: Tahmin gecmisi.
        _historical_success: Gecmis basari oranlari.
    """

    def __init__(self) -> None:
        """Sonuc tahmincisini baslatir."""
        self._predictions: list[OutcomePrediction] = []
        self._historical_success: dict[str, list[bool]] = {}

        logger.info("OutcomePredictor baslatildi")

    def predict(
        self,
        action_name: str,
        scenarios: list[Scenario] | None = None,
        context: dict[str, Any] | None = None,
    ) -> OutcomePrediction:
        """Sonuc tahmin eder.

        Args:
            action_name: Aksiyon adi.
            scenarios: Senaryolar.
            context: Baglam bilgisi.

        Returns:
            OutcomePrediction nesnesi.
        """
        action_type = self._detect_action_type(action_name)

        # Basari olasiligi
        success_prob = self._calculate_success_probability(
            action_type, scenarios, context
        )

        # Basarisizlik modlari
        failure_modes = self._identify_failure_modes(action_type, context)

        # Zincirleme etkiler
        cascading = self._predict_cascading_effects(action_type, failure_modes)

        # Uzun vadeli etki
        long_term = self._assess_long_term_impact(action_type, success_prob)

        # Guven puani
        confidence = self._calculate_confidence(scenarios, action_type)

        # Onerilen mi?
        recommended = success_prob >= 0.7 and not any(
            fm.severity == RiskLevel.CRITICAL and fm.probability > 0.1
            for fm in failure_modes
        )

        prediction = OutcomePrediction(
            action_name=action_name,
            success_probability=round(success_prob, 3),
            failure_modes=failure_modes,
            cascading_effects=cascading,
            long_term_impact=long_term,
            confidence=round(confidence, 3),
            recommended=recommended,
        )

        self._predictions.append(prediction)
        return prediction

    def record_outcome(self, action_name: str, success: bool) -> None:
        """Gercek sonucu kaydeder.

        Args:
            action_name: Aksiyon adi.
            success: Basarili mi.
        """
        action_type = self._detect_action_type(action_name)
        history = self._historical_success.setdefault(action_type, [])
        history.append(success)

        # Maks 100 kayit
        if len(history) > 100:
            self._historical_success[action_type] = history[-100:]

    def get_historical_rate(self, action_name: str) -> float | None:
        """Gecmis basari oranini getirir.

        Args:
            action_name: Aksiyon adi.

        Returns:
            Basari orani veya None.
        """
        action_type = self._detect_action_type(action_name)
        history = self._historical_success.get(action_type)
        if not history:
            return None
        return sum(1 for s in history if s) / len(history)

    def assess_from_outcomes(
        self, outcomes: list[ActionOutcome]
    ) -> OutcomePrediction:
        """Aksiyon sonuclarindan tahmin uretir.

        Args:
            outcomes: ActionOutcome listesi.

        Returns:
            OutcomePrediction nesnesi.
        """
        if not outcomes:
            return OutcomePrediction(action_name="unknown")

        avg_prob = sum(o.success_probability for o in outcomes) / len(outcomes)

        # Basarisizlik modlarini yan etkilerden cikar
        failure_modes: list[FailureMode] = []
        for o in outcomes:
            for se in o.side_effects:
                if se.severity in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                    failure_modes.append(FailureMode(
                        name=se.description,
                        probability=se.probability,
                        severity=se.severity,
                    ))

        recommended = avg_prob >= 0.7

        prediction = OutcomePrediction(
            action_name=outcomes[0].action_name,
            success_probability=round(avg_prob, 3),
            failure_modes=failure_modes,
            recommended=recommended,
            confidence=round(min(len(outcomes) / 5, 1.0), 3),
        )

        self._predictions.append(prediction)
        return prediction

    def _calculate_success_probability(
        self,
        action_type: str,
        scenarios: list[Scenario] | None,
        context: dict[str, Any] | None,
    ) -> float:
        """Basari olasiligini hesaplar."""
        # Gecmis veri varsa kullan
        historical = self.get_historical_rate(action_type)
        if historical is not None:
            base = historical
        else:
            base = 0.85

        # Senaryolardan ortalama
        if scenarios:
            scenario_probs = [
                o.success_probability
                for s in scenarios
                for o in s.outcomes
                if o.success_probability > 0
            ]
            if scenario_probs:
                scenario_avg = sum(scenario_probs) / len(scenario_probs)
                base = (base + scenario_avg) / 2

        # Baglam ayarlamasi
        if context:
            if context.get("high_load"):
                base -= 0.1
            if context.get("tested"):
                base += 0.05
            if context.get("first_time"):
                base -= 0.1

        return max(0.0, min(1.0, base))

    def _identify_failure_modes(
        self, action_type: str, context: dict[str, Any] | None
    ) -> list[FailureMode]:
        """Basarisizlik modlarini tespit eder."""
        templates = _FAILURE_MODES.get(action_type, [
            {"name": "Bilinmeyen hata", "probability": 0.1, "severity": "medium", "mitigation": "Log inceleme"},
        ])

        modes: list[FailureMode] = []
        for t in templates:
            severity = _RISK_MAP.get(t["severity"], RiskLevel.MEDIUM)
            prob = t["probability"]

            if context and context.get("high_load"):
                prob = min(prob * 1.5, 1.0)

            modes.append(FailureMode(
                name=t["name"],
                description=f"{t['name']} - {action_type} islemi sirasinda",
                probability=round(prob, 3),
                severity=severity,
                mitigation=t.get("mitigation", ""),
            ))

        return modes

    def _predict_cascading_effects(
        self, action_type: str, failure_modes: list[FailureMode]
    ) -> list[str]:
        """Zincirleme etkileri tahmin eder."""
        effects: list[str] = []

        critical_modes = [fm for fm in failure_modes if fm.severity == RiskLevel.CRITICAL]
        if critical_modes:
            effects.append("Bagimli servisler etkilenebilir")
            effects.append("Kullanici erisimi kesilebilir")

        if action_type in ("migrate", "deploy"):
            effects.append("Rollback gerekebilir")

        if action_type == "delete":
            effects.append("Iliskili veriler etkilenir")

        return effects

    def _assess_long_term_impact(self, action_type: str, success_prob: float) -> str:
        """Uzun vadeli etkiyi degerlendirir."""
        if success_prob >= 0.9:
            return "Olumlu: Sistem stabilitesi artar"
        if success_prob >= 0.7:
            return "Notr: Kisa vadeli etki, uzun vadede dengelenir"
        if success_prob >= 0.5:
            return "Dikkat: Teknik borc birikebilir"
        return "Olumsuz: Sistem guvenilirligi dusebilir"

    def _calculate_confidence(
        self, scenarios: list[Scenario] | None, action_type: str
    ) -> float:
        """Guven puani hesaplar."""
        base = 0.5

        # Gecmis veri varsa guven artar
        history = self._historical_success.get(action_type)
        if history:
            base += min(len(history) / 20, 0.3)

        # Senaryo varsa guven artar
        if scenarios:
            base += min(len(scenarios) / 10, 0.2)

        return min(base, 1.0)

    def _detect_action_type(self, action_name: str) -> str:
        """Aksiyon tipini tespit eder."""
        lower = action_name.lower()
        for action_type in _FAILURE_MODES:
            if action_type in lower:
                return action_type
        return "update"

    @property
    def prediction_count(self) -> int:
        """Tahmin sayisi."""
        return len(self._predictions)
