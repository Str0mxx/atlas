"""ATLAS Proje Yönetim Orkestratörü modülü.

Tam proje yönetimi,
Track → Predict → Alert → Report → Escalate,
çoklu proje, analitik.
"""

import logging
import time
from typing import Any

from app.core.projectmgr.auto_escalator import (
    AutoEscalator,
)
from app.core.projectmgr.blocker_detector import (
    BlockerDetector,
)
from app.core.projectmgr.deadline_predictor import (
    DeadlinePredictor,
)
from app.core.projectmgr.dependency_resolver import (
    ProjectDependencyResolver,
)
from app.core.projectmgr.milestone_manager import (
    MilestoneManager,
)
from app.core.projectmgr.progress_reporter import (
    ProjectProgressReporter,
)
from app.core.projectmgr.project_tracker import (
    ProjectTracker,
)
from app.core.projectmgr.resource_balancer import (
    ProjectResourceBalancer,
)

logger = logging.getLogger(__name__)


class ProjectMgrOrchestrator:
    """Proje yönetim orkestratörü.

    Tüm proje yönetim bileşenlerini
    koordine eder.

    Attributes:
        tracker: Proje takipçisi.
        milestones: Kilometre taşı yöneticisi.
        dependencies: Bağımlılık çözücü.
        predictor: Son tarih tahmincisi.
        blockers: Engel tespitçisi.
        reporter: İlerleme raporlayıcı.
        escalator: Otomatik eskalasyon.
        balancer: Kaynak dengeleyici.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.tracker = ProjectTracker()
        self.milestones = (
            MilestoneManager()
        )
        self.dependencies = (
            ProjectDependencyResolver()
        )
        self.predictor = (
            DeadlinePredictor()
        )
        self.blockers = BlockerDetector()
        self.reporter = (
            ProjectProgressReporter()
        )
        self.escalator = AutoEscalator()
        self.balancer = (
            ProjectResourceBalancer()
        )
        self._stats = {
            "projects_managed": 0,
            "full_cycles": 0,
        }

        logger.info(
            "ProjectMgrOrchestrator "
            "baslatildi",
        )

    def manage_project(
        self,
        name: str,
        owner: str = "",
        description: str = "",
        deadline: str = "",
        priority: str = "medium",
        team: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tam proje yönetimi yapar.

        Args:
            name: Proje adı.
            owner: Sahip.
            description: Açıklama.
            deadline: Son tarih.
            priority: Öncelik.
            team: Takım üyeleri.

        Returns:
            Yönetim bilgisi.
        """
        # Proje oluştur
        result = self.tracker.create_project(
            name=name,
            owner=owner,
            description=description,
            deadline=deadline,
            priority=priority,
        )
        pid = result["project_id"]

        # Takım ata
        if team:
            self.tracker.assign_team(
                pid, team,
            )

        # Başlangıç kilometre taşı
        self.milestones.create_milestone(
            project_id=pid,
            name=f"{name} - Kickoff",
            weight=0.5,
        )

        self._stats[
            "projects_managed"
        ] += 1

        return {
            "project_id": pid,
            "name": name,
            "team_size": len(team or []),
            "managed": True,
        }

    def run_project_cycle(
        self,
        project_id: str,
        progress: float = 0.0,
        tasks_done: int = 0,
        tasks_total: int = 0,
        elapsed_days: float = 0.0,
    ) -> dict[str, Any]:
        """Track → Predict → Alert → Report → Escalate.

        Args:
            project_id: Proje ID.
            progress: İlerleme yüzdesi.
            tasks_done: Tamamlanan görev.
            tasks_total: Toplam görev.
            elapsed_days: Geçen gün.

        Returns:
            Döngü sonucu.
        """
        # 1. Track
        self.tracker.update_progress(
            project_id, tasks_done,
            tasks_total,
        )
        health = self.tracker.score_health(
            project_id,
            on_schedule=progress >= 50
            or elapsed_days < 10,
            blockers=(
                self.blockers
                .active_blocker_count
            ),
        )

        # 2. Predict
        prediction = (
            self.predictor.predict_completion(
                project_id,
                progress=progress,
                elapsed_days=max(
                    elapsed_days, 0.1,
                ),
                remaining_tasks=(
                    tasks_total - tasks_done
                ),
            )
        )

        # 3. Alert - engel kontrolü
        active = (
            self.blockers.get_active_blockers(
                project_id,
            )
        )
        alerts = len(active)

        # 4. Report
        report = (
            self.reporter
            .generate_status_report(
                project_id=project_id,
                progress=progress,
                tasks_done=tasks_done,
                tasks_total=tasks_total,
                blockers=alerts,
                health_score=health.get(
                    "health_score", 100,
                ),
            )
        )

        # 5. Escalate (eğer gerekiyorsa)
        escalated = False
        if health.get(
            "level",
        ) == "critical":
            esc = (
                self.escalator.detect_trigger(
                    project_id,
                    "critical_health",
                )
            )
            escalated = esc.get(
                "triggered", False,
            )

        self._stats["full_cycles"] += 1

        return {
            "project_id": project_id,
            "health": health.get(
                "level", "unknown",
            ),
            "health_score": health.get(
                "health_score", 0,
            ),
            "remaining_days": (
                prediction.get(
                    "remaining_days", 0,
                )
            ),
            "active_blockers": alerts,
            "report_id": report.get(
                "report_id", "",
            ),
            "escalated": escalated,
            "cycle_complete": True,
        }

    def get_multi_project_status(
        self,
    ) -> dict[str, Any]:
        """Çoklu proje durumu döndürür.

        Returns:
            Çoklu proje bilgisi.
        """
        projects = (
            self.tracker.list_projects()
        )

        statuses = {}
        for p in projects:
            statuses[
                p["project_id"]
            ] = {
                "name": p["name"],
                "status": p["status"],
                "progress": p["progress"],
                "health": p[
                    "health_score"
                ],
            }

        active_count = sum(
            1 for p in projects
            if p["status"] == "active"
        )

        return {
            "total_projects": len(
                projects,
            ),
            "active_projects": (
                active_count
            ),
            "projects": statuses,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "projects_managed": (
                self._stats[
                    "projects_managed"
                ]
            ),
            "full_cycles": (
                self._stats["full_cycles"]
            ),
            "total_milestones": (
                self.milestones
                .milestone_count
            ),
            "completed_milestones": (
                self.milestones
                .completed_count
            ),
            "total_blockers": (
                self.blockers
                .blocker_count
            ),
            "active_blockers": (
                self.blockers
                .active_blocker_count
            ),
            "resolved_blockers": (
                self.blockers
                .resolved_count
            ),
            "reports_generated": (
                self.reporter
                .report_count
            ),
            "predictions_made": (
                self.predictor
                .prediction_count
            ),
            "escalation_rules": (
                self.escalator
                .rule_count
            ),
            "escalations": (
                self.escalator
                .escalation_count
            ),
        }

    @property
    def project_count(self) -> int:
        """Proje sayısı."""
        return self.tracker.project_count

    @property
    def cycle_count(self) -> int:
        """Döngü sayısı."""
        return self._stats[
            "full_cycles"
        ]
