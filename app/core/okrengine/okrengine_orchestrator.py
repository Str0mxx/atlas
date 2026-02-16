"""ATLAS OKR Motor Orkestratörü.

Tam OKR yönetimi pipeline,
Objective → KRs → Track → Review,
hizalama kontrolü, koçluk.
"""

import logging
from typing import Any

from app.core.okrengine.objective_definer import (
    ObjectiveDefiner,
)
from app.core.okrengine.key_result_tracker import (
    KeyResultTracker,
)
from app.core.okrengine.progress_visualizer import (
    OKRProgressVisualizer,
)
from app.core.okrengine.alignment_checker import (
    AlignmentChecker,
)
from app.core.okrengine.cadence_manager import (
    CadenceManager,
)
from app.core.okrengine.okr_score_calculator import (
    OKRScoreCalculator,
)
from app.core.okrengine.strategic_reviewer import (
    StrategicReviewer,
)
from app.core.okrengine.okr_coach import (
    OKRCoach,
)

logger = logging.getLogger(__name__)


class OKREngineOrchestrator:
    """OKR motor orkestratörü.

    Tüm OKR yönetim bileşenlerini
    koordine eder.

    Attributes:
        definer: Hedef tanımlayıcı.
        tracker: Anahtar sonuç takipçisi.
        visualizer: İlerleme görselleştiricisi.
        alignment: Hizalama kontrolcüsü.
        cadence: Dönem yöneticisi.
        scorer: OKR puan hesaplayıcısı.
        reviewer: Stratejik gözden geçirici.
        coach: OKR koçu.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.definer = (
            ObjectiveDefiner()
        )
        self.tracker = (
            KeyResultTracker()
        )
        self.visualizer = (
            OKRProgressVisualizer()
        )
        self.alignment = (
            AlignmentChecker()
        )
        self.cadence = (
            CadenceManager()
        )
        self.scorer = (
            OKRScoreCalculator()
        )
        self.reviewer = (
            StrategicReviewer()
        )
        self.coach = OKRCoach()
        self._stats = {
            "cycles_run": 0,
            "objectives_managed": 0,
        }

        logger.info(
            "OKREngineOrchestrator "
            "baslatildi",
        )

    @property
    def cycle_count(self) -> int:
        """Döngü sayısı."""
        return self._stats[
            "cycles_run"
        ]

    @property
    def managed_count(self) -> int:
        """Yönetilen hedef sayısı."""
        return self._stats[
            "objectives_managed"
        ]

    def full_okr_cycle(
        self,
        title: str = "Increase Revenue",
        level: str = "company",
        owner: str = "leadership",
        kr_descriptions: list[str]
        | None = None,
        cadence: str = "weekly",
    ) -> dict[str, Any]:
        """Tam OKR döngüsü çalıştırır.

        Define → Track → Schedule → Coach.

        Args:
            title: Hedef başlığı.
            level: Hedef seviyesi.
            owner: Hedef sahibi.
            kr_descriptions: Anahtar sonuç açıklamaları.
            cadence: Check-in sıklığı.

        Returns:
            Tam döngü bilgisi.
        """
        if kr_descriptions is None:
            kr_descriptions = [
                "Reach $1M ARR",
                "Acquire 100 customers",
            ]

        # 1. Hedef oluştur
        obj = (
            self.definer
            .create_objective(
                title, level, owner,
            )
        )

        # 2. Anahtar sonuçları tanımla
        krs = [
            self.tracker.define_kr(
                obj["objective_id"],
                desc,
            )
            for desc in kr_descriptions
        ]

        # 3. SMART doğrula
        smart = (
            self.definer.validate_smart(
                obj["objective_id"],
            )
        )

        # 4. Check-in planla
        schedule = (
            self.cadence
            .schedule_checkin(
                obj["objective_id"],
                cadence,
            )
        )

        # 5. En iyi pratikler öner
        coaching = (
            self.coach
            .suggest_best_practices(
                "writing",
            )
        )

        self._stats[
            "cycles_run"
        ] += 1
        self._stats[
            "objectives_managed"
        ] += 1

        return {
            "objective_id": obj[
                "objective_id"
            ],
            "title": title,
            "level": level,
            "owner": owner,
            "kr_count": len(krs),
            "smart_score": smart[
                "smart_score"
            ],
            "schedule_id": schedule[
                "schedule_id"
            ],
            "best_practices": coaching[
                "practice_count"
            ],
            "cycle_complete": True,
        }

    def company_wide_review(
        self,
        quarter: str = "Q1",
        year: int = 2026,
        objective_scores: list[
            dict[str, Any]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Şirket çapında OKR gözden geçirmesi.

        Args:
            quarter: Çeyrek (Q1-Q4).
            year: Yıl.
            objective_scores: Hedef skorları
                [{score, ...}].

        Returns:
            Gözden geçirme bilgisi.
        """
        if objective_scores is None:
            objective_scores = []

        # 1. Çeyrek gözden geçirme
        review = (
            self.reviewer
            .quarterly_review(
                quarter,
                year,
                objective_scores,
            )
        )

        # 2. Skorları topla
        scores_list = [
            o.get("score", 0)
            for o in objective_scores
        ]
        aggregate = (
            self.scorer.aggregate_scores(
                scores_list,
            )
        )

        # 3. Öneri üret
        recommendations = (
            self.reviewer
            .generate_recommendation(
                aggregate[
                    "overall_score"
                ],
                "stable",
                review.get("at_risk", 0),
            )
        )

        self._stats[
            "cycles_run"
        ] += 1

        return {
            "quarter": quarter,
            "year": year,
            "avg_score": review[
                "avg_score"
            ],
            "total_objectives": review[
                "total_objectives"
            ],
            "completed": review[
                "completed"
            ],
            "at_risk": review[
                "at_risk"
            ],
            "overall_score": aggregate[
                "overall_score"
            ],
            "recommendations": (
                recommendations["actions"]
            ),
            "review_complete": True,
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
            "objectives_managed": (
                self._stats[
                    "objectives_managed"
                ]
            ),
            "objectives_defined": (
                self.definer
                .objective_count
            ),
            "krs_tracked": (
                self.tracker.kr_count
            ),
            "charts_created": (
                self.visualizer
                .chart_count
            ),
            "alignment_checks": (
                self.alignment
                .check_count
            ),
            "schedules": (
                self.cadence
                .schedule_count
            ),
            "scores_calculated": (
                self.scorer.score_count
            ),
            "reviews": (
                self.reviewer
                .review_count
            ),
            "coaching_sessions": (
                self.coach.session_count
            ),
        }
