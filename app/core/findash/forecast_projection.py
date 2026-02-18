"""
Tahmin projeksiyonu modulu.

Gelir tahmini, gider tahmini,
senaryo modelleme, guven bantlari,
varsayim takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ForecastProjection:
    """Tahmin projeksiyonu.

    Attributes:
        _data_points: Veri noktalari.
        _assumptions: Varsayimlar.
        _scenarios: Senaryolar.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Projeksiyonu baslatir."""
        self._data_points: list[dict] = []
        self._assumptions: list[dict] = []
        self._scenarios: list[dict] = []
        self._stats: dict[str, int] = {
            "forecasts_made": 0,
            "scenarios_created": 0,
        }
        logger.info(
            "ForecastProjection baslatildi"
        )

    @property
    def data_point_count(self) -> int:
        """Veri noktasi sayisi."""
        return len(self._data_points)

    def add_data_point(
        self,
        metric: str = "revenue",
        value: float = 0.0,
        period: str = "",
    ) -> dict[str, Any]:
        """Veri noktasi ekler.

        Args:
            metric: Metrik.
            value: Deger.
            period: Donem.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._data_points.append({
                "metric": metric,
                "value": value,
                "period": period,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            })

            return {
                "metric": metric,
                "value": value,
                "period": period,
                "total_points": len(
                    self._data_points
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def forecast_revenue(
        self,
        months: int = 6,
    ) -> dict[str, Any]:
        """Gelir tahmini yapar.

        Args:
            months: Tahmin donemi.

        Returns:
            Tahmin bilgisi.
        """
        try:
            points = [
                p["value"]
                for p in self._data_points
                if p["metric"] == "revenue"
            ]

            return self._linear_forecast(
                points, months, "revenue"
            )

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "forecasted": False,
                "error": str(e),
            }

    def forecast_expense(
        self,
        months: int = 6,
    ) -> dict[str, Any]:
        """Gider tahmini yapar.

        Args:
            months: Tahmin donemi.

        Returns:
            Tahmin bilgisi.
        """
        try:
            points = [
                p["value"]
                for p in self._data_points
                if p["metric"] == "expense"
            ]

            return self._linear_forecast(
                points, months, "expense"
            )

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "forecasted": False,
                "error": str(e),
            }

    def create_scenario(
        self,
        name: str = "",
        scenario_type: str = "base",
        revenue_growth: float = 0.0,
        expense_growth: float = 0.0,
        months: int = 12,
    ) -> dict[str, Any]:
        """Senaryo olusturur.

        Args:
            name: Senaryo adi.
            scenario_type: Senaryo turu.
            revenue_growth: Gelir buyume orani.
            expense_growth: Gider buyume orani.
            months: Donem.

        Returns:
            Senaryo bilgisi.
        """
        try:
            sid = f"sn_{uuid4()!s:.8}"

            rev_points = [
                p["value"]
                for p in self._data_points
                if p["metric"] == "revenue"
            ]
            exp_points = [
                p["value"]
                for p in self._data_points
                if p["metric"] == "expense"
            ]

            last_rev = (
                rev_points[-1]
                if rev_points
                else 0.0
            )
            last_exp = (
                exp_points[-1]
                if exp_points
                else 0.0
            )

            projections = []
            for i in range(1, months + 1):
                rev = last_rev * (
                    1
                    + revenue_growth / 100
                ) ** i
                exp = last_exp * (
                    1
                    + expense_growth / 100
                ) ** i
                projections.append({
                    "month": i,
                    "revenue": round(rev, 2),
                    "expense": round(exp, 2),
                    "profit": round(
                        rev - exp, 2
                    ),
                })

            scenario = {
                "scenario_id": sid,
                "name": name,
                "type": scenario_type,
                "revenue_growth": (
                    revenue_growth
                ),
                "expense_growth": (
                    expense_growth
                ),
                "months": months,
                "projections": projections,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._scenarios.append(scenario)
            self._stats[
                "scenarios_created"
            ] += 1

            return {
                "scenario_id": sid,
                "name": name,
                "type": scenario_type,
                "projections": projections,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def add_assumption(
        self,
        name: str = "",
        value: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Varsayim ekler.

        Args:
            name: Varsayim adi.
            value: Deger.
            category: Kategori.

        Returns:
            Ekleme bilgisi.
        """
        try:
            aid = f"as_{uuid4()!s:.8}"
            assumption = {
                "assumption_id": aid,
                "name": name,
                "value": value,
                "category": category,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._assumptions.append(
                assumption
            )

            return {
                "assumption_id": aid,
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_confidence_bands(
        self,
        months: int = 6,
    ) -> dict[str, Any]:
        """Guven bantlarini getirir.

        Args:
            months: Tahmin donemi.

        Returns:
            Guven bantlari.
        """
        try:
            points = [
                p["value"]
                for p in self._data_points
                if p["metric"] == "revenue"
            ]

            if len(points) < 3:
                return {
                    "bands": [],
                    "confidence": (
                        "insufficient_data"
                    ),
                    "retrieved": True,
                }

            avg = sum(points) / len(points)
            variance = sum(
                (x - avg) ** 2
                for x in points
            ) / len(points)
            std_dev = variance**0.5

            n = len(points)
            x_mean = (n - 1) / 2.0
            y_mean = avg
            num = sum(
                (i - x_mean)
                * (points[i] - y_mean)
                for i in range(n)
            )
            den = sum(
                (i - x_mean) ** 2
                for i in range(n)
            )
            slope = (
                num / den if den != 0 else 0
            )
            intercept = y_mean - slope * x_mean

            bands = []
            for i in range(1, months + 1):
                mid = (
                    slope * (n + i - 1)
                    + intercept
                )
                margin = std_dev * (
                    1 + i * 0.1
                )
                bands.append({
                    "month": i,
                    "lower": round(
                        mid - margin, 2
                    ),
                    "mid": round(mid, 2),
                    "upper": round(
                        mid + margin, 2
                    ),
                })

            return {
                "bands": bands,
                "std_dev": round(std_dev, 2),
                "confidence": "calculated",
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_assumptions(
        self,
    ) -> dict[str, Any]:
        """Varsayimlari getirir.

        Returns:
            Varsayim listesi.
        """
        try:
            return {
                "assumptions": list(
                    self._assumptions
                ),
                "assumption_count": len(
                    self._assumptions
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def _linear_forecast(
        self,
        points: list[float],
        months: int,
        metric: str,
    ) -> dict[str, Any]:
        """Dogrusal tahmin yapar."""
        if len(points) < 2:
            return {
                "metric": metric,
                "forecast": [],
                "trend": "insufficient_data",
                "forecasted": True,
            }

        n = len(points)
        x_mean = (n - 1) / 2.0
        y_mean = sum(points) / n

        num = sum(
            (i - x_mean)
            * (points[i] - y_mean)
            for i in range(n)
        )
        den = sum(
            (i - x_mean) ** 2
            for i in range(n)
        )
        slope = num / den if den != 0 else 0
        intercept = y_mean - slope * x_mean

        forecast = [
            {
                "month": i,
                "value": round(
                    slope * (n + i - 1)
                    + intercept,
                    2,
                ),
            }
            for i in range(1, months + 1)
        ]

        self._stats["forecasts_made"] += 1

        return {
            "metric": metric,
            "current_value": round(
                points[-1], 2
            ),
            "slope": round(slope, 2),
            "forecast": forecast,
            "forecasted": True,
        }
