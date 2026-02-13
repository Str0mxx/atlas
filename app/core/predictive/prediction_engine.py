"""ATLAS Tahmin Orkestratoru modulu.

Coklu model ensemble, tahmin birlestirme, guven puanlama,
aciklama uretimi ve geri bildirim entegrasyonu.
"""

import logging
import time
from typing import Any

from app.core.predictive.behavior_predictor import BehaviorPredictor
from app.core.predictive.demand_predictor import DemandPredictor
from app.core.predictive.event_predictor import EventPredictor
from app.core.predictive.forecaster import Forecaster
from app.core.predictive.model_manager import ModelManager
from app.core.predictive.pattern_recognizer import PatternRecognizer
from app.core.predictive.risk_predictor import RiskPredictor
from app.core.predictive.trend_analyzer import TrendAnalyzer
from app.models.predictive import (
    ConfidenceLevel,
    DataPoint,
    EnsembleStrategy,
    PredictionResult,
)

logger = logging.getLogger(__name__)


class PredictionEngine:
    """Tahmin orkestratoru.

    Tum tahmin alt sistemlerini koordine ederek
    birlesik tahminler uretir. Multi-model ensemble,
    guven puanlama ve aciklama ozelliklerini yonetir.

    Attributes:
        pattern_recognizer: Oruntu tanima sistemi.
        trend_analyzer: Trend analiz sistemi.
        forecaster: Tahmin motoru.
        risk_predictor: Risk tahmin sistemi.
        demand_predictor: Talep tahmin sistemi.
        behavior_predictor: Davranis tahmin sistemi.
        event_predictor: Olay tahmin sistemi.
        model_manager: Model yonetim sistemi.
        _results: Tahmin sonuclari.
        _feedback: Geri bildirim gecmisi.
    """

    def __init__(
        self,
        forecast_horizon: int = 7,
        confidence_threshold: float = 0.6,
        ensemble_strategy: str = "weighted",
    ) -> None:
        """Tahmin orkestratoru baslatir.

        Args:
            forecast_horizon: Varsayilan tahmin ufku.
            confidence_threshold: Minimum guven esigi.
            ensemble_strategy: Ensemble stratejisi.
        """
        self.pattern_recognizer = PatternRecognizer()
        self.trend_analyzer = TrendAnalyzer()
        self.forecaster = Forecaster()
        self.risk_predictor = RiskPredictor()
        self.demand_predictor = DemandPredictor()
        self.behavior_predictor = BehaviorPredictor()
        self.event_predictor = EventPredictor()
        self.model_manager = ModelManager()

        self._forecast_horizon = forecast_horizon
        self._confidence_threshold = confidence_threshold

        try:
            self._ensemble_strategy = EnsembleStrategy(ensemble_strategy)
        except ValueError:
            self._ensemble_strategy = EnsembleStrategy.WEIGHTED

        self._results: list[PredictionResult] = []
        self._feedback: list[dict[str, Any]] = []

        logger.info(
            "PredictionEngine baslatildi (horizon=%d, threshold=%.2f, strategy=%s)",
            forecast_horizon, confidence_threshold, self._ensemble_strategy.value,
        )

    def predict(self, query: str, data: list[DataPoint] | None = None) -> PredictionResult:
        """Birlesik tahmin yapar.

        Birden fazla alt sistemi kullaniarak tahmin uretir.

        Args:
            query: Tahmin sorgusu/aciklamasi.
            data: Veri noktalari (varsa).

        Returns:
            PredictionResult nesnesi.
        """
        start_time = time.monotonic()
        predictions: dict[str, float] = {}
        model_contributions: dict[str, float] = {}

        values = [d.value for d in data] if data else []

        # 1. Oruntu tanima
        if data and len(data) >= 3:
            pattern = self.pattern_recognizer.detect_time_series_pattern(data)
            predictions["pattern"] = pattern.confidence
            model_contributions["pattern"] = 0.15

        # 2. Trend analizi
        if data and len(data) >= 3:
            trend = self.trend_analyzer.analyze(data)
            predictions["trend"] = trend.strength
            model_contributions["trend"] = 0.2

        # 3. Tahmin
        if values and len(values) >= 3:
            forecast = self.forecaster.forecast(values, self._forecast_horizon)
            if forecast.predictions:
                avg_prediction = sum(p.value for p in forecast.predictions) / len(forecast.predictions)
                predictions["forecast"] = avg_prediction
                model_contributions["forecast"] = 0.3

        # 4. Risk
        if data and len(data) >= 3:
            risk = self.risk_predictor.assess_risk(data)
            predictions["risk"] = risk.risk_score
            model_contributions["risk"] = 0.2

        # 5. Anomali
        if data and len(data) >= 3:
            anomalies = self.pattern_recognizer.detect_anomalies(data)
            anomaly_score = len(anomalies) / max(len(data), 1)
            predictions["anomaly"] = anomaly_score
            model_contributions["anomaly"] = 0.15

        # Ensemble birlestirme
        combined = self._combine_predictions(predictions, model_contributions)
        confidence = self._calculate_confidence(predictions, model_contributions)
        confidence_level = self._to_confidence_level(confidence)

        # Aciklama
        explanation = self._generate_explanation(query, predictions, confidence)

        result = PredictionResult(
            query=query,
            strategy=self._ensemble_strategy,
            predictions=predictions,
            combined_score=combined,
            confidence=confidence,
            confidence_level=confidence_level,
            explanation=explanation,
            model_contributions=model_contributions,
        )
        self._results.append(result)

        elapsed = (time.monotonic() - start_time) * 1000
        logger.info(
            "Tahmin tamamlandi: skor=%.2f, guven=%.2f, sure=%.1fms",
            combined, confidence, elapsed,
        )
        return result

    def _combine_predictions(
        self,
        predictions: dict[str, float],
        contributions: dict[str, float],
    ) -> float:
        """Tahminleri birlestirir.

        Args:
            predictions: Alt sistem tahminleri.
            contributions: Model katki agirliklari.

        Returns:
            Birlesik skor.
        """
        if not predictions:
            return 0.0

        if self._ensemble_strategy == EnsembleStrategy.AVERAGE:
            return sum(predictions.values()) / len(predictions)

        elif self._ensemble_strategy == EnsembleStrategy.WEIGHTED:
            weighted_sum = 0.0
            total_weight = 0.0
            for key, value in predictions.items():
                weight = contributions.get(key, 0.1)
                weighted_sum += value * weight
                total_weight += weight
            return weighted_sum / total_weight if total_weight > 0 else 0.0

        elif self._ensemble_strategy == EnsembleStrategy.BEST_PICK:
            return max(predictions.values()) if predictions else 0.0

        else:  # STACKING
            # Basit stacking: agirlikli ortalama + bonus
            avg = sum(predictions.values()) / len(predictions)
            consistency = 1.0 - (max(predictions.values()) - min(predictions.values())) if len(predictions) > 1 else 1.0
            return avg * (1 + consistency * 0.1)

    def _calculate_confidence(
        self,
        predictions: dict[str, float],
        contributions: dict[str, float],
    ) -> float:
        """Guven puanini hesaplar.

        Args:
            predictions: Alt sistem tahminleri.
            contributions: Model katki agirliklari.

        Returns:
            Guven puani (0-1).
        """
        if not predictions:
            return 0.0

        # Model sayisi guveni arttirir
        model_count_factor = min(1.0, len(predictions) / 5)

        # Tutarlilik: tahminler ne kadar yakinsasi
        values = list(predictions.values())
        if len(values) > 1:
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            import math
            consistency = max(0.0, 1.0 - math.sqrt(variance))
        else:
            consistency = 0.5

        confidence = model_count_factor * 0.4 + consistency * 0.6
        return max(0.0, min(1.0, confidence))

    def _to_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Sayisal guveni seviyeye donusturur.

        Args:
            confidence: Guven puani (0-1).

        Returns:
            ConfidenceLevel enum degeri.
        """
        if confidence >= 0.8:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.4:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.2:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _generate_explanation(
        self,
        query: str,
        predictions: dict[str, float],
        confidence: float,
    ) -> str:
        """Tahmin aciklamasi uretir.

        Args:
            query: Orijinal sorgu.
            predictions: Alt sistem tahminleri.
            confidence: Guven puani.

        Returns:
            Insan-okunabilir aciklama.
        """
        parts: list[str] = [f"'{query}' icin tahmin analizi:"]

        if "trend" in predictions:
            strength = predictions["trend"]
            parts.append(f"Trend gucu: %{strength * 100:.0f}")

        if "risk" in predictions:
            risk = predictions["risk"]
            parts.append(f"Risk skoru: %{risk * 100:.0f}")

        if "forecast" in predictions:
            parts.append(f"Tahmin degeri: {predictions['forecast']:.2f}")

        if "anomaly" in predictions:
            anomaly = predictions["anomaly"]
            if anomaly > 0:
                parts.append(f"Anomali orani: %{anomaly * 100:.0f}")

        level = self._to_confidence_level(confidence)
        parts.append(f"Guven seviyesi: {level.value}")

        return " | ".join(parts)

    def add_feedback(self, result_id: str, actual_value: float, comment: str = "") -> None:
        """Geri bildirim ekler.

        Args:
            result_id: Tahmin sonuc ID.
            actual_value: Gerceklesen deger.
            comment: Yorum.
        """
        self._feedback.append({
            "result_id": result_id,
            "actual_value": actual_value,
            "comment": comment,
        })

        # Tahmin sonucunu bul ve hata hesapla
        for result in self._results:
            if result.id == result_id:
                error = abs(result.combined_score - actual_value)
                logger.info(
                    "Geri bildirim: tahmin=%.2f, gercek=%.2f, hata=%.2f",
                    result.combined_score, actual_value, error,
                )
                break

    def get_result(self, result_id: str) -> PredictionResult | None:
        """Tahmin sonucu getirir.

        Args:
            result_id: Sonuc ID.

        Returns:
            PredictionResult veya None.
        """
        return next((r for r in self._results if r.id == result_id), None)

    @property
    def results(self) -> list[PredictionResult]:
        """Tahmin sonuclari."""
        return list(self._results)

    @property
    def result_count(self) -> int:
        """Toplam tahmin sayisi."""
        return len(self._results)

    @property
    def feedback_count(self) -> int:
        """Toplam geri bildirim sayisi."""
        return len(self._feedback)
