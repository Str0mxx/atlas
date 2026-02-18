"""
Iyilestirme takipci modulu.

Iyilestirme takibi, oncesi/sonrasi analizi,
ogrenme egrisi, kilometre tasi,
oneriler.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentImprovementTracker:
    """Agent iyilestirme takipci.

    Attributes:
        _improvements: Iyilestirme kayitlari.
        _milestones: Kilometre taslari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._improvements: list[dict] = []
        self._milestones: list[dict] = []
        self._stats: dict[str, int] = {
            "improvements_tracked": 0,
            "milestones_reached": 0,
        }
        logger.info(
            "AgentImprovementTracker "
            "baslatildi"
        )

    @property
    def improvement_count(self) -> int:
        """Iyilestirme sayisi."""
        return len(self._improvements)

    def record_improvement(
        self,
        agent_id: str = "",
        metric: str = "performance",
        before_value: float = 0.0,
        after_value: float = 0.0,
        action_taken: str = "",
        period: str = "",
    ) -> dict[str, Any]:
        """Iyilestirme kaydeder.

        Args:
            agent_id: Agent ID.
            metric: Metrik adi.
            before_value: Onceki deger.
            after_value: Sonraki deger.
            action_taken: Yapilan aksiyon.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            iid = f"im_{uuid4()!s:.8}"
            change = (
                after_value - before_value
            )
            change_pct = (
                change / before_value * 100
                if before_value > 0
                else 0
            )

            improvement = {
                "improvement_id": iid,
                "agent_id": agent_id,
                "metric": metric,
                "before_value": before_value,
                "after_value": after_value,
                "change": round(change, 4),
                "change_pct": round(
                    change_pct, 1
                ),
                "action_taken": action_taken,
                "period": period,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._improvements.append(
                improvement
            )
            self._stats[
                "improvements_tracked"
            ] += 1

            return {
                "improvement_id": iid,
                "change": round(change, 4),
                "change_pct": round(
                    change_pct, 1
                ),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_before_after(
        self,
        agent_id: str = "",
        metric: str = "",
    ) -> dict[str, Any]:
        """Oncesi/sonrasi analizi yapar.

        Args:
            agent_id: Agent ID.
            metric: Metrik filtresi.

        Returns:
            Analiz bilgisi.
        """
        try:
            recs = [
                r
                for r in self._improvements
                if (
                    not agent_id
                    or r["agent_id"] == agent_id
                )
                and (
                    not metric
                    or r["metric"] == metric
                )
            ]

            if not recs:
                return {
                    "improvements": [],
                    "analyzed": True,
                }

            total_before = sum(
                r["before_value"] for r in recs
            )
            total_after = sum(
                r["after_value"] for r in recs
            )
            avg_change = sum(
                r["change"] for r in recs
            ) / len(recs)
            avg_change_pct = sum(
                r["change_pct"] for r in recs
            ) / len(recs)

            positive = sum(
                1
                for r in recs
                if r["change"] > 0
            )

            return {
                "agent_id": agent_id or "all",
                "metric": metric or "all",
                "total_improvements": len(recs),
                "positive_changes": positive,
                "negative_changes": len(recs)
                - positive,
                "avg_before": round(
                    total_before / len(recs), 2
                ),
                "avg_after": round(
                    total_after / len(recs), 2
                ),
                "avg_change": round(
                    avg_change, 2
                ),
                "avg_change_pct": round(
                    avg_change_pct, 1
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_learning_curve(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Ogrenme egrisi getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Egri bilgisi.
        """
        try:
            recs = [
                r
                for r in self._improvements
                if not agent_id
                or r["agent_id"] == agent_id
            ]

            if len(recs) < 2:
                return {
                    "curve": [],
                    "trend": "insufficient_data",
                    "retrieved": True,
                }

            curve = []
            cumulative = 0.0
            for i, r in enumerate(recs):
                cumulative += r["change"]
                curve.append({
                    "step": i + 1,
                    "change": round(
                        r["change"], 2
                    ),
                    "cumulative": round(
                        cumulative, 2
                    ),
                    "metric": r["metric"],
                })

            first_half = recs[
                : len(recs) // 2
            ]
            second_half = recs[
                len(recs) // 2 :
            ]
            avg_first = sum(
                r["change"] for r in first_half
            ) / len(first_half)
            avg_second = sum(
                r["change"]
                for r in second_half
            ) / len(second_half)

            if avg_second > avg_first + 0.1:
                trend = "accelerating"
            elif avg_second < avg_first - 0.1:
                trend = "decelerating"
            else:
                trend = "steady"

            return {
                "agent_id": agent_id or "all",
                "curve": curve,
                "trend": trend,
                "total_improvement": round(
                    cumulative, 2
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def add_milestone(
        self,
        agent_id: str = "",
        milestone_name: str = "",
        target_metric: str = "",
        target_value: float = 0.0,
        achieved: bool = False,
    ) -> dict[str, Any]:
        """Kilometre tasi ekler.

        Args:
            agent_id: Agent ID.
            milestone_name: Tasi adi.
            target_metric: Hedef metrik.
            target_value: Hedef deger.
            achieved: Ulasildi mi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            mid = f"ms_{uuid4()!s:.8}"
            milestone = {
                "milestone_id": mid,
                "agent_id": agent_id,
                "milestone_name": (
                    milestone_name
                ),
                "target_metric": target_metric,
                "target_value": target_value,
                "achieved": achieved,
                "achieved_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                    if achieved
                    else None
                ),
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._milestones.append(milestone)
            if achieved:
                self._stats[
                    "milestones_reached"
                ] += 1

            return {
                "milestone_id": mid,
                "agent_id": agent_id,
                "achieved": achieved,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_milestones(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Kilometre taslarini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Tasi bilgisi.
        """
        try:
            milestones = [
                m
                for m in self._milestones
                if not agent_id
                or m["agent_id"] == agent_id
            ]

            achieved = sum(
                1
                for m in milestones
                if m["achieved"]
            )
            pending = len(milestones) - achieved

            return {
                "milestones": milestones,
                "total": len(milestones),
                "achieved": achieved,
                "pending": pending,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_recommendations(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Oneriler getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Oneri bilgisi.
        """
        try:
            recs = [
                r
                for r in self._improvements
                if not agent_id
                or r["agent_id"] == agent_id
            ]

            recommendations = []

            if not recs:
                recommendations.append({
                    "type": "start_tracking",
                    "message": (
                        "Iyilestirme takibi "
                        "baslatilmali"
                    ),
                    "priority": "high",
                })
                return {
                    "recommendations": (
                        recommendations
                    ),
                    "retrieved": True,
                }

            negative = [
                r
                for r in recs
                if r["change"] < 0
            ]
            if len(negative) > len(recs) * 0.5:
                recommendations.append({
                    "type": "declining",
                    "message": (
                        "Performans dususu "
                        "tespit edildi"
                    ),
                    "priority": "high",
                })

            metrics: dict[
                str, list[float]
            ] = {}
            for r in recs:
                m = r["metric"]
                if m not in metrics:
                    metrics[m] = []
                metrics[m].append(
                    r["change_pct"]
                )

            for m, changes in metrics.items():
                avg = sum(changes) / len(
                    changes
                )
                if avg < 0:
                    recommendations.append({
                        "type": "focus_area",
                        "message": (
                            f"{m} metriginde "
                            f"iyilestirme gerekli"
                        ),
                        "metric": m,
                        "priority": "medium",
                    })

            milestones = [
                ms
                for ms in self._milestones
                if (
                    not agent_id
                    or ms["agent_id"]
                    == agent_id
                )
                and not ms["achieved"]
            ]
            if milestones:
                recommendations.append({
                    "type": "pending_milestones",
                    "message": (
                        f"{len(milestones)} "
                        f"bekleyen hedef var"
                    ),
                    "priority": "medium",
                })

            return {
                "recommendations": (
                    recommendations
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
