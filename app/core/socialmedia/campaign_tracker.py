"""ATLAS Sosyal Medya Kampanya Takipçisi.

Kampanya yönetimi, performans takibi,
A/B test, bütçe takibi ve ROI hesaplama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SocialCampaignTracker:
    """Sosyal medya kampanya takipçisi.

    Kampanya yaşam döngüsünü yönetir,
    performans izler ve ROI hesaplar.

    Attributes:
        _campaigns: Kampanya kayıtları.
        _ab_tests: A/B test kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._campaigns: dict[str, dict] = {}
        self._ab_tests: dict[str, dict] = {}
        self._stats = {
            "campaigns_created": 0,
            "ab_tests_run": 0,
        }
        logger.info(
            "SocialCampaignTracker "
            "baslatildi",
        )

    @property
    def campaign_count(self) -> int:
        """Oluşturulan kampanya sayısı."""
        return self._stats[
            "campaigns_created"
        ]

    @property
    def ab_test_count(self) -> int:
        """Yürütülen A/B test sayısı."""
        return self._stats["ab_tests_run"]

    def create_campaign(
        self,
        campaign_id: str,
        name: str,
        platform: str = "instagram",
        budget: float = 0.0,
    ) -> dict[str, Any]:
        """Kampanya oluşturur.

        Args:
            campaign_id: Kampanya kimliği.
            name: Kampanya adı.
            platform: Hedef platform.
            budget: Bütçe.

        Returns:
            Kampanya bilgisi.
        """
        self._campaigns[campaign_id] = {
            "name": name,
            "platform": platform,
            "budget": budget,
            "spent": 0.0,
            "status": "active",
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "created_at": time.time(),
        }
        self._stats[
            "campaigns_created"
        ] += 1

        logger.info(
            "Kampanya olusturuldu: %s - %s",
            campaign_id,
            name,
        )

        return {
            "campaign_id": campaign_id,
            "name": name,
            "platform": platform,
            "budget": budget,
            "created": True,
        }

    def track_performance(
        self,
        campaign_id: str,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
    ) -> dict[str, Any]:
        """Kampanya performansını takip eder.

        Args:
            campaign_id: Kampanya kimliği.
            impressions: Görüntülenme.
            clicks: Tıklama.
            conversions: Dönüşüm.

        Returns:
            Performans bilgisi.
        """
        if campaign_id not in self._campaigns:
            return {"found": False}

        c = self._campaigns[campaign_id]
        c["impressions"] += impressions
        c["clicks"] += clicks
        c["conversions"] += conversions

        ctr = (
            (c["clicks"] / c["impressions"]
             * 100)
            if c["impressions"] > 0
            else 0.0
        )
        cvr = (
            (c["conversions"] / c["clicks"]
             * 100)
            if c["clicks"] > 0
            else 0.0
        )

        return {
            "campaign_id": campaign_id,
            "total_impressions": c[
                "impressions"
            ],
            "total_clicks": c["clicks"],
            "ctr": round(ctr, 2),
            "cvr": round(cvr, 2),
            "tracked": True,
        }

    def run_ab_test(
        self,
        test_id: str,
        campaign_id: str,
        variant_a: str = "",
        variant_b: str = "",
    ) -> dict[str, Any]:
        """A/B test çalıştırır.

        Args:
            test_id: Test kimliği.
            campaign_id: Kampanya kimliği.
            variant_a: A varyantı.
            variant_b: B varyantı.

        Returns:
            A/B test bilgisi.
        """
        self._ab_tests[test_id] = {
            "campaign_id": campaign_id,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "status": "running",
            "winner": None,
        }
        self._stats["ab_tests_run"] += 1

        logger.info(
            "A/B test baslatildi: %s",
            test_id,
        )

        return {
            "test_id": test_id,
            "campaign_id": campaign_id,
            "status": "running",
            "started": True,
        }

    def track_budget(
        self,
        campaign_id: str,
        amount_spent: float = 0.0,
    ) -> dict[str, Any]:
        """Bütçe takibi yapar.

        Args:
            campaign_id: Kampanya kimliği.
            amount_spent: Harcanan miktar.

        Returns:
            Bütçe bilgisi.
        """
        if campaign_id not in self._campaigns:
            return {"found": False}

        c = self._campaigns[campaign_id]
        c["spent"] += amount_spent
        remaining = c["budget"] - c["spent"]
        utilization = (
            (c["spent"] / c["budget"] * 100)
            if c["budget"] > 0
            else 0.0
        )
        over_budget = remaining < 0

        return {
            "campaign_id": campaign_id,
            "budget": c["budget"],
            "spent": c["spent"],
            "remaining": round(
                remaining, 2,
            ),
            "utilization": round(
                utilization, 2,
            ),
            "over_budget": over_budget,
            "tracked": True,
        }

    def calculate_roi(
        self,
        campaign_id: str,
        revenue: float = 0.0,
    ) -> dict[str, Any]:
        """ROI hesaplar.

        Args:
            campaign_id: Kampanya kimliği.
            revenue: Gelir.

        Returns:
            ROI bilgisi.
        """
        if campaign_id not in self._campaigns:
            return {"found": False}

        c = self._campaigns[campaign_id]
        spent = c["spent"]
        roi = (
            ((revenue - spent) / spent * 100)
            if spent > 0
            else 0.0
        )
        profitable = roi > 0

        return {
            "campaign_id": campaign_id,
            "revenue": revenue,
            "spent": spent,
            "roi_percent": round(roi, 2),
            "profitable": profitable,
            "calculated": True,
        }
