"""ATLAS Trend Analiz modulu.

Hareketli ortalamalar, ustel duzlestirme, mevsimsellik
tespiti, buyume orani ve bukum noktalari.
"""

import logging
import math

from app.models.predictive import (
    DataPoint,
    SeasonType,
    TrendDirection,
    TrendResult,
)

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Trend analiz sistemi.

    Zaman serisi verilerinde trendleri analiz eder:
    hareketli ortalama, ustel duzlestirme, mevsimsellik
    ve buyume oranlari.

    Attributes:
        _window_size: Hareketli ortalama pencere boyutu.
        _smoothing_factor: Ustel duzlestirme alpha degeri.
        _results: Analiz sonuclari gecmisi.
    """

    def __init__(
        self,
        window_size: int = 5,
        smoothing_factor: float = 0.3,
    ) -> None:
        """Trend analiz sistemini baslatir.

        Args:
            window_size: Hareketli ortalama penceresi.
            smoothing_factor: Ustel duzlestirme katsayisi (0-1).
        """
        self._window_size = max(2, window_size)
        self._smoothing_factor = max(0.0, min(1.0, smoothing_factor))
        self._results: list[TrendResult] = []

        logger.info(
            "TrendAnalyzer baslatildi (window=%d, alpha=%.2f)",
            self._window_size, self._smoothing_factor,
        )

    def moving_average(self, values: list[float]) -> list[float]:
        """Hareketli ortalama hesaplar.

        Args:
            values: Deger listesi.

        Returns:
            Hareketli ortalama listesi.
        """
        if len(values) < self._window_size:
            return [sum(values) / len(values)] if values else []

        averages: list[float] = []
        for i in range(len(values) - self._window_size + 1):
            window = values[i : i + self._window_size]
            averages.append(sum(window) / len(window))

        return averages

    def exponential_smoothing(self, values: list[float]) -> list[float]:
        """Ustel duzlestirme uygular.

        Args:
            values: Deger listesi.

        Returns:
            Duzlestirilmis deger listesi.
        """
        if not values:
            return []

        alpha = self._smoothing_factor
        smoothed = [values[0]]
        for i in range(1, len(values)):
            s = alpha * values[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(s)

        return smoothed

    def detect_seasonality(self, values: list[float]) -> SeasonType | None:
        """Mevsimsellik tespit eder.

        Autocorrelation ile periyodikligi bulur.

        Args:
            values: Deger listesi.

        Returns:
            SeasonType veya None.
        """
        n = len(values)
        if n < 14:
            return None

        mean = sum(values) / n
        centered = [v - mean for v in values]
        variance = sum(c * c for c in centered)
        if variance == 0:
            return None

        # Bilinen periyotlari kontrol et
        season_periods = {
            7: SeasonType.WEEKLY,
            30: SeasonType.MONTHLY,
            90: SeasonType.QUARTERLY,
            365: SeasonType.YEARLY,
        }

        best_season = None
        best_corr = 0.3  # Minimum esik

        for period, season in season_periods.items():
            if period >= n // 2:
                continue
            corr = sum(centered[i] * centered[i + period] for i in range(n - period)) / variance
            if corr > best_corr:
                best_corr = corr
                best_season = season

        if best_season:
            logger.info("Mevsimsellik tespit edildi: %s (korelasyon=%.2f)", best_season.value, best_corr)
        return best_season

    def calculate_growth_rate(self, values: list[float]) -> float:
        """Buyume oranini hesaplar.

        CAGR (Compound Annual Growth Rate) benzeri hesaplama.

        Args:
            values: Deger listesi.

        Returns:
            Buyume orani (-1.0 ile inf arasi).
        """
        if len(values) < 2:
            return 0.0

        start = values[0]
        end = values[-1]

        if start == 0:
            return 0.0 if end == 0 else 1.0

        return (end - start) / abs(start)

    def find_inflection_points(self, values: list[float]) -> list[int]:
        """Bukum noktalarini bulur.

        Ikinci turev isaretinin degistigi noktalari tespit eder.

        Args:
            values: Deger listesi.

        Returns:
            Bukum noktasi indeksleri.
        """
        if len(values) < 3:
            return []

        # Birinci turev (farkliliklari)
        first_diff = [values[i + 1] - values[i] for i in range(len(values) - 1)]

        # Ikinci turev
        second_diff = [first_diff[i + 1] - first_diff[i] for i in range(len(first_diff) - 1)]

        # Isaret degisimlerini bul
        inflections: list[int] = []
        for i in range(1, len(second_diff)):
            if second_diff[i - 1] * second_diff[i] < 0:
                inflections.append(i + 1)  # Orijinal indeks

        return inflections

    def analyze(self, data: list[DataPoint]) -> TrendResult:
        """Kapsamli trend analizi yapar.

        Tum analiz yontemlerini birlestirerek sonuc uretir.

        Args:
            data: Veri noktalari listesi.

        Returns:
            TrendResult nesnesi.
        """
        values = [d.value for d in data]
        if not values:
            result = TrendResult(direction=TrendDirection.STABLE, strength=0.0)
            self._results.append(result)
            return result

        # Hareketli ortalama
        ma = self.moving_average(values)

        # Ustel duzlestirme
        smoothed = self.exponential_smoothing(values)

        # Trend yonu ve gucu (lineer regresyon)
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0.0

        # R-squared
        ss_res = sum((values[i] - (y_mean + slope * (i - x_mean))) ** 2 for i in range(n))
        ss_tot = sum((v - y_mean) ** 2 for v in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        strength = max(0.0, min(1.0, abs(r_squared)))

        # Yon
        if slope > 0.01:
            direction = TrendDirection.RISING
        elif slope < -0.01:
            direction = TrendDirection.FALLING
        else:
            direction = TrendDirection.STABLE

        # Volatilite kontrolu
        if len(values) > 2:
            changes = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
            avg_change = sum(changes) / len(changes) if changes else 0.0
            if avg_change > abs(y_mean) * 0.2 and strength < 0.3:
                direction = TrendDirection.VOLATILE

        # Mevsimsellik
        seasonality = self.detect_seasonality(values)

        # Buyume orani
        growth_rate = self.calculate_growth_rate(values)

        # Bukum noktalari
        inflections = self.find_inflection_points(values)

        result = TrendResult(
            direction=direction,
            slope=slope,
            strength=strength,
            start_value=values[0],
            end_value=values[-1],
            change_rate=growth_rate,
            seasonality=seasonality,
            inflection_points=inflections,
            moving_averages=ma,
        )
        self._results.append(result)

        logger.info(
            "Trend analizi tamamlandi: yon=%s, guc=%.2f, buyume=%.2f%%",
            direction.value, strength, growth_rate * 100,
        )
        return result

    @property
    def results(self) -> list[TrendResult]:
        """Analiz sonuclari gecmisi."""
        return list(self._results)

    @property
    def result_count(self) -> int:
        """Toplam analiz sayisi."""
        return len(self._results)
