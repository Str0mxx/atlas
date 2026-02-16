"""
Günlük öğrenme planlama modülü.

Günlük hedefler, zaman tahsisi, alışkanlık
oluşturma, seri takibi, esneklik.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DailyLearningPlanner:
    """Günlük öğrenme planlayıcı.

    Attributes:
        _plans: Plan kayıtları.
        _streaks: Seri kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Planlayıcıyı başlatır."""
        self._plans: list[dict] = []
        self._streaks: dict[str, int] = {}
        self._stats: dict[str, int] = {
            "plans_created": 0,
        }
        logger.info(
            "DailyLearningPlanner baslatildi"
        )

    @property
    def plan_count(self) -> int:
        """Plan sayısı."""
        return len(self._plans)

    def set_daily_goals(
        self,
        learning_minutes: int = 30,
        topics: list[str] | None = None,
        activities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Günlük hedefler belirler.

        Args:
            learning_minutes: Öğrenme süresi.
            topics: Konular.
            activities: Aktiviteler.

        Returns:
            Hedef bilgisi.
        """
        try:
            pid = f"dp_{uuid4()!s:.8}"
            topic_list = topics or ["general"]
            activity_list = activities or [
                "reading", "practice"
            ]

            record = {
                "plan_id": pid,
                "learning_minutes": learning_minutes,
                "topics": topic_list,
                "activities": activity_list,
                "completed": False,
            }
            self._plans.append(record)
            self._stats["plans_created"] += 1

            return {
                "plan_id": pid,
                "learning_minutes": learning_minutes,
                "topics": topic_list,
                "activities": activity_list,
                "goal_count": (
                    len(topic_list)
                    + len(activity_list)
                ),
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def allocate_time(
        self,
        total_minutes: int = 60,
        topics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Zaman tahsis eder.

        Args:
            total_minutes: Toplam dakika.
            topics: Konular.

        Returns:
            Tahsis bilgisi.
        """
        try:
            topic_list = topics or ["general"]
            per_topic = (
                total_minutes // len(topic_list)
            )
            remainder = (
                total_minutes % len(topic_list)
            )

            allocation = {}
            for i, t in enumerate(topic_list):
                extra = 1 if i < remainder else 0
                allocation[t] = per_topic + extra

            return {
                "total_minutes": total_minutes,
                "allocation": allocation,
                "topic_count": len(topic_list),
                "per_topic_avg": per_topic,
                "allocated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "allocated": False,
                "error": str(e),
            }

    def build_habit(
        self,
        habit_name: str = "daily_learning",
        trigger: str = "morning",
        duration_min: int = 30,
    ) -> dict[str, Any]:
        """Alışkanlık oluşturur.

        Args:
            habit_name: Alışkanlık adı.
            trigger: Tetikleyici.
            duration_min: Süre (dakika).

        Returns:
            Alışkanlık bilgisi.
        """
        try:
            hid = f"hab_{uuid4()!s:.8}"

            self._streaks[habit_name] = 0

            return {
                "habit_id": hid,
                "habit_name": habit_name,
                "trigger": trigger,
                "duration_min": duration_min,
                "current_streak": 0,
                "built": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "built": False,
                "error": str(e),
            }

    def track_streak(
        self,
        habit_name: str = "daily_learning",
        completed_today: bool = True,
    ) -> dict[str, Any]:
        """Seri takibi yapar.

        Args:
            habit_name: Alışkanlık adı.
            completed_today: Bugün tamamlandı mı.

        Returns:
            Seri bilgisi.
        """
        try:
            current = self._streaks.get(
                habit_name, 0
            )

            if completed_today:
                current += 1
                self._streaks[
                    habit_name
                ] = current
            else:
                self._streaks[habit_name] = 0
                current = 0

            if current >= 30:
                badge = "gold"
            elif current >= 14:
                badge = "silver"
            elif current >= 7:
                badge = "bronze"
            else:
                badge = "starter"

            return {
                "habit_name": habit_name,
                "streak": current,
                "completed_today": completed_today,
                "badge": badge,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def adjust_flexibility(
        self,
        plan_id: str = "",
        new_minutes: int = 0,
        reason: str = "",
    ) -> dict[str, Any]:
        """Esneklik ayarlar.

        Args:
            plan_id: Plan ID.
            new_minutes: Yeni süre.
            reason: Sebep.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            plan = None
            for p in self._plans:
                if p["plan_id"] == plan_id:
                    plan = p
                    break

            if not plan:
                return {
                    "adjusted": False,
                    "error": "plan_not_found",
                }

            old_minutes = plan[
                "learning_minutes"
            ]
            plan["learning_minutes"] = new_minutes

            return {
                "plan_id": plan_id,
                "old_minutes": old_minutes,
                "new_minutes": new_minutes,
                "reason": reason,
                "adjusted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "adjusted": False,
                "error": str(e),
            }
