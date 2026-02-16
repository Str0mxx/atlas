"""ATLAS Mentor Eşleştirici modülü.

Beceri eşleme, müsaitlik kontrolü,
uyumluluk puanlama, atama takibi,
geri bildirim toplama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MentorMatcher:
    """Mentor eşleştirici.

    Mentor-mentee eşleştirmesi yapar.

    Attributes:
        _mentors: Mentor kayıtları.
        _assignments: Atama kayıtları.
    """

    def __init__(self) -> None:
        """Eşleştiriciyi başlatır."""
        self._mentors: dict[
            str, dict[str, Any]
        ] = {}
        self._assignments: dict[
            str, dict[str, Any]
        ] = {}
        self._feedback: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "matches_made": 0,
            "feedback_collected": 0,
        }

        logger.info(
            "MentorMatcher baslatildi",
        )

    def match_skills(
        self,
        mentee_id: str,
        required_skills: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Beceri eşlemesi yapar.

        Args:
            mentee_id: Mentee kimliği.
            required_skills: Gerekli
                beceriler.

        Returns:
            Eşleme bilgisi.
        """
        required_skills = (
            required_skills or []
        )

        matches = []
        for mid, mentor in (
            self._mentors.items()
        ):
            skills = mentor.get(
                "skills", [],
            )
            overlap = [
                s for s in required_skills
                if s in skills
            ]
            if overlap:
                score = (
                    len(overlap)
                    / len(required_skills)
                    * 100
                    if required_skills
                    else 0
                )
                matches.append({
                    "mentor_id": mid,
                    "name": mentor.get(
                        "name", mid,
                    ),
                    "matching_skills": (
                        overlap
                    ),
                    "match_score": score,
                })

        matches.sort(
            key=lambda x: x[
                "match_score"
            ],
            reverse=True,
        )

        return {
            "mentee_id": mentee_id,
            "candidates": matches[:5],
            "total_found": len(matches),
            "matched": True,
        }

    def check_availability(
        self,
        mentor_id: str,
    ) -> dict[str, Any]:
        """Müsaitlik kontrolü yapar.

        Args:
            mentor_id: Mentor kimliği.

        Returns:
            Müsaitlik bilgisi.
        """
        mentor = self._mentors.get(
            mentor_id,
        )
        if not mentor:
            return {
                "mentor_id": mentor_id,
                "found": False,
            }

        current = sum(
            1 for a in (
                self._assignments.values()
            )
            if (
                a["mentor_id"] == mentor_id
                and a["status"] == "active"
            )
        )

        max_mentees = mentor.get(
            "max_mentees", 3,
        )
        available = current < max_mentees

        return {
            "mentor_id": mentor_id,
            "available": available,
            "current_mentees": current,
            "max_mentees": max_mentees,
            "checked": True,
        }

    def score_compatibility(
        self,
        mentor_id: str,
        mentee_id: str,
        mentor_skills: list[str]
        | None = None,
        mentee_needs: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Uyumluluk puanlar.

        Args:
            mentor_id: Mentor kimliği.
            mentee_id: Mentee kimliği.
            mentor_skills: Mentor becerileri.
            mentee_needs: Mentee ihtiyaçları.

        Returns:
            Uyumluluk bilgisi.
        """
        mentor_skills = (
            mentor_skills or []
        )
        mentee_needs = mentee_needs or []

        if not mentee_needs:
            return {
                "mentor_id": mentor_id,
                "mentee_id": mentee_id,
                "score": 0.0,
                "scored": True,
            }

        overlap = [
            s for s in mentee_needs
            if s in mentor_skills
        ]
        score = (
            len(overlap)
            / len(mentee_needs)
            * 100
        )

        return {
            "mentor_id": mentor_id,
            "mentee_id": mentee_id,
            "score": score,
            "matching": overlap,
            "scored": True,
        }

    def assign_mentor(
        self,
        mentor_id: str,
        mentee_id: str,
        skill_area: str = "",
    ) -> dict[str, Any]:
        """Mentor atar.

        Args:
            mentor_id: Mentor kimliği.
            mentee_id: Mentee kimliği.
            skill_area: Beceri alanı.

        Returns:
            Atama bilgisi.
        """
        self._counter += 1
        aid = f"assign_{self._counter}"

        self._assignments[aid] = {
            "assignment_id": aid,
            "mentor_id": mentor_id,
            "mentee_id": mentee_id,
            "skill_area": skill_area,
            "status": "active",
            "timestamp": time.time(),
        }

        self._stats["matches_made"] += 1

        return {
            "assignment_id": aid,
            "mentor_id": mentor_id,
            "mentee_id": mentee_id,
            "skill_area": skill_area,
            "assigned": True,
        }

    def collect_feedback(
        self,
        assignment_id: str,
        rating: int = 5,
        comment: str = "",
    ) -> dict[str, Any]:
        """Geri bildirim toplar.

        Args:
            assignment_id: Atama kimliği.
            rating: Puan (1-5).
            comment: Yorum.

        Returns:
            Geri bildirim bilgisi.
        """
        assignment = (
            self._assignments.get(
                assignment_id,
            )
        )
        if not assignment:
            return {
                "assignment_id": (
                    assignment_id
                ),
                "found": False,
            }

        rating = max(1, min(5, rating))

        self._feedback.append({
            "assignment_id": assignment_id,
            "rating": rating,
            "comment": comment,
            "timestamp": time.time(),
        })

        self._stats[
            "feedback_collected"
        ] += 1

        return {
            "assignment_id": (
                assignment_id
            ),
            "rating": rating,
            "collected": True,
        }

    def register_mentor(
        self,
        mentor_id: str,
        name: str = "",
        skills: list[str]
        | None = None,
        max_mentees: int = 3,
    ) -> dict[str, Any]:
        """Mentor kaydeder.

        Args:
            mentor_id: Mentor kimliği.
            name: İsim.
            skills: Beceriler.
            max_mentees: Maksimum mentee.

        Returns:
            Kayıt bilgisi.
        """
        skills = skills or []

        self._mentors[mentor_id] = {
            "mentor_id": mentor_id,
            "name": name,
            "skills": skills,
            "max_mentees": max_mentees,
            "registered": time.time(),
        }

        return {
            "mentor_id": mentor_id,
            "name": name,
            "skill_count": len(skills),
            "registered": True,
        }

    @property
    def match_count(self) -> int:
        """Eşleme sayısı."""
        return self._stats[
            "matches_made"
        ]

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayısı."""
        return self._stats[
            "feedback_collected"
        ]
