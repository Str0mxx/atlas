"""ATLAS Beceri Değerlendirici modülü.

Beceri değerlendirme, bilgi testi,
boşluk tespiti, seviye belirleme,
kıyaslama karşılaştırma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SkillAssessor:
    """Beceri değerlendirici.

    Kullanıcı becerilerini değerlendirir.

    Attributes:
        _assessments: Değerlendirme kayıtları.
        _benchmarks: Kıyaslama verileri.
    """

    def __init__(self) -> None:
        """Değerlendiriciyi başlatır."""
        self._assessments: dict[
            str, dict[str, Any]
        ] = {}
        self._benchmarks: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "assessments_done": 0,
            "gaps_found": 0,
        }

        logger.info(
            "SkillAssessor baslatildi",
        )

    def evaluate_skill(
        self,
        user_id: str,
        skill_name: str,
        answers: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Beceri değerlendirmesi yapar.

        Args:
            user_id: Kullanıcı kimliği.
            skill_name: Beceri adı.
            answers: Yanıtlar.

        Returns:
            Değerlendirme bilgisi.
        """
        answers = answers or []
        self._counter += 1
        aid = f"assess_{self._counter}"

        correct = sum(
            1 for a in answers
            if a.get("correct", False)
        )
        total = len(answers) if answers else 1
        score = (correct / total) * 100

        if score >= 90:
            level = "expert"
        elif score >= 70:
            level = "advanced"
        elif score >= 50:
            level = "intermediate"
        else:
            level = "beginner"

        self._assessments[aid] = {
            "assessment_id": aid,
            "user_id": user_id,
            "skill_name": skill_name,
            "score": score,
            "level": level,
            "correct": correct,
            "total": total,
            "timestamp": time.time(),
        }

        self._stats[
            "assessments_done"
        ] += 1

        return {
            "assessment_id": aid,
            "user_id": user_id,
            "skill_name": skill_name,
            "score": score,
            "level": level,
            "evaluated": True,
        }

    def test_knowledge(
        self,
        user_id: str,
        topic: str,
        questions: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Bilgi testi yapar.

        Args:
            user_id: Kullanıcı kimliği.
            topic: Konu.
            questions: Sorular.

        Returns:
            Test bilgisi.
        """
        questions = questions or []

        correct = sum(
            1 for q in questions
            if q.get("correct", False)
        )
        total = len(questions) if questions else 1
        score = (correct / total) * 100
        passed = score >= 60

        return {
            "user_id": user_id,
            "topic": topic,
            "score": score,
            "passed": passed,
            "correct": correct,
            "total": total,
            "tested": True,
        }

    def identify_gaps(
        self,
        user_id: str,
        required_skills: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Boşlukları tespit eder.

        Args:
            user_id: Kullanıcı kimliği.
            required_skills: Gerekli beceriler.

        Returns:
            Boşluk bilgisi.
        """
        required_skills = (
            required_skills or []
        )

        assessed = {
            a["skill_name"]
            for a in self._assessments.values()
            if a["user_id"] == user_id
        }

        gaps = [
            s for s in required_skills
            if s not in assessed
        ]

        weak = [
            a["skill_name"]
            for a in self._assessments.values()
            if a["user_id"] == user_id
            and a["score"] < 50
        ]

        all_gaps = list(
            set(gaps + weak),
        )

        self._stats[
            "gaps_found"
        ] += len(all_gaps)

        return {
            "user_id": user_id,
            "missing_skills": gaps,
            "weak_skills": weak,
            "total_gaps": len(all_gaps),
            "identified": True,
        }

    def determine_level(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Genel seviye belirler.

        Args:
            user_id: Kullanıcı kimliği.

        Returns:
            Seviye bilgisi.
        """
        user_assessments = [
            a for a in (
                self._assessments.values()
            )
            if a["user_id"] == user_id
        ]

        if not user_assessments:
            return {
                "user_id": user_id,
                "level": "beginner",
                "avg_score": 0.0,
                "determined": True,
            }

        avg = sum(
            a["score"]
            for a in user_assessments
        ) / len(user_assessments)

        if avg >= 90:
            level = "expert"
        elif avg >= 70:
            level = "advanced"
        elif avg >= 50:
            level = "intermediate"
        else:
            level = "beginner"

        return {
            "user_id": user_id,
            "level": level,
            "avg_score": avg,
            "assessments": len(
                user_assessments,
            ),
            "determined": True,
        }

    def compare_benchmark(
        self,
        user_id: str,
        skill_name: str,
        benchmark_score: float = 70.0,
    ) -> dict[str, Any]:
        """Kıyaslama karşılaştırması yapar.

        Args:
            user_id: Kullanıcı kimliği.
            skill_name: Beceri adı.
            benchmark_score: Kıyaslama puanı.

        Returns:
            Karşılaştırma bilgisi.
        """
        user_score = 0.0
        for a in self._assessments.values():
            if (
                a["user_id"] == user_id
                and a["skill_name"] == skill_name
            ):
                user_score = a["score"]
                break

        diff = user_score - benchmark_score
        above = diff >= 0

        return {
            "user_id": user_id,
            "skill_name": skill_name,
            "user_score": user_score,
            "benchmark_score": (
                benchmark_score
            ),
            "difference": diff,
            "above_benchmark": above,
            "compared": True,
        }

    @property
    def assessment_count(self) -> int:
        """Değerlendirme sayısı."""
        return self._stats[
            "assessments_done"
        ]

    @property
    def gap_count(self) -> int:
        """Boşluk sayısı."""
        return self._stats["gaps_found"]
