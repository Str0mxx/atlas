"""ATLAS İşe Alım Sinyal Analizcisi.

İş ilanı analizi, büyüme göstergeleri,
beceri talebi, takım genişleme, stratejik yön.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class HiringSignalAnalyzer:
    """İşe alım sinyal analizcisi.

    Rakip iş ilanlarını analiz eder,
    büyüme ve stratejik yön sinyalleri çıkarır.

    Attributes:
        _analyses: Analiz kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizcisi başlatır."""
        self._analyses: list[dict] = []
        self._stats = {
            "postings_analyzed": 0,
            "signals_detected": 0,
        }
        logger.info(
            "HiringSignalAnalyzer "
            "baslatildi",
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "postings_analyzed"
        ]

    @property
    def signal_count(self) -> int:
        """Tespit edilen sinyal sayısı."""
        return self._stats[
            "signals_detected"
        ]

    def analyze_postings(
        self,
        competitor_id: str,
        postings: list[dict[str, str]]
        | None = None,
    ) -> dict[str, Any]:
        """İş ilanlarını analiz eder.

        Args:
            competitor_id: Rakip kimliği.
            postings: İş ilanları
                [{title, department}].

        Returns:
            Analiz bilgisi.
        """
        if postings is None:
            postings = []

        departments: dict[str, int] = {}
        for p in postings:
            dept = p.get(
                "department", "other",
            )
            departments[dept] = (
                departments.get(dept, 0) + 1
            )

        self._stats[
            "postings_analyzed"
        ] += len(postings)

        top_dept = (
            max(
                departments,
                key=departments.get,
            )
            if departments
            else ""
        )

        return {
            "competitor_id": competitor_id,
            "total_postings": len(postings),
            "departments": departments,
            "top_department": top_dept,
            "analyzed": True,
        }

    def detect_growth(
        self,
        competitor_id: str,
        current_headcount: int = 0,
        open_positions: int = 0,
    ) -> dict[str, Any]:
        """Büyüme göstergesi tespit eder.

        Args:
            competitor_id: Rakip kimliği.
            current_headcount: Mevcut kadro.
            open_positions: Açık pozisyon.

        Returns:
            Büyüme bilgisi.
        """
        if current_headcount <= 0:
            growth_rate = 0.0
        else:
            growth_rate = round(
                open_positions
                / current_headcount
                * 100,
                1,
            )

        if growth_rate >= 20:
            signal = "rapid_expansion"
        elif growth_rate >= 10:
            signal = "strong_growth"
        elif growth_rate >= 5:
            signal = "moderate_growth"
        elif growth_rate > 0:
            signal = "slow_growth"
        else:
            signal = "stable"

        self._stats[
            "signals_detected"
        ] += 1

        return {
            "competitor_id": competitor_id,
            "growth_rate": growth_rate,
            "signal": signal,
            "detected": True,
        }

    def analyze_skills(
        self,
        competitor_id: str,
        required_skills: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Beceri talebini analiz eder.

        Args:
            competitor_id: Rakip kimliği.
            required_skills: Aranan beceriler.

        Returns:
            Beceri analizi bilgisi.
        """
        if required_skills is None:
            required_skills = []

        categories = {
            "engineering": [
                "python",
                "java",
                "react",
                "aws",
                "docker",
                "kubernetes",
            ],
            "data": [
                "ml",
                "ai",
                "data_science",
                "analytics",
            ],
            "business": [
                "sales",
                "marketing",
                "finance",
                "strategy",
            ],
        }

        skill_map: dict[str, int] = {}
        for skill in required_skills:
            s_lower = skill.lower()
            for cat, kws in (
                categories.items()
            ):
                if s_lower in kws:
                    skill_map[cat] = (
                        skill_map.get(
                            cat, 0,
                        )
                        + 1
                    )
                    break

        focus = (
            max(
                skill_map,
                key=skill_map.get,
            )
            if skill_map
            else "general"
        )

        return {
            "competitor_id": competitor_id,
            "skill_count": len(
                required_skills,
            ),
            "categories": skill_map,
            "primary_focus": focus,
            "analyzed": True,
        }

    def detect_expansion(
        self,
        competitor_id: str,
        new_locations: list[str]
        | None = None,
        new_departments: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Takım genişleme tespit eder.

        Args:
            competitor_id: Rakip kimliği.
            new_locations: Yeni konumlar.
            new_departments: Yeni departmanlar.

        Returns:
            Genişleme bilgisi.
        """
        if new_locations is None:
            new_locations = []
        if new_departments is None:
            new_departments = []

        expansion_score = (
            len(new_locations) * 2
            + len(new_departments)
        )

        if expansion_score >= 5:
            level = "major"
        elif expansion_score >= 3:
            level = "moderate"
        elif expansion_score >= 1:
            level = "minor"
        else:
            level = "none"

        self._stats[
            "signals_detected"
        ] += 1

        return {
            "competitor_id": competitor_id,
            "new_locations": new_locations,
            "new_departments": (
                new_departments
            ),
            "expansion_level": level,
            "detected": True,
        }

    def infer_direction(
        self,
        competitor_id: str,
        hiring_focus: str = "general",
        growth_rate: float = 0.0,
        new_roles: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Stratejik yön çıkarır.

        Args:
            competitor_id: Rakip kimliği.
            hiring_focus: İşe alım odağı.
            growth_rate: Büyüme oranı.
            new_roles: Yeni roller.

        Returns:
            Stratejik yön bilgisi.
        """
        if new_roles is None:
            new_roles = []

        directions = {
            "engineering": (
                "product_development"
            ),
            "data": "ai_investment",
            "business": (
                "market_expansion"
            ),
            "general": "steady_operations",
        }
        direction = directions.get(
            hiring_focus,
            "steady_operations",
        )

        if growth_rate >= 20:
            urgency = "aggressive"
        elif growth_rate >= 10:
            urgency = "active"
        else:
            urgency = "measured"

        return {
            "competitor_id": competitor_id,
            "inferred_direction": direction,
            "urgency": urgency,
            "new_role_count": len(
                new_roles,
            ),
            "inferred": True,
        }
