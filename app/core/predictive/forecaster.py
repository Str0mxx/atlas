"""ATLAS Tahmin Motoru modulu.

Zaman serisi tahmini, regresyon modelleri, ensemble
yontemleri, guven araliklari ve senaryo projeksiyonlari.
"""

import logging
import math
from typing import Any

from app.models.predictive import (
    DataPoint,
    Forecast,
    ForecastMethod,
    MetricType,
)

logger = logging.getLogger(__name__)


class Forecaster:
    """Tahmin motoru.

    Birden fazla yontemle zaman serisi tahmini yapar:
    hareketli ortalama, ustel duzlestirme, regresyon
    ve ensemble.

    Attributes:
        _default_method: Varsayilan tahmin yontemi.
        _confidence_level: Guven araligi seviyesi (0-1).
        _forecasts: Tahmin gecmisi.
    """

    def __init__(
        self,
        default_method: ForecastMethod = ForecastMethod.MOVING_AVERAGE,
        confidence_level: float = 0.95,
    ) -> None:
        """Tahmin motorunu baslatir.

        Args:
            default_method: Varsayilan tahmin yontemi.
            confidence_level: Guven araligi seviyesi.
        """
        self._default_method = default_method
        self._confidence_level = max(0.0, min(1.0, confidence_level))
        self._forecasts: list[Forecast] = []

        logger.info(
            "Forecaster baslatildi (method=%s, confidence=%.2f)",
            default_method.value, confidence_level,
        )

    def forecast_moving_average(self, values: list[float], horizon: int = 7, window: int = 5) -> Forecast:
        """Hareketli ortalama ile tahmin yapar.

        Args:
            values: Gecmis deger listesi.
            horizon: Tahmin ufku (kac adim ileri).
            window: Pencere boyutu.

        Returns:
            Forecast nesnesi.
        """
        if not values:
            return Forecast(method=ForecastMethod.MOVING_AVERAGE, horizon=horizon)

        w = min(window, len(values))
        recent = values[-w:]
        avg = sum(recent) / len(recent)

        # Varyans hesapla (guven araligi icin)
        variance = sum((v - avg) ** 2 for v in recent) / len(recent) if len(recent) > 1 else 0.0
        std_dev = math.sqrt(variance)

        # Z-score (guven seviyesine gore)
        z = 1.96 if self._confidence_level >= 0.95 else 1.645 if self._confidence_level >= 0.90 else 1.28

        predictions: list[DataPoint] = []
        lower: list[float] = []
        upper: list[float] = []

        for i in range(horizon):
            predictions.append(DataPoint(value=avg, label=f"t+{i + 1}"))
            margin = z * std_dev * math.sqrt(1 + i / max(len(values), 1))
            lower.append(avg - margin)
            upper.append(avg + margin)

        # Hata metrigi (son window'daki MAE)
        if len(values) > w:
            errors = []
            for i in range(w, len(values)):
                predicted = sum(values[i - w : i]) / w
                errors.append(abs(values[i] - predicted))
            mae = sum(errors) / len(errors) if errors else 0.0
        else:
            mae = std_dev

        forecast = Forecast(
            method=ForecastMethod.MOVING_AVERAGE,
            predictions=predictions,
            confidence_lower=lower,
            confidence_upper=upper,
            confidence_level=self._confidence_level,
            error_metric=mae,
            metric_type=MetricType.MAE,
            horizon=horizon,
        )
        self._forecasts.append(forecast)
        return forecast

    def forecast_exponential_smoothing(self, values: list[float], horizon: int = 7, alpha: float = 0.3) -> Forecast:
        """Ustel duzlestirme ile tahmin yapar.

        Args:
            values: Gecmis deger listesi.
            horizon: Tahmin ufku.
            alpha: Duzlestirme katsayisi.

        Returns:
            Forecast nesnesi.
        """
        if not values:
            return Forecast(method=ForecastMethod.EXPONENTIAL_SMOOTHING, horizon=horizon)

        # Ustel duzlestirme
        smoothed = [values[0]]
        for i in range(1, len(values)):
            s = alpha * values[i] + (1 - alpha) * smoothed[-1]
            smoothed.append(s)

        last_smoothed = smoothed[-1]

        # Hata hesapla
        errors = [abs(values[i] - smoothed[i]) for i in range(len(values))]
        mae = sum(errors) / len(errors) if errors else 0.0
        std_error = math.sqrt(sum(e ** 2 for e in errors) / len(errors)) if errors else 0.0

        z = 1.96 if self._confidence_level >= 0.95 else 1.645

        predictions: list[DataPoint] = []
        lower: list[float] = []
        upper: list[float] = []

        for i in range(horizon):
            predictions.append(DataPoint(value=last_smoothed, label=f"t+{i + 1}"))
            margin = z * std_error * math.sqrt(1 + i * 0.1)
            lower.append(last_smoothed - margin)
            upper.append(last_smoothed + margin)

        forecast = Forecast(
            method=ForecastMethod.EXPONENTIAL_SMOOTHING,
            predictions=predictions,
            confidence_lower=lower,
            confidence_upper=upper,
            confidence_level=self._confidence_level,
            error_metric=mae,
            metric_type=MetricType.MAE,
            horizon=horizon,
        )
        self._forecasts.append(forecast)
        return forecast

    def forecast_linear_regression(self, values: list[float], horizon: int = 7) -> Forecast:
        """Lineer regresyon ile tahmin yapar.

        Args:
            values: Gecmis deger listesi.
            horizon: Tahmin ufku.

        Returns:
            Forecast nesnesi.
        """
        n = len(values)
        if n < 2:
            return Forecast(method=ForecastMethod.LINEAR_REGRESSION, horizon=horizon)

        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0.0
        intercept = y_mean - slope * x_mean

        # R-squared ve hata
        predicted_vals = [intercept + slope * i for i in range(n)]
        ss_res = sum((values[i] - predicted_vals[i]) ** 2 for i in range(n))
        ss_tot = sum((v - y_mean) ** 2 for v in values)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        rmse = math.sqrt(ss_res / n)

        z = 1.96 if self._confidence_level >= 0.95 else 1.645

        predictions: list[DataPoint] = []
        lower: list[float] = []
        upper: list[float] = []

        for i in range(horizon):
            x = n + i
            pred = intercept + slope * x
            predictions.append(DataPoint(value=pred, label=f"t+{i + 1}"))
            margin = z * rmse * math.sqrt(1 + 1 / n + (x - x_mean) ** 2 / max(denominator, 1e-10))
            lower.append(pred - margin)
            upper.append(pred + margin)

        forecast = Forecast(
            method=ForecastMethod.LINEAR_REGRESSION,
            predictions=predictions,
            confidence_lower=lower,
            confidence_upper=upper,
            confidence_level=self._confidence_level,
            error_metric=rmse,
            metric_type=MetricType.RMSE,
            horizon=horizon,
        )
        self._forecasts.append(forecast)
        return forecast

    def forecast_ensemble(self, values: list[float], horizon: int = 7) -> Forecast:
        """Ensemble (birlesik) tahmin yapar.

        Birden fazla yontemi birlestirir.

        Args:
            values: Gecmis deger listesi.
            horizon: Tahmin ufku.

        Returns:
            Birlesik Forecast nesnesi.
        """
        if not values:
            return Forecast(method=ForecastMethod.ENSEMBLE, horizon=horizon)

        ma = self.forecast_moving_average(values, horizon)
        es = self.forecast_exponential_smoothing(values, horizon)
        lr = self.forecast_linear_regression(values, horizon)

        # Hata bazli agirlik (dusuk hata = yuksek agirlik)
        errors = [
            max(ma.error_metric, 1e-10),
            max(es.error_metric, 1e-10),
            max(lr.error_metric, 1e-10),
        ]
        inv_errors = [1.0 / e for e in errors]
        total_inv = sum(inv_errors)
        weights = [ie / total_inv for ie in inv_errors]

        predictions: list[DataPoint] = []
        lower: list[float] = []
        upper: list[float] = []

        for i in range(horizon):
            vals = [
                ma.predictions[i].value if i < len(ma.predictions) else 0.0,
                es.predictions[i].value if i < len(es.predictions) else 0.0,
                lr.predictions[i].value if i < len(lr.predictions) else 0.0,
            ]
            combined = sum(w * v for w, v in zip(weights, vals))
            predictions.append(DataPoint(value=combined, label=f"t+{i + 1}"))

            lo = [
                ma.confidence_lower[i] if i < len(ma.confidence_lower) else combined,
                es.confidence_lower[i] if i < len(es.confidence_lower) else combined,
                lr.confidence_lower[i] if i < len(lr.confidence_lower) else combined,
            ]
            hi = [
                ma.confidence_upper[i] if i < len(ma.confidence_upper) else combined,
                es.confidence_upper[i] if i < len(es.confidence_upper) else combined,
                lr.confidence_upper[i] if i < len(lr.confidence_upper) else combined,
            ]
            lower.append(sum(w * v for w, v in zip(weights, lo)))
            upper.append(sum(w * v for w, v in zip(weights, hi)))

        ensemble_error = sum(w * e for w, e in zip(weights, errors))

        forecast = Forecast(
            method=ForecastMethod.ENSEMBLE,
            predictions=predictions,
            confidence_lower=lower,
            confidence_upper=upper,
            confidence_level=self._confidence_level,
            error_metric=ensemble_error,
            metric_type=MetricType.MAE,
            horizon=horizon,
        )
        self._forecasts.append(forecast)
        logger.info("Ensemble tahmin tamamlandi: horizon=%d, agirliklar=%s", horizon, [f"{w:.2f}" for w in weights])
        return forecast

    def forecast(self, values: list[float], horizon: int = 7, method: ForecastMethod | None = None) -> Forecast:
        """Belirtilen yontemle tahmin yapar.

        Args:
            values: Gecmis deger listesi.
            horizon: Tahmin ufku.
            method: Tahmin yontemi. None ise varsayilan kullanilir.

        Returns:
            Forecast nesnesi.
        """
        m = method or self._default_method

        if m == ForecastMethod.MOVING_AVERAGE:
            return self.forecast_moving_average(values, horizon)
        elif m == ForecastMethod.EXPONENTIAL_SMOOTHING:
            return self.forecast_exponential_smoothing(values, horizon)
        elif m == ForecastMethod.LINEAR_REGRESSION:
            return self.forecast_linear_regression(values, horizon)
        elif m == ForecastMethod.ENSEMBLE:
            return self.forecast_ensemble(values, horizon)
        else:
            return self.forecast_moving_average(values, horizon)

    def scenario_projection(
        self,
        values: list[float],
        horizon: int = 7,
        scenarios: dict[str, float] | None = None,
    ) -> dict[str, Forecast]:
        """Senaryo projeksiyonlari uretir.

        Args:
            values: Gecmis deger listesi.
            horizon: Tahmin ufku.
            scenarios: Senaryo carpanlari (orn: optimistic=1.2, pessimistic=0.8).

        Returns:
            Senaryo adi -> Forecast eslesmesi.
        """
        if scenarios is None:
            scenarios = {"optimistic": 1.2, "baseline": 1.0, "pessimistic": 0.8}

        base = self.forecast(values, horizon)
        results: dict[str, Forecast] = {}

        for name, multiplier in scenarios.items():
            adjusted_predictions = [
                DataPoint(value=p.value * multiplier, label=f"{name}_t+{i + 1}")
                for i, p in enumerate(base.predictions)
            ]
            adjusted_lower = [v * multiplier for v in base.confidence_lower]
            adjusted_upper = [v * multiplier for v in base.confidence_upper]

            results[name] = Forecast(
                method=base.method,
                predictions=adjusted_predictions,
                confidence_lower=adjusted_lower,
                confidence_upper=adjusted_upper,
                confidence_level=base.confidence_level,
                error_metric=base.error_metric,
                metric_type=base.metric_type,
                horizon=horizon,
            )

        logger.info("Senaryo projeksiyonlari olusturuldu: %s", list(scenarios.keys()))
        return results

    @property
    def forecasts(self) -> list[Forecast]:
        """Tahmin gecmisi."""
        return list(self._forecasts)

    @property
    def forecast_count(self) -> int:
        """Toplam tahmin sayisi."""
        return len(self._forecasts)
