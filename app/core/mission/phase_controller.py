"""ATLAS Faz Kontrolcu modulu.

Faz gecisleri, gecit incelemeleri, git/gitme kararlari,
faz geri alma ve paralel faz yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.mission import PhaseDefinition, PhaseState

logger = logging.getLogger(__name__)

# Gecerli durum gecisleri
_VALID_TRANSITIONS: dict[PhaseState, list[PhaseState]] = {
    PhaseState.PENDING: [PhaseState.READY],
    PhaseState.READY: [PhaseState.ACTIVE],
    PhaseState.ACTIVE: [PhaseState.REVIEW, PhaseState.FAILED],
    PhaseState.REVIEW: [PhaseState.PASSED, PhaseState.FAILED, PhaseState.ACTIVE],
    PhaseState.FAILED: [PhaseState.ROLLED_BACK, PhaseState.ACTIVE],
    PhaseState.PASSED: [],
    PhaseState.SKIPPED: [],
    PhaseState.ROLLED_BACK: [PhaseState.PENDING],
}


class PhaseController:
    """Faz kontrolcusu.

    Faz yasam dongusunu yonetir, gecit incelemelerini
    yapar, paralel fazlari koordine eder.

    Attributes:
        _phases: Kontrol edilen fazlar.
        _gate_results: Gecit inceleme sonuclari.
        _require_approval: Faz gecislerinde onay gerekli mi.
    """

    def __init__(self, require_approval: bool = False) -> None:
        """Faz kontrolcuyu baslatir.

        Args:
            require_approval: Gecislerde onay gerekli mi.
        """
        self._phases: dict[str, PhaseDefinition] = {}
        self._gate_results: dict[str, dict[str, Any]] = {}
        self._require_approval = require_approval

        logger.info(
            "PhaseController baslatildi (approval=%s)",
            require_approval,
        )

    def register_phase(self, phase: PhaseDefinition) -> None:
        """Fazi kaydeder.

        Args:
            phase: Faz tanimi.
        """
        self._phases[phase.phase_id] = phase

    def transition(
        self,
        phase_id: str,
        target_state: PhaseState,
    ) -> bool:
        """Faz durumunu degistirir.

        Args:
            phase_id: Faz ID.
            target_state: Hedef durum.

        Returns:
            Basarili ise True.
        """
        phase = self._phases.get(phase_id)
        if not phase:
            return False

        valid = _VALID_TRANSITIONS.get(phase.state, [])
        if target_state not in valid:
            return False

        old_state = phase.state
        phase.state = target_state

        if target_state == PhaseState.ACTIVE and not phase.started_at:
            phase.started_at = datetime.now(timezone.utc)
        elif target_state in (PhaseState.PASSED, PhaseState.FAILED):
            phase.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Faz gecisi: %s %s -> %s",
            phase_id, old_state.value, target_state.value,
        )
        return True

    def ready_phase(self, phase_id: str) -> bool:
        """Fazi hazir yapar.

        Args:
            phase_id: Faz ID.

        Returns:
            Basarili ise True.
        """
        return self.transition(phase_id, PhaseState.READY)

    def start_phase(self, phase_id: str) -> bool:
        """Fazi baslatir.

        Args:
            phase_id: Faz ID.

        Returns:
            Basarili ise True.
        """
        return self.transition(phase_id, PhaseState.ACTIVE)

    def submit_for_review(self, phase_id: str) -> bool:
        """Fazi incelemeye gonderir.

        Args:
            phase_id: Faz ID.

        Returns:
            Basarili ise True.
        """
        return self.transition(phase_id, PhaseState.REVIEW)

    def gate_review(
        self,
        phase_id: str,
        criteria_results: dict[str, bool],
    ) -> dict[str, Any]:
        """Gecit incelemesi yapar.

        Args:
            phase_id: Faz ID.
            criteria_results: Kriter -> sonuc eslesmesi.

        Returns:
            Inceleme sonucu.
        """
        phase = self._phases.get(phase_id)
        if not phase or phase.state != PhaseState.REVIEW:
            return {"success": False, "reason": "Faz inceleme durumunda degil"}

        passed_count = sum(1 for v in criteria_results.values() if v)
        total = len(criteria_results)
        all_passed = passed_count == total and total > 0

        result = {
            "success": True,
            "phase_id": phase_id,
            "passed": all_passed,
            "criteria_met": passed_count,
            "criteria_total": total,
            "go_decision": all_passed,
        }

        self._gate_results[phase_id] = result

        if all_passed:
            self.transition(phase_id, PhaseState.PASSED)
            phase.progress = 1.0
        else:
            # Basarisiz -> tekrar aktif (duzeltme icin)
            self.transition(phase_id, PhaseState.ACTIVE)

        return result

    def go_no_go(self, phase_id: str) -> bool:
        """Git/gitme karari verir.

        Args:
            phase_id: Faz ID.

        Returns:
            Git ise True.
        """
        result = self._gate_results.get(phase_id)
        if not result:
            return False
        return result.get("go_decision", False)

    def rollback_phase(self, phase_id: str) -> bool:
        """Fazi geri alir.

        Args:
            phase_id: Faz ID.

        Returns:
            Basarili ise True.
        """
        phase = self._phases.get(phase_id)
        if not phase:
            return False

        if phase.state == PhaseState.FAILED:
            if self.transition(phase_id, PhaseState.ROLLED_BACK):
                phase.progress = 0.0
                phase.completed_at = None
                return True

        return False

    def skip_phase(self, phase_id: str) -> bool:
        """Fazi atlar.

        Args:
            phase_id: Faz ID.

        Returns:
            Basarili ise True.
        """
        phase = self._phases.get(phase_id)
        if not phase or phase.state not in (
            PhaseState.PENDING, PhaseState.READY,
        ):
            return False

        phase.state = PhaseState.SKIPPED
        return True

    def update_progress(
        self,
        phase_id: str,
        progress: float,
    ) -> bool:
        """Faz ilerlemesini gunceller.

        Args:
            phase_id: Faz ID.
            progress: Ilerleme (0-1).

        Returns:
            Basarili ise True.
        """
        phase = self._phases.get(phase_id)
        if not phase or phase.state != PhaseState.ACTIVE:
            return False

        phase.progress = max(0.0, min(1.0, progress))
        return True

    def get_parallel_phases(
        self,
        mission_id: str,
    ) -> list[PhaseDefinition]:
        """Paralel calisabilir fazlari getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Paralel faz listesi.
        """
        return [
            p for p in self._phases.values()
            if p.mission_id == mission_id and p.parallel
        ]

    def get_active_phases(
        self,
        mission_id: str = "",
    ) -> list[PhaseDefinition]:
        """Aktif fazlari getirir.

        Args:
            mission_id: Gorev filtresi.

        Returns:
            Aktif faz listesi.
        """
        phases = [
            p for p in self._phases.values()
            if p.state == PhaseState.ACTIVE
        ]
        if mission_id:
            phases = [p for p in phases if p.mission_id == mission_id]
        return phases

    def get_phase(self, phase_id: str) -> PhaseDefinition | None:
        """Fazi getirir.

        Args:
            phase_id: Faz ID.

        Returns:
            PhaseDefinition veya None.
        """
        return self._phases.get(phase_id)

    @property
    def total_phases(self) -> int:
        """Toplam faz sayisi."""
        return len(self._phases)

    @property
    def passed_count(self) -> int:
        """Gecen faz sayisi."""
        return sum(
            1 for p in self._phases.values()
            if p.state == PhaseState.PASSED
        )
