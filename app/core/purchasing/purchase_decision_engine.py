"""ATLAS Satın Alma Karar Motoru modülü.

Karar kriterleri, çok faktörlü puanlama,
bütçe kontrolü, onay yönlendirme,
öneri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PurchaseDecisionEngine:
    """Satın alma karar motoru.

    Satın alma kararlarını analiz eder.

    Attributes:
        _decisions: Karar kayıtları.
        _criteria: Kriter kayıtları.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._decisions: dict[
            str, dict[str, Any]
        ] = {}
        self._criteria: dict[
            str, dict[str, float]
        ] = {
            "default": {
                "price": 0.30,
                "quality": 0.25,
                "delivery": 0.20,
                "reliability": 0.15,
                "support": 0.10,
            },
        }
        self._counter = 0
        self._stats = {
            "decisions_made": 0,
            "approvals_routed": 0,
            "recommendations_given": 0,
        }

        logger.info(
            "PurchaseDecisionEngine "
            "baslatildi",
        )

    def set_criteria(
        self,
        profile: str,
        weights: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Karar kriteri belirler.

        Args:
            profile: Profil adı.
            weights: Ağırlıklar.

        Returns:
            Kriter bilgisi.
        """
        weights = weights or {}
        self._criteria[profile] = weights

        return {
            "profile": profile,
            "weights": weights,
            "factor_count": len(weights),
            "set": True,
        }

    def score_options(
        self,
        options: list[dict[str, Any]]
        | None = None,
        profile: str = "default",
    ) -> dict[str, Any]:
        """Seçenekleri puanlar.

        Args:
            options: Seçenekler.
            profile: Profil.

        Returns:
            Puanlama bilgisi.
        """
        options = options or []
        weights = self._criteria.get(
            profile,
            self._criteria["default"],
        )

        scored = []
        for opt in options:
            total = 0.0
            for factor, weight in (
                weights.items()
            ):
                val = opt.get(factor, 50)
                total += val * weight
            scored.append({
                "name": opt.get(
                    "name", "unknown",
                ),
                "score": round(total, 1),
            })

        scored.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return {
            "options": scored,
            "count": len(scored),
            "best": (
                scored[0]["name"]
                if scored else None
            ),
        }

    def check_budget(
        self,
        amount: float,
        budget_limit: float,
        spent_so_far: float = 0.0,
    ) -> dict[str, Any]:
        """Bütçe kontrol eder.

        Args:
            amount: Tutar.
            budget_limit: Bütçe limiti.
            spent_so_far: Harcanan.

        Returns:
            Bütçe bilgisi.
        """
        remaining = (
            budget_limit - spent_so_far
        )
        within_budget = amount <= remaining
        usage_pct = round(
            (spent_so_far + amount)
            / max(budget_limit, 0.01) * 100,
            1,
        )

        status = (
            "within" if usage_pct <= 80
            else "warning" if usage_pct <= 100
            else "exceeded"
        )

        return {
            "amount": amount,
            "budget_limit": budget_limit,
            "remaining": round(
                remaining, 2,
            ),
            "within_budget": within_budget,
            "usage_pct": usage_pct,
            "status": status,
        }

    def route_approval(
        self,
        amount: float,
        category: str = "general",
    ) -> dict[str, Any]:
        """Onay yönlendirir.

        Args:
            amount: Tutar.
            category: Kategori.

        Returns:
            Yönlendirme bilgisi.
        """
        if amount < 100:
            level = "auto"
            approver = "system"
        elif amount < 1000:
            level = "manager"
            approver = "department_manager"
        elif amount < 10000:
            level = "director"
            approver = "department_director"
        else:
            level = "executive"
            approver = "cfo"

        self._stats[
            "approvals_routed"
        ] += 1

        return {
            "amount": amount,
            "category": category,
            "approval_level": level,
            "approver": approver,
            "auto_approved": level == "auto",
        }

    def recommend(
        self,
        item: str,
        options: list[dict[str, Any]]
        | None = None,
        budget: float = 0.0,
        urgency: str = "medium",
    ) -> dict[str, Any]:
        """Öneri yapar.

        Args:
            item: Ürün.
            options: Seçenekler.
            budget: Bütçe.
            urgency: Aciliyet.

        Returns:
            Öneri bilgisi.
        """
        self._counter += 1
        did = f"dec_{self._counter}"

        options = options or []
        scored = self.score_options(options)
        best = scored.get("best")

        reasons = []
        if best:
            reasons.append(
                f"Best overall score: {best}",
            )
        if urgency == "high":
            reasons.append(
                "High urgency - prioritize "
                "delivery speed",
            )
        if budget > 0:
            reasons.append(
                f"Budget: ${budget:.2f}",
            )

        decision = {
            "decision_id": did,
            "item": item,
            "recommendation": best,
            "reasons": reasons,
            "urgency": urgency,
            "timestamp": time.time(),
        }
        self._decisions[did] = decision
        self._stats[
            "decisions_made"
        ] += 1
        self._stats[
            "recommendations_given"
        ] += 1

        return {
            "decision_id": did,
            "item": item,
            "recommendation": best,
            "reasons": reasons,
            "reason_count": len(reasons),
        }

    def get_decision(
        self,
        decision_id: str,
    ) -> dict[str, Any] | None:
        """Karar döndürür."""
        return self._decisions.get(
            decision_id,
        )

    @property
    def decision_count(self) -> int:
        """Karar sayısı."""
        return self._stats[
            "decisions_made"
        ]

    @property
    def approval_count(self) -> int:
        """Onay sayısı."""
        return self._stats[
            "approvals_routed"
        ]
