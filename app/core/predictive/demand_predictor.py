"""ATLAS Talep Tahmini modulu.

Satis tahmini, kaynak talebi, kapasite planlama,
envanter optimizasyonu ve mevsimsel duzeltmeler.
"""

import logging
import math
from typing import Any

from app.models.predictive import (
    DataPoint,
    DemandCategory,
    DemandForecast,
)

logger = logging.getLogger(__name__)


class DemandPredictor:
    """Talep tahmin sistemi.

    Satis, kaynak, kapasite ve envanter taleplerini
    tahmin eder. Mevsimsel duzeltmeler uygular.

    Attributes:
        _seasonal_factors: Mevsimsel carpanlar (ay bazli).
        _forecasts: Tahmin gecmisi.
        _safety_stock_factor: Guvenlik stogu carpani.
    """

    def __init__(
        self,
        seasonal_factors: dict[int, float] | None = None,
        safety_stock_factor: float = 1.5,
    ) -> None:
        """Talep tahmin sistemini baslatir.

        Args:
            seasonal_factors: Ay -> carpan eslesmesi (1-12).
            safety_stock_factor: Guvenlik stogu carpani.
        """
        self._seasonal_factors = seasonal_factors or {
            1: 0.8, 2: 0.85, 3: 0.95, 4: 1.0, 5: 1.05, 6: 1.1,
            7: 1.0, 8: 0.9, 9: 1.05, 10: 1.1, 11: 1.2, 12: 1.3,
        }
        self._safety_stock_factor = safety_stock_factor
        self._forecasts: list[DemandForecast] = []

        logger.info("DemandPredictor baslatildi (safety_stock=%.1f)", safety_stock_factor)

    def forecast_sales(self, history: list[DataPoint], horizon_days: int = 30, month: int = 1) -> DemandForecast:
        """Satis tahmini yapar.

        Args:
            history: Gecmis satis verileri.
            horizon_days: Tahmin ufku (gun).
            month: Hedef ay (mevsimsel duzeltme icin).

        Returns:
            DemandForecast nesnesi.
        """
        values = [d.value for d in history]
        if not values:
            return DemandForecast(category=DemandCategory.SALES, forecast_horizon_days=horizon_days)

        # Ortalama ve trend
        mean = sum(values) / len(values)
        current = values[-1]

        # Basit lineer trend
        if len(values) >= 2:
            trend = (values[-1] - values[0]) / len(values)
        else:
            trend = 0.0

        # Mevsimsel carpan
        seasonal = self._seasonal_factors.get(month, 1.0)

        # Tahmin: son deger + trend * gun + mevsimsel
        predicted = (current + trend * horizon_days) * seasonal
        predicted = max(0.0, predicted)

        change_pct = ((predicted - current) / max(abs(current), 1e-10)) * 100

        # Guven: veri miktarina bagdli
        confidence = min(1.0, len(values) / 30)

        forecast = DemandForecast(
            category=DemandCategory.SALES,
            current_demand=current,
            predicted_demand=predicted,
            change_percent=change_pct,
            seasonal_factor=seasonal,
            confidence=confidence,
            forecast_horizon_days=horizon_days,
        )
        self._forecasts.append(forecast)
        logger.info("Satis tahmini: mevcut=%.1f, tahmin=%.1f, degisim=%%%.1f", current, predicted, change_pct)
        return forecast

    def forecast_resource_demand(self, usage_data: list[DataPoint], horizon_days: int = 30) -> DemandForecast:
        """Kaynak talebi tahmini yapar.

        Args:
            usage_data: Gecmis kullanim verileri.
            horizon_days: Tahmin ufku.

        Returns:
            DemandForecast nesnesi.
        """
        values = [d.value for d in usage_data]
        if not values:
            return DemandForecast(category=DemandCategory.RESOURCE, forecast_horizon_days=horizon_days)

        mean = sum(values) / len(values)
        current = values[-1]

        # Buyume trendi
        if len(values) >= 3:
            recent_growth = (values[-1] - values[-3]) / max(abs(values[-3]), 1e-10) / 2
        else:
            recent_growth = 0.0

        predicted = current * (1 + recent_growth * horizon_days / 30)
        predicted = max(0.0, predicted)
        change_pct = ((predicted - current) / max(abs(current), 1e-10)) * 100

        forecast = DemandForecast(
            category=DemandCategory.RESOURCE,
            current_demand=current,
            predicted_demand=predicted,
            change_percent=change_pct,
            confidence=min(1.0, len(values) / 20),
            forecast_horizon_days=horizon_days,
        )
        self._forecasts.append(forecast)
        return forecast

    def plan_capacity(self, demand_forecast: DemandForecast, current_capacity: float) -> dict[str, Any]:
        """Kapasite planlama yapar.

        Args:
            demand_forecast: Talep tahmini.
            current_capacity: Mevcut kapasite.

        Returns:
            Kapasite plani (utilization, gap, recommendation).
        """
        predicted = demand_forecast.predicted_demand
        utilization = predicted / max(current_capacity, 1e-10)
        gap = predicted - current_capacity

        if utilization > 0.9:
            recommendation = "Kapasite acilen arttirilmali"
            urgency = "critical"
        elif utilization > 0.75:
            recommendation = "Kapasite artisi planlanmali"
            urgency = "high"
        elif utilization > 0.5:
            recommendation = "Kapasite yeterli, izlemeye devam"
            urgency = "normal"
        else:
            recommendation = "Kapasite fazlasi var, optimizasyon onerilir"
            urgency = "low"

        return {
            "current_capacity": current_capacity,
            "predicted_demand": predicted,
            "utilization_rate": min(utilization, 2.0),
            "capacity_gap": gap,
            "recommendation": recommendation,
            "urgency": urgency,
        }

    def optimize_inventory(self, demand_forecast: DemandForecast, lead_time_days: int = 7) -> DemandForecast:
        """Envanter optimizasyonu yapar.

        Args:
            demand_forecast: Talep tahmini.
            lead_time_days: Tedarik suresi (gun).

        Returns:
            Optimize edilmis DemandForecast nesnesi.
        """
        daily_demand = demand_forecast.predicted_demand / max(demand_forecast.forecast_horizon_days, 1)

        # Guvenlik stogu = carpan * gunluk talep * sqrt(tedarik suresi)
        safety_stock = self._safety_stock_factor * daily_demand * math.sqrt(lead_time_days)

        # Yeniden siparis noktasi = gunluk talep * tedarik suresi + guvenlik stogu
        reorder_point = daily_demand * lead_time_days + safety_stock

        # Optimal envanter = tahmin edilen talep + guvenlik stogu
        optimal = demand_forecast.predicted_demand + safety_stock

        forecast = DemandForecast(
            category=DemandCategory.INVENTORY,
            current_demand=demand_forecast.current_demand,
            predicted_demand=demand_forecast.predicted_demand,
            change_percent=demand_forecast.change_percent,
            seasonal_factor=demand_forecast.seasonal_factor,
            optimal_inventory=optimal,
            reorder_point=reorder_point,
            confidence=demand_forecast.confidence,
            forecast_horizon_days=demand_forecast.forecast_horizon_days,
        )
        self._forecasts.append(forecast)

        logger.info(
            "Envanter optimizasyonu: optimal=%.1f, reorder=%.1f, safety=%.1f",
            optimal, reorder_point, safety_stock,
        )
        return forecast

    def apply_seasonal_adjustment(self, value: float, month: int) -> float:
        """Mevsimsel duzeltme uygular.

        Args:
            value: Ham deger.
            month: Ay (1-12).

        Returns:
            Duzeltilmis deger.
        """
        factor = self._seasonal_factors.get(month, 1.0)
        return value * factor

    @property
    def forecasts(self) -> list[DemandForecast]:
        """Tahmin gecmisi."""
        return list(self._forecasts)

    @property
    def forecast_count(self) -> int:
        """Toplam tahmin sayisi."""
        return len(self._forecasts)
