"""ATLAS Proje Takipçisi modülü.

Proje yaşam döngüsü, durum takibi,
sağlık puanlama, takım atama,
kaynak tahsisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProjectTracker:
    """Proje takipçisi.

    Projeleri takip eder ve yönetir.

    Attributes:
        _projects: Proje kayıtları.
        _teams: Takım atamaları.
    """

    def __init__(self) -> None:
        """Takipçisini başlatır."""
        self._projects: dict[
            str, dict[str, Any]
        ] = {}
        self._teams: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "projects_created": 0,
            "status_changes": 0,
            "team_assignments": 0,
        }

        logger.info(
            "ProjectTracker baslatildi",
        )

    def create_project(
        self,
        name: str,
        owner: str = "",
        description: str = "",
        deadline: str = "",
        priority: str = "medium",
    ) -> dict[str, Any]:
        """Proje oluşturur.

        Args:
            name: Proje adı.
            owner: Sahip.
            description: Açıklama.
            deadline: Son tarih.
            priority: Öncelik.

        Returns:
            Proje bilgisi.
        """
        self._counter += 1
        pid = f"proj_{self._counter}"

        project = {
            "project_id": pid,
            "name": name,
            "owner": owner,
            "description": description,
            "deadline": deadline,
            "priority": priority,
            "status": "draft",
            "health_score": 100.0,
            "progress": 0.0,
            "tasks_total": 0,
            "tasks_done": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._projects[pid] = project
        self._stats["projects_created"] += 1

        return {
            "project_id": pid,
            "name": name,
            "status": "draft",
            "created": True,
        }

    def update_status(
        self,
        project_id: str,
        status: str,
    ) -> dict[str, Any]:
        """Durum günceller.

        Args:
            project_id: Proje ID.
            status: Yeni durum.

        Returns:
            Güncelleme bilgisi.
        """
        if project_id not in self._projects:
            return {
                "project_id": project_id,
                "updated": False,
                "reason": "not_found",
            }

        proj = self._projects[project_id]
        old = proj["status"]
        proj["status"] = status
        proj["updated_at"] = time.time()
        self._stats["status_changes"] += 1

        return {
            "project_id": project_id,
            "old_status": old,
            "new_status": status,
            "updated": True,
        }

    def update_progress(
        self,
        project_id: str,
        tasks_done: int,
        tasks_total: int,
    ) -> dict[str, Any]:
        """İlerleme günceller.

        Args:
            project_id: Proje ID.
            tasks_done: Tamamlanan.
            tasks_total: Toplam.

        Returns:
            İlerleme bilgisi.
        """
        if project_id not in self._projects:
            return {
                "project_id": project_id,
                "updated": False,
            }

        proj = self._projects[project_id]
        proj["tasks_done"] = tasks_done
        proj["tasks_total"] = tasks_total
        prog = round(
            tasks_done
            / max(tasks_total, 1)
            * 100, 1,
        )
        proj["progress"] = prog
        proj["updated_at"] = time.time()

        return {
            "project_id": project_id,
            "progress": prog,
            "tasks_done": tasks_done,
            "tasks_total": tasks_total,
            "updated": True,
        }

    def score_health(
        self,
        project_id: str,
        on_schedule: bool = True,
        blockers: int = 0,
        team_morale: float = 80.0,
    ) -> dict[str, Any]:
        """Sağlık puanlar.

        Args:
            project_id: Proje ID.
            on_schedule: Zamanında mı.
            blockers: Engel sayısı.
            team_morale: Takım morali.

        Returns:
            Sağlık bilgisi.
        """
        if project_id not in self._projects:
            return {
                "project_id": project_id,
                "scored": False,
            }

        score = 100.0
        if not on_schedule:
            score -= 25
        score -= blockers * 10
        score -= max(0, (80 - team_morale))
        score = max(0, min(100, score))

        level = (
            "healthy" if score >= 80
            else "at_risk" if score >= 50
            else "critical"
        )

        proj = self._projects[project_id]
        proj["health_score"] = round(
            score, 1,
        )

        return {
            "project_id": project_id,
            "health_score": round(
                score, 1,
            ),
            "level": level,
            "on_schedule": on_schedule,
            "blockers": blockers,
            "scored": True,
        }

    def assign_team(
        self,
        project_id: str,
        members: list[str],
    ) -> dict[str, Any]:
        """Takım atar.

        Args:
            project_id: Proje ID.
            members: Üyeler.

        Returns:
            Atama bilgisi.
        """
        if project_id not in self._projects:
            return {
                "project_id": project_id,
                "assigned": False,
            }

        self._teams[project_id] = members
        self._stats[
            "team_assignments"
        ] += 1

        return {
            "project_id": project_id,
            "members": members,
            "count": len(members),
            "assigned": True,
        }

    def get_project(
        self,
        project_id: str,
    ) -> dict[str, Any] | None:
        """Proje döndürür."""
        return self._projects.get(
            project_id,
        )

    def list_projects(
        self,
        status: str = "",
    ) -> list[dict[str, Any]]:
        """Projeleri listeler."""
        projects = list(
            self._projects.values(),
        )
        if status:
            projects = [
                p for p in projects
                if p["status"] == status
            ]
        return projects

    @property
    def project_count(self) -> int:
        """Proje sayısı."""
        return self._stats[
            "projects_created"
        ]

    @property
    def active_count(self) -> int:
        """Aktif proje sayısı."""
        return sum(
            1 for p in self._projects.values()
            if p["status"] == "active"
        )
