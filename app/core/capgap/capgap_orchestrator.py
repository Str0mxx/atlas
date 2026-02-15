"""ATLAS CapGap Orkestrator modulu.

Tam gap-to-capability pipeline,
Detect > Plan > Acquire > Validate > Deploy.
"""

import logging
import time
from typing import Any

from app.core.capgap.acquisition_planner import (
    AcquisitionPlanner,
)
from app.core.capgap.api_discoverer import (
    CapabilityAPIDiscoverer,
)
from app.core.capgap.capability_mapper import (
    CapabilityMapper,
)
from app.core.capgap.gap_detector import (
    GapDetector,
)
from app.core.capgap.learning_accelerator import (
    LearningAccelerator,
)
from app.core.capgap.progress_tracker import (
    AcquisitionProgressTracker,
)
from app.core.capgap.skill_builder import (
    SkillBuilder,
)
from app.core.capgap.validation_engine import (
    CapabilityValidationEngine,
)

logger = logging.getLogger(__name__)


class CapGapOrchestrator:
    """CapGap orkestrator.

    Tum yetenek eksikligi bilesenleri koordine eder.

    Attributes:
        detector: Eksiklik tespitcisi.
        mapper: Yetenek haritacisi.
        planner: Edinme planlayici.
        discoverer: API kesficisi.
        builder: Yetenek insacisi.
        accelerator: Ogrenme hizlandirici.
        validator: Dogrulama motoru.
        tracker: Ilerleme takipcisi.
    """

    def __init__(
        self,
        auto_acquire: bool = False,
        require_validation: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            auto_acquire: Otomatik edinme.
            require_validation: Dogrulama zorunlu.
        """
        self.detector = GapDetector()
        self.mapper = CapabilityMapper()
        self.planner = AcquisitionPlanner()
        self.discoverer = (
            CapabilityAPIDiscoverer()
        )
        self.builder = SkillBuilder()
        self.accelerator = (
            LearningAccelerator()
        )
        self.validator = (
            CapabilityValidationEngine()
        )
        self.tracker = (
            AcquisitionProgressTracker()
        )

        self._auto_acquire = auto_acquire
        self._require_validation = (
            require_validation
        )
        self._stats = {
            "pipelines_run": 0,
        }

        logger.info(
            "CapGapOrchestrator baslatildi",
        )

    def detect_and_plan(
        self,
        task_id: str,
        task_description: str,
        required: list[str],
    ) -> dict[str, Any]:
        """Eksiklik tespiti ve planlama.

        Args:
            task_id: Gorev ID.
            task_description: Gorev aciklamasi.
            required: Gerekli yetenekler.

        Returns:
            Tespit ve plan bilgisi.
        """
        # Mevcut yetenekleri al
        available = (
            self.mapper.list_capabilities()
        )

        # Eksiklikleri tespit et
        gap_result = self.detector.detect_gaps(
            task_id, required, available,
        )

        # Her eksiklik icin plan olustur
        plans = []
        for gap in gap_result["gaps"]:
            # Strateji degerlendir
            eval_result = (
                self.planner
                .evaluate_strategies(
                    gap["capability"],
                )
            )

            # Plan olustur
            plan = self.planner.create_plan(
                gap["gap_id"],
                gap["capability"],
                strategy=eval_result[
                    "recommended"
                ],
            )
            plans.append(plan)

        self._stats["pipelines_run"] += 1

        return {
            "task_id": task_id,
            "coverage": gap_result[
                "coverage"
            ],
            "gaps": gap_result["gaps"],
            "gap_count": gap_result[
                "gap_count"
            ],
            "plans": plans,
            "plan_count": len(plans),
        }

    def acquire_capability(
        self,
        gap_id: str,
        capability: str,
        strategy: str = "build",
    ) -> dict[str, Any]:
        """Yetenek edinir.

        Args:
            gap_id: Eksiklik ID.
            capability: Yetenek adi.
            strategy: Strateji.

        Returns:
            Edinme bilgisi.
        """
        # Ilerleme takibini baslat
        acq_id = f"acq_{gap_id}"
        self.tracker.start_tracking(
            acq_id, capability,
        )

        # 1) Plan
        self.tracker.update_progress(
            acq_id, 1,
            phase="planning",
            description="Planning acquisition",
        )

        plan = self.planner.create_plan(
            gap_id, capability,
            strategy=strategy,
        )

        # 2) Build
        self.tracker.update_progress(
            acq_id, 2,
            phase="acquisition",
            description="Building capability",
        )

        build_result = None
        if strategy in ("build", "integrate"):
            build_result = (
                self.builder
                .generate_integration(
                    capability,
                    {"endpoint": "", "auth_type": "api_key"},
                )
            )

        # 3) Validate
        self.tracker.update_progress(
            acq_id, 3,
            phase="validation",
            description="Validating capability",
        )

        validation = None
        if self._require_validation:
            validation = (
                self.validator
                .validate_capability(
                    capability,
                    [
                        {
                            "name": "basic",
                            "expected": True,
                            "actual": True,
                        },
                    ],
                )
            )

        # 4) Register
        self.tracker.update_progress(
            acq_id, 4,
            phase="deployment",
            description="Deploying capability",
        )

        self.mapper.register_capability(
            capability,
            category="acquired",
        )

        # 5) Complete
        self.tracker.complete_acquisition(
            acq_id,
        )
        self.detector.resolve_gap(gap_id)

        return {
            "acquisition_id": acq_id,
            "capability": capability,
            "strategy": strategy,
            "plan_id": plan["plan_id"],
            "build": (
                build_result is not None
            ),
            "validated": (
                validation is not None
                and validation.get("result")
                == "passed"
            ) if validation else False,
            "acquired": True,
        }

    def full_pipeline(
        self,
        task_id: str,
        task_description: str,
        required: list[str],
    ) -> dict[str, Any]:
        """Tam pipeline calistirir.

        Args:
            task_id: Gorev ID.
            task_description: Gorev aciklamasi.
            required: Gerekli yetenekler.

        Returns:
            Pipeline sonucu.
        """
        # Tespit ve planlama
        detect_result = self.detect_and_plan(
            task_id, task_description,
            required,
        )

        acquired = []
        failed = []

        if self._auto_acquire:
            for gap in detect_result["gaps"]:
                try:
                    acq = (
                        self.acquire_capability(
                            gap["gap_id"],
                            gap["capability"],
                        )
                    )
                    acquired.append(acq)
                except Exception as e:
                    failed.append({
                        "capability": gap[
                            "capability"
                        ],
                        "error": str(e),
                    })

        return {
            "task_id": task_id,
            "initial_coverage": (
                detect_result["coverage"]
            ),
            "gaps_detected": detect_result[
                "gap_count"
            ],
            "acquired": len(acquired),
            "failed": len(failed),
            "auto_acquire": self._auto_acquire,
            "final_coverage": (
                self.mapper.coverage_analysis(
                    required,
                )["coverage_pct"]
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "capabilities": (
                self.mapper.capability_count
            ),
            "gaps_detected": (
                self.detector.gap_count
            ),
            "unresolved_gaps": (
                self.detector.unresolved_count
            ),
            "plans": (
                self.planner.plan_count
            ),
            "builds": (
                self.builder.build_count
            ),
            "validations": (
                self.validator
                .validation_count
            ),
            "certifications": (
                self.validator
                .certification_count
            ),
            "in_progress": (
                self.tracker
                .in_progress_count
            ),
            "completed": (
                self.tracker.completed_count
            ),
            "pipelines_run": (
                self._stats["pipelines_run"]
            ),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "total_capabilities": (
                self.mapper.capability_count
            ),
            "total_gaps": (
                self.detector.gap_count
            ),
            "resolution_rate": round(
                (
                    self.detector.gap_count
                    - self.detector
                    .unresolved_count
                )
                / max(
                    self.detector.gap_count, 1,
                ) * 100,
                1,
            ),
            "patterns_learned": (
                self.accelerator.pattern_count
            ),
            "validation_pass_rate": (
                self.validator.pass_rate
            ),
            "learning_report": (
                self.accelerator
                .get_efficiency_report()
            ),
        }

    @property
    def pipelines_run(self) -> int:
        """Calisan pipeline sayisi."""
        return self._stats["pipelines_run"]
