"""ATLAS Hedef Uretici modulu.

Firsatlari tespit eder, hedef adaylari uretir,
degere gore onceliklendirir, fizibilite ve
kullanici hizalama kontrolu yapar.
"""

import logging
from typing import Any

from app.models.goal_pursuit import (
    AlignmentLevel,
    GoalCandidate,
    GoalDefinition,
    GoalPriority,
    GoalState,
    OpportunityType,
)

logger = logging.getLogger(__name__)


class GoalGenerator:
    """Hedef uretici.

    Firsatlari analiz eder, hedef adaylari uretir
    ve onceliklendirir.

    Attributes:
        _candidates: Hedef adaylari.
        _goals: Uretilen hedefler.
        _templates: Hedef sablonlari.
        _filters: Firsat filtreleri.
    """

    def __init__(self) -> None:
        """Hedef ureticisini baslatir."""
        self._candidates: dict[str, GoalCandidate] = {}
        self._goals: dict[str, GoalDefinition] = {}
        self._templates: dict[str, dict[str, Any]] = {}
        self._filters: dict[str, Any] = {}
        self._opportunity_history: list[dict[str, Any]] = []

        logger.info("GoalGenerator baslatildi")

    def identify_opportunity(
        self,
        opportunity_type: OpportunityType,
        title: str,
        description: str = "",
        estimated_value: float = 0.0,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GoalCandidate:
        """Firsat tespit eder ve hedef adayi olusturur.

        Args:
            opportunity_type: Firsat turu.
            title: Baslik.
            description: Aciklama.
            estimated_value: Tahmini deger.
            source: Kaynak.
            metadata: Ek bilgiler.

        Returns:
            GoalCandidate nesnesi.
        """
        candidate = GoalCandidate(
            title=title,
            description=description,
            opportunity_type=opportunity_type,
            source=source,
            expected_value=estimated_value,
            metadata=metadata or {},
        )
        self._candidates[candidate.candidate_id] = candidate

        self._opportunity_history.append({
            "candidate_id": candidate.candidate_id,
            "type": opportunity_type.value,
            "title": title,
            "value": estimated_value,
        })

        logger.info(
            "Firsat tespit edildi: %s (%s)",
            title, opportunity_type.value,
        )
        return candidate

    def generate_goal(
        self,
        candidate_id: str,
        success_criteria: list[str] | None = None,
        constraints: list[str] | None = None,
        priority: GoalPriority = GoalPriority.MEDIUM,
    ) -> GoalDefinition | None:
        """Adaydan hedef uretir.

        Args:
            candidate_id: Aday ID.
            success_criteria: Basari kriterleri.
            constraints: Kisitlamalar.
            priority: Oncelik.

        Returns:
            GoalDefinition veya None.
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return None

        goal = GoalDefinition(
            title=candidate.title,
            description=candidate.description,
            state=GoalState.CANDIDATE,
            priority=priority,
            success_criteria=success_criteria or [],
            constraints=constraints or [],
            estimated_value=candidate.expected_value,
            tags=list(candidate.tags),
            metadata={
                "candidate_id": candidate_id,
                "opportunity_type": candidate.opportunity_type.value,
                "source": candidate.source,
            },
        )
        self._goals[goal.goal_id] = goal

        logger.info("Hedef uretildi: %s", goal.title)
        return goal

    def generate_from_template(
        self,
        template_name: str,
        overrides: dict[str, Any] | None = None,
    ) -> GoalDefinition | None:
        """Sablondan hedef uretir.

        Args:
            template_name: Sablon adi.
            overrides: Ustune yazilacak alanlar.

        Returns:
            GoalDefinition veya None.
        """
        template = self._templates.get(template_name)
        if not template:
            return None

        params = dict(template)
        if overrides:
            params.update(overrides)

        goal = GoalDefinition(**params)
        self._goals[goal.goal_id] = goal

        logger.info("Sablondan hedef uretildi: %s", template_name)
        return goal

    def register_template(
        self,
        name: str,
        template: dict[str, Any],
    ) -> None:
        """Hedef sablonu kaydeder.

        Args:
            name: Sablon adi.
            template: Sablon icerigi.
        """
        self._templates[name] = template

    def prioritize_candidates(self) -> list[GoalCandidate]:
        """Adaylari degere gore onceliklendirir.

        Returns:
            Sirali aday listesi.
        """
        candidates = list(self._candidates.values())
        return sorted(
            candidates,
            key=lambda c: c.expected_value * c.feasibility,
            reverse=True,
        )

    def check_feasibility(
        self,
        candidate_id: str,
        score: float,
    ) -> bool:
        """Fizibilite puani atar.

        Args:
            candidate_id: Aday ID.
            score: Fizibilite puani (0-1).

        Returns:
            Basarili ise True.
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        candidate.feasibility = max(0.0, min(1.0, score))
        return True

    def check_alignment(
        self,
        candidate_id: str,
        level: AlignmentLevel,
    ) -> bool:
        """Kullanici hizalama seviyesi atar.

        Args:
            candidate_id: Aday ID.
            level: Hizalama seviyesi.

        Returns:
            Basarili ise True.
        """
        candidate = self._candidates.get(candidate_id)
        if not candidate:
            return False

        candidate.alignment = level
        return True

    def get_candidate(self, candidate_id: str) -> GoalCandidate | None:
        """Aday getirir.

        Args:
            candidate_id: Aday ID.

        Returns:
            GoalCandidate veya None.
        """
        return self._candidates.get(candidate_id)

    def get_goal(self, goal_id: str) -> GoalDefinition | None:
        """Hedef getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            GoalDefinition veya None.
        """
        return self._goals.get(goal_id)

    def get_candidates_by_type(
        self,
        opportunity_type: OpportunityType,
    ) -> list[GoalCandidate]:
        """Ture gore adaylari getirir.

        Args:
            opportunity_type: Firsat turu.

        Returns:
            Aday listesi.
        """
        return [
            c for c in self._candidates.values()
            if c.opportunity_type == opportunity_type
        ]

    def remove_candidate(self, candidate_id: str) -> bool:
        """Aday kaldirir.

        Args:
            candidate_id: Aday ID.

        Returns:
            Basarili ise True.
        """
        if candidate_id in self._candidates:
            del self._candidates[candidate_id]
            return True
        return False

    @property
    def total_candidates(self) -> int:
        """Toplam aday sayisi."""
        return len(self._candidates)

    @property
    def total_goals(self) -> int:
        """Toplam hedef sayisi."""
        return len(self._goals)

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)
