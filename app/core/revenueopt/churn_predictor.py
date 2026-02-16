"""ATLAS Kayıp Tahmincisi modülü.

Kayıp risk puanlama, erken uyarı,
kök neden analizi, tutundurma
aksiyonları, geri kazanma kampanyaları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ChurnPredictor:
    """Kayıp tahmincisi.

    Müşteri kayıp riskini tahmin eder.

    Attributes:
        _customers: Müşteri kayıtları.
        _actions: Aksiyon kayıtları.
    """

    def __init__(self) -> None:
        """Tahmenciyi başlatır."""
        self._customers: dict[
            str, dict[str, Any]
        ] = {}
        self._actions: list[
            dict[str, Any]
        ] = []
        self._campaigns: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "risks_scored": 0,
            "warnings_issued": 0,
        }

        logger.info(
            "ChurnPredictor baslatildi",
        )

    def score_churn_risk(
        self,
        customer_id: str,
        days_inactive: int = 0,
        support_tickets: int = 0,
        usage_decline_pct: float = 0.0,
    ) -> dict[str, Any]:
        """Kayıp risk puanı hesaplar.

        Args:
            customer_id: Müşteri kimliği.
            days_inactive: İnaktif gün.
            support_tickets: Destek talepleri.
            usage_decline_pct: Kullanım
                düşüş yüzdesi.

        Returns:
            Risk bilgisi.
        """
        score = (
            days_inactive * 1.5
            + support_tickets * 10
            + usage_decline_pct * 0.5
        )
        score = min(100, max(0, score))

        if score >= 75:
            level = "critical"
        elif score >= 50:
            level = "high"
        elif score >= 25:
            level = "medium"
        else:
            level = "low"

        self._customers[customer_id] = {
            "customer_id": customer_id,
            "risk_score": round(score, 1),
            "risk_level": level,
            "timestamp": time.time(),
        }

        self._stats[
            "risks_scored"
        ] += 1

        return {
            "customer_id": customer_id,
            "risk_score": round(score, 1),
            "risk_level": level,
            "scored": True,
        }

    def issue_early_warning(
        self,
        customer_id: str,
        threshold: float = 50.0,
    ) -> dict[str, Any]:
        """Erken uyarı verir.

        Args:
            customer_id: Müşteri kimliği.
            threshold: Eşik değer.

        Returns:
            Uyarı bilgisi.
        """
        customer = self._customers.get(
            customer_id,
        )
        if not customer:
            return {
                "customer_id": customer_id,
                "found": False,
            }

        score = customer["risk_score"]
        warning = score >= threshold

        if warning:
            self._stats[
                "warnings_issued"
            ] += 1

        return {
            "customer_id": customer_id,
            "risk_score": score,
            "warning": warning,
            "threshold": threshold,
            "issued": warning,
        }

    def analyze_root_cause(
        self,
        customer_id: str,
        factors: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Kök neden analizi yapar.

        Args:
            customer_id: Müşteri kimliği.
            factors: Faktörler.

        Returns:
            Analiz bilgisi.
        """
        factors = factors or {}

        causes = []
        if factors.get(
            "price_sensitivity", 0,
        ) > 70:
            causes.append("price_too_high")
        if factors.get(
            "support_issues", 0,
        ) > 3:
            causes.append(
                "poor_support_experience",
            )
        if factors.get(
            "competitor_switch", False,
        ):
            causes.append(
                "competitor_attraction",
            )
        if factors.get(
            "usage_decline", 0,
        ) > 50:
            causes.append(
                "low_product_value",
            )

        if not causes:
            causes.append("unknown")

        primary = causes[0]

        return {
            "customer_id": customer_id,
            "primary_cause": primary,
            "all_causes": causes,
            "cause_count": len(causes),
            "analyzed": True,
        }

    def suggest_retention_actions(
        self,
        customer_id: str,
        risk_level: str = "medium",
    ) -> dict[str, Any]:
        """Tutundurma aksiyonları önerir.

        Args:
            customer_id: Müşteri kimliği.
            risk_level: Risk seviyesi.

        Returns:
            Aksiyon bilgisi.
        """
        action_map = {
            "critical": [
                "personal_call",
                "custom_discount",
                "executive_outreach",
            ],
            "high": [
                "retention_offer",
                "dedicated_support",
            ],
            "medium": [
                "check_in_email",
                "feature_highlight",
            ],
            "low": [
                "engagement_campaign",
            ],
        }

        actions = action_map.get(
            risk_level,
            action_map["medium"],
        )

        for a in actions:
            self._actions.append({
                "customer_id": customer_id,
                "action": a,
                "timestamp": time.time(),
            })

        return {
            "customer_id": customer_id,
            "actions": actions,
            "action_count": len(actions),
            "suggested": True,
        }

    def create_winback_campaign(
        self,
        customer_ids: list[str]
        | None = None,
        offer_type: str = "discount",
        discount_pct: float = 20.0,
    ) -> dict[str, Any]:
        """Geri kazanma kampanyası oluşturur.

        Args:
            customer_ids: Müşteri kimlikleri.
            offer_type: Teklif tipi.
            discount_pct: İndirim yüzdesi.

        Returns:
            Kampanya bilgisi.
        """
        customer_ids = customer_ids or []
        self._counter += 1
        cid = f"wb_{self._counter}"

        campaign = {
            "campaign_id": cid,
            "customer_count": len(
                customer_ids,
            ),
            "offer_type": offer_type,
            "discount_pct": discount_pct,
            "status": "created",
            "timestamp": time.time(),
        }

        self._campaigns.append(campaign)

        return {
            "campaign_id": cid,
            "target_count": len(
                customer_ids,
            ),
            "offer_type": offer_type,
            "discount_pct": discount_pct,
            "created": True,
        }

    @property
    def risk_count(self) -> int:
        """Risk puanlama sayısı."""
        return self._stats[
            "risks_scored"
        ]

    @property
    def warning_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "warnings_issued"
        ]
