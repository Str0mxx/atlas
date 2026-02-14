"""ATLAS Mufredat Yoneticisi modulu.

Ogrenme ilerlemesi, zorluk olcekleme,
on kosul takibi, ustalik degerlendirme
ve bosluk belirleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.adaptive import SkillLevel

logger = logging.getLogger(__name__)


class CurriculumManager:
    """Mufredat yoneticisi.

    Ogrenme surecini planlar, takip eder
    ve zorlugu ayarlar.

    Attributes:
        _curriculum: Mufredat ogeleleri.
        _progress: Ilerleme kayitlari.
        _prerequisites: On kosullar.
        _mastery: Ustalik degerlendirmeleri.
    """

    def __init__(self) -> None:
        """Mufredat yoneticisini baslatir."""
        self._curriculum: dict[str, dict[str, Any]] = {}
        self._progress: dict[str, dict[str, Any]] = {}
        self._prerequisites: dict[str, list[str]] = {}
        self._mastery: dict[str, dict[str, Any]] = {}
        self._difficulty_scale: dict[str, float] = {}

        logger.info("CurriculumManager baslatildi")

    def add_topic(
        self,
        name: str,
        difficulty: float = 0.5,
        prerequisites: list[str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Konu ekler.

        Args:
            name: Konu adi.
            difficulty: Zorluk (0.0-1.0).
            prerequisites: On kosullar.
            description: Aciklama.

        Returns:
            Konu bilgisi.
        """
        topic = {
            "name": name,
            "difficulty": max(0.0, min(1.0, difficulty)),
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._curriculum[name] = topic
        self._prerequisites[name] = prerequisites or []
        self._difficulty_scale[name] = topic["difficulty"]
        return topic

    def record_progress(
        self,
        learner: str,
        topic: str,
        score: float,
    ) -> dict[str, Any]:
        """Ilerleme kaydeder.

        Args:
            learner: Ogrenci.
            topic: Konu.
            score: Skor (0.0-1.0).

        Returns:
            Ilerleme bilgisi.
        """
        key = f"{learner}:{topic}"
        if key not in self._progress:
            self._progress[key] = {
                "learner": learner,
                "topic": topic,
                "scores": [],
                "attempts": 0,
            }

        progress = self._progress[key]
        progress["scores"].append(
            max(0.0, min(1.0, score)),
        )
        progress["attempts"] += 1

        # Ustalik guncelle
        self._update_mastery(learner, topic)
        return progress

    def check_prerequisites(
        self,
        learner: str,
        topic: str,
    ) -> dict[str, Any]:
        """On kosullari kontrol eder.

        Args:
            learner: Ogrenci.
            topic: Konu.

        Returns:
            Kontrol sonucu.
        """
        prereqs = self._prerequisites.get(topic, [])
        if not prereqs:
            return {"met": True, "missing": []}

        missing: list[str] = []
        for prereq in prereqs:
            mastery = self._get_mastery_level(learner, prereq)
            if mastery in (
                SkillLevel.NOVICE.value,
                SkillLevel.BEGINNER.value,
            ):
                missing.append(prereq)

        return {
            "met": len(missing) == 0,
            "missing": missing,
            "total_prereqs": len(prereqs),
        }

    def assess_mastery(
        self,
        learner: str,
        topic: str,
    ) -> dict[str, Any]:
        """Ustaligi degerlendirir.

        Args:
            learner: Ogrenci.
            topic: Konu.

        Returns:
            Degerlendirme sonucu.
        """
        key = f"{learner}:{topic}"
        progress = self._progress.get(key)
        if not progress:
            return {
                "level": SkillLevel.NOVICE.value,
                "avg_score": 0.0,
                "attempts": 0,
                "mastered": False,
            }

        scores = progress["scores"]
        avg = sum(scores) / len(scores) if scores else 0.0
        level = self._get_mastery_level(learner, topic)

        return {
            "level": level,
            "avg_score": avg,
            "attempts": progress["attempts"],
            "mastered": level in (
                SkillLevel.ADVANCED.value,
                SkillLevel.EXPERT.value,
            ),
        }

    def identify_gaps(
        self,
        learner: str,
    ) -> list[dict[str, Any]]:
        """Bosluklar belirler.

        Args:
            learner: Ogrenci.

        Returns:
            Bosluk listesi.
        """
        gaps: list[dict[str, Any]] = []

        for topic_name in self._curriculum:
            key = f"{learner}:{topic_name}"
            progress = self._progress.get(key)

            if not progress:
                gaps.append({
                    "topic": topic_name,
                    "reason": "not_started",
                    "difficulty": self._difficulty_scale.get(
                        topic_name, 0.5,
                    ),
                })
                continue

            scores = progress["scores"]
            if scores:
                avg = sum(scores) / len(scores)
                if avg < 0.5:
                    gaps.append({
                        "topic": topic_name,
                        "reason": "low_performance",
                        "avg_score": avg,
                        "difficulty": self._difficulty_scale.get(
                            topic_name, 0.5,
                        ),
                    })

        # Zorluga gore sirala
        gaps.sort(key=lambda g: g.get("difficulty", 0.5))
        return gaps

    def get_next_topics(
        self,
        learner: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Sonraki konulari onerir.

        Args:
            learner: Ogrenci.
            limit: Maks oneri.

        Returns:
            Onerilen konular.
        """
        suggestions: list[dict[str, Any]] = []

        for topic_name, topic in self._curriculum.items():
            key = f"{learner}:{topic_name}"

            # Zaten ustalasmissa atla
            mastery = self._get_mastery_level(learner, topic_name)
            if mastery in (
                SkillLevel.ADVANCED.value,
                SkillLevel.EXPERT.value,
            ):
                continue

            # On kosul kontrolu
            prereq_check = self.check_prerequisites(
                learner, topic_name,
            )
            if not prereq_check["met"]:
                continue

            progress = self._progress.get(key)
            priority = topic["difficulty"]
            if progress:
                avg = (
                    sum(progress["scores"])
                    / len(progress["scores"])
                ) if progress["scores"] else 0.0
                priority = 1.0 - avg  # Dusuk skor = yuksek oncelik

            suggestions.append({
                "topic": topic_name,
                "difficulty": topic["difficulty"],
                "priority": priority,
                "mastery": mastery,
            })

        suggestions.sort(
            key=lambda s: s["priority"],
            reverse=True,
        )
        return suggestions[:limit]

    def scale_difficulty(
        self,
        topic: str,
        factor: float,
    ) -> float:
        """Zorlugu olcekler.

        Args:
            topic: Konu.
            factor: Carpan.

        Returns:
            Yeni zorluk degeri.
        """
        if topic not in self._curriculum:
            return 0.0

        current = self._difficulty_scale.get(topic, 0.5)
        new_val = max(0.0, min(1.0, current * factor))
        self._difficulty_scale[topic] = new_val
        self._curriculum[topic]["difficulty"] = new_val
        return new_val

    def _update_mastery(
        self,
        learner: str,
        topic: str,
    ) -> None:
        """Ustaligi gunceller.

        Args:
            learner: Ogrenci.
            topic: Konu.
        """
        key = f"{learner}:{topic}"
        progress = self._progress.get(key)
        if not progress or not progress["scores"]:
            return

        scores = progress["scores"]
        avg = sum(scores[-5:]) / len(scores[-5:])
        level = SkillLevel.NOVICE.value

        if avg >= 0.9:
            level = SkillLevel.EXPERT.value
        elif avg >= 0.7:
            level = SkillLevel.ADVANCED.value
        elif avg >= 0.5:
            level = SkillLevel.INTERMEDIATE.value
        elif avg >= 0.3:
            level = SkillLevel.BEGINNER.value

        mastery_key = f"{learner}:{topic}"
        self._mastery[mastery_key] = {
            "level": level,
            "avg_score": avg,
        }

    def _get_mastery_level(
        self,
        learner: str,
        topic: str,
    ) -> str:
        """Ustalik seviyesini getirir.

        Args:
            learner: Ogrenci.
            topic: Konu.

        Returns:
            Seviye degeri.
        """
        key = f"{learner}:{topic}"
        mastery = self._mastery.get(key)
        if mastery:
            return mastery["level"]
        return SkillLevel.NOVICE.value

    @property
    def topic_count(self) -> int:
        """Konu sayisi."""
        return len(self._curriculum)

    @property
    def learner_count(self) -> int:
        """Ogrenci sayisi."""
        learners = set()
        for key in self._progress:
            learner = key.split(":")[0]
            learners.add(learner)
        return len(learners)

    @property
    def mastery_count(self) -> int:
        """Ustalik kaydi sayisi."""
        return len(self._mastery)
