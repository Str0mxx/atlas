"""
Agent puan karti modulu.

Performans metrikleri, gorev tamamlama,
basari orani, kalite puani,
trend gostergeleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentScorecard:
    """Agent puan karti.

    Attributes:
        _agents: Agent kayitlari.
        _metrics: Metrik kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Puan kartini baslatir."""
        self._agents: dict[str, dict] = {}
        self._metrics: list[dict] = []
        self._stats: dict[str, int] = {
            "agents_tracked": 0,
            "metrics_recorded": 0,
        }
        logger.info(
            "AgentScorecard baslatildi"
        )

    @property
    def agent_count(self) -> int:
        """Agent sayisi."""
        return len(self._agents)

    def register_agent(
        self,
        agent_id: str = "",
        agent_name: str = "",
        agent_type: str = "general",
    ) -> dict[str, Any]:
        """Agent kaydeder.

        Args:
            agent_id: Agent ID.
            agent_name: Agent adi.
            agent_type: Agent turu.

        Returns:
            Kayit bilgisi.
        """
        try:
            if not agent_id:
                agent_id = (
                    f"ag_{uuid4()!s:.8}"
                )

            self._agents[agent_id] = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_type": agent_type,
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "total_quality": 0.0,
                "quality_count": 0,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "agents_tracked"
            ] += 1

            return {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def record_metric(
        self,
        agent_id: str = "",
        metric_type: str = "task",
        success: bool = True,
        quality_score: float = 0.0,
        duration_ms: int = 0,
        period: str = "",
    ) -> dict[str, Any]:
        """Metrik kaydeder.

        Args:
            agent_id: Agent ID.
            metric_type: Metrik turu.
            success: Basarili mi.
            quality_score: Kalite puani.
            duration_ms: Sure (ms).
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            mid = f"mt_{uuid4()!s:.8}"
            metric = {
                "metric_id": mid,
                "agent_id": agent_id,
                "metric_type": metric_type,
                "success": success,
                "quality_score": quality_score,
                "duration_ms": duration_ms,
                "period": period,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._metrics.append(metric)
            self._stats[
                "metrics_recorded"
            ] += 1

            if agent_id in self._agents:
                ag = self._agents[agent_id]
                ag["total_tasks"] += 1
                if success:
                    ag["completed_tasks"] += 1
                else:
                    ag["failed_tasks"] += 1
                if quality_score > 0:
                    ag[
                        "total_quality"
                    ] += quality_score
                    ag["quality_count"] += 1

            return {
                "metric_id": mid,
                "agent_id": agent_id,
                "success": success,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_scorecard(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Puan karti getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Puan karti bilgisi.
        """
        try:
            if agent_id not in self._agents:
                return {
                    "agent_id": agent_id,
                    "found": False,
                    "retrieved": True,
                }

            ag = self._agents[agent_id]
            total = ag["total_tasks"]
            completed = ag["completed_tasks"]
            success_rate = (
                (completed / total * 100)
                if total > 0
                else 0.0
            )
            avg_quality = (
                (
                    ag["total_quality"]
                    / ag["quality_count"]
                )
                if ag["quality_count"] > 0
                else 0.0
            )

            agent_metrics = [
                m
                for m in self._metrics
                if m["agent_id"] == agent_id
            ]
            durations = [
                m["duration_ms"]
                for m in agent_metrics
                if m["duration_ms"] > 0
            ]
            avg_duration = (
                sum(durations) / len(durations)
                if durations
                else 0
            )

            return {
                "agent_id": agent_id,
                "agent_name": ag["agent_name"],
                "agent_type": ag["agent_type"],
                "total_tasks": total,
                "completed_tasks": completed,
                "failed_tasks": ag[
                    "failed_tasks"
                ],
                "success_rate": round(
                    success_rate, 1
                ),
                "avg_quality": round(
                    avg_quality, 1
                ),
                "avg_duration_ms": round(
                    avg_duration
                ),
                "found": True,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_trend(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Trend gostergeleri getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Trend bilgisi.
        """
        try:
            agent_metrics = [
                m
                for m in self._metrics
                if m["agent_id"] == agent_id
            ]

            if len(agent_metrics) < 4:
                return {
                    "agent_id": agent_id,
                    "trend": (
                        "insufficient_data"
                    ),
                    "analyzed": True,
                }

            mid = len(agent_metrics) // 2
            first_half = agent_metrics[:mid]
            second_half = agent_metrics[mid:]

            first_rate = (
                sum(
                    1
                    for m in first_half
                    if m["success"]
                )
                / len(first_half)
                * 100
            )
            second_rate = (
                sum(
                    1
                    for m in second_half
                    if m["success"]
                )
                / len(second_half)
                * 100
            )

            change = second_rate - first_rate
            if change > 5:
                direction = "improving"
            elif change < -5:
                direction = "declining"
            else:
                direction = "stable"

            return {
                "agent_id": agent_id,
                "early_success_rate": round(
                    first_rate, 1
                ),
                "recent_success_rate": round(
                    second_rate, 1
                ),
                "change": round(change, 1),
                "direction": direction,
                "data_points": len(
                    agent_metrics
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_all_scorecards(
        self,
    ) -> dict[str, Any]:
        """Tum puan kartlarini getirir.

        Returns:
            Tum puan kartlari.
        """
        try:
            cards = []
            for aid in self._agents:
                card = self.get_scorecard(
                    agent_id=aid
                )
                if card.get("found"):
                    cards.append(card)

            return {
                "scorecards": cards,
                "agent_count": len(cards),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
