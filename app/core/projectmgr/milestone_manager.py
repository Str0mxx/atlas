"""ATLAS Kilometre Taşı Yöneticisi modülü.

Kilometre taşı tanımlama, ilerleme takibi,
tamamlanma doğrulama, bağımlılık yönetimi,
kutlama tetikleyicileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MilestoneManager:
    """Kilometre taşı yöneticisi.

    Proje kilometre taşlarını yönetir.

    Attributes:
        _milestones: Kilometre taşı kayıtları.
        _dependencies: Bağımlılıklar.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._milestones: dict[
            str, dict[str, Any]
        ] = {}
        self._dependencies: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "milestones_created": 0,
            "milestones_completed": 0,
            "celebrations": 0,
        }

        logger.info(
            "MilestoneManager baslatildi",
        )

    def create_milestone(
        self,
        project_id: str,
        name: str,
        due_date: str = "",
        description: str = "",
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Kilometre taşı oluşturur.

        Args:
            project_id: Proje ID.
            name: Ad.
            due_date: Son tarih.
            description: Açıklama.
            weight: Ağırlık.

        Returns:
            Kilometre taşı bilgisi.
        """
        self._counter += 1
        mid = f"ms_{self._counter}"

        milestone = {
            "milestone_id": mid,
            "project_id": project_id,
            "name": name,
            "due_date": due_date,
            "description": description,
            "weight": weight,
            "status": "pending",
            "progress": 0.0,
            "tasks": [],
            "created_at": time.time(),
        }
        self._milestones[mid] = milestone
        self._stats[
            "milestones_created"
        ] += 1

        return {
            "milestone_id": mid,
            "name": name,
            "project_id": project_id,
            "created": True,
        }

    def update_progress(
        self,
        milestone_id: str,
        progress: float,
    ) -> dict[str, Any]:
        """İlerleme günceller.

        Args:
            milestone_id: Kilometre taşı ID.
            progress: İlerleme yüzdesi.

        Returns:
            İlerleme bilgisi.
        """
        if (
            milestone_id
            not in self._milestones
        ):
            return {
                "milestone_id": milestone_id,
                "updated": False,
            }

        ms = self._milestones[milestone_id]
        ms["progress"] = min(progress, 100)

        if progress >= 100:
            ms["status"] = "completed"
            self._stats[
                "milestones_completed"
            ] += 1

        elif progress > 0:
            ms["status"] = "in_progress"

        return {
            "milestone_id": milestone_id,
            "progress": ms["progress"],
            "status": ms["status"],
            "updated": True,
        }

    def verify_completion(
        self,
        milestone_id: str,
        criteria: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tamamlanma doğrular.

        Args:
            milestone_id: Kilometre taşı ID.
            criteria: Kriterler.

        Returns:
            Doğrulama bilgisi.
        """
        if (
            milestone_id
            not in self._milestones
        ):
            return {
                "milestone_id": milestone_id,
                "verified": False,
                "reason": "not_found",
            }

        ms = self._milestones[milestone_id]
        criteria = criteria or []

        # Bağımlılıklar tamamlandı mı
        deps = self._dependencies.get(
            milestone_id, [],
        )
        deps_met = all(
            self._milestones.get(
                d, {},
            ).get("status") == "completed"
            for d in deps
        )

        complete = (
            ms["progress"] >= 100
            and deps_met
        )

        return {
            "milestone_id": milestone_id,
            "complete": complete,
            "progress": ms["progress"],
            "dependencies_met": deps_met,
            "criteria_count": len(criteria),
            "verified": True,
        }

    def add_dependency(
        self,
        milestone_id: str,
        depends_on: str,
    ) -> dict[str, Any]:
        """Bağımlılık ekler.

        Args:
            milestone_id: Kilometre taşı ID.
            depends_on: Bağımlı olunan ID.

        Returns:
            Bağımlılık bilgisi.
        """
        if (
            milestone_id
            not in self._dependencies
        ):
            self._dependencies[
                milestone_id
            ] = []

        self._dependencies[
            milestone_id
        ].append(depends_on)

        return {
            "milestone_id": milestone_id,
            "depends_on": depends_on,
            "added": True,
        }

    def check_celebration(
        self,
        milestone_id: str,
    ) -> dict[str, Any]:
        """Kutlama kontrolü yapar.

        Args:
            milestone_id: Kilometre taşı ID.

        Returns:
            Kutlama bilgisi.
        """
        if (
            milestone_id
            not in self._milestones
        ):
            return {
                "celebrate": False,
            }

        ms = self._milestones[milestone_id]
        celebrate = (
            ms["status"] == "completed"
        )

        if celebrate:
            self._stats["celebrations"] += 1

        significance = (
            "major" if ms["weight"] >= 2.0
            else "standard"
        )

        return {
            "milestone_id": milestone_id,
            "celebrate": celebrate,
            "name": ms["name"],
            "significance": significance,
        }

    def get_milestones(
        self,
        project_id: str = "",
        status: str = "",
    ) -> list[dict[str, Any]]:
        """Kilometre taşlarını listeler."""
        results = list(
            self._milestones.values(),
        )
        if project_id:
            results = [
                m for m in results
                if m["project_id"]
                == project_id
            ]
        if status:
            results = [
                m for m in results
                if m["status"] == status
            ]
        return results

    def get_milestone(
        self,
        milestone_id: str,
    ) -> dict[str, Any] | None:
        """Kilometre taşı döndürür."""
        return self._milestones.get(
            milestone_id,
        )

    @property
    def milestone_count(self) -> int:
        """Kilometre taşı sayısı."""
        return self._stats[
            "milestones_created"
        ]

    @property
    def completed_count(self) -> int:
        """Tamamlanan sayısı."""
        return self._stats[
            "milestones_completed"
        ]
