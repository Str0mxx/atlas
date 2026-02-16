"""ATLAS Anlaşma Akış Yöneticisi.

Pipeline yönetimi, aşama takibi,
dönüşüm oranları ve önceliklendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

STAGES = [
    "prospect",
    "qualified",
    "proposal",
    "negotiation",
    "closed_won",
    "closed_lost",
]


class DealFlowManager:
    """Anlaşma akış yöneticisi.

    Anlaşma pipeline'ını yönetir,
    aşamaları takip eder ve tahmin yapar.

    Attributes:
        _deals: Anlaşma kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._deals: dict[str, dict] = {}
        self._stats = {
            "deals_created": 0,
            "deals_closed": 0,
        }
        logger.info(
            "DealFlowManager baslatildi",
        )

    @property
    def deal_count(self) -> int:
        """Oluşturulan anlaşma sayısı."""
        return self._stats["deals_created"]

    @property
    def closed_count(self) -> int:
        """Kapanan anlaşma sayısı."""
        return self._stats["deals_closed"]

    def create_deal(
        self,
        deal_id: str,
        partner_id: str,
        value: float = 0.0,
    ) -> dict[str, Any]:
        """Anlaşma oluşturur.

        Args:
            deal_id: Anlaşma kimliği.
            partner_id: Ortak kimliği.
            value: Anlaşma değeri.

        Returns:
            Anlaşma bilgisi.
        """
        self._deals[deal_id] = {
            "partner_id": partner_id,
            "value": value,
            "stage": "prospect",
            "probability": 0.1,
            "created_at": time.time(),
        }
        self._stats["deals_created"] += 1

        logger.info(
            "Anlasma olusturuldu: %s "
            "(deger: %.0f)",
            deal_id,
            value,
        )

        return {
            "deal_id": deal_id,
            "partner_id": partner_id,
            "value": value,
            "stage": "prospect",
            "created": True,
        }

    def advance_stage(
        self,
        deal_id: str,
    ) -> dict[str, Any]:
        """Anlaşmayı sonraki aşamaya ilerletir.

        Args:
            deal_id: Anlaşma kimliği.

        Returns:
            Aşama bilgisi.
        """
        if deal_id not in self._deals:
            return {"found": False}

        deal = self._deals[deal_id]
        current = deal["stage"]
        idx = STAGES.index(current)

        if idx < len(STAGES) - 2:
            new_stage = STAGES[idx + 1]
            deal["stage"] = new_stage
            prob_map = {
                "qualified": 0.3,
                "proposal": 0.5,
                "negotiation": 0.7,
                "closed_won": 1.0,
            }
            deal["probability"] = prob_map.get(
                new_stage, deal["probability"],
            )

            if new_stage == "closed_won":
                self._stats[
                    "deals_closed"
                ] += 1

            return {
                "deal_id": deal_id,
                "previous_stage": current,
                "new_stage": new_stage,
                "probability": deal[
                    "probability"
                ],
                "advanced": True,
            }

        return {
            "deal_id": deal_id,
            "stage": current,
            "advanced": False,
        }

    def get_conversion_rates(
        self,
    ) -> dict[str, Any]:
        """Dönüşüm oranlarını hesaplar.

        Returns:
            Dönüşüm oranı bilgisi.
        """
        stage_counts: dict[str, int] = {}
        for deal in self._deals.values():
            stage = deal["stage"]
            stage_counts[stage] = (
                stage_counts.get(stage, 0) + 1
            )

        total = len(self._deals) or 1
        rates = {
            s: round(
                stage_counts.get(s, 0)
                / total
                * 100,
                1,
            )
            for s in STAGES
        }

        return {
            "total_deals": len(self._deals),
            "stage_counts": stage_counts,
            "conversion_rates": rates,
            "calculated": True,
        }

    def forecast_pipeline(
        self,
    ) -> dict[str, Any]:
        """Pipeline tahmini yapar.

        Returns:
            Tahmin bilgisi.
        """
        weighted_value = sum(
            d["value"] * d["probability"]
            for d in self._deals.values()
        )
        total_value = sum(
            d["value"]
            for d in self._deals.values()
        )

        return {
            "total_deals": len(self._deals),
            "total_value": total_value,
            "weighted_value": round(
                weighted_value, 2,
            ),
            "forecasted": True,
        }

    def prioritize_deals(
        self,
    ) -> dict[str, Any]:
        """Anlaşmaları önceliklendirir.

        Returns:
            Önceliklendirme bilgisi.
        """
        ranked = sorted(
            self._deals.items(),
            key=lambda x: (
                x[1]["value"]
                * x[1]["probability"]
            ),
            reverse=True,
        )

        top = [
            {
                "deal_id": did,
                "weighted": round(
                    d["value"]
                    * d["probability"],
                    2,
                ),
            }
            for did, d in ranked[:5]
        ]

        return {
            "total_deals": len(self._deals),
            "top_deals": top,
            "prioritized": True,
        }
