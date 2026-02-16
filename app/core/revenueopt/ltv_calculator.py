"""ATLAS Yaşam Boyu Değer Hesaplayıcı modülü.

LTV hesaplama, segment analizi,
kohort takibi, tahmin modelleri,
yatırım rehberliği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LTVCalculator:
    """Yaşam boyu değer hesaplayıcı.

    Müşteri yaşam boyu değerini hesaplar.

    Attributes:
        _customers: Müşteri LTV kayıtları.
        _segments: Segment kayıtları.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._customers: dict[
            str, dict[str, Any]
        ] = {}
        self._segments: dict[
            str, dict[str, Any]
        ] = {}
        self._cohorts: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "ltvs_calculated": 0,
            "segments_analyzed": 0,
        }

        logger.info(
            "LTVCalculator baslatildi",
        )

    def calculate_ltv(
        self,
        customer_id: str,
        avg_purchase: float = 0.0,
        purchase_frequency: float = 0.0,
        lifespan_months: int = 12,
        margin_pct: float = 100.0,
    ) -> dict[str, Any]:
        """LTV hesaplar.

        Args:
            customer_id: Müşteri kimliği.
            avg_purchase: Ortalama satın alma.
            purchase_frequency: Satın alma
                sıklığı (aylık).
            lifespan_months: Yaşam süresi
                (ay).
            margin_pct: Marj yüzdesi.

        Returns:
            LTV bilgisi.
        """
        annual_value = (
            avg_purchase
            * purchase_frequency
            * 12
        )
        ltv = (
            annual_value
            * (lifespan_months / 12)
            * (margin_pct / 100)
        )

        self._customers[customer_id] = {
            "customer_id": customer_id,
            "ltv": round(ltv, 2),
            "avg_purchase": avg_purchase,
            "frequency": purchase_frequency,
            "lifespan": lifespan_months,
            "timestamp": time.time(),
        }

        self._stats[
            "ltvs_calculated"
        ] += 1

        return {
            "customer_id": customer_id,
            "ltv": round(ltv, 2),
            "annual_value": round(
                annual_value, 2,
            ),
            "calculated": True,
        }

    def analyze_segment(
        self,
        segment_name: str,
        customer_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Segment analizi yapar.

        Args:
            segment_name: Segment adı.
            customer_ids: Müşteri kimlikleri.

        Returns:
            Analiz bilgisi.
        """
        customer_ids = customer_ids or []

        ltvs = [
            self._customers[cid]["ltv"]
            for cid in customer_ids
            if cid in self._customers
        ]

        if not ltvs:
            return {
                "segment": segment_name,
                "avg_ltv": 0.0,
                "analyzed": True,
            }

        avg_ltv = sum(ltvs) / len(ltvs)
        max_ltv = max(ltvs)
        min_ltv = min(ltvs)

        self._segments[segment_name] = {
            "name": segment_name,
            "count": len(ltvs),
            "avg_ltv": round(avg_ltv, 2),
            "max_ltv": max_ltv,
            "min_ltv": min_ltv,
        }

        self._stats[
            "segments_analyzed"
        ] += 1

        return {
            "segment": segment_name,
            "count": len(ltvs),
            "avg_ltv": round(avg_ltv, 2),
            "max_ltv": max_ltv,
            "min_ltv": min_ltv,
            "analyzed": True,
        }

    def track_cohort(
        self,
        cohort_name: str,
        customer_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kohort takibi yapar.

        Args:
            cohort_name: Kohort adı.
            customer_ids: Müşteri kimlikleri.

        Returns:
            Takip bilgisi.
        """
        customer_ids = customer_ids or []
        self._cohorts[cohort_name] = (
            customer_ids
        )

        ltvs = [
            self._customers[cid]["ltv"]
            for cid in customer_ids
            if cid in self._customers
        ]

        avg = (
            sum(ltvs) / len(ltvs)
            if ltvs
            else 0.0
        )

        return {
            "cohort": cohort_name,
            "size": len(customer_ids),
            "avg_ltv": round(avg, 2),
            "tracked": True,
        }

    def predict_ltv(
        self,
        customer_id: str,
        growth_rate: float = 0.0,
        months_ahead: int = 12,
    ) -> dict[str, Any]:
        """LTV tahmini yapar.

        Args:
            customer_id: Müşteri kimliği.
            growth_rate: Büyüme oranı.
            months_ahead: İlerisi (ay).

        Returns:
            Tahmin bilgisi.
        """
        customer = self._customers.get(
            customer_id,
        )
        if not customer:
            return {
                "customer_id": customer_id,
                "found": False,
            }

        current_ltv = customer["ltv"]
        predicted = (
            current_ltv
            * (1 + growth_rate / 100)
            ** (months_ahead / 12)
        )

        return {
            "customer_id": customer_id,
            "current_ltv": current_ltv,
            "predicted_ltv": round(
                predicted, 2,
            ),
            "growth_rate": growth_rate,
            "months_ahead": months_ahead,
            "predicted": True,
        }

    def guide_investment(
        self,
        customer_id: str,
        acquisition_cost: float = 0.0,
    ) -> dict[str, Any]:
        """Yatırım rehberliği yapar.

        Args:
            customer_id: Müşteri kimliği.
            acquisition_cost: Edinme maliyeti.

        Returns:
            Rehberlik bilgisi.
        """
        customer = self._customers.get(
            customer_id,
        )
        if not customer:
            return {
                "customer_id": customer_id,
                "found": False,
            }

        ltv = customer["ltv"]
        ratio = (
            ltv / acquisition_cost
            if acquisition_cost > 0
            else 0.0
        )

        if ratio >= 3:
            recommendation = "invest_more"
        elif ratio >= 1:
            recommendation = "maintain"
        else:
            recommendation = (
                "reduce_spending"
            )

        return {
            "customer_id": customer_id,
            "ltv": ltv,
            "acquisition_cost": (
                acquisition_cost
            ),
            "ltv_cac_ratio": round(
                ratio, 2,
            ),
            "recommendation": (
                recommendation
            ),
            "guided": True,
        }

    @property
    def ltv_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "ltvs_calculated"
        ]

    @property
    def segment_count(self) -> int:
        """Segment sayısı."""
        return self._stats[
            "segments_analyzed"
        ]
