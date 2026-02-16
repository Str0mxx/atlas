"""ATLAS Kampanya ROI Analizcisi modülü.

ROI hesaplama, atıf modelleme,
kanal karşılaştırma, bütçe
optimizasyonu, performans tahmini.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CampaignROIAnalyzer:
    """Kampanya ROI analizcisi.

    Kampanya getirisini analiz eder.

    Attributes:
        _campaigns: Kampanya kayıtları.
        _channels: Kanal kayıtları.
    """

    def __init__(self) -> None:
        """Analizcıyı başlatır."""
        self._campaigns: dict[
            str, dict[str, Any]
        ] = {}
        self._channels: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "rois_calculated": 0,
            "budgets_optimized": 0,
        }

        logger.info(
            "CampaignROIAnalyzer "
            "baslatildi",
        )

    def calculate_roi(
        self,
        campaign_id: str,
        spend: float = 0.0,
        revenue: float = 0.0,
    ) -> dict[str, Any]:
        """ROI hesaplar.

        Args:
            campaign_id: Kampanya kimliği.
            spend: Harcama.
            revenue: Gelir.

        Returns:
            ROI bilgisi.
        """
        roi = (
            ((revenue - spend) / spend)
            * 100
            if spend > 0
            else 0.0
        )

        self._campaigns[campaign_id] = {
            "campaign_id": campaign_id,
            "spend": spend,
            "revenue": revenue,
            "roi": round(roi, 1),
            "profit": round(
                revenue - spend, 2,
            ),
            "timestamp": time.time(),
        }

        self._stats[
            "rois_calculated"
        ] += 1

        return {
            "campaign_id": campaign_id,
            "spend": spend,
            "revenue": revenue,
            "roi_pct": round(roi, 1),
            "profit": round(
                revenue - spend, 2,
            ),
            "calculated": True,
        }

    def model_attribution(
        self,
        campaign_id: str,
        touchpoints: list[dict[str, Any]]
        | None = None,
        model: str = "last_touch",
    ) -> dict[str, Any]:
        """Atıf modelleme yapar.

        Args:
            campaign_id: Kampanya kimliği.
            touchpoints: Temas noktaları.
            model: Atıf modeli.

        Returns:
            Atıf bilgisi.
        """
        touchpoints = touchpoints or []

        if not touchpoints:
            return {
                "campaign_id": campaign_id,
                "attributions": {},
                "modeled": True,
            }

        attributions: dict[
            str, float
        ] = {}
        n = len(touchpoints)

        if model == "last_touch":
            last = touchpoints[-1]
            ch = last.get(
                "channel", "unknown",
            )
            attributions[ch] = 100.0
        elif model == "first_touch":
            first = touchpoints[0]
            ch = first.get(
                "channel", "unknown",
            )
            attributions[ch] = 100.0
        else:
            share = 100.0 / n
            for tp in touchpoints:
                ch = tp.get(
                    "channel", "unknown",
                )
                attributions[ch] = (
                    attributions.get(ch, 0)
                    + share
                )

        return {
            "campaign_id": campaign_id,
            "model": model,
            "attributions": {
                k: round(v, 1)
                for k, v in (
                    attributions.items()
                )
            },
            "modeled": True,
        }

    def compare_channels(
        self,
        channels: dict[str, dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Kanalları karşılaştırır.

        Args:
            channels: Kanal verileri
                {name: {spend, revenue}}.

        Returns:
            Karşılaştırma bilgisi.
        """
        channels = channels or {}

        results = []
        for name, data in channels.items():
            spend = data.get("spend", 0)
            revenue = data.get("revenue", 0)
            roi = (
                ((revenue - spend) / spend)
                * 100
                if spend > 0
                else 0.0
            )
            results.append({
                "channel": name,
                "spend": spend,
                "revenue": revenue,
                "roi_pct": round(roi, 1),
            })

            self._channels[name] = {
                "spend": spend,
                "revenue": revenue,
                "roi": round(roi, 1),
            }

        results.sort(
            key=lambda x: x["roi_pct"],
            reverse=True,
        )

        best = (
            results[0]["channel"]
            if results
            else None
        )

        return {
            "channels": results,
            "best_channel": best,
            "compared": True,
        }

    def optimize_budget(
        self,
        total_budget: float = 0.0,
        channel_rois: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Bütçe optimizasyonu yapar.

        Args:
            total_budget: Toplam bütçe.
            channel_rois: Kanal ROI'ları.

        Returns:
            Optimizasyon bilgisi.
        """
        channel_rois = (
            channel_rois or {}
        )

        if not channel_rois:
            return {
                "allocations": {},
                "optimized": True,
            }

        total_roi = sum(
            max(0, r)
            for r in channel_rois.values()
        )

        allocations = {}
        for ch, roi in (
            channel_rois.items()
        ):
            weight = (
                max(0, roi) / total_roi
                if total_roi > 0
                else 1 / len(channel_rois)
            )
            allocations[ch] = round(
                total_budget * weight, 2,
            )

        self._stats[
            "budgets_optimized"
        ] += 1

        return {
            "total_budget": total_budget,
            "allocations": allocations,
            "optimized": True,
        }

    def predict_performance(
        self,
        campaign_id: str,
        planned_spend: float = 0.0,
    ) -> dict[str, Any]:
        """Performans tahmini yapar.

        Args:
            campaign_id: Kampanya kimliği.
            planned_spend: Planlanan harcama.

        Returns:
            Tahmin bilgisi.
        """
        campaign = self._campaigns.get(
            campaign_id,
        )
        if not campaign:
            return {
                "campaign_id": campaign_id,
                "found": False,
            }

        roi_rate = campaign["roi"] / 100
        predicted_revenue = (
            planned_spend * (1 + roi_rate)
        )
        predicted_profit = (
            predicted_revenue - planned_spend
        )

        return {
            "campaign_id": campaign_id,
            "planned_spend": planned_spend,
            "predicted_revenue": round(
                predicted_revenue, 2,
            ),
            "predicted_profit": round(
                predicted_profit, 2,
            ),
            "based_on_roi": campaign["roi"],
            "predicted": True,
        }

    @property
    def roi_count(self) -> int:
        """ROI hesaplama sayısı."""
        return self._stats[
            "rois_calculated"
        ]

    @property
    def budget_opt_count(self) -> int:
        """Bütçe optimizasyonu sayısı."""
        return self._stats[
            "budgets_optimized"
        ]
