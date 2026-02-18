"""
Gorev tamamlama orani modulu.

Tamamlama takibi, zaman analizi,
basarisizlik nedenleri, karsilastirma,
tarihsel gorunum.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TaskCompletionRate:
    """Gorev tamamlama orani.

    Attributes:
        _tasks: Gorev kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._tasks: list[dict] = []
        self._stats: dict[str, int] = {
            "tasks_recorded": 0,
            "failures_analyzed": 0,
        }
        logger.info(
            "TaskCompletionRate baslatildi"
        )

    @property
    def task_count(self) -> int:
        """Gorev sayisi."""
        return len(self._tasks)

    def record_task(
        self,
        agent_id: str = "",
        task_type: str = "general",
        status: str = "completed",
        duration_ms: int = 0,
        failure_reason: str = "",
        period: str = "",
    ) -> dict[str, Any]:
        """Gorev kaydeder.

        Args:
            agent_id: Agent ID.
            task_type: Gorev turu.
            status: Durum.
            duration_ms: Sure (ms).
            failure_reason: Basarisizlik nedeni.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            tid = f"tk_{uuid4()!s:.8}"
            task = {
                "task_id": tid,
                "agent_id": agent_id,
                "task_type": task_type,
                "status": status,
                "duration_ms": duration_ms,
                "failure_reason": (
                    failure_reason
                ),
                "period": period,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._tasks.append(task)
            self._stats[
                "tasks_recorded"
            ] += 1

            return {
                "task_id": tid,
                "agent_id": agent_id,
                "status": status,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_completion_rate(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Tamamlama oranini getirir.

        Args:
            agent_id: Agent ID (bos ise tum).

        Returns:
            Tamamlama orani bilgisi.
        """
        try:
            tasks = (
                [
                    t
                    for t in self._tasks
                    if t["agent_id"] == agent_id
                ]
                if agent_id
                else list(self._tasks)
            )

            if not tasks:
                return {
                    "completion_rate": 0.0,
                    "total": 0,
                    "retrieved": True,
                }

            total = len(tasks)
            completed = sum(
                1
                for t in tasks
                if t["status"] == "completed"
            )
            failed = sum(
                1
                for t in tasks
                if t["status"] == "failed"
            )
            rate = completed / total * 100

            return {
                "agent_id": agent_id or "all",
                "total_tasks": total,
                "completed": completed,
                "failed": failed,
                "in_progress": total
                - completed
                - failed,
                "completion_rate": round(
                    rate, 1
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_time_analysis(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Zaman analizi yapar.

        Args:
            agent_id: Agent ID.

        Returns:
            Zaman analiz bilgisi.
        """
        try:
            tasks = [
                t
                for t in self._tasks
                if (
                    not agent_id
                    or t["agent_id"] == agent_id
                )
                and t["duration_ms"] > 0
            ]

            if not tasks:
                return {
                    "avg_duration_ms": 0,
                    "analyzed": True,
                }

            durations = [
                t["duration_ms"] for t in tasks
            ]
            avg = sum(durations) / len(durations)
            min_d = min(durations)
            max_d = max(durations)
            sorted_d = sorted(durations)
            median = sorted_d[len(sorted_d) // 2]

            return {
                "agent_id": agent_id or "all",
                "task_count": len(tasks),
                "avg_duration_ms": round(avg),
                "min_duration_ms": min_d,
                "max_duration_ms": max_d,
                "median_duration_ms": median,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_failure_reasons(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Basarisizlik nedenlerini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Neden bilgisi.
        """
        try:
            failed = [
                t
                for t in self._tasks
                if t["status"] == "failed"
                and (
                    not agent_id
                    or t["agent_id"] == agent_id
                )
            ]

            reasons: dict[str, int] = {}
            for t in failed:
                reason = (
                    t.get("failure_reason")
                    or "unknown"
                )
                reasons[reason] = (
                    reasons.get(reason, 0) + 1
                )

            self._stats[
                "failures_analyzed"
            ] += 1

            sorted_reasons = sorted(
                reasons.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            return {
                "reasons": [
                    {
                        "reason": r,
                        "count": c,
                        "percentage": round(
                            c / len(failed) * 100,
                            1,
                        )
                        if failed
                        else 0,
                    }
                    for r, c in sorted_reasons
                ],
                "total_failures": len(failed),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def compare_agents(
        self,
    ) -> dict[str, Any]:
        """Agentlari karsilastirir.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            agents: dict[
                str, dict[str, int]
            ] = {}
            for t in self._tasks:
                aid = t["agent_id"]
                if aid not in agents:
                    agents[aid] = {
                        "total": 0,
                        "completed": 0,
                    }
                agents[aid]["total"] += 1
                if t["status"] == "completed":
                    agents[aid][
                        "completed"
                    ] += 1

            comparisons = []
            for aid, data in agents.items():
                rate = (
                    data["completed"]
                    / data["total"]
                    * 100
                    if data["total"] > 0
                    else 0
                )
                comparisons.append({
                    "agent_id": aid,
                    "total_tasks": data["total"],
                    "completed": data[
                        "completed"
                    ],
                    "completion_rate": round(
                        rate, 1
                    ),
                })

            comparisons.sort(
                key=lambda x: x[
                    "completion_rate"
                ],
                reverse=True,
            )

            return {
                "comparisons": comparisons,
                "agent_count": len(comparisons),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def get_historical_view(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Tarihsel gorunum getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Tarihsel bilgi.
        """
        try:
            tasks = [
                t
                for t in self._tasks
                if not agent_id
                or t["agent_id"] == agent_id
            ]

            periods: dict[
                str, dict[str, int]
            ] = {}
            for t in tasks:
                p = t.get("period") or "unknown"
                if p not in periods:
                    periods[p] = {
                        "total": 0,
                        "completed": 0,
                    }
                periods[p]["total"] += 1
                if t["status"] == "completed":
                    periods[p]["completed"] += 1

            history = [
                {
                    "period": p,
                    "total": d["total"],
                    "completed": d["completed"],
                    "rate": round(
                        d["completed"]
                        / d["total"]
                        * 100,
                        1,
                    )
                    if d["total"] > 0
                    else 0,
                }
                for p, d in sorted(
                    periods.items()
                )
            ]

            return {
                "history": history,
                "period_count": len(history),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
