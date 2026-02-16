"""ATLAS A/B Test Orkestratörü.

Tam deney pipeline,
Design → Split → Measure → Analyze → Rollout,
platform entegrasyonu, analitik.
"""

import logging
import time
from typing import Any

from app.core.abtesting.ab_statistical_analyzer import (
    ABStatisticalAnalyzer,
)
from app.core.abtesting.auto_rollout import (
    AutoRollout,
)
from app.core.abtesting.experiment_archive import (
    ExperimentArchive,
)
from app.core.abtesting.experiment_designer import (
    ABExperimentDesigner,
)
from app.core.abtesting.multivariate_tester import (
    MultivariateTester,
)
from app.core.abtesting.traffic_splitter import (
    TrafficSplitter,
)
from app.core.abtesting.variant_manager import (
    VariantManager,
)
from app.core.abtesting.winner_detector import (
    WinnerDetector,
)

logger = logging.getLogger(__name__)


class ABTestingOrchestrator:
    """A/B test orkestratörü.

    Tüm A/B test bileşenlerini
    koordine eder.

    Attributes:
        designer: Deney tasarımcısı.
        variants: Varyant yöneticisi.
        splitter: Trafik bölücü.
        analyzer: İstatistiksel analizci.
        winner: Kazanan tespitçisi.
        rollout: Otomatik yayılım.
        archive: Deney arşivi.
        multivariate: Çok değişkenli test.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.designer = (
            ABExperimentDesigner()
        )
        self.variants = VariantManager()
        self.splitter = TrafficSplitter()
        self.analyzer = (
            ABStatisticalAnalyzer()
        )
        self.winner = WinnerDetector()
        self.rollout = AutoRollout()
        self.archive = ExperimentArchive()
        self.multivariate = (
            MultivariateTester()
        )
        self._stats = {
            "pipelines_run": 0,
            "experiments_completed": 0,
        }

        logger.info(
            "ABTestingOrchestrator "
            "baslatildi",
        )

    def run_experiment(
        self,
        experiment_id: str,
        name: str = "",
        control_conversions: int = 0,
        control_total: int = 0,
        treatment_conversions: int = 0,
        treatment_total: int = 0,
        confidence: float = 0.95,
    ) -> dict[str, Any]:
        """Design → Split → Measure → Analyze → Rollout.

        Args:
            experiment_id: Deney kimliği.
            name: Deney adı.
            control_conversions: Kontrol dönüşüm.
            control_total: Kontrol toplam.
            treatment_conversions: Tedavi dönüşüm.
            treatment_total: Tedavi toplam.
            confidence: Güven düzeyi.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Design
        self.designer.define_hypothesis(
            experiment_id,
            metric="conversion",
        )
        self.designer.create_variants(
            experiment_id,
        )
        self.designer.define_success_metrics(
            experiment_id,
        )

        # 2. Analyze
        result = (
            self.analyzer
            .test_significance(
                control_conversions=(
                    control_conversions
                ),
                control_total=(
                    control_total
                ),
                treatment_conversions=(
                    treatment_conversions
                ),
                treatment_total=(
                    treatment_total
                ),
                confidence=confidence,
            )
        )

        # 3. Determine winner
        variant_results = [
            {
                "name": "control",
                "conversion": result[
                    "control_rate"
                ],
                "significant": result[
                    "significant"
                ],
            },
            {
                "name": "treatment",
                "conversion": result[
                    "treatment_rate"
                ],
                "significant": result[
                    "significant"
                ],
            },
        ]
        winner_result = (
            self.winner
            .determine_winner(
                experiment_id,
                variant_results,
            )
        )

        # 4. Archive
        self.archive.archive_experiment(
            experiment_id,
            name=name,
            winner=winner_result.get(
                "winner", "",
            ),
            lift_pct=result.get(
                "lift_pct", 0,
            ),
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "experiments_completed"
        ] += 1

        return {
            "experiment_id": experiment_id,
            "significant": result[
                "significant"
            ],
            "winner": winner_result.get(
                "winner", "",
            ),
            "lift_pct": result[
                "lift_pct"
            ],
            "p_value": result[
                "p_value"
            ],
            "pipeline_complete": True,
        }

    def quick_test(
        self,
        control_rate: float = 0.10,
        treatment_rate: float = 0.12,
        sample_size: int = 1000,
    ) -> dict[str, Any]:
        """Hızlı test yapar.

        Args:
            control_rate: Kontrol oranı.
            treatment_rate: Tedavi oranı.
            sample_size: Örneklem boyutu.

        Returns:
            Test bilgisi.
        """
        c_conv = int(
            control_rate * sample_size,
        )
        t_conv = int(
            treatment_rate * sample_size,
        )

        result = (
            self.analyzer
            .test_significance(
                c_conv, sample_size,
                t_conv, sample_size,
            )
        )

        return {
            "control_rate": control_rate,
            "treatment_rate": (
                treatment_rate
            ),
            "significant": result[
                "significant"
            ],
            "p_value": result["p_value"],
            "lift_pct": result[
                "lift_pct"
            ],
            "tested": True,
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
            "experiments_completed": (
                self._stats[
                    "experiments_completed"
                ]
            ),
            "hypotheses_defined": (
                self.designer
                .hypothesis_count
            ),
            "variants_configured": (
                self.variants.variant_count
            ),
            "assignments_made": (
                self.splitter
                .assignment_count
            ),
            "tests_performed": (
                self.analyzer.test_count
            ),
            "winners_detected": (
                self.winner
                .detection_count
            ),
            "rollouts_started": (
                self.rollout.rollout_count
            ),
            "experiments_archived": (
                self.archive.archive_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def completed_count(self) -> int:
        """Tamamlanan deney sayısı."""
        return self._stats[
            "experiments_completed"
        ]
