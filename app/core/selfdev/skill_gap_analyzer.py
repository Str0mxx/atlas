"""
Beceri açığı analiz modülü.

Mevcut beceri değerlendirme, hedef eşleme,
açık tespiti, önceliklendirme, yol haritası.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SelfDevSkillGapAnalyzer:
    """Beceri açığı analizcisi.

    Attributes:
        _skills: Beceri kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizcıyı başlatır."""
        self._skills: list[dict] = []
        self._stats: dict[str, int] = {
            "assessments_done": 0,
        }
        logger.info(
            "SelfDevSkillGapAnalyzer baslatildi"
        )

    @property
    def skill_count(self) -> int:
        """Beceri sayısı."""
        return len(self._skills)

    def assess_current_skills(
        self,
        skills: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Mevcut becerileri değerlendirir.

        Args:
            skills: Beceri listesi.

        Returns:
            Değerlendirme sonucu.
        """
        try:
            items = skills or []
            levels = {
                "novice": 1,
                "beginner": 2,
                "intermediate": 3,
                "advanced": 4,
                "expert": 5,
                "master": 6,
            }

            for s in items:
                sid = f"sk_{uuid4()!s:.8}"
                record = {
                    "skill_id": sid,
                    "name": s.get("name", ""),
                    "level": s.get(
                        "level", "novice"
                    ),
                    "score": levels.get(
                        s.get("level", "novice"),
                        1,
                    ),
                }
                self._skills.append(record)

            avg_score = (
                sum(
                    sk["score"]
                    for sk in self._skills
                )
                / len(self._skills)
                if self._skills
                else 0.0
            )

            self._stats[
                "assessments_done"
            ] += 1

            return {
                "skills_assessed": len(items),
                "total_skills": len(
                    self._skills
                ),
                "avg_score": round(
                    avg_score, 1
                ),
                "assessed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def map_target_skills(
        self,
        role: str = "",
        target_skills: list[str] | None = None,
    ) -> dict[str, Any]:
        """Hedef becerileri eşler.

        Args:
            role: Hedef rol.
            target_skills: Hedef beceriler.

        Returns:
            Eşleme sonucu.
        """
        try:
            targets = target_skills or []

            role_defaults = {
                "data_scientist": [
                    "python", "statistics",
                    "machine_learning", "sql",
                ],
                "web_developer": [
                    "javascript", "html_css",
                    "react", "node_js",
                ],
                "devops": [
                    "docker", "kubernetes",
                    "ci_cd", "linux",
                ],
            }

            if not targets and role:
                targets = role_defaults.get(
                    role, []
                )

            current_names = {
                s["name"] for s in self._skills
            }
            existing = [
                t for t in targets
                if t in current_names
            ]
            new_skills = [
                t for t in targets
                if t not in current_names
            ]

            return {
                "role": role,
                "target_count": len(targets),
                "existing": existing,
                "new_skills_needed": new_skills,
                "coverage_pct": round(
                    len(existing)
                    / len(targets)
                    * 100,
                    1,
                ) if targets else 100.0,
                "mapped": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "mapped": False,
                "error": str(e),
            }

    def identify_gaps(
        self,
        target_level: str = "intermediate",
    ) -> dict[str, Any]:
        """Açıkları tespit eder.

        Args:
            target_level: Hedef seviye.

        Returns:
            Açık bilgisi.
        """
        try:
            levels = {
                "novice": 1,
                "beginner": 2,
                "intermediate": 3,
                "advanced": 4,
                "expert": 5,
                "master": 6,
            }
            target_score = levels.get(
                target_level, 3
            )

            gaps = []
            on_target = []
            for sk in self._skills:
                if sk["score"] < target_score:
                    gaps.append({
                        "name": sk["name"],
                        "current": sk["level"],
                        "target": target_level,
                        "gap": (
                            target_score
                            - sk["score"]
                        ),
                    })
                else:
                    on_target.append(sk["name"])

            return {
                "target_level": target_level,
                "gaps": gaps,
                "gap_count": len(gaps),
                "on_target_count": len(
                    on_target
                ),
                "identified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "identified": False,
                "error": str(e),
            }

    def rank_priorities(
        self,
        gaps: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Öncelikleri sıralar.

        Args:
            gaps: Açık listesi.

        Returns:
            Öncelik sıralaması.
        """
        try:
            items = gaps or []
            if not items:
                return {
                    "ranked": True,
                    "priorities": [],
                    "count": 0,
                }

            sorted_gaps = sorted(
                items,
                key=lambda g: g.get("gap", 0),
                reverse=True,
            )

            for i, g in enumerate(sorted_gaps):
                g["rank"] = i + 1
                g["priority"] = (
                    "critical"
                    if g.get("gap", 0) >= 3
                    else "high"
                    if g.get("gap", 0) >= 2
                    else "medium"
                )

            return {
                "priorities": sorted_gaps,
                "count": len(sorted_gaps),
                "ranked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "ranked": False,
                "error": str(e),
            }

    def create_roadmap(
        self,
        gaps: list[dict] | None = None,
        weeks_available: int = 12,
    ) -> dict[str, Any]:
        """Yol haritası oluşturur.

        Args:
            gaps: Açık listesi.
            weeks_available: Müsait hafta.

        Returns:
            Yol haritası.
        """
        try:
            items = gaps or []
            if not items:
                return {
                    "created": True,
                    "phases": [],
                    "total_weeks": 0,
                }

            weeks_per_gap = max(
                1,
                weeks_available // len(items),
            )

            phases = []
            current_week = 1
            for g in items:
                phases.append({
                    "skill": g.get("name", ""),
                    "start_week": current_week,
                    "end_week": (
                        current_week
                        + weeks_per_gap
                        - 1
                    ),
                    "duration_weeks": weeks_per_gap,
                })
                current_week += weeks_per_gap

            return {
                "phases": phases,
                "phase_count": len(phases),
                "total_weeks": min(
                    current_week - 1,
                    weeks_available,
                ),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }
