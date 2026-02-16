"""ATLAS Kampanya Yöneticisi modülü.

Outreach kampanyaları, sekans yönetimi,
A/B testi, performans takibi,
optimizasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CampaignManager:
    """Kampanya yöneticisi.

    İletişim kampanyalarını yönetir.

    Attributes:
        _campaigns: Kampanya kayıtları.
        _sequences: Sekans tanımları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._campaigns: dict[
            str, dict[str, Any]
        ] = {}
        self._sequences: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._ab_tests: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "campaigns_created": 0,
            "campaigns_completed": 0,
            "sequences_created": 0,
            "ab_tests_run": 0,
        }

        logger.info(
            "CampaignManager baslatildi",
        )

    def create_campaign(
        self,
        name: str,
        contact_ids: list[str],
        template: str = "",
        schedule: str = "immediate",
    ) -> dict[str, Any]:
        """Kampanya oluşturur.

        Args:
            name: Kampanya adı.
            contact_ids: Kişi ID'leri.
            template: Şablon.
            schedule: Zamanlama.

        Returns:
            Kampanya bilgisi.
        """
        self._counter += 1
        cid = f"camp_{self._counter}"

        campaign = {
            "campaign_id": cid,
            "name": name,
            "contact_ids": contact_ids,
            "template": template,
            "schedule": schedule,
            "status": "active",
            "sent_count": 0,
            "response_count": 0,
            "open_count": 0,
            "bounce_count": 0,
            "created_at": time.time(),
        }
        self._campaigns[cid] = campaign
        self._stats[
            "campaigns_created"
        ] += 1

        return {
            "campaign_id": cid,
            "name": name,
            "contacts": len(contact_ids),
            "status": "active",
            "created": True,
        }

    def pause_campaign(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Kampanyayı duraklatır.

        Args:
            campaign_id: Kampanya ID.

        Returns:
            Güncelleme bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        camp["status"] = "paused"
        return {
            "campaign_id": campaign_id,
            "status": "paused",
            "paused": True,
        }

    def resume_campaign(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Kampanyayı sürdürür.

        Args:
            campaign_id: Kampanya ID.

        Returns:
            Güncelleme bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        camp["status"] = "active"
        return {
            "campaign_id": campaign_id,
            "status": "active",
            "resumed": True,
        }

    def complete_campaign(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Kampanyayı tamamlar.

        Args:
            campaign_id: Kampanya ID.

        Returns:
            Tamamlama bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        camp["status"] = "completed"
        camp["completed_at"] = time.time()
        self._stats[
            "campaigns_completed"
        ] += 1

        return {
            "campaign_id": campaign_id,
            "status": "completed",
            "completed": True,
        }

    def record_send(
        self,
        campaign_id: str,
        contact_id: str,
    ) -> dict[str, Any]:
        """Gönderim kaydeder.

        Args:
            campaign_id: Kampanya ID.
            contact_id: Kişi ID.

        Returns:
            Kayıt bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        camp["sent_count"] += 1
        return {
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "sent_count": camp["sent_count"],
            "recorded": True,
        }

    def record_response(
        self,
        campaign_id: str,
        contact_id: str,
        response_type: str = "reply",
    ) -> dict[str, Any]:
        """Yanıt kaydeder.

        Args:
            campaign_id: Kampanya ID.
            contact_id: Kişi ID.
            response_type: Yanıt tipi.

        Returns:
            Kayıt bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        camp["response_count"] += 1
        return {
            "campaign_id": campaign_id,
            "contact_id": contact_id,
            "response_type": response_type,
            "response_count": camp[
                "response_count"
            ],
            "recorded": True,
        }

    def create_sequence(
        self,
        campaign_id: str,
        steps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Sekans oluşturur.

        Args:
            campaign_id: Kampanya ID.
            steps: Adımlar.

        Returns:
            Sekans bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        self._sequences[campaign_id] = steps
        self._stats[
            "sequences_created"
        ] += 1

        return {
            "campaign_id": campaign_id,
            "steps": len(steps),
            "created": True,
        }

    def create_ab_test(
        self,
        campaign_id: str,
        variant_a: dict[str, Any],
        variant_b: dict[str, Any],
        split_ratio: float = 0.5,
    ) -> dict[str, Any]:
        """A/B testi oluşturur.

        Args:
            campaign_id: Kampanya ID.
            variant_a: A varyantı.
            variant_b: B varyantı.
            split_ratio: Bölme oranı.

        Returns:
            Test bilgisi.
        """
        self._counter += 1
        tid = f"ab_{self._counter}"

        test = {
            "test_id": tid,
            "campaign_id": campaign_id,
            "variant_a": {
                **variant_a,
                "sends": 0,
                "responses": 0,
            },
            "variant_b": {
                **variant_b,
                "sends": 0,
                "responses": 0,
            },
            "split_ratio": split_ratio,
            "status": "running",
            "created_at": time.time(),
        }
        self._ab_tests.append(test)
        self._stats["ab_tests_run"] += 1

        return {
            "test_id": tid,
            "campaign_id": campaign_id,
            "split_ratio": split_ratio,
            "created": True,
        }

    def get_performance(
        self,
        campaign_id: str,
    ) -> dict[str, Any]:
        """Performans getirir.

        Args:
            campaign_id: Kampanya ID.

        Returns:
            Performans bilgisi.
        """
        camp = self._campaigns.get(
            campaign_id,
        )
        if not camp:
            return {
                "error": (
                    "campaign_not_found"
                ),
            }

        sent = camp["sent_count"]
        responses = camp["response_count"]
        response_rate = (
            responses / max(sent, 1)
        ) * 100

        return {
            "campaign_id": campaign_id,
            "name": camp["name"],
            "status": camp["status"],
            "sent": sent,
            "responses": responses,
            "response_rate": round(
                response_rate, 1,
            ),
            "contacts": len(
                camp["contact_ids"],
            ),
        }

    def get_campaigns(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Kampanyaları getirir.

        Args:
            status: Durum filtresi.
            limit: Maks kayıt.

        Returns:
            Kampanya listesi.
        """
        results = list(
            self._campaigns.values(),
        )
        if status:
            results = [
                c for c in results
                if c["status"] == status
            ]
        return results[:limit]

    @property
    def campaign_count(self) -> int:
        """Kampanya sayısı."""
        return self._stats[
            "campaigns_created"
        ]

    @property
    def active_count(self) -> int:
        """Aktif kampanya sayısı."""
        return sum(
            1 for c in self._campaigns.values()
            if c["status"] == "active"
        )
