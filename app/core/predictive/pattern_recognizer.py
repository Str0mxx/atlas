"""ATLAS Oruntu Tanima modulu.

Zaman serisi, davranissal, anomali, donesel ve
trend oruntulerini tespit eder.
"""

import logging
import math
from typing import Any

from app.models.predictive import (
    DataPoint,
    Pattern,
    PatternType,
)

logger = logging.getLogger(__name__)


class PatternRecognizer:
    """Oruntu tanima sistemi.

    Zaman serisi verilerinde oruntuleri tespit eder:
    trend, donesellik, anomali ve davranissal oruntular.

    Attributes:
        _patterns: Tespit edilen oruntular.
        _anomaly_threshold: Anomali esigi (sigma).
        _min_cycle_length: Minimum dongu uzunlugu.
    """

    def __init__(
        self,
        anomaly_threshold: float = 2.0,
        min_cycle_length: int = 3,
    ) -> None:
        """Oruntu tanima sistemini baslatir.

        Args:
            anomaly_threshold: Anomali tespit esigi (standart sapma carpani).
            min_cycle_length: Minimum donesel oruntu uzunlugu.
        """
        self._patterns: list[Pattern] = []
        self._anomaly_threshold = anomaly_threshold
        self._min_cycle_length = min_cycle_length

        logger.info(
            "PatternRecognizer baslatildi (anomaly=%.1f, min_cycle=%d)",
            anomaly_threshold, min_cycle_length,
        )

    def detect_time_series_pattern(self, data: list[DataPoint]) -> Pattern:
        """Zaman serisi oruntusunu tespit eder.

        Temel istatistikleri hesaplar ve genel egilimi belirler.

        Args:
            data: Veri noktalari listesi.

        Returns:
            Tespit edilen Pattern nesnesi.
        """
        values = [d.value for d in data]
        if not values:
            return Pattern(pattern_type=PatternType.TIME_SERIES, name="empty", confidence=0.0)

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values) if len(values) > 1 else 0.0
        std_dev = math.sqrt(variance)

        # Trend yonu
        if len(values) >= 2:
            first_half = sum(values[: len(values) // 2]) / max(len(values) // 2, 1)
            second_half = sum(values[len(values) // 2 :]) / max(len(values) - len(values) // 2, 1)
            trend = "rising" if second_half > first_half else "falling" if second_half < first_half else "stable"
        else:
            trend = "stable"

        confidence = min(1.0, len(values) / 30)  # 30+ nokta yuksek guven

        pattern = Pattern(
            pattern_type=PatternType.TIME_SERIES,
            name=f"ts_{trend}",
            description=f"Zaman serisi: {trend}, ort={mean:.2f}, std={std_dev:.2f}",
            confidence=confidence,
            data_points=data,
            parameters={"mean": mean, "std_dev": std_dev, "trend": trend, "count": len(values)},
        )
        self._patterns.append(pattern)
        logger.info("Zaman serisi oruntulu tespit edildi: %s (guven=%.2f)", trend, confidence)
        return pattern

    def detect_behavioral_pattern(self, actions: list[dict[str, Any]]) -> Pattern:
        """Davranissal oruntuyu tespit eder.

        Tekrarlanan eylem dizilerini bulur.

        Args:
            actions: Eylem listesi (her biri dict: action, timestamp, vb).

        Returns:
            Davranissal Pattern nesnesi.
        """
        if not actions:
            return Pattern(pattern_type=PatternType.BEHAVIORAL, name="no_data", confidence=0.0)

        # Eylem frekanslarini hesapla
        action_counts: dict[str, int] = {}
        for act in actions:
            key = act.get("action", "unknown")
            action_counts[key] = action_counts.get(key, 0) + 1

        total = sum(action_counts.values())
        dominant_action = max(action_counts, key=action_counts.get) if action_counts else "unknown"  # type: ignore[arg-type]
        dominance_ratio = action_counts.get(dominant_action, 0) / total if total > 0 else 0.0

        # Ardisik tekrarlar
        sequences: list[str] = [a.get("action", "") for a in actions]
        repeat_count = sum(1 for i in range(1, len(sequences)) if sequences[i] == sequences[i - 1])
        repetition_rate = repeat_count / max(len(sequences) - 1, 1)

        confidence = min(1.0, (dominance_ratio + repetition_rate) / 2 + len(actions) / 100)

        pattern = Pattern(
            pattern_type=PatternType.BEHAVIORAL,
            name=f"behavior_{dominant_action}",
            description=f"Baskin eylem: {dominant_action} (%{dominance_ratio * 100:.0f})",
            confidence=min(1.0, confidence),
            parameters={
                "action_counts": action_counts,
                "dominant_action": dominant_action,
                "dominance_ratio": dominance_ratio,
                "repetition_rate": repetition_rate,
            },
        )
        self._patterns.append(pattern)
        logger.info("Davranissal oruntu tespit edildi: %s", dominant_action)
        return pattern

    def detect_anomalies(self, data: list[DataPoint]) -> list[Pattern]:
        """Anomali noktalarini tespit eder.

        Z-score ile anomalileri belirler.

        Args:
            data: Veri noktalari listesi.

        Returns:
            Anomali Pattern listesi.
        """
        values = [d.value for d in data]
        if len(values) < 3:
            return []

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return []

        anomalies: list[Pattern] = []
        for i, dp in enumerate(data):
            z_score = abs(dp.value - mean) / std_dev
            if z_score >= self._anomaly_threshold:
                anomaly = Pattern(
                    pattern_type=PatternType.ANOMALY,
                    name=f"anomaly_idx_{i}",
                    description=f"Anomali: deger={dp.value:.2f}, z_score={z_score:.2f}",
                    confidence=min(1.0, z_score / (self._anomaly_threshold * 2)),
                    data_points=[dp],
                    parameters={"index": i, "z_score": z_score, "mean": mean, "std_dev": std_dev},
                )
                anomalies.append(anomaly)
                self._patterns.append(anomaly)

        logger.info("Anomali tespiti: %d anomali bulundu", len(anomalies))
        return anomalies

    def detect_cyclical_pattern(self, data: list[DataPoint]) -> Pattern | None:
        """Donesel oruntuyu tespit eder.

        Autocorrelation ile dongu uzunlugunu bulur.

        Args:
            data: Veri noktalari listesi.

        Returns:
            Donesel Pattern nesnesi veya None.
        """
        values = [d.value for d in data]
        n = len(values)
        if n < self._min_cycle_length * 2:
            return None

        mean = sum(values) / n
        centered = [v - mean for v in values]

        # Autocorrelation hesapla
        variance = sum(c * c for c in centered)
        if variance == 0:
            return None

        best_lag = 0
        best_corr = 0.0
        for lag in range(self._min_cycle_length, n // 2):
            corr = sum(centered[i] * centered[i + lag] for i in range(n - lag)) / variance
            if corr > best_corr:
                best_corr = corr
                best_lag = lag

        if best_corr < 0.3:  # Minimum korelasyon esigi
            return None

        pattern = Pattern(
            pattern_type=PatternType.CYCLICAL,
            name=f"cycle_{best_lag}",
            description=f"Donesel oruntu: periyot={best_lag}, korelasyon={best_corr:.2f}",
            confidence=min(1.0, best_corr),
            data_points=data,
            parameters={"period": best_lag, "correlation": best_corr},
        )
        self._patterns.append(pattern)
        logger.info("Donesel oruntu tespit edildi: periyot=%d, korelasyon=%.2f", best_lag, best_corr)
        return pattern

    def identify_trend(self, data: list[DataPoint]) -> Pattern:
        """Trend yonunu ve gucunu belirler.

        Lineer regresyon ile trend hesaplar.

        Args:
            data: Veri noktalari listesi.

        Returns:
            Trend Pattern nesnesi.
        """
        values = [d.value for d in data]
        n = len(values)
        if n < 2:
            return Pattern(pattern_type=PatternType.TREND, name="insufficient_data", confidence=0.0)

        # Lineer regresyon (en kucuk kareler)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0

        # R-squared
        ss_res = sum((values[i] - (y_mean + slope * (i - x_mean))) ** 2 for i in range(n))
        ss_tot = sum((v - y_mean) ** 2 for v in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        if slope > 0.01:
            direction = "rising"
        elif slope < -0.01:
            direction = "falling"
        else:
            direction = "stable"

        pattern = Pattern(
            pattern_type=PatternType.TREND,
            name=f"trend_{direction}",
            description=f"Trend: {direction}, egim={slope:.4f}, R²={r_squared:.3f}",
            confidence=max(0.0, min(1.0, abs(r_squared))),
            data_points=data,
            parameters={"slope": slope, "r_squared": r_squared, "direction": direction, "y_mean": y_mean},
        )
        self._patterns.append(pattern)
        logger.info("Trend tespit edildi: %s (egim=%.4f)", direction, slope)
        return pattern

    @property
    def patterns(self) -> list[Pattern]:
        """Tespit edilen tum oruntular."""
        return list(self._patterns)

    @property
    def pattern_count(self) -> int:
        """Toplam oruntu sayisi."""
        return len(self._patterns)

    def clear(self) -> None:
        """Oruntu gecmisini temizler."""
        self._patterns.clear()
