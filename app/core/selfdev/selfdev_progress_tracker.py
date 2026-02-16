"""
İlerleme takip modülü.

Öğrenme ilerlemesi, beceri gelişimi,
kilometre taşı, başarı rozetleri, analitik.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SelfDevProgressTracker:
    """İlerleme takipçisi.

    Attributes:
        _progress: İlerleme kayıtları.
        _milestones: Kilometre taşları.
        _badges: Rozetler.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._progress: list[dict] = []
        self._milestones: list[dict] = []
        self._badges: list[str] = []
        self._stats: dict[str, int] = {
            "entries_logged": 0,
        }
        logger.info(
            "SelfDevProgressTracker baslatildi"
        )

    @property
    def progress_count(self) -> int:
        """İlerleme sayısı."""
        return len(self._progress)

    def log_learning(
        self,
        topic: str = "",
        minutes: int = 0,
        content_type: str = "course",
        notes: str = "",
    ) -> dict[str, Any]:
        """Öğrenme kaydeder.

        Args:
            topic: Konu.
            minutes: Dakika.
            content_type: İçerik türü.
            notes: Notlar.

        Returns:
            Kayıt bilgisi.
        """
        try:
            lid = f"lr_{uuid4()!s:.8}"

            record = {
                "learning_id": lid,
                "topic": topic,
                "minutes": minutes,
                "content_type": content_type,
                "notes": notes,
            }
            self._progress.append(record)
            self._stats["entries_logged"] += 1

            total_minutes = sum(
                p["minutes"]
                for p in self._progress
            )

            return {
                "learning_id": lid,
                "topic": topic,
                "minutes": minutes,
                "total_minutes": total_minutes,
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def track_skill_development(
        self,
        skill: str = "",
        old_level: str = "novice",
        new_level: str = "beginner",
    ) -> dict[str, Any]:
        """Beceri gelişimini takip eder.

        Args:
            skill: Beceri.
            old_level: Eski seviye.
            new_level: Yeni seviye.

        Returns:
            Gelişim bilgisi.
        """
        try:
            levels = [
                "novice", "beginner",
                "intermediate", "advanced",
                "expert", "master",
            ]

            old_idx = (
                levels.index(old_level)
                if old_level in levels
                else 0
            )
            new_idx = (
                levels.index(new_level)
                if new_level in levels
                else 0
            )

            improvement = new_idx - old_idx

            if improvement > 0:
                status = "improved"
            elif improvement == 0:
                status = "maintained"
            else:
                status = "declined"

            return {
                "skill": skill,
                "old_level": old_level,
                "new_level": new_level,
                "improvement": improvement,
                "status": status,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def add_milestone(
        self,
        name: str = "",
        description: str = "",
        target_value: float = 100.0,
        current_value: float = 0.0,
    ) -> dict[str, Any]:
        """Kilometre taşı ekler.

        Args:
            name: Ad.
            description: Açıklama.
            target_value: Hedef değer.
            current_value: Mevcut değer.

        Returns:
            Kilometre taşı bilgisi.
        """
        try:
            mid = f"ms_{uuid4()!s:.8}"

            progress_pct = round(
                current_value
                / target_value
                * 100,
                1,
            ) if target_value > 0 else 0.0

            reached = progress_pct >= 100

            record = {
                "milestone_id": mid,
                "name": name,
                "description": description,
                "target_value": target_value,
                "current_value": current_value,
                "progress_pct": min(
                    progress_pct, 100.0
                ),
                "reached": reached,
            }
            self._milestones.append(record)

            return {
                "milestone_id": mid,
                "name": name,
                "progress_pct": min(
                    progress_pct, 100.0
                ),
                "reached": reached,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def award_badge(
        self,
        total_hours: float = 0.0,
        streak_days: int = 0,
        skills_improved: int = 0,
    ) -> dict[str, Any]:
        """Başarı rozeti verir.

        Args:
            total_hours: Toplam saat.
            streak_days: Seri gün.
            skills_improved: Gelişen beceri.

        Returns:
            Rozet bilgisi.
        """
        try:
            new_badges = []

            if total_hours >= 100:
                new_badges.append("centurion")
            elif total_hours >= 50:
                new_badges.append("dedicated")
            elif total_hours >= 10:
                new_badges.append("committed")

            if streak_days >= 30:
                new_badges.append("streak_master")
            elif streak_days >= 7:
                new_badges.append("consistent")

            if skills_improved >= 5:
                new_badges.append("polymath")
            elif skills_improved >= 3:
                new_badges.append("multi_skilled")

            for badge in new_badges:
                if badge not in self._badges:
                    self._badges.append(badge)

            return {
                "new_badges": new_badges,
                "total_badges": len(
                    self._badges
                ),
                "all_badges": list(
                    self._badges
                ),
                "awarded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "awarded": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir.

        Returns:
            Analitik verileri.
        """
        try:
            total_minutes = sum(
                p["minutes"]
                for p in self._progress
            )
            total_hours = round(
                total_minutes / 60, 1
            )

            topics: dict[str, int] = {}
            for p in self._progress:
                t = p["topic"]
                topics[t] = (
                    topics.get(t, 0)
                    + p["minutes"]
                )

            top_topic = (
                max(topics, key=topics.get)  # type: ignore[arg-type]
                if topics
                else "none"
            )

            milestones_reached = sum(
                1 for m in self._milestones
                if m["reached"]
            )

            return {
                "total_minutes": total_minutes,
                "total_hours": total_hours,
                "entries": len(self._progress),
                "topics": topics,
                "top_topic": top_topic,
                "milestones_total": len(
                    self._milestones
                ),
                "milestones_reached": (
                    milestones_reached
                ),
                "badges": len(self._badges),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
