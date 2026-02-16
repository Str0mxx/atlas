"""
Maliyet yapısı haritacısı.

İş modelindeki maliyet kalemlerini analiz
eder, sabit/değişken olarak sınıflandırır,
maliyet sürücülerini belirler ve
optimizasyon fırsatlarını tespit eder.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CostStructureMapper:
    """
    Maliyet yapısı haritacısı.

    Maliyet kalemlerini analiz ederek
    yapısal sınıflandırma, sürücü tespiti
    ve optimizasyon önerileri sunar.
    """

    def __init__(self) -> None:
        """Maliyet haritacısını başlatır."""
        self._costs: list[dict] = []
        self._stats: dict = {
            "analyses_done": 0,
        }

    @property
    def analysis_count(self) -> int:
        """Yapılan analiz sayısını döner."""
        return self._stats["analyses_done"]

    def analyze_costs(
        self,
        costs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Maliyetleri analiz eder.

        Args:
            costs: Maliyet kalemleri listesi.

        Returns:
            Maliyet analiz sonuçları.
        """
        try:
            if costs is None:
                costs = []
            total = sum(
                c.get("amount", 0)
                for c in costs
            )
            count = len(costs)
            avg = round(
                total / max(count, 1), 2
            )
            self._stats["analyses_done"] += 1
            return {
                "total_cost": round(total, 2),
                "cost_count": count,
                "average_cost": avg,
                "analyzed": True,
            }
        except Exception as e:
            logger.error(
                f"Maliyet analiz hatası: {e}"
            )
            return {
                "total_cost": 0.0,
                "cost_count": 0,
                "average_cost": 0.0,
                "analyzed": False,
            }
    def classify_fixed_variable(
        self,
        costs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Sabit ve değişken maliyetleri sınıflar.

        Args:
            costs: Maliyet kalemleri listesi.

        Returns:
            Sabit/değişken sınıflandırma sonucu.
        """
        try:
            if costs is None:
                costs = []
            fixed = sum(
                c.get("amount", 0)
                for c in costs
                if c.get("category") == "fixed"
            )
            variable = sum(
                c.get("amount", 0)
                for c in costs
                if c.get("category") == "variable"
            )
            total = fixed + variable
            fixed_pct = round(
                (fixed / max(total, 1)) * 100,
                1,
            )
            variable_pct = round(
                (variable / max(total, 1)) * 100,
                1,
            )
            if fixed_pct > 70:
                structure = "cost_heavy"
            elif fixed_pct >= 40:
                structure = "balanced"
            else:
                structure = "variable_heavy"
            return {
                "fixed": round(fixed, 2),
                "variable": round(variable, 2),
                "fixed_pct": fixed_pct,
                "variable_pct": variable_pct,
                "structure": structure,
                "classified": True,
            }
        except Exception as e:
            logger.error(
                f"Sınıflandırma hatası: {e}"
            )
            return {
                "fixed": 0.0,
                "variable": 0.0,
                "fixed_pct": 0.0,
                "variable_pct": 0.0,
                "structure": "unknown",
                "classified": False,
            }
    def identify_drivers(
        self,
        costs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Maliyet sürücülerini belirler.

        Args:
            costs: Maliyet kalemleri listesi.

        Returns:
            Maliyet sürücüleri bilgisi.
        """
        try:
            if costs is None:
                costs = []
            sorted_costs = sorted(
                costs,
                key=lambda c: c.get(
                    "amount", 0
                ),
                reverse=True,
            )
            top_drivers = [
                {
                    "name": c.get(
                        "name", "unknown"
                    ),
                    "amount": c.get(
                        "amount", 0
                    ),
                }
                for c in sorted_costs[:3]
            ]
            return {
                "drivers": top_drivers,
                "driver_count": len(
                    top_drivers
                ),
                "identified": True,
            }
        except Exception as e:
            logger.error(
                f"Sürücü tespit hatası: {e}"
            )
            return {
                "drivers": [],
                "driver_count": 0,
                "identified": False,
            }
    def find_optimization(
        self,
        total_cost: float = 0.0,
        industry_avg: float = 0.0,
    ) -> dict[str, Any]:
        """
        Optimizasyon fırsatlarını bulur.

        Args:
            total_cost: Toplam maliyet.
            industry_avg: Sektör ortalaması.

        Returns:
            Optimizasyon fırsat analizi.
        """
        try:
            gap = round(
                total_cost - industry_avg, 2
            )
            gap_pct = round(
                (gap / max(industry_avg, 1))
                * 100,
                1,
            )
            opportunities: list[str] = []
            if gap > 0:
                opportunities.append(
                    "reduce_overhead"
                )
            if gap_pct > 20:
                opportunities.append(
                    "renegotiate_contracts"
                )
            if gap_pct > 50:
                opportunities.append(
                    "restructure_operations"
                )
            if not opportunities:
                opportunities.append(
                    "cost_efficient"
                )
            return {
                "gap": gap,
                "gap_pct": gap_pct,
                "opportunities": opportunities,
                "opportunity_count": len(
                    opportunities
                ),
                "optimized": True,
            }
        except Exception as e:
            logger.error(
                f"Optimizasyon hatası: {e}"
            )
            return {
                "gap": 0.0,
                "gap_pct": 0.0,
                "opportunities": [],
                "opportunity_count": 0,
                "optimized": False,
            }
    def benchmark_costs(
        self,
        cost_ratio: float = 0.0,
        benchmarks: (
            dict[str, float] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Maliyetleri kıyaslar.

        Args:
            cost_ratio: Maliyet oranı.
            benchmarks: Kıyaslama değerleri.

        Returns:
            Kıyaslama sonuçları.
        """
        try:
            if benchmarks is None:
                benchmarks = {
                    "industry_avg": 45.0,
                    "best_in_class": 30.0,
                    "worst": 70.0,
                }
            best = benchmarks.get(
                "best_in_class", 30
            )
            avg = benchmarks.get(
                "industry_avg", 45
            )
            worst = benchmarks.get(
                "worst", 70
            )
            if cost_ratio <= best:
                position = "excellent"
                percentile = 90
            elif cost_ratio <= avg:
                position = "above_average"
                percentile = 60
            elif cost_ratio <= worst:
                position = "below_average"
                percentile = 30
            else:
                position = "poor"
                percentile = 10
            return {
                "cost_ratio": cost_ratio,
                "benchmarks": benchmarks,
                "position": position,
                "percentile": percentile,
                "benchmarked": True,
            }
        except Exception as e:
            logger.error(
                f"Kıyaslama hatası: {e}"
            )
            return {
                "cost_ratio": 0.0,
                "benchmarks": {},
                "position": "unknown",
                "percentile": 0,
                "benchmarked": False,
            }
