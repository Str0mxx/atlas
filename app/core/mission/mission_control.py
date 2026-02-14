"""ATLAS Gorev Kontrol Merkezi modulu.

Tam gorev yasam dongusu, coklu gorev yonetimi,
oncelik isleme, sistem entegrasyonu ve insan eskalasyonu.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.mission import (
    AlertSeverity,
    ContingencyType,
    MissionDefinition,
    MissionSnapshot,
    MissionState,
    PhaseState,
    ReportType,
)

from app.core.mission.contingency_manager import ContingencyManager
from app.core.mission.mission_definer import MissionDefiner
from app.core.mission.mission_planner import MissionPlanner
from app.core.mission.mission_reporter import MissionReporter
from app.core.mission.phase_controller import PhaseController
from app.core.mission.progress_tracker import ProgressTracker
from app.core.mission.resource_commander import ResourceCommander
from app.core.mission.situation_room import SituationRoom

logger = logging.getLogger(__name__)


class MissionControl:
    """Gorev kontrol merkezi.

    Tum gorev alt sistemlerini koordine eder,
    tam yasam dongusu yonetimi saglar.

    Attributes:
        _definer: Gorev tanimlayici.
        _planner: Gorev planlayici.
        _phases: Faz kontrolcusu.
        _resources: Kaynak komutani.
        _progress: Ilerleme takipci.
        _situation: Durum odasi.
        _contingency: Olasilik yoneticisi.
        _reporter: Raporlayici.
        _max_concurrent: Maks esli gorev.
        _auto_abort_threshold: Otomatik iptal esigi.
        _require_phase_approval: Faz onay gerekli mi.
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        auto_abort_threshold: float = 0.3,
        require_phase_approval: bool = False,
    ) -> None:
        """Kontrol merkezini baslatir.

        Args:
            max_concurrent: Maks esli gorev.
            auto_abort_threshold: Saglik esigi altinda iptal.
            require_phase_approval: Faz gecislerinde onay.
        """
        self._definer = MissionDefiner()
        self._planner = MissionPlanner()
        self._phases = PhaseController(require_approval=require_phase_approval)
        self._resources = ResourceCommander()
        self._progress = ProgressTracker()
        self._situation = SituationRoom()
        self._contingency = ContingencyManager()
        self._reporter = MissionReporter()

        self._max_concurrent = max_concurrent
        self._auto_abort_threshold = auto_abort_threshold
        self._require_phase_approval = require_phase_approval

        logger.info(
            "MissionControl baslatildi "
            "(max_concurrent=%d, abort_threshold=%.2f)",
            max_concurrent, auto_abort_threshold,
        )

    def create_mission(
        self,
        name: str,
        goal: str,
        description: str = "",
        priority: int = 5,
        timeline_hours: float = 0.0,
        budget: float = 0.0,
    ) -> dict[str, Any]:
        """Gorev olusturur.

        Args:
            name: Gorev adi.
            goal: Hedef.
            description: Aciklama.
            priority: Oncelik.
            timeline_hours: Zaman siniri.
            budget: Butce.

        Returns:
            Olusturma sonucu.
        """
        # Kapasite kontrolu
        active = self._get_active_mission_count()
        if active >= self._max_concurrent:
            return {
                "success": False,
                "reason": f"Maks esli gorev limiti ({self._max_concurrent})",
            }

        mission = self._definer.define_mission(
            name=name,
            goal=goal,
            description=description,
            priority=priority,
            timeline_hours=timeline_hours,
            budget=budget,
        )

        if budget > 0:
            self._resources.set_budget(mission.mission_id, budget)

        self._reporter.add_log(
            mission.mission_id,
            f"Gorev olusturuldu: {name}",
            source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission.mission_id,
            "name": name,
            "state": mission.state.value,
        }

    def plan_mission(
        self,
        mission_id: str,
        phases: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Gorevi planlar.

        Args:
            mission_id: Gorev ID.
            phases: Faz tanimlari listesi.

        Returns:
            Planlama sonucu.
        """
        mission = self._definer.get_mission(mission_id)
        if not mission:
            return {"success": False, "reason": "Gorev bulunamadi"}

        self._definer.activate_mission(mission_id)

        phase_ids = []
        for i, phase_def in enumerate(phases):
            phase = self._planner.create_phase(
                mission_id=mission_id,
                name=phase_def.get("name", f"Phase-{i}"),
                order=phase_def.get("order", i),
                description=phase_def.get("description", ""),
                dependencies=phase_def.get("dependencies"),
                gate_criteria=phase_def.get("gate_criteria"),
                parallel=phase_def.get("parallel", False),
            )
            self._phases.register_phase(phase)
            phase_ids.append(phase.phase_id)

        # Ilerleme takibini baslat
        self._progress.init_mission(mission_id, phase_ids)

        self._reporter.add_log(
            mission_id,
            f"{len(phase_ids)} faz planlandirildi",
            source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "phases": phase_ids,
            "risks": self._planner.identify_risks(mission_id),
        }

    def start_mission(self, mission_id: str) -> dict[str, Any]:
        """Gorevi baslatir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Baslatma sonucu.
        """
        mission = self._definer.get_mission(mission_id)
        if not mission:
            return {"success": False, "reason": "Gorev bulunamadi"}

        if mission.state not in (MissionState.DRAFT, MissionState.PLANNING):
            return {"success": False, "reason": "Gorev baslatilamaz"}

        mission.state = MissionState.ACTIVE
        mission.started_at = datetime.now(timezone.utc)

        # Ilk fazi hazirla ve baslat
        phases = self._planner.get_phases(mission_id)
        started_phases = []
        for phase in phases:
            if not phase.dependencies:
                self._phases.ready_phase(phase.phase_id)
                self._phases.start_phase(phase.phase_id)
                started_phases.append(phase.phase_id)

        self._reporter.add_log(
            mission_id, "Gorev baslatildi", source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "state": mission.state.value,
            "started_phases": started_phases,
        }

    def advance_phase(
        self,
        mission_id: str,
        phase_id: str,
        criteria_results: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Fazi ilerletir.

        Args:
            mission_id: Gorev ID.
            phase_id: Faz ID.
            criteria_results: Gecit kriter sonuclari.

        Returns:
            Ilerleme sonucu.
        """
        phase = self._phases.get_phase(phase_id)
        if not phase:
            return {"success": False, "reason": "Faz bulunamadi"}

        if phase.state == PhaseState.ACTIVE:
            # Incelemeye gonder
            self._phases.submit_for_review(phase_id)
            if criteria_results:
                result = self._phases.gate_review(phase_id, criteria_results)
                if result.get("passed"):
                    self._progress.update_phase_progress(
                        mission_id, phase_id, 1.0,
                    )
                    # Sonraki fazlari baslat
                    self._start_next_phases(mission_id, phase_id)
                return result
            return {"success": True, "state": "review"}

        return {"success": False, "reason": "Faz ilerletilemez"}

    def update_progress(
        self,
        mission_id: str,
        phase_id: str,
        progress: float,
    ) -> bool:
        """Ilerlemeyi gunceller.

        Args:
            mission_id: Gorev ID.
            phase_id: Faz ID.
            progress: Ilerleme (0-1).

        Returns:
            Basarili ise True.
        """
        self._phases.update_progress(phase_id, progress)
        return self._progress.update_phase_progress(
            mission_id, phase_id, progress,
        )

    def handle_failure(
        self,
        mission_id: str,
        phase_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Hatayi isler.

        Args:
            mission_id: Gorev ID.
            phase_id: Faz ID.
            description: Hata aciklamasi.

        Returns:
            Isleme sonucu.
        """
        # Uyari olustur
        self._situation.raise_alert(
            mission_id, description or "Hata tespit edildi",
            AlertSeverity.CRITICAL, source=phase_id,
        )

        # Kurtarma dene
        recovery = self._contingency.initiate_recovery(
            mission_id, description, ["assess", "fix", "verify"],
        )

        # Saglik kontrolu - otomatik iptal
        health = self._calculate_health(mission_id)
        auto_aborted = False
        if health < self._auto_abort_threshold:
            self.abort_mission(mission_id, "Saglik esigi altinda")
            auto_aborted = True

        self._reporter.add_log(
            mission_id,
            f"Hata islendi: {description}",
            level="error",
            source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "recovery": recovery,
            "health": health,
            "auto_aborted": auto_aborted,
        }

    def abort_mission(
        self,
        mission_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Gorevi iptal eder.

        Args:
            mission_id: Gorev ID.
            reason: Iptal nedeni.

        Returns:
            Iptal sonucu.
        """
        mission = self._definer.get_mission(mission_id)
        if not mission:
            return {"success": False, "reason": "Gorev bulunamadi"}

        mission.state = MissionState.ABORTED
        mission.completed_at = datetime.now(timezone.utc)

        # Olasilik yoneticisine bildir
        self._contingency.abort_mission(mission_id, reason)

        # Kaynaklari serbest birak
        resources = self._resources.get_mission_resources(mission_id)
        for agent_id in resources["agents"]:
            self._resources.release_agent(agent_id)
        for tool_id in resources["tools"]:
            self._resources.release_tool(tool_id)

        self._reporter.add_log(
            mission_id,
            f"Gorev iptal edildi: {reason}",
            level="warning",
            source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "reason": reason,
            "state": MissionState.ABORTED.value,
        }

    def complete_mission(
        self,
        mission_id: str,
    ) -> dict[str, Any]:
        """Gorevi tamamlar.

        Args:
            mission_id: Gorev ID.

        Returns:
            Tamamlama sonucu.
        """
        mission = self._definer.get_mission(mission_id)
        if not mission:
            return {"success": False, "reason": "Gorev bulunamadi"}

        mission.state = MissionState.COMPLETED
        mission.completed_at = datetime.now(timezone.utc)

        # Kaynaklari serbest birak
        resources = self._resources.get_mission_resources(mission_id)
        for agent_id in resources["agents"]:
            self._resources.release_agent(agent_id)
        for tool_id in resources["tools"]:
            self._resources.release_tool(tool_id)

        # Gorev-sonrasi rapor
        duration = 0.0
        if mission.started_at:
            duration = (
                mission.completed_at - mission.started_at
            ).total_seconds() / 3600

        self._reporter.generate_post_mission_report(
            mission_id,
            outcome="completed",
            duration_hours=round(duration, 2),
        )

        self._reporter.add_log(
            mission_id, "Gorev tamamlandi", source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "state": MissionState.COMPLETED.value,
            "duration_hours": round(duration, 2),
        }

    def assign_resource(
        self,
        mission_id: str,
        resource_id: str,
        resource_type: str = "agent",
    ) -> dict[str, Any]:
        """Kaynak atar.

        Args:
            mission_id: Gorev ID.
            resource_id: Kaynak ID.
            resource_type: Kaynak tipi.

        Returns:
            Atama sonucu.
        """
        if resource_type == "agent":
            assignment = self._resources.assign_agent(mission_id, resource_id)
        elif resource_type == "tool":
            assignment = self._resources.assign_tool(mission_id, resource_id)
        else:
            return {"success": False, "reason": "Gecersiz kaynak tipi"}

        if not assignment:
            return {"success": False, "reason": "Kaynak atanamadi"}

        return {
            "success": True,
            "assignment_id": assignment.assignment_id,
            "resource_id": resource_id,
            "resource_type": resource_type,
        }

    def get_mission_status(
        self,
        mission_id: str,
    ) -> dict[str, Any]:
        """Gorev durumunu getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Durum bilgileri.
        """
        mission = self._definer.get_mission(mission_id)
        if not mission:
            return {}

        progress = self._progress.get_status(mission_id)
        resources = self._resources.get_mission_resources(mission_id)
        alerts = self._situation.get_alerts(mission_id)
        blockers = self._progress.get_blockers(mission_id)

        return {
            "mission_id": mission_id,
            "name": mission.name,
            "state": mission.state.value,
            "priority": mission.priority,
            "progress": progress,
            "resources": resources,
            "active_alerts": len(alerts),
            "active_blockers": len(blockers),
            "health": self._calculate_health(mission_id),
        }

    def get_snapshot(self) -> MissionSnapshot:
        """Anlik goruntuyu getirir.

        Returns:
            MissionSnapshot nesnesi.
        """
        missions = self._definer.get_all_missions()
        active = [
            m for m in missions
            if m.state in (MissionState.ACTIVE, MissionState.PLANNING)
        ]
        completed = [
            m for m in missions
            if m.state == MissionState.COMPLETED
        ]

        # Ortalama ilerleme
        progresses = [
            self._progress.get_progress(m.mission_id) for m in active
        ]
        avg_progress = (
            sum(progresses) / len(progresses) if progresses else 0.0
        )

        # Toplam faz/milestone
        total_phases = self._planner.total_phases
        active_phases = len(self._phases.get_active_phases())
        total_milestones = self._planner.total_milestones
        completed_milestones = sum(
            1 for ms in self._planner._milestones.values()
            if ms.state == MilestoneState.COMPLETED
        )

        # Saglik
        health_scores = [
            self._calculate_health(m.mission_id) for m in active
        ]
        avg_health = (
            sum(health_scores) / len(health_scores)
            if health_scores else 1.0
        )

        return MissionSnapshot(
            total_missions=len(missions),
            active_missions=len(active),
            completed_missions=len(completed),
            total_phases=total_phases,
            active_phases=active_phases,
            total_milestones=total_milestones,
            completed_milestones=completed_milestones,
            active_alerts=self._situation.active_alert_count,
            avg_progress=round(min(1.0, avg_progress), 3),
            health_score=round(max(0.0, min(1.0, avg_health)), 3),
        )

    def escalate(
        self,
        mission_id: str,
        message: str,
        to: str = "human",
    ) -> dict[str, Any]:
        """Insan eskalasyonu yapar.

        Args:
            mission_id: Gorev ID.
            message: Eskalasyon mesaji.
            to: Hedef.

        Returns:
            Eskalasyon sonucu.
        """
        self._situation.raise_alert(
            mission_id, message,
            AlertSeverity.EMERGENCY, source="escalation",
        )

        self._situation.record_decision(
            mission_id,
            f"Eskalasyon: {message}",
            rationale="Insan mudahalesi gerekli",
            decided_by="mission_control",
        )

        self._reporter.add_log(
            mission_id,
            f"Eskalasyon: {message} -> {to}",
            level="warning",
            source="mission_control",
        )

        return {
            "success": True,
            "mission_id": mission_id,
            "escalated_to": to,
            "message": message,
        }

    def _start_next_phases(
        self,
        mission_id: str,
        completed_phase_id: str,
    ) -> list[str]:
        """Sonraki fazlari baslatir."""
        started = []
        phases = self._planner.get_phases(mission_id)

        for phase in phases:
            if phase.state != PhaseState.PENDING:
                continue
            if completed_phase_id not in phase.dependencies:
                continue
            if self._planner.is_phase_ready(phase.phase_id):
                self._phases.ready_phase(phase.phase_id)
                self._phases.start_phase(phase.phase_id)
                started.append(phase.phase_id)

        return started

    def _calculate_health(self, mission_id: str) -> float:
        """Gorev sagligini hesaplar."""
        health = 1.0

        # Aktif uyarilari etkile
        alerts = self._situation.get_alerts(mission_id)
        critical = sum(
            1 for a in alerts
            if a.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY)
        )
        health -= critical * 0.2

        # Engelleyicileri etkile
        blockers = self._progress.get_blockers(mission_id)
        health -= len(blockers) * 0.1

        # Aktif olasilik planlarini etkile
        active_plans = self._contingency.get_plans(
            mission_id, active_only=True,
        )
        health -= len(active_plans) * 0.05

        return max(0.0, min(1.0, health))

    def _get_active_mission_count(self) -> int:
        """Aktif gorev sayisini hesaplar."""
        return sum(
            1 for m in self._definer.get_all_missions()
            if m.state in (MissionState.ACTIVE, MissionState.PLANNING)
        )

    # Alt sistem erisimi
    @property
    def definer(self) -> MissionDefiner:
        """Gorev tanimlayici."""
        return self._definer

    @property
    def planner(self) -> MissionPlanner:
        """Gorev planlayici."""
        return self._planner

    @property
    def phases(self) -> PhaseController:
        """Faz kontrolcusu."""
        return self._phases

    @property
    def resources(self) -> ResourceCommander:
        """Kaynak komutani."""
        return self._resources

    @property
    def progress(self) -> ProgressTracker:
        """Ilerleme takipci."""
        return self._progress

    @property
    def situation(self) -> SituationRoom:
        """Durum odasi."""
        return self._situation

    @property
    def contingency(self) -> ContingencyManager:
        """Olasilik yoneticisi."""
        return self._contingency

    @property
    def reporter(self) -> MissionReporter:
        """Raporlayici."""
        return self._reporter
