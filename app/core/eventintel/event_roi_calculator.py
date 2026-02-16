"""ATLAS Etkinlik ROI Hesaplayıcı.

Maliyet takibi, lead atıflandırma,
gelir etkisi, ROI hesaplama ve karşılaştırma.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventROICalculator:
    """Etkinlik ROI hesaplayıcısı.

    Etkinlik yatırım getirilerini hesaplar,
    maliyetleri takip eder ve karşılaştırır.

    Attributes:
        _events: Etkinlik ROI kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._events: dict[str, dict] = {}
        self._stats = {
            "rois_calculated": 0,
            "comparisons_made": 0,
        }
        logger.info(
            "EventROICalculator baslatildi",
        )

    @property
    def calculated_count(self) -> int:
        """Hesaplanan ROI sayısı."""
        return self._stats[
            "rois_calculated"
        ]

    @property
    def comparison_count(self) -> int:
        """Yapılan karşılaştırma sayısı."""
        return self._stats[
            "comparisons_made"
        ]

    def track_costs(
        self,
        event_id: str,
        ticket: float = 0.0,
        travel: float = 0.0,
        accommodation: float = 0.0,
        misc: float = 0.0,
    ) -> dict[str, Any]:
        """Maliyet takibi yapar.

        Args:
            event_id: Etkinlik kimliği.
            ticket: Bilet maliyeti.
            travel: Seyahat maliyeti.
            accommodation: Konaklama maliyeti.
            misc: Diğer maliyetler.

        Returns:
            Maliyet bilgisi.
        """
        total = (
            ticket + travel
            + accommodation + misc
        )
        self._events[event_id] = {
            "costs": {
                "ticket": ticket,
                "travel": travel,
                "accommodation": accommodation,
                "misc": misc,
                "total": total,
            },
            "leads": 0,
            "revenue": 0.0,
        }

        return {
            "event_id": event_id,
            "total_cost": total,
            "tracked": True,
        }

    def attribute_leads(
        self,
        event_id: str,
        lead_count: int = 0,
        qualified_count: int = 0,
    ) -> dict[str, Any]:
        """Lead atıflandırma yapar.

        Args:
            event_id: Etkinlik kimliği.
            lead_count: Lead sayısı.
            qualified_count: Nitelikli lead.

        Returns:
            Atıflandırma bilgisi.
        """
        if event_id in self._events:
            self._events[event_id][
                "leads"
            ] = lead_count

        qualification_rate = (
            qualified_count / lead_count
            if lead_count > 0
            else 0.0
        )

        return {
            "event_id": event_id,
            "lead_count": lead_count,
            "qualified_count": qualified_count,
            "qualification_rate": round(
                qualification_rate, 2,
            ),
            "attributed": True,
        }

    def track_revenue_impact(
        self,
        event_id: str,
        direct_revenue: float = 0.0,
        pipeline_value: float = 0.0,
    ) -> dict[str, Any]:
        """Gelir etkisi takibi yapar.

        Args:
            event_id: Etkinlik kimliği.
            direct_revenue: Doğrudan gelir.
            pipeline_value: Pipeline değeri.

        Returns:
            Gelir bilgisi.
        """
        total_impact = (
            direct_revenue + pipeline_value
        )

        if event_id in self._events:
            self._events[event_id][
                "revenue"
            ] = total_impact

        return {
            "event_id": event_id,
            "direct_revenue": direct_revenue,
            "pipeline_value": pipeline_value,
            "total_impact": total_impact,
            "tracked": True,
        }

    def calculate_roi(
        self,
        event_id: str,
    ) -> dict[str, Any]:
        """ROI hesaplar.

        Args:
            event_id: Etkinlik kimliği.

        Returns:
            ROI bilgisi.
        """
        if event_id not in self._events:
            return {
                "event_id": event_id,
                "found": False,
            }

        data = self._events[event_id]
        cost = data["costs"]["total"]
        revenue = data["revenue"]

        roi = (
            (revenue - cost) / cost * 100
            if cost > 0
            else 0.0
        )

        if roi >= 200:
            category = "excellent"
        elif roi >= 100:
            category = "good"
        elif roi >= 0:
            category = "moderate"
        else:
            category = "poor"

        self._stats[
            "rois_calculated"
        ] += 1

        return {
            "event_id": event_id,
            "total_cost": cost,
            "total_revenue": revenue,
            "roi_pct": round(roi, 1),
            "category": category,
            "calculated": True,
        }

    def compare_events(
        self,
        event_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Etkinlikleri karşılaştırır.

        Args:
            event_ids: Etkinlik kimlikleri.

        Returns:
            Karşılaştırma bilgisi.
        """
        if event_ids is None:
            event_ids = []

        results = []
        for eid in event_ids:
            if eid in self._events:
                data = self._events[eid]
                cost = data["costs"]["total"]
                rev = data["revenue"]
                roi = (
                    (rev - cost) / cost * 100
                    if cost > 0
                    else 0.0
                )
                results.append({
                    "event_id": eid,
                    "cost": cost,
                    "revenue": rev,
                    "roi_pct": round(roi, 1),
                })

        results.sort(
            key=lambda x: x["roi_pct"],
            reverse=True,
        )
        self._stats[
            "comparisons_made"
        ] += 1

        best = (
            results[0]["event_id"]
            if results
            else ""
        )

        return {
            "results": results,
            "best_event": best,
            "compared": True,
        }
