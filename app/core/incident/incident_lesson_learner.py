"""
Ders cikarma modulu.

Alinan dersler, onleme tedbirleri,
surec iyilestirme, bilgi tabani
guncelleme, egitim tetikleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class IncidentLessonLearner:
    """Ders cikarma motoru.

    Attributes:
        _lessons: Ders kayitlari.
        _preventions: Onleme tedbirleri.
        _improvements: Iyilestirmeler.
        _knowledge: Bilgi tabani.
        _trainings: Egitim tetikleri.
        _stats: Istatistikler.
    """

    LESSON_CATEGORIES: list[str] = [
        "detection",
        "containment",
        "investigation",
        "recovery",
        "communication",
        "process",
        "technology",
        "people",
    ]

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._lessons: dict[
            str, dict
        ] = {}
        self._preventions: dict[
            str, dict
        ] = {}
        self._improvements: dict[
            str, dict
        ] = {}
        self._knowledge: dict[
            str, dict
        ] = {}
        self._trainings: list[dict] = []
        self._stats: dict[str, int] = {
            "lessons_learned": 0,
            "preventions_defined": 0,
            "improvements_proposed": 0,
            "kb_articles_created": 0,
            "trainings_triggered": 0,
        }
        logger.info(
            "IncidentLessonLearner "
            "baslatildi"
        )

    @property
    def lesson_count(self) -> int:
        """Ders sayisi."""
        return len(self._lessons)

    def record_lesson(
        self,
        incident_id: str = "",
        title: str = "",
        category: str = "process",
        description: str = "",
        what_went_well: str = "",
        what_went_wrong: str = "",
        recommendations: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Ders kaydeder.

        Args:
            incident_id: Olay ID.
            title: Baslik.
            category: Kategori.
            description: Aciklama.
            what_went_well: Iyi giden.
            what_went_wrong: Kotu giden.
            recommendations: Oneriler.

        Returns:
            Ders bilgisi.
        """
        try:
            if (
                category
                not in self.LESSON_CATEGORIES
            ):
                return {
                    "recorded": False,
                    "error": (
                        f"Gecersiz: "
                        f"{category}"
                    ),
                }

            lid = f"ll_{uuid4()!s:.8}"
            self._lessons[lid] = {
                "lesson_id": lid,
                "incident_id": incident_id,
                "title": title,
                "category": category,
                "description": description,
                "what_went_well": (
                    what_went_well
                ),
                "what_went_wrong": (
                    what_went_wrong
                ),
                "recommendations": (
                    recommendations or []
                ),
                "status": "documented",
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "lessons_learned"
            ] += 1

            return {
                "lesson_id": lid,
                "category": category,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def define_prevention(
        self,
        lesson_id: str = "",
        title: str = "",
        measure_type: str = "",
        description: str = "",
        priority: str = "high",
        owner: str = "",
        deadline: str = "",
    ) -> dict[str, Any]:
        """Onleme tedbiri tanimlar.

        Args:
            lesson_id: Ders ID.
            title: Baslik.
            measure_type: Tedbir tipi.
            description: Aciklama.
            priority: Oncelik.
            owner: Sorumlu.
            deadline: Son tarih.

        Returns:
            Tedbir bilgisi.
        """
        try:
            pid = f"pm_{uuid4()!s:.8}"
            self._preventions[pid] = {
                "prevention_id": pid,
                "lesson_id": lesson_id,
                "title": title,
                "measure_type": measure_type,
                "description": description,
                "priority": priority,
                "owner": owner,
                "deadline": deadline,
                "status": "proposed",
                "defined_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "preventions_defined"
            ] += 1

            return {
                "prevention_id": pid,
                "priority": priority,
                "defined": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "defined": False,
                "error": str(e),
            }

    def propose_improvement(
        self,
        lesson_id: str = "",
        area: str = "",
        current_state: str = "",
        proposed_state: str = "",
        effort: str = "medium",
        impact: str = "high",
    ) -> dict[str, Any]:
        """Surec iyilestirmesi onerir.

        Args:
            lesson_id: Ders ID.
            area: Alan.
            current_state: Mevcut durum.
            proposed_state: Onerilen durum.
            effort: Efor.
            impact: Etki.

        Returns:
            Iyilestirme bilgisi.
        """
        try:
            iid = f"pi_{uuid4()!s:.8}"
            self._improvements[iid] = {
                "improvement_id": iid,
                "lesson_id": lesson_id,
                "area": area,
                "current_state": (
                    current_state
                ),
                "proposed_state": (
                    proposed_state
                ),
                "effort": effort,
                "impact": impact,
                "status": "proposed",
                "proposed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "improvements_proposed"
            ] += 1

            return {
                "improvement_id": iid,
                "area": area,
                "proposed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "proposed": False,
                "error": str(e),
            }

    def create_kb_article(
        self,
        incident_id: str = "",
        title: str = "",
        content: str = "",
        tags: (
            list[str] | None
        ) = None,
        category: str = "",
    ) -> dict[str, Any]:
        """Bilgi tabani makalesi olusturur.

        Args:
            incident_id: Olay ID.
            title: Baslik.
            content: Icerik.
            tags: Etiketler.
            category: Kategori.

        Returns:
            Makale bilgisi.
        """
        try:
            kid = f"kb_{uuid4()!s:.8}"
            self._knowledge[kid] = {
                "article_id": kid,
                "incident_id": incident_id,
                "title": title,
                "content": content,
                "tags": tags or [],
                "category": category,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "kb_articles_created"
            ] += 1

            return {
                "article_id": kid,
                "title": title,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def trigger_training(
        self,
        lesson_id: str = "",
        topic: str = "",
        target_audience: str = "",
        urgency: str = "normal",
        description: str = "",
    ) -> dict[str, Any]:
        """Egitim tetikler.

        Args:
            lesson_id: Ders ID.
            topic: Konu.
            target_audience: Hedef kitle.
            urgency: Aciliyet.
            description: Aciklama.

        Returns:
            Egitim bilgisi.
        """
        try:
            tid = f"tr_{uuid4()!s:.8}"
            self._trainings.append({
                "training_id": tid,
                "lesson_id": lesson_id,
                "topic": topic,
                "target_audience": (
                    target_audience
                ),
                "urgency": urgency,
                "description": description,
                "status": "triggered",
                "triggered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })
            self._stats[
                "trainings_triggered"
            ] += 1

            return {
                "training_id": tid,
                "topic": topic,
                "triggered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "triggered": False,
                "error": str(e),
            }

    def get_lessons(
        self,
        incident_id: str = "",
    ) -> dict[str, Any]:
        """Dersleri getirir.

        Args:
            incident_id: Olay ID filtresi.

        Returns:
            Ders listesi.
        """
        try:
            if incident_id:
                filtered = [
                    l
                    for l in (
                        self._lessons.values()
                    )
                    if l["incident_id"]
                    == incident_id
                ]
            else:
                filtered = list(
                    self._lessons.values()
                )

            return {
                "lessons": filtered,
                "count": len(filtered),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_cat: dict[str, int] = {}
            for l in (
                self._lessons.values()
            ):
                c = l["category"]
                by_cat[c] = (
                    by_cat.get(c, 0) + 1
                )

            return {
                "total_lessons": len(
                    self._lessons
                ),
                "total_preventions": len(
                    self._preventions
                ),
                "total_improvements": len(
                    self._improvements
                ),
                "total_kb_articles": len(
                    self._knowledge
                ),
                "total_trainings": len(
                    self._trainings
                ),
                "by_category": by_cat,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
