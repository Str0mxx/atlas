"""ATLAS Gelir Tahmin Edici modülü.

Gelir tahmini, senaryo modelleme,
mevsimsellik, güven aralıkları,
varyans analizi.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class RevenueForecaster:
    """Gelir tahmin edici.

    Geliri tahmin eder ve modeller.

    Attributes:
        _forecasts: Tahmin kayıtları.
        _scenarios: Senaryo kayıtları.
    """

    def __init__(self) -> None:
        """Tahmin ediciyi başlatır."""
        self._forecasts: dict[
            str, dict[str, Any]
        ] = {}
        self._scenarios: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "forecasts_made": 0,
            "scenarios_modeled": 0,
        }

        logger.info(
            "RevenueForecaster baslatildi",
        )

    def forecast_revenue(
        self,
        historical: list[float]
        | None = None,
        periods_ahead: int = 3,
        method: str = "linear",
    ) -> dict[str, Any]:
        """Gelir tahmini yapar.

        Args:
            historical: Geçmiş veriler.
            periods_ahead: İleriki dönem.
            method: Tahmin yöntemi.

        Returns:
            Tahmin bilgisi.
        """
        historical = historical or []
        self._counter += 1
        fid = f"fcst_{self._counter}"

        if not historical:
            return {
                "forecast_id": fid,
                "predictions": [],
                "forecasted": True,
            }

        avg = (
            sum(historical)
            / len(historical)
        )

        if method == "linear" and len(
            historical,
        ) >= 2:
            n = len(historical)
            growth = (
                (historical[-1]
                 - historical[0])
                / (n - 1)
            )
            predictions = [
                round(
                    historical[-1]
                    + growth * (i + 1),
                    2,
                )
                for i in range(periods_ahead)
            ]
        elif method == "exponential" and len(
            historical,
        ) >= 2:
            ratio = (
                historical[-1]
                / historical[0]
                if historical[0] > 0
                else 1.0
            )
            n = len(historical)
            growth_rate = (
                ratio ** (1 / (n - 1))
                if n > 1
                else 1.0
            )
            predictions = [
                round(
                    historical[-1]
                    * growth_rate ** (i + 1),
                    2,
                )
                for i in range(periods_ahead)
            ]
        else:
            predictions = [
                round(avg, 2)
                for _ in range(periods_ahead)
            ]

        self._forecasts[fid] = {
            "forecast_id": fid,
            "method": method,
            "historical_count": len(
                historical,
            ),
            "predictions": predictions,
            "timestamp": time.time(),
        }

        self._stats[
            "forecasts_made"
        ] += 1

        return {
            "forecast_id": fid,
            "method": method,
            "predictions": predictions,
            "periods": periods_ahead,
            "forecasted": True,
        }

    def model_scenario(
        self,
        scenario_name: str,
        base_revenue: float = 0.0,
        growth_pct: float = 0.0,
        periods: int = 4,
    ) -> dict[str, Any]:
        """Senaryo modeller.

        Args:
            scenario_name: Senaryo adı.
            base_revenue: Temel gelir.
            growth_pct: Büyüme yüzdesi.
            periods: Dönem sayısı.

        Returns:
            Senaryo bilgisi.
        """
        projections = []
        current = base_revenue
        for i in range(periods):
            current *= (
                1 + growth_pct / 100
            )
            projections.append(
                round(current, 2),
            )

        total = sum(projections)

        self._scenarios[scenario_name] = {
            "name": scenario_name,
            "base": base_revenue,
            "growth_pct": growth_pct,
            "projections": projections,
            "total": round(total, 2),
        }

        self._stats[
            "scenarios_modeled"
        ] += 1

        return {
            "scenario": scenario_name,
            "projections": projections,
            "total": round(total, 2),
            "modeled": True,
        }

    def handle_seasonality(
        self,
        monthly_data: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Mevsimsellik işler.

        Args:
            monthly_data: Aylık veriler.

        Returns:
            Mevsimsellik bilgisi.
        """
        monthly_data = monthly_data or []

        if len(monthly_data) < 12:
            return {
                "seasonal": False,
                "reason": (
                    "insufficient_data"
                ),
                "handled": True,
            }

        avg = (
            sum(monthly_data)
            / len(monthly_data)
        )
        indices = [
            round(m / avg, 3)
            if avg > 0
            else 1.0
            for m in monthly_data[:12]
        ]

        max_idx = max(indices)
        min_idx = min(indices)
        variation = max_idx - min_idx

        seasonal = variation > 0.3

        peak = indices.index(max_idx) + 1
        trough = indices.index(min_idx) + 1

        return {
            "seasonal": seasonal,
            "indices": indices,
            "peak_month": peak,
            "trough_month": trough,
            "variation": round(
                variation, 3,
            ),
            "handled": True,
        }

    def confidence_interval(
        self,
        forecast_id: str,
        confidence: float = 0.95,
    ) -> dict[str, Any]:
        """Güven aralığı hesaplar.

        Args:
            forecast_id: Tahmin kimliği.
            confidence: Güven düzeyi.

        Returns:
            Aralık bilgisi.
        """
        forecast = self._forecasts.get(
            forecast_id,
        )
        if not forecast:
            return {
                "forecast_id": forecast_id,
                "found": False,
            }

        predictions = forecast[
            "predictions"
        ]
        if not predictions:
            return {
                "forecast_id": forecast_id,
                "intervals": [],
                "calculated": True,
            }

        z = (
            1.96
            if confidence >= 0.95
            else 1.645
        )

        intervals = []
        for i, pred in enumerate(
            predictions,
        ):
            margin = pred * 0.1 * (i + 1)
            intervals.append({
                "prediction": pred,
                "lower": round(
                    pred - z * margin, 2,
                ),
                "upper": round(
                    pred + z * margin, 2,
                ),
            })

        return {
            "forecast_id": forecast_id,
            "confidence": confidence,
            "intervals": intervals,
            "calculated": True,
        }

    def analyze_variance(
        self,
        predicted: list[float]
        | None = None,
        actual: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Varyans analizi yapar.

        Args:
            predicted: Tahmin değerler.
            actual: Gerçek değerler.

        Returns:
            Varyans bilgisi.
        """
        predicted = predicted or []
        actual = actual or []

        n = min(
            len(predicted), len(actual),
        )
        if n == 0:
            return {
                "mape": 0.0,
                "analyzed": True,
            }

        errors = []
        for i in range(n):
            if actual[i] != 0:
                err = abs(
                    (actual[i]
                     - predicted[i])
                    / actual[i]
                )
                errors.append(err)

        mape = (
            (sum(errors) / len(errors))
            * 100
            if errors
            else 0.0
        )

        rmse = (
            math.sqrt(
                sum(
                    (actual[i]
                     - predicted[i]) ** 2
                    for i in range(n)
                )
                / n,
            )
        )

        return {
            "mape": round(mape, 2),
            "rmse": round(rmse, 2),
            "data_points": n,
            "accuracy_pct": round(
                100 - mape, 2,
            ),
            "analyzed": True,
        }

    @property
    def forecast_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats[
            "forecasts_made"
        ]

    @property
    def scenario_count(self) -> int:
        """Senaryo sayısı."""
        return self._stats[
            "scenarios_modeled"
        ]
