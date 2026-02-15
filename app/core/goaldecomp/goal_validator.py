"""ATLAS Hedef Dogrulayici modulu.

Fizibilite kontrolu, tamlama kontrolu,
tutarlilik kontrolu, kaynak yeterliligi, zaman gecerliligi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GoalValidator:
    """Hedef dogrulayici.

    Hedefleri dogrulanabilirlik acisindan kontrol eder.

    Attributes:
        _validations: Dogrulama kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Hedef dogrulayiciyi baslatir."""
        self._validations: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "validated": 0,
            "passed": 0,
            "failed": 0,
        }

        logger.info(
            "GoalValidator baslatildi",
        )

    def validate_goal(
        self,
        goal_id: str,
        description: str,
        constraints: list[str] | None = None,
        available_resources: (
            dict[str, Any] | None
        ) = None,
        deadline_hours: float | None = None,
    ) -> dict[str, Any]:
        """Hedefi dogrular.

        Args:
            goal_id: Hedef ID.
            description: Hedef aciklamasi.
            constraints: Kisitlar.
            available_resources: Mevcut kaynaklar.
            deadline_hours: Son tarih (saat).

        Returns:
            Dogrulama sonucu.
        """
        checks = []

        # Fizibilite kontrolu
        feasibility = (
            self._check_feasibility(
                description,
            )
        )
        checks.append(feasibility)

        # Tamlama kontrolu
        completeness = (
            self._check_completeness(
                description,
                constraints,
            )
        )
        checks.append(completeness)

        # Tutarlilik kontrolu
        consistency = (
            self._check_consistency(
                description,
                constraints or [],
            )
        )
        checks.append(consistency)

        # Kaynak yeterliligi
        if available_resources:
            sufficiency = (
                self._check_resource_sufficiency(
                    available_resources,
                )
            )
            checks.append(sufficiency)

        # Zaman gecerliligi
        if deadline_hours is not None:
            timeline = (
                self._check_timeline(
                    deadline_hours,
                )
            )
            checks.append(timeline)

        # Genel sonuc
        all_passed = all(
            c["passed"] for c in checks
        )
        result = (
            "valid" if all_passed
            else "invalid"
        )

        validation = {
            "goal_id": goal_id,
            "result": result,
            "checks": checks,
            "check_count": len(checks),
            "passed_count": sum(
                1 for c in checks
                if c["passed"]
            ),
            "validated_at": time.time(),
        }

        self._validations[goal_id] = validation
        self._stats["validated"] += 1
        if all_passed:
            self._stats["passed"] += 1
        else:
            self._stats["failed"] += 1

        return validation

    def _check_feasibility(
        self,
        description: str,
    ) -> dict[str, Any]:
        """Fizibilite kontrolu yapar.

        Args:
            description: Hedef aciklamasi.

        Returns:
            Kontrol sonucu.
        """
        # Cok genel veya imkansiz hedefler
        infeasible_words = [
            "impossible", "never",
            "infinite", "everything",
            "all problems",
        ]
        lower = description.lower()

        is_feasible = not any(
            w in lower
            for w in infeasible_words
        )

        return {
            "check": "feasibility",
            "passed": is_feasible,
            "details": (
                "Goal appears feasible"
                if is_feasible
                else "Goal may be infeasible"
            ),
        }

    def _check_completeness(
        self,
        description: str,
        constraints: list[str] | None,
    ) -> dict[str, Any]:
        """Tamlama kontrolu yapar.

        Args:
            description: Hedef aciklamasi.
            constraints: Kisitlar.

        Returns:
            Kontrol sonucu.
        """
        issues = []

        if len(description.split()) < 3:
            issues.append(
                "Description too brief",
            )

        if not description.strip():
            issues.append(
                "Empty description",
            )

        is_complete = len(issues) == 0

        return {
            "check": "completeness",
            "passed": is_complete,
            "issues": issues,
            "details": (
                "Goal is complete"
                if is_complete
                else f"Issues: {', '.join(issues)}"
            ),
        }

    def _check_consistency(
        self,
        description: str,
        constraints: list[str],
    ) -> dict[str, Any]:
        """Tutarlilik kontrolu yapar.

        Args:
            description: Hedef aciklamasi.
            constraints: Kisitlar.

        Returns:
            Kontrol sonucu.
        """
        conflicts = []

        # Celisikli kisitlar
        constraint_pairs = [
            ("fast", "cheap"),
            ("quick", "thorough"),
        ]

        lower_constraints = [
            c.lower() for c in constraints
        ]
        for a, b in constraint_pairs:
            if (
                a in lower_constraints
                and b in lower_constraints
            ):
                conflicts.append(
                    f"'{a}' conflicts with "
                    f"'{b}'"
                )

        is_consistent = len(conflicts) == 0

        return {
            "check": "consistency",
            "passed": is_consistent,
            "conflicts": conflicts,
            "details": (
                "No conflicts detected"
                if is_consistent
                else (
                    f"Conflicts: "
                    f"{', '.join(conflicts)}"
                )
            ),
        }

    def _check_resource_sufficiency(
        self,
        resources: dict[str, Any],
    ) -> dict[str, Any]:
        """Kaynak yeterliligi kontrolu yapar.

        Args:
            resources: Mevcut kaynaklar.

        Returns:
            Kontrol sonucu.
        """
        issues = []

        budget = resources.get("budget", 0)
        if budget <= 0:
            issues.append("No budget allocated")

        agents = resources.get("agents", 0)
        if agents <= 0:
            issues.append(
                "No agents available",
            )

        is_sufficient = len(issues) == 0

        return {
            "check": "resource_sufficiency",
            "passed": is_sufficient,
            "issues": issues,
            "details": (
                "Resources sufficient"
                if is_sufficient
                else (
                    f"Issues: "
                    f"{', '.join(issues)}"
                )
            ),
        }

    def _check_timeline(
        self,
        deadline_hours: float,
    ) -> dict[str, Any]:
        """Zaman gecerliligi kontrolu yapar.

        Args:
            deadline_hours: Son tarih (saat).

        Returns:
            Kontrol sonucu.
        """
        is_valid = deadline_hours > 0

        return {
            "check": "timeline",
            "passed": is_valid,
            "deadline_hours": deadline_hours,
            "details": (
                "Timeline is valid"
                if is_valid
                else "Invalid deadline"
            ),
        }

    def get_validation(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Dogrulama sonucu getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Dogrulama bilgisi.
        """
        v = self._validations.get(goal_id)
        if not v:
            return {
                "error": "validation_not_found",
            }
        return dict(v)

    @property
    def validation_count(self) -> int:
        """Dogrulama sayisi."""
        return self._stats["validated"]

    @property
    def pass_rate(self) -> float:
        """Basari orani."""
        total = self._stats["validated"]
        if total == 0:
            return 0.0
        return round(
            self._stats["passed"]
            / total * 100, 1,
        )
