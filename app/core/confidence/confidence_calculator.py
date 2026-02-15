"""ATLAS Guven Hesaplayici modulu.

Coklu faktor puanlama, tarihsel dogruluk,
veri kalitesi, model kesinligi, baglam asinaliği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """Guven hesaplayici.

    Coklu faktorlerden guven puani hesaplar.

    Attributes:
        _history: Hesaplama gecmisi.
        _domain_accuracy: Alan dogrulugu.
    """

    def __init__(
        self,
        default_weights: dict[str, float] | None = None,
    ) -> None:
        """Guven hesaplayiciyi baslatir.

        Args:
            default_weights: Varsayilan agirliklar.
        """
        self._weights = default_weights or {
            "historical_accuracy": 0.3,
            "data_quality": 0.2,
            "model_certainty": 0.25,
            "context_familiarity": 0.25,
        }
        self._history: list[
            dict[str, Any]
        ] = []
        self._domain_accuracy: dict[
            str, list[float]
        ] = {}
        self._context_cache: dict[
            str, int
        ] = {}
        self._stats = {
            "calculations": 0,
            "avg_score": 0.0,
        }

        logger.info(
            "ConfidenceCalculator baslatildi",
        )

    def calculate(
        self,
        factors: dict[str, float],
        domain: str = "",
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Guven puani hesaplar.

        Args:
            factors: Faktor degerleri (0.0-1.0).
            domain: Alan.
            weights: Ozel agirliklar.

        Returns:
            Hesaplama sonucu.
        """
        w = weights or self._weights
        total_weight = 0.0
        weighted_sum = 0.0

        factor_details = {}
        for name, value in factors.items():
            value = max(0.0, min(1.0, value))
            weight = w.get(name, 0.1)
            weighted_sum += value * weight
            total_weight += weight
            factor_details[name] = {
                "value": value,
                "weight": weight,
                "contribution": round(
                    value * weight, 4,
                ),
            }

        score = (
            weighted_sum / total_weight
            if total_weight > 0
            else 0.0
        )
        score = round(
            max(0.0, min(1.0, score)), 4,
        )

        level = self._score_to_level(score)

        result = {
            "score": score,
            "level": level,
            "factors": factor_details,
            "domain": domain,
            "timestamp": time.time(),
        }

        self._history.append(result)
        self._stats["calculations"] += 1

        # Running average
        n = self._stats["calculations"]
        self._stats["avg_score"] = (
            self._stats["avg_score"] * (n - 1)
            + score
        ) / n

        return result

    def calculate_historical_accuracy(
        self,
        domain: str,
    ) -> float:
        """Tarihsel dogruluk hesaplar.

        Args:
            domain: Alan.

        Returns:
            Dogruluk degeri (0.0-1.0).
        """
        history = self._domain_accuracy.get(
            domain, [],
        )
        if not history:
            return 0.5
        return round(
            sum(history) / len(history), 4,
        )

    def assess_data_quality(
        self,
        completeness: float = 1.0,
        freshness: float = 1.0,
        consistency: float = 1.0,
    ) -> float:
        """Veri kalitesini degerlendirir.

        Args:
            completeness: Tamlık (0.0-1.0).
            freshness: Tazelik (0.0-1.0).
            consistency: Tutarlilik (0.0-1.0).

        Returns:
            Kalite puani.
        """
        score = (
            completeness * 0.4
            + freshness * 0.3
            + consistency * 0.3
        )
        return round(
            max(0.0, min(1.0, score)), 4,
        )

    def assess_model_certainty(
        self,
        prediction_confidence: float = 0.5,
        model_age_days: int = 0,
        validation_score: float = 0.5,
    ) -> float:
        """Model kesinligini degerlendirir.

        Args:
            prediction_confidence: Tahmin guveni.
            model_age_days: Model yasi (gun).
            validation_score: Dogrulama puani.

        Returns:
            Kesinlik puani.
        """
        age_penalty = min(
            0.3, model_age_days * 0.01,
        )
        score = (
            prediction_confidence * 0.5
            + validation_score * 0.5
            - age_penalty
        )
        return round(
            max(0.0, min(1.0, score)), 4,
        )

    def assess_context_familiarity(
        self,
        context_key: str,
    ) -> float:
        """Baglam asinaligini degerlendirir.

        Args:
            context_key: Baglam anahtari.

        Returns:
            Asinalik puani (0.0-1.0).
        """
        count = self._context_cache.get(
            context_key, 0,
        )
        self._context_cache[context_key] = count + 1

        # Logaritmik olcek: 10+ = tam asinalik
        import math
        familiarity = min(
            1.0,
            math.log(count + 1) / math.log(11),
        )
        return round(familiarity, 4)

    def record_accuracy(
        self,
        domain: str,
        accurate: bool,
    ) -> None:
        """Dogruluk kaydeder.

        Args:
            domain: Alan.
            accurate: Dogru mu.
        """
        if domain not in self._domain_accuracy:
            self._domain_accuracy[domain] = []
        self._domain_accuracy[domain].append(
            1.0 if accurate else 0.0,
        )

    def _score_to_level(
        self,
        score: float,
    ) -> str:
        """Puani seviyeye cevirir.

        Args:
            score: Puan.

        Returns:
            Seviye.
        """
        if score >= 0.9:
            return "very_high"
        if score >= 0.7:
            return "high"
        if score >= 0.5:
            return "medium"
        if score >= 0.3:
            return "low"
        return "very_low"

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayisi."""
        return self._stats["calculations"]

    @property
    def avg_score(self) -> float:
        """Ortalama puan."""
        return round(self._stats["avg_score"], 4)
