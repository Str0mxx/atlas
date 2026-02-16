"""
ATLAS İş Modeli Orkestratörü.

Tam iş modeli kanvas yönetimi pipeline,
Build → Analyze → Test → Optimize,
pivot tespiti ve rekabet analizi.
"""

import logging
from typing import Any

from app.core.bizmodel.canvas_builder import (
    CanvasBuilder,
)
from app.core.bizmodel.revenue_stream_analyzer import (
    RevenueStreamAnalyzer,
)
from app.core.bizmodel.customer_segmenter import (
    BizCustomerSegmenter,
)
from app.core.bizmodel.cost_structure_mapper import (
    CostStructureMapper,
)
from app.core.bizmodel.value_proposition_tester import (
    ValuePropositionTester,
)
from app.core.bizmodel.pivot_signal_detector import (
    PivotSignalDetector,
)
from app.core.bizmodel.model_optimizer import (
    BusinessModelOptimizer,
)
from app.core.bizmodel.competitive_position_analyzer import (
    CompetitivePositionAnalyzer,
)

logger = logging.getLogger(__name__)


class BizModelOrchestrator:
    """İş modeli orkestratörü.

    Tüm iş modeli bileşenlerini
    koordine eder.

    Attributes:
        builder: Kanvas oluşturucu.
        revenue: Gelir analizcisi.
        segmenter: Müşteri segmentleyici.
        costs: Maliyet haritacısı.
        value_tester: Değer test edici.
        pivot: Pivot tespitçisi.
        optimizer: Model optimizasyoncusu.
        competitive: Rekabet analizcisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.builder = CanvasBuilder()
        self.revenue = (
            RevenueStreamAnalyzer()
        )
        self.segmenter = (
            BizCustomerSegmenter()
        )
        self.costs = CostStructureMapper()
        self.value_tester = (
            ValuePropositionTester()
        )
        self.pivot = PivotSignalDetector()
        self.optimizer = (
            BusinessModelOptimizer()
        )
        self.competitive = (
            CompetitivePositionAnalyzer()
        )
        self._stats: dict[str, int] = {
            "cycles_run": 0,
            "models_managed": 0,
        }

        logger.info(
            "BizModelOrchestrator "
            "baslatildi"
        )

    @property
    def cycle_count(self) -> int:
        """Döngü sayısı."""
        return self._stats["cycles_run"]

    @property
    def managed_count(self) -> int:
        """Yönetilen model sayısı."""
        return self._stats[
            "models_managed"
        ]

    def full_model_cycle(
        self,
        name: str = "New Business",
        proposition: str = "unique value",
        revenue_streams: list[
            dict[str, Any]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Tam iş modeli döngüsü çalıştırır.

        Build → Analyze → Test → Optimize.

        Args:
            name: İş modeli adı.
            proposition: Değer önerisi.
            revenue_streams: Gelir akışları.

        Returns:
            Tam döngü bilgisi.
        """
        try:
            if revenue_streams is None:
                revenue_streams = []

            # 1. Kanvas oluştur
            canvas = (
                self.builder.create_canvas(
                    name
                )
            )

            # 2. Gelir analizi
            rev = (
                self.revenue.analyze_revenue(
                    revenue_streams
                )
            )

            # 3. Değer önerisi testi
            vp_test = (
                self.value_tester
                .test_value_prop(
                    proposition
                )
            )

            # 4. Optimizasyon önerileri
            opt = (
                self.optimizer
                .suggest_optimizations(
                    rev["total_revenue"],
                    rev["total_revenue"]
                    * 0.6,
                )
            )

            self._stats["cycles_run"] += 1
            self._stats[
                "models_managed"
            ] += 1

            result = {
                "canvas_id": canvas[
                    "canvas_id"
                ],
                "name": name,
                "total_revenue": rev[
                    "total_revenue"
                ],
                "value_score": vp_test[
                    "score"
                ],
                "value_grade": vp_test[
                    "grade"
                ],
                "optimization_count": opt[
                    "suggestion_count"
                ],
                "cycle_complete": True,
            }

            logger.info(
                f"Tam model dongusu: "
                f"{name}, "
                f"gelir={rev['total_revenue']}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Model dongusu "
                f"hatasi: {e}"
            )
            return {
                "canvas_id": "",
                "name": name,
                "total_revenue": 0.0,
                "value_score": 0,
                "value_grade": "unknown",
                "optimization_count": 0,
                "cycle_complete": False,
                "error": str(e),
            }

    def strategic_review(
        self,
        our_score: float = 50.0,
        market_avg: float = 50.0,
        market_share: float = 10.0,
        warning_metrics: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Stratejik gözden geçirme yapar.

        Args:
            our_score: Bizim skor.
            market_avg: Pazar ortalaması.
            market_share: Pazar payı.
            warning_metrics: Uyarı metrikleri.

        Returns:
            Stratejik gözden geçirme.
        """
        try:
            # 1. Pozisyon haritalama
            pos = (
                self.competitive
                .map_position(
                    our_score,
                    market_avg,
                    market_share,
                )
            )

            # 2. Uyarı tespiti
            warnings = (
                self.pivot
                .detect_warnings(
                    warning_metrics
                )
            )

            # 3. Pivot önerisi
            pivot_rec = (
                self.pivot
                .recommend_pivot(
                    warnings[
                        "warning_count"
                    ],
                    "stable",
                    50.0,
                )
            )

            self._stats["cycles_run"] += 1

            result = {
                "position": pos[
                    "position"
                ],
                "relative_score": pos[
                    "relative_score"
                ],
                "warning_count": warnings[
                    "warning_count"
                ],
                "severity": warnings[
                    "severity"
                ],
                "pivot_recommendation": (
                    pivot_rec[
                        "recommendation"
                    ]
                ),
                "pivot_urgency": pivot_rec[
                    "urgency"
                ],
                "review_complete": True,
            }

            logger.info(
                f"Stratejik gozden gecirme: "
                f"pozisyon={pos['position']}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Stratejik gozden "
                f"gecirme hatasi: {e}"
            )
            return {
                "position": "unknown",
                "relative_score": 0.0,
                "warning_count": 0,
                "severity": "unknown",
                "pivot_recommendation": (
                    "unknown"
                ),
                "pivot_urgency": "unknown",
                "review_complete": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "cycles_run": self._stats[
                "cycles_run"
            ],
            "models_managed": self._stats[
                "models_managed"
            ],
            "canvases_created": (
                self.builder.canvas_count
            ),
            "revenue_analyses": (
                self.revenue.analysis_count
            ),
            "segments_created": (
                self.segmenter.segment_count
            ),
            "cost_analyses": (
                self.costs.analysis_count
            ),
            "value_tests": (
                self.value_tester.test_count
            ),
            "pivot_detections": (
                self.pivot.detection_count
            ),
            "optimizations": (
                self.optimizer
                .optimization_count
            ),
            "competitive_analyses": (
                self.competitive
                .analysis_count
            ),
        }
