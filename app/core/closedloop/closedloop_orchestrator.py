"""ATLAS Kapali Dongu Orkestrator modulu.

Tam dongu yonetimi, aksiyon-sonuc-ogrenme-iyilestirme,
sistem entegrasyonu, raporlama, analitik.
"""

import logging
import time
from typing import Any

from app.core.closedloop.action_tracker import (
    ActionTracker,
)
from app.core.closedloop.causality_analyzer import (
    CausalityAnalyzer,
)
from app.core.closedloop.experiment_tracker import (
    ClosedLoopExperimentTracker,
)
from app.core.closedloop.feedback_collector import (
    FeedbackCollector,
)
from app.core.closedloop.improvement_engine import (
    ImprovementEngine,
)
from app.core.closedloop.learning_integrator import (
    LearningIntegrator,
)
from app.core.closedloop.loop_monitor import (
    LoopMonitor,
)
from app.core.closedloop.outcome_detector import (
    OutcomeDetector,
)

logger = logging.getLogger(__name__)


class ClosedLoopOrchestrator:
    """Kapali dongu orkestrator.

    Tum kapali dongu bilesenleri koordine eder.

    Attributes:
        actions: Aksiyon takipcisi.
        outcomes: Sonuc tespitcisi.
        feedback: Geri bildirim toplayici.
        causality: Nedensellik analizcisi.
        learning: Ogrenme entegratoru.
        monitor: Dongu izleyici.
        experiments: Deney takipcisi.
        improvements: Iyilestirme motoru.
    """

    def __init__(
        self,
        detection_timeout: int = 300,
        min_confidence: float = 0.5,
        experiment_duration_hours: int = 24,
        auto_apply_learnings: bool = False,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            detection_timeout: Tespit zaman asimi.
            min_confidence: Minimum guven esigi.
            experiment_duration_hours: Deney suresi.
            auto_apply_learnings: Otomatik ogrenme.
        """
        self.actions = ActionTracker()
        self.outcomes = OutcomeDetector(
            detection_timeout=detection_timeout,
        )
        self.feedback = FeedbackCollector()
        self.causality = CausalityAnalyzer(
            min_confidence=min_confidence,
        )
        self.learning = LearningIntegrator(
            min_confidence=min_confidence,
        )
        self.monitor = LoopMonitor()
        self.experiments = (
            ClosedLoopExperimentTracker(
                default_duration_hours=(
                    experiment_duration_hours
                ),
            )
        )
        self.improvements = ImprovementEngine(
            auto_apply=auto_apply_learnings,
        )

        self._min_confidence = min_confidence
        self._stats = {
            "loops_executed": 0,
            "full_loops": 0,
        }

        logger.info(
            "ClosedLoopOrchestrator baslatildi",
        )

    def execute_action(
        self,
        action_id: str,
        name: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aksiyonu calistirir ve takip baslatir.

        Args:
            action_id: Aksiyon ID.
            name: Aksiyon adi.
            context: Baglam.

        Returns:
            Calistirma bilgisi.
        """
        # 1. Kaydet
        self.actions.register_action(
            action_id, name, context,
        )

        # 2. Baslat
        self.actions.start_action(action_id)

        self._stats["loops_executed"] += 1

        return {
            "action_id": action_id,
            "name": name,
            "status": "running",
            "loop_started": True,
        }

    def record_outcome(
        self,
        action_id: str,
        outcome_type: str,
        metrics: dict[str, Any] | None = None,
        success: bool | None = None,
    ) -> dict[str, Any]:
        """Sonucu kaydeder ve analiz baslatir.

        Args:
            action_id: Aksiyon ID.
            outcome_type: Sonuc tipi.
            metrics: Metrikler.
            success: Basarili mi.

        Returns:
            Kayit bilgisi.
        """
        # Aksiyonu tamamla
        if success is not None:
            if success:
                self.actions.complete_action(
                    action_id,
                )
            else:
                self.actions.fail_action(
                    action_id,
                )

        # Sonuc tespit
        outcome = self.outcomes.detect_outcome(
            action_id,
            outcome_type=outcome_type,
            metrics=metrics,
        )

        # Nedensellik baglama
        self.causality.link_action_outcome(
            action_id,
            outcome["outcome_id"],
            confidence=outcome.get(
                "confidence", 0.5,
            ),
        )

        return {
            "action_id": action_id,
            "outcome_id": outcome["outcome_id"],
            "outcome_type": outcome_type,
            "recorded": True,
        }

    def collect_and_learn(
        self,
        action_id: str,
        rating: float | None = None,
        outcome_type: str = "unknown",
    ) -> dict[str, Any]:
        """Geri bildirim toplar ve ogrenir.

        Args:
            action_id: Aksiyon ID.
            rating: Puanlama.
            outcome_type: Sonuc tipi.

        Returns:
            Ogrenme bilgisi.
        """
        # Geri bildirim
        if rating is not None:
            self.feedback.collect_explicit(
                action_id, rating,
            )

        # Nedensel cikarim
        outcomes = self.outcomes.get_outcomes(
            action_id,
        )
        inference = self.causality.infer_causality(
            action_id, outcomes,
        )

        confidence = inference.get(
            "confidence", 0.0,
        )

        # Ogrenme kaydi
        learning_result = (
            self.learning.record_learning(
                action_id,
                outcome_type=outcome_type,
                confidence=confidence,
            )
        )

        # Dongu izleme
        stages = {
            "action": True,
            "outcome": len(outcomes) > 0,
            "feedback": rating is not None,
            "learn": True,
            "improve": False,
        }
        loop_status = self.monitor.track_loop(
            action_id, stages,
        )

        return {
            "action_id": action_id,
            "confidence": confidence,
            "causal": inference.get("causal", False),
            "loop_completion": loop_status[
                "completion"
            ],
            "learned": True,
        }

    def full_loop(
        self,
        action_id: str,
        name: str,
        outcome_type: str,
        rating: float | None = None,
        context: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tam dongu calistirir.

        Args:
            action_id: Aksiyon ID.
            name: Aksiyon adi.
            outcome_type: Sonuc tipi.
            rating: Puanlama.
            context: Baglam.
            metrics: Metrikler.

        Returns:
            Dongu sonucu.
        """
        # 1. Aksiyon
        self.execute_action(
            action_id, name, context,
        )

        # 2. Sonuc
        success = outcome_type == "success"
        outcome = self.record_outcome(
            action_id,
            outcome_type,
            metrics=metrics,
            success=success,
        )

        # 3. Geri bildirim + Ogrenme
        learn = self.collect_and_learn(
            action_id,
            rating=rating,
            outcome_type=outcome_type,
        )

        # 4. Iyilestirme (basarisiz ise)
        improvement_id = None
        if outcome_type == "failure":
            imp_id = f"imp_{action_id}"
            self.improvements.identify_improvement(
                imp_id,
                description=(
                    f"Fix issue from action {name}"
                ),
                source_action=action_id,
                priority="high",
            )
            improvement_id = imp_id

        # Tam dongu izleme
        # Basarili sonuclarda iyilestirme gerekmez
        improve_done = (
            outcome_type == "success"
            or improvement_id is not None
        )
        stages = {
            "action": True,
            "outcome": True,
            "feedback": rating is not None,
            "learn": True,
            "improve": improve_done,
        }
        self.monitor.track_loop(
            action_id, stages,
        )

        all_complete = all(stages.values())
        if all_complete:
            self._stats["full_loops"] += 1

        return {
            "action_id": action_id,
            "outcome_type": outcome_type,
            "outcome_id": outcome["outcome_id"],
            "confidence": learn["confidence"],
            "loop_complete": all_complete,
            "improvement_id": improvement_id,
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        health = self.monitor.check_health()

        return {
            "loops_executed": (
                self._stats["loops_executed"]
            ),
            "full_loops": (
                self._stats["full_loops"]
            ),
            "actions": self.actions.action_count,
            "outcomes": (
                self.outcomes.outcome_count
            ),
            "feedback": (
                self.feedback.feedback_count
            ),
            "causal_links": (
                self.causality.link_count
            ),
            "learnings": (
                self.learning.learning_count
            ),
            "improvements": (
                self.improvements.improvement_count
            ),
            "experiments": (
                self.experiments.experiment_count
            ),
            "health": health,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "loop_health": (
                self.monitor.check_health()
            ),
            "completion_rate": (
                self.monitor.get_completion_rate()
            ),
            "gaps": (
                self.monitor.get_gaps(limit=10)
            ),
            "top_improvements": (
                self.improvements.prioritize(
                    limit=5,
                )
            ),
            "active_experiments": (
                self.experiments.list_experiments(
                    status="running",
                )
            ),
            "knowledge_count": (
                self.learning.knowledge_count
            ),
            "pattern_count": (
                self.learning.pattern_count
            ),
        }

    @property
    def total_loops(self) -> int:
        """Toplam dongu sayisi."""
        return self._stats["loops_executed"]

    @property
    def full_loop_count(self) -> int:
        """Tam dongu sayisi."""
        return self._stats["full_loops"]
