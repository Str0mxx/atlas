"""ATLAS Ilerleme Takipci modulu.

Gercek zamanli durum, kilometre tasi takibi,
burndown grafigi, ETA hesaplama ve engelleyici tespit.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.mission import MilestoneState, PhaseState

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Ilerleme takipci.

    Gorev ilerlemesini izler, ETA hesaplar,
    engelleyicileri tespit eder.

    Attributes:
        _mission_progress: Gorev ilerleme verileri.
        _phase_progress: Faz ilerleme verileri.
        _milestones: Kilometre tasi durumu.
        _blockers: Engelleyiciler.
        _history: Ilerleme gecmisi.
    """

    def __init__(self) -> None:
        """Ilerleme takipciyi baslatir."""
        self._mission_progress: dict[str, float] = {}
        self._phase_progress: dict[str, dict[str, float]] = {}
        self._milestones: dict[str, dict[str, MilestoneState]] = {}
        self._blockers: dict[str, list[dict[str, Any]]] = {}
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._start_times: dict[str, datetime] = {}

        logger.info("ProgressTracker baslatildi")

    def init_mission(
        self,
        mission_id: str,
        phase_ids: list[str],
    ) -> None:
        """Gorev takibini baslatir.

        Args:
            mission_id: Gorev ID.
            phase_ids: Faz ID'leri.
        """
        self._mission_progress[mission_id] = 0.0
        self._phase_progress[mission_id] = {pid: 0.0 for pid in phase_ids}
        self._milestones.setdefault(mission_id, {})
        self._blockers[mission_id] = []
        self._history[mission_id] = []
        self._start_times[mission_id] = datetime.now(timezone.utc)

    def update_phase_progress(
        self,
        mission_id: str,
        phase_id: str,
        progress: float,
    ) -> bool:
        """Faz ilerlemesini gunceller.

        Args:
            mission_id: Gorev ID.
            phase_id: Faz ID.
            progress: Ilerleme (0-1).

        Returns:
            Basarili ise True.
        """
        phases = self._phase_progress.get(mission_id)
        if not phases or phase_id not in phases:
            return False

        progress = max(0.0, min(1.0, progress))
        phases[phase_id] = progress

        # Gorev ilerlemesini hesapla
        total = sum(phases.values())
        self._mission_progress[mission_id] = round(
            total / len(phases), 3,
        )

        # Gecmise kaydet
        self._history.setdefault(mission_id, []).append({
            "phase_id": phase_id,
            "progress": progress,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return True

    def add_milestone(
        self,
        mission_id: str,
        milestone_id: str,
    ) -> None:
        """Kilometre tasi ekler.

        Args:
            mission_id: Gorev ID.
            milestone_id: Kilometre tasi ID.
        """
        self._milestones.setdefault(mission_id, {})[milestone_id] = (
            MilestoneState.PENDING
        )

    def complete_milestone(
        self,
        mission_id: str,
        milestone_id: str,
    ) -> bool:
        """Kilometre tasini tamamlar.

        Args:
            mission_id: Gorev ID.
            milestone_id: Kilometre tasi ID.

        Returns:
            Basarili ise True.
        """
        ms = self._milestones.get(mission_id, {})
        if milestone_id not in ms:
            return False

        ms[milestone_id] = MilestoneState.COMPLETED
        return True

    def add_blocker(
        self,
        mission_id: str,
        description: str,
        phase_id: str = "",
        severity: str = "medium",
    ) -> str:
        """Engelleyici ekler.

        Args:
            mission_id: Gorev ID.
            description: Aciklama.
            phase_id: Ilgili faz.
            severity: Siddet.

        Returns:
            Engelleyici ID.
        """
        blocker_id = f"blk-{len(self._blockers.get(mission_id, []))}"
        blocker = {
            "blocker_id": blocker_id,
            "description": description,
            "phase_id": phase_id,
            "severity": severity,
            "resolved": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._blockers.setdefault(mission_id, []).append(blocker)
        return blocker_id

    def resolve_blocker(
        self,
        mission_id: str,
        blocker_id: str,
    ) -> bool:
        """Engelleyiciyi cozer.

        Args:
            mission_id: Gorev ID.
            blocker_id: Engelleyici ID.

        Returns:
            Basarili ise True.
        """
        blockers = self._blockers.get(mission_id, [])
        for b in blockers:
            if b["blocker_id"] == blocker_id and not b["resolved"]:
                b["resolved"] = True
                return True
        return False

    def get_blockers(
        self,
        mission_id: str,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Engelleyicileri getirir.

        Args:
            mission_id: Gorev ID.
            active_only: Sadece aktif olanlar.

        Returns:
            Engelleyici listesi.
        """
        blockers = self._blockers.get(mission_id, [])
        if active_only:
            return [b for b in blockers if not b["resolved"]]
        return list(blockers)

    def get_progress(self, mission_id: str) -> float:
        """Gorev ilerlemesini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Ilerleme (0-1).
        """
        return self._mission_progress.get(mission_id, 0.0)

    def get_phase_progress(
        self,
        mission_id: str,
    ) -> dict[str, float]:
        """Faz ilerlemelerini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Faz ID -> ilerleme.
        """
        return dict(self._phase_progress.get(mission_id, {}))

    def get_burndown(self, mission_id: str) -> list[dict[str, Any]]:
        """Burndown verilerini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Zaman serisi veri.
        """
        return list(self._history.get(mission_id, []))

    def calculate_eta(
        self,
        mission_id: str,
    ) -> float:
        """Tahmini tamamlanma suresi hesaplar (saat).

        Args:
            mission_id: Gorev ID.

        Returns:
            Kalan saat tahmini (0 = hesaplanamadi).
        """
        progress = self._mission_progress.get(mission_id, 0.0)
        start = self._start_times.get(mission_id)

        if not start or progress <= 0:
            return 0.0

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() / 3600
        if progress >= 1.0:
            return 0.0

        # Dogrusal tahmin
        total_estimated = elapsed / progress
        remaining = total_estimated - elapsed
        return round(max(0.0, remaining), 2)

    def get_milestone_status(
        self,
        mission_id: str,
    ) -> dict[str, Any]:
        """Kilometre tasi durumunu getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Durum bilgileri.
        """
        ms = self._milestones.get(mission_id, {})
        total = len(ms)
        completed = sum(
            1 for s in ms.values()
            if s == MilestoneState.COMPLETED
        )

        return {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "completion_rate": round(completed / total, 3) if total > 0 else 0.0,
        }

    def get_status(self, mission_id: str) -> dict[str, Any]:
        """Tam durum getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Durum sozlugu.
        """
        return {
            "mission_id": mission_id,
            "progress": self.get_progress(mission_id),
            "phases": self.get_phase_progress(mission_id),
            "milestones": self.get_milestone_status(mission_id),
            "active_blockers": len(self.get_blockers(mission_id)),
            "eta_hours": self.calculate_eta(mission_id),
        }

    @property
    def tracked_missions(self) -> int:
        """Takip edilen gorev sayisi."""
        return len(self._mission_progress)
