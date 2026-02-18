"""
Agent siralama modulu.

Performans siralama, coklu metrik,
kategori liderleri, iyilestirme takibi,
lider tablosu.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AgentRanking:
    """Agent siralama.

    Attributes:
        _agents: Agent kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Siralamayi baslatir."""
        self._agents: dict[str, dict] = {}
        self._stats: dict[str, int] = {
            "agents_ranked": 0,
            "rankings_generated": 0,
        }
        logger.info(
            "AgentRanking baslatildi"
        )

    @property
    def agent_count(self) -> int:
        """Agent sayisi."""
        return len(self._agents)

    def add_agent(
        self,
        agent_id: str = "",
        agent_name: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Agent ekler.

        Args:
            agent_id: Agent ID.
            agent_name: Agent adi.
            category: Kategori.

        Returns:
            Ekleme bilgisi.
        """
        try:
            if not agent_id:
                agent_id = (
                    f"ar_{uuid4()!s:.8}"
                )

            self._agents[agent_id] = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "category": category,
                "scores": [],
                "total_score": 0.0,
                "task_count": 0,
                "success_count": 0,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats["agents_ranked"] += 1

            return {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def record_score(
        self,
        agent_id: str = "",
        metric: str = "overall",
        score: float = 0.0,
        success: bool = True,
        period: str = "",
    ) -> dict[str, Any]:
        """Puan kaydeder.

        Args:
            agent_id: Agent ID.
            metric: Metrik adi.
            score: Puan.
            success: Basarili mi.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            sid = f"sc_{uuid4()!s:.8}"

            if agent_id in self._agents:
                ag = self._agents[agent_id]
                ag["scores"].append({
                    "score_id": sid,
                    "metric": metric,
                    "score": score,
                    "success": success,
                    "period": period,
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                })
                ag["total_score"] += score
                ag["task_count"] += 1
                if success:
                    ag["success_count"] += 1

            return {
                "score_id": sid,
                "agent_id": agent_id,
                "score": score,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_ranking(
        self,
        metric: str = "overall",
        category: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Siralama getirir.

        Args:
            metric: Metrik adi.
            category: Kategori filtresi.
            limit: Sonuc limiti.

        Returns:
            Siralama bilgisi.
        """
        try:
            agents = {
                aid: ag
                for aid, ag in self._agents.items()
                if (
                    not category
                    or ag["category"] == category
                )
                and ag["task_count"] > 0
            }

            rankings = []
            for aid, ag in agents.items():
                if metric == "overall":
                    avg = (
                        ag["total_score"]
                        / ag["task_count"]
                    )
                elif metric == "success_rate":
                    avg = (
                        ag["success_count"]
                        / ag["task_count"]
                        * 100
                    )
                else:
                    metric_scores = [
                        s["score"]
                        for s in ag["scores"]
                        if s["metric"] == metric
                    ]
                    avg = (
                        sum(metric_scores)
                        / len(metric_scores)
                        if metric_scores
                        else 0
                    )

                rankings.append({
                    "agent_id": aid,
                    "agent_name": ag[
                        "agent_name"
                    ],
                    "category": ag["category"],
                    "avg_score": round(avg, 2),
                    "task_count": ag[
                        "task_count"
                    ],
                    "success_count": ag[
                        "success_count"
                    ],
                })

            rankings.sort(
                key=lambda x: x["avg_score"],
                reverse=True,
            )

            for i, r in enumerate(rankings):
                r["rank"] = i + 1

            self._stats[
                "rankings_generated"
            ] += 1

            return {
                "rankings": rankings[:limit],
                "total_agents": len(rankings),
                "metric": metric,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_category_leaders(
        self,
    ) -> dict[str, Any]:
        """Kategori liderlerini getirir.

        Returns:
            Lider bilgisi.
        """
        try:
            categories: dict[
                str, list[dict]
            ] = {}
            for aid, ag in self._agents.items():
                cat = ag["category"]
                if cat not in categories:
                    categories[cat] = []
                if ag["task_count"] > 0:
                    avg = (
                        ag["total_score"]
                        / ag["task_count"]
                    )
                    categories[cat].append({
                        "agent_id": aid,
                        "agent_name": ag[
                            "agent_name"
                        ],
                        "avg_score": round(
                            avg, 2
                        ),
                        "task_count": ag[
                            "task_count"
                        ],
                    })

            leaders = {}
            for cat, agents in categories.items():
                if agents:
                    agents.sort(
                        key=lambda x: x[
                            "avg_score"
                        ],
                        reverse=True,
                    )
                    leaders[cat] = agents[0]

            return {
                "leaders": leaders,
                "category_count": len(leaders),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_improvement_ranking(
        self,
    ) -> dict[str, Any]:
        """Iyilestirme siralamasini getirir.

        Returns:
            Iyilestirme bilgisi.
        """
        try:
            improvements = []
            for aid, ag in self._agents.items():
                scores = ag["scores"]
                if len(scores) < 4:
                    continue

                mid = len(scores) // 2
                first = scores[:mid]
                second = scores[mid:]

                avg_first = sum(
                    s["score"] for s in first
                ) / len(first)
                avg_second = sum(
                    s["score"] for s in second
                ) / len(second)
                change = avg_second - avg_first

                improvements.append({
                    "agent_id": aid,
                    "agent_name": ag[
                        "agent_name"
                    ],
                    "early_avg": round(
                        avg_first, 2
                    ),
                    "recent_avg": round(
                        avg_second, 2
                    ),
                    "improvement": round(
                        change, 2
                    ),
                })

            improvements.sort(
                key=lambda x: x[
                    "improvement"
                ],
                reverse=True,
            )

            return {
                "improvements": improvements,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_leaderboard(
        self,
        period: str = "",
    ) -> dict[str, Any]:
        """Lider tablosu getirir.

        Args:
            period: Donem filtresi.

        Returns:
            Lider tablosu bilgisi.
        """
        try:
            board = []
            for aid, ag in self._agents.items():
                if period:
                    scores = [
                        s["score"]
                        for s in ag["scores"]
                        if s["period"] == period
                    ]
                    successes = sum(
                        1
                        for s in ag["scores"]
                        if s["period"] == period
                        and s["success"]
                    )
                    total = len(scores)
                else:
                    scores = [
                        s["score"]
                        for s in ag["scores"]
                    ]
                    successes = ag[
                        "success_count"
                    ]
                    total = ag["task_count"]

                if not scores:
                    continue

                avg = sum(scores) / len(scores)
                rate = (
                    successes / total * 100
                    if total > 0
                    else 0
                )

                board.append({
                    "agent_id": aid,
                    "agent_name": ag[
                        "agent_name"
                    ],
                    "avg_score": round(avg, 2),
                    "success_rate": round(
                        rate, 1
                    ),
                    "tasks": total,
                })

            board.sort(
                key=lambda x: x["avg_score"],
                reverse=True,
            )

            for i, b in enumerate(board):
                b["position"] = i + 1

            return {
                "leaderboard": board,
                "period": period or "all",
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
