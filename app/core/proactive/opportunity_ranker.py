"""ATLAS Fırsat Sıralayıcı modülü.

Fırsat puanlama, değer tahmini,
aciliyet değerlendirme, fizibilite kontrolü,
öncelik sıralaması.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OpportunityRanker:
    """Fırsat sıralayıcı.

    Fırsatları puanlar ve sıralar.

    Attributes:
        _opportunities: Fırsat kayıtları.
        _rankings: Sıralama geçmişi.
    """

    def __init__(self) -> None:
        """Sıralayıcıyı başlatır."""
        self._opportunities: list[
            dict[str, Any]
        ] = []
        self._rankings: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "opportunities_scored": 0,
            "rankings_generated": 0,
        }

        logger.info(
            "OpportunityRanker baslatildi",
        )

    def score_opportunity(
        self,
        title: str,
        opportunity_type: str = "efficiency",
        value_estimate: float = 0.0,
        urgency: float = 0.5,
        feasibility: float = 0.5,
        risk: float = 0.3,
    ) -> dict[str, Any]:
        """Fırsatı puanlar.

        Args:
            title: Fırsat başlığı.
            opportunity_type: Fırsat tipi.
            value_estimate: Değer tahmini.
            urgency: Aciliyet (0-1).
            feasibility: Fizibilite (0-1).
            risk: Risk (0-1).

        Returns:
            Puanlama bilgisi.
        """
        self._counter += 1
        oid = f"opp_{self._counter}"

        # Puanlama: değer + aciliyet + fizibilite - risk
        urgency = max(0.0, min(1.0, urgency))
        feasibility = max(0.0, min(1.0, feasibility))
        risk = max(0.0, min(1.0, risk))

        score = round(
            (value_estimate * 0.3)
            + (urgency * 25)
            + (feasibility * 25)
            + ((1 - risk) * 20),
            2,
        )

        opportunity = {
            "opportunity_id": oid,
            "title": title,
            "opportunity_type": opportunity_type,
            "value_estimate": value_estimate,
            "urgency": urgency,
            "feasibility": feasibility,
            "risk": risk,
            "score": score,
            "created_at": time.time(),
        }
        self._opportunities.append(opportunity)
        self._stats["opportunities_scored"] += 1

        return opportunity

    def estimate_value(
        self,
        opportunity_id: str,
        revenue_impact: float = 0.0,
        cost_saving: float = 0.0,
        time_saving_hours: float = 0.0,
        strategic_value: float = 0.0,
    ) -> dict[str, Any]:
        """Değer tahmini yapar.

        Args:
            opportunity_id: Fırsat ID.
            revenue_impact: Gelir etkisi.
            cost_saving: Maliyet tasarrufu.
            time_saving_hours: Zaman tasarrufu (saat).
            strategic_value: Stratejik değer.

        Returns:
            Değer bilgisi.
        """
        opp = None
        for o in self._opportunities:
            if o["opportunity_id"] == opportunity_id:
                opp = o
                break

        if not opp:
            return {"error": "opportunity_not_found"}

        total_value = (
            revenue_impact
            + cost_saving
            + (time_saving_hours * 50)
            + strategic_value
        )
        opp["value_estimate"] = total_value
        opp["value_breakdown"] = {
            "revenue_impact": revenue_impact,
            "cost_saving": cost_saving,
            "time_saving_hours": time_saving_hours,
            "strategic_value": strategic_value,
        }

        return {
            "opportunity_id": opportunity_id,
            "total_value": total_value,
            "breakdown": opp["value_breakdown"],
        }

    def assess_urgency(
        self,
        opportunity_id: str,
        deadline: float | None = None,
        competitor_pressure: float = 0.0,
        decay_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Aciliyet değerlendirir.

        Args:
            opportunity_id: Fırsat ID.
            deadline: Son tarih (timestamp).
            competitor_pressure: Rekabet baskısı.
            decay_rate: Değer azalma hızı.

        Returns:
            Aciliyet bilgisi.
        """
        opp = None
        for o in self._opportunities:
            if o["opportunity_id"] == opportunity_id:
                opp = o
                break

        if not opp:
            return {"error": "opportunity_not_found"}

        urgency = 0.5
        now = time.time()

        if deadline:
            remaining = deadline - now
            if remaining < 3600:
                urgency = 1.0
            elif remaining < 86400:
                urgency = 0.8
            elif remaining < 604800:
                urgency = 0.6
            else:
                urgency = 0.4

        urgency = min(
            1.0,
            urgency + competitor_pressure * 0.3,
        )
        urgency = min(
            1.0,
            urgency + decay_rate * 0.2,
        )

        opp["urgency"] = round(urgency, 3)

        return {
            "opportunity_id": opportunity_id,
            "urgency": opp["urgency"],
        }

    def check_feasibility(
        self,
        opportunity_id: str,
        resources_available: bool = True,
        skills_available: bool = True,
        budget_available: bool = True,
        dependencies_met: bool = True,
    ) -> dict[str, Any]:
        """Fizibilite kontrolü yapar.

        Args:
            opportunity_id: Fırsat ID.
            resources_available: Kaynak var mı.
            skills_available: Yetenek var mı.
            budget_available: Bütçe var mı.
            dependencies_met: Bağımlılıklar karşılandı mı.

        Returns:
            Fizibilite bilgisi.
        """
        opp = None
        for o in self._opportunities:
            if o["opportunity_id"] == opportunity_id:
                opp = o
                break

        if not opp:
            return {"error": "opportunity_not_found"}

        checks = [
            resources_available,
            skills_available,
            budget_available,
            dependencies_met,
        ]
        feasibility = sum(checks) / len(checks)
        opp["feasibility"] = round(feasibility, 3)

        blockers = []
        if not resources_available:
            blockers.append("resources")
        if not skills_available:
            blockers.append("skills")
        if not budget_available:
            blockers.append("budget")
        if not dependencies_met:
            blockers.append("dependencies")

        return {
            "opportunity_id": opportunity_id,
            "feasibility": opp["feasibility"],
            "blockers": blockers,
            "feasible": feasibility >= 0.5,
        }

    def rank_opportunities(
        self,
        top_n: int = 10,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        """Fırsatları sıralar.

        Args:
            top_n: Üst N fırsat.
            min_score: Min puan filtresi.

        Returns:
            Sıralama bilgisi.
        """
        filtered = [
            o for o in self._opportunities
            if o.get("score", 0) >= min_score
        ]
        ranked = sorted(
            filtered,
            key=lambda x: x.get("score", 0),
            reverse=True,
        )[:top_n]

        self._stats["rankings_generated"] += 1

        ranking = {
            "ranked": ranked,
            "count": len(ranked),
            "total_opportunities": len(
                self._opportunities,
            ),
        }
        self._rankings.append(ranking)

        return ranking

    def get_opportunity(
        self,
        opportunity_id: str,
    ) -> dict[str, Any]:
        """Fırsat detayı getirir.

        Args:
            opportunity_id: Fırsat ID.

        Returns:
            Fırsat bilgisi.
        """
        for o in self._opportunities:
            if o["opportunity_id"] == opportunity_id:
                return dict(o)
        return {"error": "opportunity_not_found"}

    @property
    def opportunity_count(self) -> int:
        """Fırsat sayısı."""
        return len(self._opportunities)

    @property
    def scored_count(self) -> int:
        """Puanlanan fırsat sayısı."""
        return self._stats[
            "opportunities_scored"
        ]
