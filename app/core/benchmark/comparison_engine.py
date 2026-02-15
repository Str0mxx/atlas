"""ATLAS Karsilastirma Motoru modulu.

Sistem arasi karsilastirma, donem karsilastirmasi,
akran benchmarking, endustri standartlari, bosluk analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ComparisonEngine:
    """Karsilastirma motoru.

    Benchmark karsilastirmalari yapar.

    Attributes:
        _baselines: Temel degerler.
        _comparisons: Karsilastirma kayitlari.
    """

    def __init__(self) -> None:
        """Karsilastirma motorunu baslatir."""
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}
        self._standards: dict[
            str, dict[str, Any]
        ] = {}
        self._comparisons: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "comparisons": 0,
        }

        logger.info(
            "ComparisonEngine baslatildi",
        )

    def set_baseline(
        self,
        kpi_id: str,
        value: float,
        period: str = "",
    ) -> dict[str, Any]:
        """Temel deger ayarlar.

        Args:
            kpi_id: KPI ID.
            value: Deger.
            period: Donem.

        Returns:
            Ayarlama bilgisi.
        """
        self._baselines[kpi_id] = {
            "value": value,
            "period": period,
            "set_at": time.time(),
        }

        return {
            "kpi_id": kpi_id,
            "baseline": value,
            "set": True,
        }

    def set_standard(
        self,
        kpi_id: str,
        value: float,
        source: str = "industry",
    ) -> dict[str, Any]:
        """Standart deger ayarlar.

        Args:
            kpi_id: KPI ID.
            value: Deger.
            source: Kaynak.

        Returns:
            Ayarlama bilgisi.
        """
        self._standards[kpi_id] = {
            "value": value,
            "source": source,
            "set_at": time.time(),
        }

        return {
            "kpi_id": kpi_id,
            "standard": value,
            "source": source,
        }

    def compare_to_baseline(
        self,
        kpi_id: str,
        current_value: float,
    ) -> dict[str, Any]:
        """Temel degerle karsilastirir.

        Args:
            kpi_id: KPI ID.
            current_value: Guncel deger.

        Returns:
            Karsilastirma sonucu.
        """
        baseline = self._baselines.get(kpi_id)
        if not baseline:
            return {
                "kpi_id": kpi_id,
                "error": "no_baseline",
            }

        base_val = baseline["value"]
        if base_val == 0:
            change_pct = (
                100.0
                if current_value != 0
                else 0.0
            )
        else:
            change_pct = (
                (current_value - base_val)
                / abs(base_val) * 100
            )

        result = {
            "kpi_id": kpi_id,
            "current": current_value,
            "baseline": base_val,
            "change_pct": round(change_pct, 2),
            "improved": current_value > base_val,
        }

        self._comparisons.append(result)
        self._stats["comparisons"] += 1

        return result

    def compare_periods(
        self,
        kpi_id: str,
        period_a_values: list[float],
        period_b_values: list[float],
    ) -> dict[str, Any]:
        """Donemleri karsilastirir.

        Args:
            kpi_id: KPI ID.
            period_a_values: Donem A degerleri.
            period_b_values: Donem B degerleri.

        Returns:
            Karsilastirma sonucu.
        """
        avg_a = (
            sum(period_a_values) / len(period_a_values)
            if period_a_values
            else 0.0
        )
        avg_b = (
            sum(period_b_values) / len(period_b_values)
            if period_b_values
            else 0.0
        )

        if avg_a == 0:
            change_pct = (
                100.0 if avg_b != 0 else 0.0
            )
        else:
            change_pct = (
                (avg_b - avg_a) / abs(avg_a) * 100
            )

        self._stats["comparisons"] += 1

        return {
            "kpi_id": kpi_id,
            "period_a_avg": round(avg_a, 4),
            "period_b_avg": round(avg_b, 4),
            "change_pct": round(change_pct, 2),
            "improved": avg_b > avg_a,
        }

    def compare_to_standard(
        self,
        kpi_id: str,
        current_value: float,
    ) -> dict[str, Any]:
        """Standartla karsilastirir.

        Args:
            kpi_id: KPI ID.
            current_value: Guncel deger.

        Returns:
            Karsilastirma sonucu.
        """
        standard = self._standards.get(kpi_id)
        if not standard:
            return {
                "kpi_id": kpi_id,
                "error": "no_standard",
            }

        std_val = standard["value"]
        gap = current_value - std_val
        if std_val != 0:
            gap_pct = gap / abs(std_val) * 100
        else:
            gap_pct = 100.0 if gap != 0 else 0.0

        self._stats["comparisons"] += 1

        return {
            "kpi_id": kpi_id,
            "current": current_value,
            "standard": std_val,
            "source": standard["source"],
            "gap": round(gap, 4),
            "gap_pct": round(gap_pct, 2),
            "meets_standard": current_value >= std_val,
        }

    def gap_analysis(
        self,
        current_values: dict[str, float],
        target_values: dict[str, float],
    ) -> dict[str, Any]:
        """Bosluk analizi yapar.

        Args:
            current_values: Guncel degerler.
            target_values: Hedef degerler.

        Returns:
            Bosluk analiz sonucu.
        """
        gaps = {}
        total_gap = 0.0

        for kpi_id, target in target_values.items():
            current = current_values.get(kpi_id, 0.0)
            gap = target - current
            if target != 0:
                gap_pct = gap / abs(target) * 100
            else:
                gap_pct = 0.0

            gaps[kpi_id] = {
                "current": current,
                "target": target,
                "gap": round(gap, 4),
                "gap_pct": round(gap_pct, 2),
                "met": current >= target,
            }
            total_gap += abs(gap_pct)

        met_count = sum(
            1 for g in gaps.values() if g["met"]
        )

        return {
            "gaps": gaps,
            "total_kpis": len(gaps),
            "met_count": met_count,
            "avg_gap_pct": round(
                total_gap / max(len(gaps), 1), 2,
            ),
        }

    @property
    def baseline_count(self) -> int:
        """Temel deger sayisi."""
        return len(self._baselines)

    @property
    def standard_count(self) -> int:
        """Standart sayisi."""
        return len(self._standards)

    @property
    def comparison_count(self) -> int:
        """Karsilastirma sayisi."""
        return self._stats["comparisons"]
