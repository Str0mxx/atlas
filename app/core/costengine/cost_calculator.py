"""ATLAS Maliyet Hesaplayici modulu.

API call, compute, storage, time, opportunity
maliyet hesaplama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CostCalculator:
    """Maliyet hesaplayici.

    Karar basina maliyet hesaplar.

    Attributes:
        _calculations: Hesaplama kayitlari.
        _rates: Birim fiyatlar.
    """

    def __init__(self) -> None:
        """Maliyet hesaplayiciyi baslatir."""
        self._calculations: list[
            dict[str, Any]
        ] = []
        self._rates: dict[
            str, dict[str, Any]
        ] = {}
        self._defaults = {
            "api_call": 0.01,
            "compute_per_sec": 0.001,
            "storage_per_mb": 0.0001,
            "time_per_hour": 10.0,
            "opportunity_factor": 0.05,
        }
        self._stats = {
            "calculated": 0,
            "total_cost": 0.0,
        }

        logger.info(
            "CostCalculator baslatildi",
        )

    def set_rate(
        self,
        cost_type: str,
        rate: float,
        unit: str = "",
    ) -> dict[str, Any]:
        """Birim fiyat ayarlar.

        Args:
            cost_type: Maliyet tipi.
            rate: Birim fiyat.
            unit: Birim.

        Returns:
            Ayarlama bilgisi.
        """
        self._rates[cost_type] = {
            "rate": rate,
            "unit": unit,
            "set_at": time.time(),
        }

        return {
            "cost_type": cost_type,
            "rate": rate,
            "set": True,
        }

    def calculate_api_cost(
        self,
        service: str,
        calls: int = 1,
        rate: float | None = None,
    ) -> dict[str, Any]:
        """API call maliyeti hesaplar.

        Args:
            service: Servis adi.
            calls: Cagri sayisi.
            rate: Ozel fiyat.

        Returns:
            Maliyet bilgisi.
        """
        unit_rate = rate
        if unit_rate is None:
            svc = self._rates.get(
                f"api_{service}",
            )
            if svc:
                unit_rate = svc["rate"]
            else:
                unit_rate = self._defaults[
                    "api_call"
                ]

        cost = unit_rate * calls

        result = {
            "category": "api_call",
            "service": service,
            "calls": calls,
            "rate": unit_rate,
            "cost": round(cost, 6),
            "timestamp": time.time(),
        }

        self._calculations.append(result)
        self._stats["calculated"] += 1
        self._stats["total_cost"] += cost

        return result

    def calculate_compute_cost(
        self,
        duration_seconds: float,
        cpu_units: float = 1.0,
        rate: float | None = None,
    ) -> dict[str, Any]:
        """Compute maliyeti hesaplar.

        Args:
            duration_seconds: Sure (sn).
            cpu_units: CPU birimleri.
            rate: Ozel fiyat.

        Returns:
            Maliyet bilgisi.
        """
        unit_rate = (
            rate
            if rate is not None
            else self._defaults["compute_per_sec"]
        )

        cost = unit_rate * duration_seconds * cpu_units

        result = {
            "category": "compute",
            "duration_seconds": duration_seconds,
            "cpu_units": cpu_units,
            "rate": unit_rate,
            "cost": round(cost, 6),
            "timestamp": time.time(),
        }

        self._calculations.append(result)
        self._stats["calculated"] += 1
        self._stats["total_cost"] += cost

        return result

    def calculate_storage_cost(
        self,
        size_mb: float,
        duration_hours: float = 1.0,
        rate: float | None = None,
    ) -> dict[str, Any]:
        """Storage maliyeti hesaplar.

        Args:
            size_mb: Boyut (MB).
            duration_hours: Sure (saat).
            rate: Ozel fiyat.

        Returns:
            Maliyet bilgisi.
        """
        unit_rate = (
            rate
            if rate is not None
            else self._defaults["storage_per_mb"]
        )

        cost = (
            unit_rate * size_mb * duration_hours
        )

        result = {
            "category": "storage",
            "size_mb": size_mb,
            "duration_hours": duration_hours,
            "rate": unit_rate,
            "cost": round(cost, 6),
            "timestamp": time.time(),
        }

        self._calculations.append(result)
        self._stats["calculated"] += 1
        self._stats["total_cost"] += cost

        return result

    def calculate_time_cost(
        self,
        hours: float,
        rate: float | None = None,
    ) -> dict[str, Any]:
        """Zaman maliyeti hesaplar.

        Args:
            hours: Saat.
            rate: Saatlik ucret.

        Returns:
            Maliyet bilgisi.
        """
        unit_rate = (
            rate
            if rate is not None
            else self._defaults["time_per_hour"]
        )

        cost = unit_rate * hours

        result = {
            "category": "time",
            "hours": hours,
            "rate": unit_rate,
            "cost": round(cost, 6),
            "timestamp": time.time(),
        }

        self._calculations.append(result)
        self._stats["calculated"] += 1
        self._stats["total_cost"] += cost

        return result

    def calculate_opportunity_cost(
        self,
        base_cost: float,
        alternatives: int = 1,
        factor: float | None = None,
    ) -> dict[str, Any]:
        """Firsat maliyeti hesaplar.

        Args:
            base_cost: Temel maliyet.
            alternatives: Alternatif sayisi.
            factor: Firsat carpani.

        Returns:
            Maliyet bilgisi.
        """
        opp_factor = (
            factor
            if factor is not None
            else self._defaults[
                "opportunity_factor"
            ]
        )

        cost = base_cost * opp_factor * alternatives

        result = {
            "category": "opportunity",
            "base_cost": base_cost,
            "alternatives": alternatives,
            "factor": opp_factor,
            "cost": round(cost, 6),
            "timestamp": time.time(),
        }

        self._calculations.append(result)
        self._stats["calculated"] += 1
        self._stats["total_cost"] += cost

        return result

    def calculate_total(
        self,
        components: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplam maliyet hesaplar.

        Args:
            components: Maliyet bilesenleri.

        Returns:
            Toplam maliyet.
        """
        total = sum(
            c.get("cost", 0.0) for c in components
        )

        by_category: dict[str, float] = {}
        for c in components:
            cat = c.get("category", "other")
            by_category[cat] = (
                by_category.get(cat, 0.0)
                + c.get("cost", 0.0)
            )

        return {
            "total_cost": round(total, 6),
            "components": len(components),
            "by_category": by_category,
        }

    def get_history(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Hesaplama gecmisini getirir.

        Args:
            category: Kategori filtresi.
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        calcs = self._calculations
        if category:
            calcs = [
                c for c in calcs
                if c.get("category") == category
            ]
        return list(calcs[-limit:])

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayisi."""
        return self._stats["calculated"]

    @property
    def total_cost(self) -> float:
        """Toplam maliyet."""
        return round(
            self._stats["total_cost"], 6,
        )
