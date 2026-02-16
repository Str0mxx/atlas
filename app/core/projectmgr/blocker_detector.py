"""ATLAS Engel Tespitçisi modülü.

Engel tanımlama, etki değerlendirme,
çözüm önerileri, eskalasyon tetikleme,
takip.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BlockerDetector:
    """Engel tespitçisi.

    Proje engellerini tespit ve takip eder.

    Attributes:
        _blockers: Engel kayıtları.
        _resolutions: Çözüm kayıtları.
    """

    def __init__(self) -> None:
        """Tespitçisini başlatır."""
        self._blockers: dict[
            str, dict[str, Any]
        ] = {}
        self._resolutions: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "blockers_detected": 0,
            "blockers_resolved": 0,
            "escalations_triggered": 0,
        }

        logger.info(
            "BlockerDetector baslatildi",
        )

    def detect_blocker(
        self,
        project_id: str,
        description: str,
        severity: str = "medium",
        affected_tasks: (
            list[str] | None
        ) = None,
        category: str = "general",
    ) -> dict[str, Any]:
        """Engel tespit eder.

        Args:
            project_id: Proje ID.
            description: Açıklama.
            severity: Ciddiyet.
            affected_tasks: Etkilenen görevler.
            category: Kategori.

        Returns:
            Engel bilgisi.
        """
        self._counter += 1
        bid = f"block_{self._counter}"

        blocker = {
            "blocker_id": bid,
            "project_id": project_id,
            "description": description,
            "severity": severity,
            "category": category,
            "affected_tasks": (
                affected_tasks or []
            ),
            "status": "active",
            "resolved": False,
            "created_at": time.time(),
        }
        self._blockers[bid] = blocker
        self._stats[
            "blockers_detected"
        ] += 1

        return {
            "blocker_id": bid,
            "severity": severity,
            "affected_count": len(
                affected_tasks or [],
            ),
            "detected": True,
        }

    def assess_impact(
        self,
        blocker_id: str,
    ) -> dict[str, Any]:
        """Etki değerlendirir.

        Args:
            blocker_id: Engel ID.

        Returns:
            Etki bilgisi.
        """
        if (
            blocker_id
            not in self._blockers
        ):
            return {
                "blocker_id": blocker_id,
                "assessed": False,
            }

        blocker = self._blockers[
            blocker_id
        ]
        affected = len(
            blocker["affected_tasks"],
        )

        severity_weight = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 5,
        }.get(blocker["severity"], 2)

        impact_score = round(
            affected * severity_weight
            * 10, 1,
        )
        impact_score = min(
            impact_score, 100,
        )

        # Gecikme tahmini
        delay_estimate = round(
            severity_weight * 2, 1,
        )

        impact_level = (
            "critical"
            if impact_score >= 70
            else "high" if impact_score >= 40
            else "medium"
            if impact_score >= 20
            else "low"
        )

        return {
            "blocker_id": blocker_id,
            "impact_score": impact_score,
            "impact_level": impact_level,
            "delay_estimate_days": (
                delay_estimate
            ),
            "affected_tasks": affected,
            "assessed": True,
        }

    def suggest_resolution(
        self,
        blocker_id: str,
    ) -> dict[str, Any]:
        """Çözüm önerir.

        Args:
            blocker_id: Engel ID.

        Returns:
            Çözüm önerileri.
        """
        if (
            blocker_id
            not in self._blockers
        ):
            return {
                "blocker_id": blocker_id,
                "suggestions": [],
            }

        blocker = self._blockers[
            blocker_id
        ]
        suggestions = []

        cat = blocker["category"]
        if cat == "technical":
            suggestions = [
                "Review technical approach",
                "Consult domain expert",
                "Create proof of concept",
            ]
        elif cat == "resource":
            suggestions = [
                "Reallocate team members",
                "Request additional budget",
                "Outsource specific tasks",
            ]
        elif cat == "dependency":
            suggestions = [
                "Contact dependency owner",
                "Find alternative approach",
                "Implement workaround",
            ]
        else:
            suggestions = [
                "Analyze root cause",
                "Escalate to management",
                "Define workaround plan",
            ]

        return {
            "blocker_id": blocker_id,
            "category": cat,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    def resolve_blocker(
        self,
        blocker_id: str,
        resolution: str = "",
    ) -> dict[str, Any]:
        """Engeli çözer.

        Args:
            blocker_id: Engel ID.
            resolution: Çözüm açıklaması.

        Returns:
            Çözüm bilgisi.
        """
        if (
            blocker_id
            not in self._blockers
        ):
            return {
                "blocker_id": blocker_id,
                "resolved": False,
                "reason": "not_found",
            }

        blocker = self._blockers[
            blocker_id
        ]
        blocker["status"] = "resolved"
        blocker["resolved"] = True
        blocker[
            "resolved_at"
        ] = time.time()

        duration = round(
            blocker["resolved_at"]
            - blocker["created_at"], 1,
        )

        self._resolutions.append({
            "blocker_id": blocker_id,
            "resolution": resolution,
            "duration": duration,
        })
        self._stats[
            "blockers_resolved"
        ] += 1

        return {
            "blocker_id": blocker_id,
            "resolution": resolution,
            "duration_seconds": duration,
            "resolved": True,
        }

    def should_escalate(
        self,
        blocker_id: str,
        max_age_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Eskalasyon gerekli mi kontrol eder.

        Args:
            blocker_id: Engel ID.
            max_age_hours: Maks yaş (saat).

        Returns:
            Eskalasyon bilgisi.
        """
        if (
            blocker_id
            not in self._blockers
        ):
            return {
                "escalate": False,
            }

        blocker = self._blockers[
            blocker_id
        ]
        if blocker["resolved"]:
            return {
                "escalate": False,
                "reason": "already_resolved",
            }

        age_hours = (
            time.time()
            - blocker["created_at"]
        ) / 3600

        escalate = (
            blocker["severity"]
            in ("high", "critical")
            or age_hours > max_age_hours
        )

        if escalate:
            self._stats[
                "escalations_triggered"
            ] += 1

        return {
            "blocker_id": blocker_id,
            "escalate": escalate,
            "severity": blocker["severity"],
            "age_hours": round(
                age_hours, 1,
            ),
        }

    def get_active_blockers(
        self,
        project_id: str = "",
    ) -> list[dict[str, Any]]:
        """Aktif engelleri listeler."""
        blockers = [
            b for b in
            self._blockers.values()
            if not b["resolved"]
        ]
        if project_id:
            blockers = [
                b for b in blockers
                if b["project_id"]
                == project_id
            ]
        return blockers

    @property
    def blocker_count(self) -> int:
        """Engel sayısı."""
        return self._stats[
            "blockers_detected"
        ]

    @property
    def active_blocker_count(self) -> int:
        """Aktif engel sayısı."""
        return sum(
            1 for b in
            self._blockers.values()
            if not b["resolved"]
        )

    @property
    def resolved_count(self) -> int:
        """Çözülen sayısı."""
        return self._stats[
            "blockers_resolved"
        ]
