"""ATLAS Guven Orkestrator modulu.

Tam guven pipeline, karar yonlendirme,
guven yonetimi, raporlama, analitik.
"""

import logging
import time
from typing import Any

from app.core.confidence.accuracy_tracker import (
    AccuracyTracker,
)
from app.core.confidence.autonomy_controller import (
    ConfidenceAutonomyController,
)
from app.core.confidence.calibration_engine import (
    CalibrationEngine,
)
from app.core.confidence.confidence_calculator import (
    ConfidenceCalculator,
)
from app.core.confidence.escalation_router import (
    ConfidenceEscalationRouter,
)
from app.core.confidence.human_feedback import (
    HumanFeedbackHandler,
)
from app.core.confidence.threshold_manager import (
    ThresholdManager,
)
from app.core.confidence.trust_evolver import (
    TrustEvolver,
)

logger = logging.getLogger(__name__)


class ConfidenceOrchestrator:
    """Guven orkestrator.

    Tum guven bilesenleri koordine eder.

    Attributes:
        calculator: Guven hesaplayici.
        thresholds: Esik yoneticisi.
        autonomy: Otonomi kontrolcusu.
        accuracy: Dogruluk takipcisi.
        trust: Guven evrimcisi.
        escalation: Eskalasyon yonlendirici.
        feedback: Insan geri bildirimi.
        calibration: Kalibrasyon motoru.
    """

    def __init__(
        self,
        auto_execute_threshold: float = 0.8,
        ask_human_threshold: float = 0.3,
        trust_decay_rate: float = 0.01,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            auto_execute_threshold: Otomatik esik.
            ask_human_threshold: Insana sorma esigi.
            trust_decay_rate: Guven azalma orani.
        """
        self.calculator = ConfidenceCalculator()
        self.thresholds = ThresholdManager(
            auto_execute=auto_execute_threshold,
            ask_human=ask_human_threshold,
        )
        self.autonomy = (
            ConfidenceAutonomyController(
                auto_threshold=(
                    auto_execute_threshold
                ),
                ask_threshold=ask_human_threshold,
            )
        )
        self.accuracy = AccuracyTracker()
        self.trust = TrustEvolver(
            decay_rate=trust_decay_rate,
        )
        self.escalation = (
            ConfidenceEscalationRouter()
        )
        self.feedback = HumanFeedbackHandler()
        self.calibration = CalibrationEngine()

        self._stats = {
            "decisions": 0,
            "auto_executed": 0,
            "escalated": 0,
        }

        logger.info(
            "ConfidenceOrchestrator baslatildi",
        )

    def make_decision(
        self,
        action_id: str,
        factors: dict[str, float],
        domain: str = "",
        action_type: str = "",
    ) -> dict[str, Any]:
        """Guven tabanli karar verir.

        Args:
            action_id: Aksiyon ID.
            factors: Guven faktorleri.
            domain: Alan.
            action_type: Aksiyon tipi.

        Returns:
            Karar bilgisi.
        """
        # 1. Guven hesapla
        calc = self.calculator.calculate(
            factors, domain=domain,
        )
        raw_score = calc["score"]

        # 2. Kalibre et
        score = self.calibration.calibrate_score(
            raw_score,
        )

        # 3. Guven seviyesi ile birlestir
        trust_info = self.trust.get_trust(domain)
        trust_score = trust_info["score"]
        adjusted_score = (
            score * 0.7 + trust_score * 0.3
        )
        adjusted_score = round(
            max(0.0, min(1.0, adjusted_score)), 4,
        )

        # 4. Otonomi karari
        decision = self.autonomy.decide(
            action_id,
            adjusted_score,
            action_type=action_type,
        )

        # 5. Eskalasyon gerekli mi
        if decision["decision"] in (
            "ask_human", "reject",
        ):
            self.escalation.escalate(
                action_id,
                domain=domain,
                reason=decision["reason"],
            )
            self._stats["escalated"] += 1

        if decision["decision"] == "auto_execute":
            self._stats["auto_executed"] += 1

        self._stats["decisions"] += 1

        return {
            "action_id": action_id,
            "raw_score": raw_score,
            "calibrated_score": score,
            "trust_score": trust_score,
            "final_score": adjusted_score,
            "decision": decision["decision"],
            "reason": decision["reason"],
            "domain": domain,
        }

    def record_result(
        self,
        action_id: str,
        predicted_outcome: str,
        actual_outcome: str,
        domain: str = "",
    ) -> dict[str, Any]:
        """Sonuc kaydeder ve ogrenir.

        Args:
            action_id: Aksiyon ID.
            predicted_outcome: Tahmini sonuc.
            actual_outcome: Gercek sonuc.
            domain: Alan.

        Returns:
            Ogrenme bilgisi.
        """
        # Dogruluk kaydi
        self.accuracy.record_prediction(
            action_id,
            confidence=0.5,
            predicted_outcome=predicted_outcome,
            domain=domain,
        )
        result = self.accuracy.record_outcome(
            action_id,
            actual_outcome=actual_outcome,
        )

        correct = result.get("correct", False)

        # Guven guncelle
        if correct:
            self.trust.record_success(domain)
        else:
            self.trust.record_failure(domain)

        # Kalibrasyon ornegi
        decisions = (
            self.autonomy.get_decision_history(
                limit=1,
            )
        )
        if decisions:
            conf = decisions[-1].get(
                "confidence", 0.5,
            )
            self.calibration.add_sample(
                conf, correct, domain=domain,
            )

        return {
            "action_id": action_id,
            "correct": correct,
            "accuracy": self.accuracy.overall_accuracy,
            "trust_updated": True,
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "total_decisions": (
                self._stats["decisions"]
            ),
            "auto_executed": (
                self._stats["auto_executed"]
            ),
            "escalated": (
                self._stats["escalated"]
            ),
            "overall_accuracy": (
                self.accuracy.overall_accuracy
            ),
            "calibration": (
                self.calibration.detect_miscalibration()
            ),
            "trust_domains": (
                self.trust.domain_count
            ),
            "pending_escalations": (
                self.escalation.pending_count
            ),
            "feedback_count": (
                self.feedback.feedback_count
            ),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "accuracy": (
                self.accuracy.overall_accuracy
            ),
            "accuracy_trend": (
                self.accuracy.analyze_trend()
            ),
            "domain_accuracy": (
                self.accuracy.get_domain_accuracy()
            ),
            "brier_score": (
                self.calibration.brier_score
            ),
            "trust_levels": (
                self.trust.get_all_trust()
            ),
            "agreement_rate": (
                self.feedback.get_agreement_rate()
            ),
            "calculator_avg": (
                self.calculator.avg_score
            ),
        }

    @property
    def total_decisions(self) -> int:
        """Toplam karar sayisi."""
        return self._stats["decisions"]

    @property
    def auto_rate(self) -> float:
        """Otomatik calistirma orani."""
        total = self._stats["decisions"]
        if total == 0:
            return 0.0
        return round(
            self._stats["auto_executed"] / total,
            4,
        )
