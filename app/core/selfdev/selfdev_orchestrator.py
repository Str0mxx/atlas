"""
Kişisel gelişim orkestratör modülü.

Tam öğrenme yönetimi,
Assess → Plan → Learn → Track → Certify,
sürekli büyüme ve analitik.
"""

import logging
from typing import Any

from app.core.selfdev.certification_path import (
    CertificationPath,
)
from app.core.selfdev.course_recommender import (
    CourseRecommender,
)
from app.core.selfdev.daily_learning_planner import (
    DailyLearningPlanner,
)
from app.core.selfdev.mentor_finder import (
    SelfDevMentorFinder,
)
from app.core.selfdev.podcast_curator import (
    PodcastCurator,
)
from app.core.selfdev.reading_list_builder import (
    ReadingListBuilder,
)
from app.core.selfdev.selfdev_progress_tracker import (
    SelfDevProgressTracker,
)
from app.core.selfdev.skill_gap_analyzer import (
    SelfDevSkillGapAnalyzer,
)

logger = logging.getLogger(__name__)


class SelfDevOrchestrator:
    """Kişisel gelişim orkestratör.

    Attributes:
        _skill_gap: Beceri açığı.
        _course: Kurs öneri.
        _reading: Okuma listesi.
        _podcast: Podcast küratör.
        _planner: Günlük planlayıcı.
        _progress: İlerleme takip.
        _cert: Sertifika yolu.
        _mentor: Mentor bulucu.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self._skill_gap = (
            SelfDevSkillGapAnalyzer()
        )
        self._course = CourseRecommender()
        self._reading = ReadingListBuilder()
        self._podcast = PodcastCurator()
        self._planner = DailyLearningPlanner()
        self._progress = SelfDevProgressTracker()
        self._cert = CertificationPath()
        self._mentor = SelfDevMentorFinder()
        logger.info(
            "SelfDevOrchestrator baslatildi"
        )

    def full_learning_cycle(
        self,
        skills: list[dict] | None = None,
        target_level: str = "intermediate",
        daily_minutes: int = 30,
    ) -> dict[str, Any]:
        """Tam öğrenme döngüsü.

        Assess → Plan → Learn → Track → Certify.

        Args:
            skills: Mevcut beceriler.
            target_level: Hedef seviye.
            daily_minutes: Günlük dakika.

        Returns:
            Tam döngü raporu.
        """
        try:
            assessment = (
                self._skill_gap.assess_current_skills(
                    skills=skills,
                )
            )

            gaps = self._skill_gap.identify_gaps(
                target_level=target_level,
            )

            plan = self._planner.set_daily_goals(
                learning_minutes=daily_minutes,
            )

            courses = (
                self._course.discover_courses(
                    topic="general",
                    level=target_level,
                )
            )

            return {
                "assessment": assessment,
                "gaps": gaps,
                "plan": plan,
                "courses": courses,
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def daily_briefing(
        self,
    ) -> dict[str, Any]:
        """Günlük brifing.

        Returns:
            Günlük özet.
        """
        try:
            progress = (
                self._progress.get_analytics()
            )
            skills = (
                self._skill_gap.skill_count
            )
            books = self._reading.book_count
            podcasts = (
                self._podcast.queue_size
            )

            return {
                "progress": progress,
                "skills_tracked": skills,
                "books_in_list": books,
                "podcast_queue": podcasts,
                "briefed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "briefed": False,
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
            return {
                "skills": (
                    self._skill_gap.skill_count
                ),
                "courses": (
                    self._course.course_count
                ),
                "books": (
                    self._reading.book_count
                ),
                "podcasts": (
                    self._podcast.podcast_count
                ),
                "plans": (
                    self._planner.plan_count
                ),
                "progress_entries": (
                    self._progress.progress_count
                ),
                "certifications": (
                    self._cert.cert_count
                ),
                "mentors": (
                    self._mentor.mentor_count
                ),
                "components": 8,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
