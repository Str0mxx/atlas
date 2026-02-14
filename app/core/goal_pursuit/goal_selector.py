"""ATLAS Hedef Secici modulu.

Coklu kriter secimi, kaynak uygunlugu,
catisma tespiti, kullanici tercihi ve
stratejik uyum kontrolu.
"""

import logging
from typing import Any

from app.models.goal_pursuit import (
    AlignmentLevel,
    GoalDefinition,
    GoalPriority,
    GoalState,
)

logger = logging.getLogger(__name__)

_PRIORITY_WEIGHTS: dict[GoalPriority, float] = {
    GoalPriority.CRITICAL: 1.0,
    GoalPriority.HIGH: 0.8,
    GoalPriority.MEDIUM: 0.5,
    GoalPriority.LOW: 0.3,
    GoalPriority.OPPORTUNISTIC: 0.1,
}

_ALIGNMENT_SCORES: dict[AlignmentLevel, float] = {
    AlignmentLevel.STRONG: 1.0,
    AlignmentLevel.MODERATE: 0.7,
    AlignmentLevel.WEAK: 0.4,
    AlignmentLevel.NEUTRAL: 0.2,
    AlignmentLevel.MISALIGNED: -0.5,
}


class GoalSelector:
    """Hedef secici.

    Adaylar arasindan en uygun hedefleri
    coklu kritere gore secer.

    Attributes:
        _goals: Degerlendirilen hedefler.
        _scores: Hedef puanlari.
        _criteria_weights: Kriter agirliklari.
        _available_resources: Mevcut kaynaklar.
        _conflicts: Catisma kayitlari.
        _user_preferences: Kullanici tercihleri.
    """

    def __init__(self) -> None:
        """Hedef seciciyi baslatir."""
        self._goals: dict[str, GoalDefinition] = {}
        self._scores: dict[str, dict[str, float]] = {}
        self._criteria_weights: dict[str, float] = {
            "value": 0.3,
            "feasibility": 0.2,
            "alignment": 0.2,
            "priority": 0.15,
            "strategic_fit": 0.15,
        }
        self._available_resources: dict[str, float] = {}
        self._conflicts: list[dict[str, Any]] = []
        self._user_preferences: dict[str, Any] = {}

        logger.info("GoalSelector baslatildi")

    def add_goal(self, goal: GoalDefinition) -> None:
        """Degerlendirmeye hedef ekler.

        Args:
            goal: Hedef tanimi.
        """
        self._goals[goal.goal_id] = goal

    def score_goal(
        self,
        goal_id: str,
        value_score: float = 0.5,
        feasibility_score: float = 0.5,
        alignment_level: AlignmentLevel = AlignmentLevel.NEUTRAL,
        strategic_fit: float = 0.5,
    ) -> dict[str, float] | None:
        """Hedefe puan verir.

        Args:
            goal_id: Hedef ID.
            value_score: Deger puani (0-1).
            feasibility_score: Fizibilite puani (0-1).
            alignment_level: Hizalama seviyesi.
            strategic_fit: Stratejik uyum (0-1).

        Returns:
            Puan detaylari veya None.
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        priority_score = _PRIORITY_WEIGHTS.get(goal.priority, 0.5)
        alignment_score = _ALIGNMENT_SCORES.get(alignment_level, 0.2)

        scores = {
            "value": max(0.0, min(1.0, value_score)),
            "feasibility": max(0.0, min(1.0, feasibility_score)),
            "alignment": alignment_score,
            "priority": priority_score,
            "strategic_fit": max(0.0, min(1.0, strategic_fit)),
        }

        # Agirlikli toplam
        weighted = sum(
            scores[k] * self._criteria_weights.get(k, 0.0)
            for k in scores
        )
        scores["weighted_total"] = round(weighted, 4)

        self._scores[goal_id] = scores
        return scores

    def select_top(self, count: int = 5) -> list[dict[str, Any]]:
        """En iyi hedefleri secer.

        Args:
            count: Secilecek hedef sayisi.

        Returns:
            Sirali hedef listesi.
        """
        ranked = []
        for goal_id, scores in self._scores.items():
            goal = self._goals.get(goal_id)
            if goal:
                ranked.append({
                    "goal_id": goal_id,
                    "title": goal.title,
                    "priority": goal.priority.value,
                    "weighted_total": scores.get("weighted_total", 0.0),
                    "scores": dict(scores),
                })

        ranked.sort(
            key=lambda r: r["weighted_total"],
            reverse=True,
        )
        return ranked[:count]

    def check_resource_availability(
        self,
        goal_id: str,
        required_resources: dict[str, float],
    ) -> dict[str, Any]:
        """Kaynak uygunlugunu kontrol eder.

        Args:
            goal_id: Hedef ID.
            required_resources: Gereken kaynaklar.

        Returns:
            Uygunluk sonucu.
        """
        missing = {}
        available = True

        for resource, amount in required_resources.items():
            current = self._available_resources.get(resource, 0.0)
            if current < amount:
                missing[resource] = amount - current
                available = False

        return {
            "goal_id": goal_id,
            "available": available,
            "missing": missing,
        }

    def set_available_resources(
        self,
        resources: dict[str, float],
    ) -> None:
        """Mevcut kaynaklari ayarlar.

        Args:
            resources: Kaynak -> miktar eslesmesi.
        """
        self._available_resources.update(resources)

    def detect_conflicts(
        self,
        goal_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Hedefler arasi catismalari tespit eder.

        Args:
            goal_ids: Kontrol edilecek hedef ID'leri.

        Returns:
            Catisma listesi.
        """
        conflicts: list[dict[str, Any]] = []

        for i, gid1 in enumerate(goal_ids):
            g1 = self._goals.get(gid1)
            if not g1:
                continue
            for gid2 in goal_ids[i + 1:]:
                g2 = self._goals.get(gid2)
                if not g2:
                    continue

                # Kaynak catismasi
                shared_deps = set(g1.dependencies) & set(g2.dependencies)
                if shared_deps:
                    conflict = {
                        "type": "resource",
                        "goals": [gid1, gid2],
                        "shared": list(shared_deps),
                    }
                    conflicts.append(conflict)

                # Kisitlama catismasi
                shared_constraints = (
                    set(g1.constraints) & set(g2.constraints)
                )
                if shared_constraints:
                    conflict = {
                        "type": "constraint",
                        "goals": [gid1, gid2],
                        "shared": list(shared_constraints),
                    }
                    conflicts.append(conflict)

        self._conflicts.extend(conflicts)
        return conflicts

    def set_criteria_weights(
        self,
        weights: dict[str, float],
    ) -> None:
        """Kriter agirliklarini ayarlar.

        Args:
            weights: Kriter -> agirlik eslesmesi.
        """
        self._criteria_weights.update(weights)

    def set_user_preferences(
        self,
        preferences: dict[str, Any],
    ) -> None:
        """Kullanici tercihlerini ayarlar.

        Args:
            preferences: Tercih sozlugu.
        """
        self._user_preferences.update(preferences)

    def filter_by_state(
        self,
        state: GoalState,
    ) -> list[GoalDefinition]:
        """Duruma gore filtreler.

        Args:
            state: Hedef durumu.

        Returns:
            Hedef listesi.
        """
        return [
            g for g in self._goals.values()
            if g.state == state
        ]

    def approve_goal(self, goal_id: str) -> bool:
        """Hedefe onay verir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Basarili ise True.
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal.state = GoalState.APPROVED
        logger.info("Hedef onaylandi: %s", goal.title)
        return True

    def reject_goal(self, goal_id: str) -> bool:
        """Hedefi reddeder.

        Args:
            goal_id: Hedef ID.

        Returns:
            Basarili ise True.
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return False

        goal.state = GoalState.ABANDONED
        return True

    def get_goal(self, goal_id: str) -> GoalDefinition | None:
        """Hedef getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            GoalDefinition veya None.
        """
        return self._goals.get(goal_id)

    @property
    def total_goals(self) -> int:
        """Toplam hedef sayisi."""
        return len(self._goals)

    @property
    def scored_count(self) -> int:
        """Puanlanan hedef sayisi."""
        return len(self._scores)

    @property
    def conflict_count(self) -> int:
        """Catisma sayisi."""
        return len(self._conflicts)
