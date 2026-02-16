"""ATLAS Kriz Yönetimi Orkestratörü.

Tam kriz yönetimi pipeline,
Detect → Escalate → Communicate → Act → Recover → Learn,
7/24 hazırlık, analitik.
"""

import logging
import time
from typing import Any

from app.core.crisismgr.action_plan_generator import (
    CrisisActionPlanGenerator,
)
from app.core.crisismgr.communication_template import (
    CrisisCommunicationTemplate,
)
from app.core.crisismgr.crisis_detector import (
    CrisisMgrDetector,
)
from app.core.crisismgr.escalation_protocol import (
    EscalationProtocol,
)
from app.core.crisismgr.post_crisis_analyzer import (
    PostCrisisAnalyzer,
)
from app.core.crisismgr.recovery_tracker import (
    CrisisRecoveryTracker,
)
from app.core.crisismgr.simulation_runner import (
    CrisisSimulationRunner,
)
from app.core.crisismgr.stakeholder_notifier import (
    StakeholderNotifier,
)

logger = logging.getLogger(__name__)


class CrisisMgrOrchestrator:
    """Kriz yönetimi orkestratörü.

    Tüm kriz yönetimi bileşenlerini
    koordine eder.

    Attributes:
        detector: Kriz tespitçisi.
        escalation: Eskalasyon protokolü.
        comms: İletişim şablonu.
        notifier: Paydaş bilgilendiricisi.
        planner: Aksiyon planı üretici.
        post_crisis: Kriz sonrası analizcisi.
        simulator: Simülasyon çalıştırıcı.
        recovery: Kurtarma takipçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.detector = CrisisMgrDetector()
        self.escalation = (
            EscalationProtocol()
        )
        self.comms = (
            CrisisCommunicationTemplate()
        )
        self.notifier = (
            StakeholderNotifier()
        )
        self.planner = (
            CrisisActionPlanGenerator()
        )
        self.post_crisis = (
            PostCrisisAnalyzer()
        )
        self.simulator = (
            CrisisSimulationRunner()
        )
        self.recovery = (
            CrisisRecoveryTracker()
        )
        self._stats = {
            "pipelines_run": 0,
            "crises_managed": 0,
        }

        logger.info(
            "CrisisMgrOrchestrator "
            "baslatildi",
        )

    def handle_crisis(
        self,
        crisis_id: str,
        metric_name: str = "error_rate",
        current_value: float = 0.0,
        baseline: float = 0.0,
        std_dev: float = 1.0,
        crisis_type: str = "general",
    ) -> dict[str, Any]:
        """Detect → Escalate → Communicate → Act.

        Args:
            crisis_id: Kriz kimliği.
            metric_name: Metrik adı.
            current_value: Güncel değer.
            baseline: Taban değer.
            std_dev: Standart sapma.
            crisis_type: Kriz tipi.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Detect
        detection = (
            self.detector.detect_anomaly(
                metric_name=metric_name,
                current_value=(
                    current_value
                ),
                baseline=baseline,
                std_dev=std_dev,
            )
        )

        # 2. Escalate
        self.escalation.define_levels(
            crisis_id,
        )

        # 3. Generate action plan
        plan = self.planner.generate_plan(
            crisis_id=crisis_id,
            crisis_type=crisis_type,
            severity=detection["severity"],
        )

        # 4. Notify
        self.notifier.route_notification(
            crisis_id=crisis_id,
            stakeholder="team_lead",
            message=(
                f"Crisis detected: "
                f"{metric_name} "
                f"anomaly ({detection['severity']})"
            ),
        )

        # 5. Start recovery tracking
        self.recovery.track_progress(
            crisis_id=crisis_id,
            phase="containment",
            progress_pct=0.0,
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "crises_managed"
        ] += 1

        return {
            "crisis_id": crisis_id,
            "is_anomaly": detection[
                "is_anomaly"
            ],
            "severity": detection[
                "severity"
            ],
            "plan_steps": plan[
                "step_count"
            ],
            "notified": True,
            "recovery_started": True,
            "pipeline_complete": True,
        }

    def post_crisis_review(
        self,
        crisis_id: str,
        symptoms: list[str]
        | None = None,
        factors: list[str]
        | None = None,
        lessons: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kriz sonrası inceleme yapar.

        Args:
            crisis_id: Kriz kimliği.
            symptoms: Belirtiler.
            factors: Faktörler.
            lessons: Dersler.

        Returns:
            İnceleme bilgisi.
        """
        symptoms = symptoms or []
        factors = factors or []
        lessons = lessons or []

        rca = (
            self.post_crisis
            .root_cause_analysis(
                crisis_id,
                symptoms=symptoms,
                contributing_factors=(
                    factors
                ),
            )
        )

        self.post_crisis.extract_lessons(
            crisis_id, lessons=lessons,
        )

        recs = (
            self.post_crisis
            .recommend_improvements(
                crisis_id,
            )
        )

        return {
            "crisis_id": crisis_id,
            "root_cause": rca[
                "root_cause"
            ],
            "lessons_count": len(lessons),
            "recommendations": recs[
                "count"
            ],
            "reviewed": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": (
                self._stats[
                    "pipelines_run"
                ]
            ),
            "crises_managed": (
                self._stats[
                    "crises_managed"
                ]
            ),
            "anomalies_detected": (
                self.detector.anomaly_count
            ),
            "warnings_issued": (
                self.detector.warning_count
            ),
            "escalations": (
                self.escalation
                .escalation_count
            ),
            "notifications_sent": (
                self.notifier
                .notification_count
            ),
            "plans_generated": (
                self.planner.plan_count
            ),
            "recoveries_tracked": (
                self.recovery
                .recovery_count
            ),
            "drills_executed": (
                self.simulator.drill_count
            ),
            "post_analyses": (
                self.post_crisis
                .analysis_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def crisis_count(self) -> int:
        """Kriz sayısı."""
        return self._stats[
            "crises_managed"
        ]
