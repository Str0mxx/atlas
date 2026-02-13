"""ATLAS Evrim Orkestratoru modulu.

Surekli izleme dongusu: Observe -> Analyze -> Plan ->
Implement -> Test -> Deploy. Onay kapilari, gunluk/haftalik
evrim dongusu ve acil durdurma.
"""

import logging
import time
from typing import Any

from app.core.evolution.approval_manager import ApprovalManager
from app.core.evolution.code_evolver import CodeEvolver
from app.core.evolution.experiment_runner import ExperimentRunner
from app.core.evolution.improvement_planner import ImprovementPlanner
from app.core.evolution.knowledge_learner import KnowledgeLearner
from app.core.evolution.performance_monitor import PerformanceMonitor
from app.core.evolution.safety_guardian import SafetyGuardian
from app.core.evolution.weakness_detector import WeaknessDetector
from app.models.evolution import (
    ApprovalStatus,
    EvolutionCycle,
    EvolutionCycleType,
    EvolutionPhase,
)

logger = logging.getLogger(__name__)


class EvolutionController:
    """Evrim orkestratoru.

    Tum evrim bilesenlerini koordine eder:
    Observe -> Analyze -> Plan -> Implement -> Test -> Deploy.

    Attributes:
        _monitor: Performans izleme.
        _detector: Zayiflik tespiti.
        _planner: Iyilestirme planlama.
        _evolver: Kod evrimi.
        _guardian: Guvenlik koruma.
        _runner: Deney yonetimi.
        _approvals: Onay yonetimi.
        _learner: Bilgi ogrenme.
        _cycles: Evrim dongu gecmisi.
        _paused: Durduruldu mu.
    """

    def __init__(
        self,
        auto_approve_minor: bool = True,
        max_daily_changes: int = 10,
        cycle_hours: int = 24,
    ) -> None:
        """Evrim orkestratörunu baslatir.

        Args:
            auto_approve_minor: Minor otomatik onay.
            max_daily_changes: Gunluk max otomatik degisiklik.
            cycle_hours: Dongu suresi (saat).
        """
        self._monitor = PerformanceMonitor()
        self._detector = WeaknessDetector()
        self._planner = ImprovementPlanner()
        self._evolver = CodeEvolver()
        self._guardian = SafetyGuardian(auto_approve_minor=auto_approve_minor)
        self._runner = ExperimentRunner()
        self._approvals = ApprovalManager()
        self._learner = KnowledgeLearner()

        self._max_daily_changes = max_daily_changes
        self._cycle_hours = cycle_hours
        self._daily_auto_count = 0
        self._paused = False
        self._cycles: list[EvolutionCycle] = []

        logger.info(
            "EvolutionController baslatildi (auto_minor=%s, daily_max=%d, cycle=%dh)",
            auto_approve_minor, max_daily_changes, cycle_hours,
        )

    def run_cycle(self, cycle_type: EvolutionCycleType = EvolutionCycleType.DAILY) -> EvolutionCycle:
        """Tam evrim dongusu calistirir.

        Args:
            cycle_type: Dongu tipi.

        Returns:
            EvolutionCycle nesnesi.
        """
        cycle = EvolutionCycle(cycle_type=cycle_type)

        if self._paused:
            cycle.phase = EvolutionPhase.PAUSED
            cycle.paused = True
            self._cycles.append(cycle)
            logger.warning("Evrim durdurulmus, dongu atlanıyor")
            return cycle

        # 1. OBSERVE - Gozlem
        cycle.phase = EvolutionPhase.OBSERVING
        metrics = self._monitor.get_all_metrics()
        error_patterns = self._monitor.detect_error_patterns()

        # 2. ANALYZE - Analiz
        cycle.phase = EvolutionPhase.ANALYZING
        weaknesses = self._detector.run_full_analysis(
            metrics=metrics,
            error_patterns=error_patterns,
        )
        cycle.weaknesses_found = len(weaknesses)

        if not weaknesses:
            cycle.phase = EvolutionPhase.COMPLETE
            self._cycles.append(cycle)
            logger.info("Zayiflik bulunamadi, dongu tamamlandi")
            return cycle

        # 3. PLAN - Planlama
        cycle.phase = EvolutionPhase.PLANNING
        plans = self._planner.create_plans_from_weaknesses(weaknesses)
        cycle.improvements_planned = len(plans)

        # 4. IMPLEMENT - Uygulama
        cycle.phase = EvolutionPhase.IMPLEMENTING
        changes = self._evolver.generate_changes(plans)

        # 5. TEST - Test
        cycle.phase = EvolutionPhase.TESTING
        for change in changes:
            experiment = self._runner.run_sandbox_test(change)

            if experiment.status.value != "passed":
                continue

            # 6. APPROVE - Onay
            cycle.phase = EvolutionPhase.APPROVING
            safety = self._guardian.check_safety(change)

            if self._guardian.can_auto_approve(safety) and self._daily_auto_count < self._max_daily_changes:
                self._evolver.apply_change(change)
                self._daily_auto_count += 1
                cycle.changes_auto_approved += 1
                cycle.changes_applied += 1

                # Ogren
                self._learner.learn_from_fix(change, experiment)
            elif safety.requires_approval:
                req = self._approvals.queue_change(change)
                # Simule: beklemeye alinir
                logger.info("Onay bekleniyor: %s", req.title)
            else:
                self._evolver.apply_change(change)
                cycle.changes_applied += 1
                self._learner.learn_from_fix(change, experiment)

        # 7. DEPLOY
        cycle.phase = EvolutionPhase.DEPLOYING

        # 8. Complete
        cycle.phase = EvolutionPhase.COMPLETE
        self._cycles.append(cycle)

        logger.info(
            "Evrim dongusu tamamlandi: %d zayiflik, %d plan, %d uygulama",
            cycle.weaknesses_found, cycle.improvements_planned, cycle.changes_applied,
        )
        return cycle

    def pause(self) -> None:
        """Evrimi durdurur."""
        self._paused = True
        logger.warning("Evrim DURDURULDU")

    def resume(self) -> None:
        """Evrimi devam ettirir."""
        self._paused = False
        self._daily_auto_count = 0
        logger.info("Evrim devam ediyor")

    def emergency_stop(self) -> int:
        """Acil durdurma - tum degisiklikleri geri alir.

        Returns:
            Geri alinan degisiklik sayisi.
        """
        self._paused = True
        count = self._evolver.rollback_all()
        logger.warning("ACIL DURDURMA: %d degisiklik geri alindi", count)
        return count

    def process_approval(self, request_id: str, approved: bool, responder: str = "admin") -> bool:
        """Onay isler.

        Args:
            request_id: Istek ID.
            approved: Onaylandi mi.
            responder: Onaylayan kisi.

        Returns:
            Basarili mi.
        """
        if approved:
            result = self._approvals.approve(request_id, responder)
            if result:
                request = self._approvals.get_request(request_id)
                if request:
                    change = self._evolver.get_change(request.change_id)
                    if change:
                        self._evolver.apply_change(change)
            return result
        return self._approvals.reject(request_id, responder)

    def reset_daily_counter(self) -> None:
        """Gunluk sayaci sifirlar."""
        self._daily_auto_count = 0

    def get_status(self) -> dict[str, Any]:
        """Sistem durumunu getirir.

        Returns:
            Durum sozlugu.
        """
        return {
            "paused": self._paused,
            "daily_auto_count": self._daily_auto_count,
            "max_daily_changes": self._max_daily_changes,
            "cycle_hours": self._cycle_hours,
            "total_cycles": len(self._cycles),
            "metrics_tracked": self._monitor.metric_count,
            "weaknesses_found": self._detector.weakness_count,
            "plans_created": self._planner.plan_count,
            "changes_made": self._evolver.change_count,
            "experiments_run": self._runner.experiment_count,
            "pending_approvals": self._approvals.pending_count,
            "patterns_learned": self._learner.pattern_count,
        }

    @property
    def monitor(self) -> PerformanceMonitor:
        """Performans izleyici."""
        return self._monitor

    @property
    def detector(self) -> WeaknessDetector:
        """Zayiflik tespitcisi."""
        return self._detector

    @property
    def planner(self) -> ImprovementPlanner:
        """Iyilestirme planlayici."""
        return self._planner

    @property
    def evolver(self) -> CodeEvolver:
        """Kod evrimcisi."""
        return self._evolver

    @property
    def guardian(self) -> SafetyGuardian:
        """Guvenlik koruyucu."""
        return self._guardian

    @property
    def runner(self) -> ExperimentRunner:
        """Deney yoneticisi."""
        return self._runner

    @property
    def approvals(self) -> ApprovalManager:
        """Onay yoneticisi."""
        return self._approvals

    @property
    def learner(self) -> KnowledgeLearner:
        """Bilgi ogrenici."""
        return self._learner

    @property
    def is_paused(self) -> bool:
        """Durduruldu mu."""
        return self._paused

    @property
    def cycle_count(self) -> int:
        """Dongu sayisi."""
        return len(self._cycles)

    @property
    def cycles(self) -> list[EvolutionCycle]:
        """Dongu gecmisi."""
        return list(self._cycles)
