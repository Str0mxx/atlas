"""ATLAS Senaryo Orkestratörü.

Tam senaryo planlama pipeline,
Build → Analyze → Simulate → Recommend,
stratejik karar desteği, analitik.
"""

import logging
from typing import Any

from app.core.scenario.best_case_optimizer import (
    BestCaseOptimizer,
)
from app.core.scenario.decision_tree_generator import (
    DecisionTreeGenerator,
)
from app.core.scenario.impact_calculator import (
    ScenarioImpactCalculator,
)
from app.core.scenario.probability_estimator import (
    ScenarioProbabilityEstimator,
)
from app.core.scenario.scenario_builder import (
    ScenarioBuilder,
)
from app.core.scenario.strategic_recommender import (
    StrategicRecommender,
)
from app.core.scenario.war_game_simulator import (
    WarGameSimulator,
)
from app.core.scenario.worst_case_analyzer import (
    WorstCaseAnalyzer,
)

logger = logging.getLogger(__name__)


class ScenarioOrchestrator:
    """Senaryo orkestratörü.

    Tüm senaryo bileşenlerini koordine eder.

    Attributes:
        builder: Senaryo oluşturucu.
        probability: Olasılık tahmincisi.
        impact: Etki hesaplayıcı.
        decision_tree: Karar ağacı üretici.
        worst_case: En kötü durum analizcisi.
        best_case: En iyi durum optimizasyonu.
        recommender: Stratejik önerici.
        war_game: Savaş oyunu simülatörü.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.builder = ScenarioBuilder()
        self.probability = (
            ScenarioProbabilityEstimator()
        )
        self.impact = (
            ScenarioImpactCalculator()
        )
        self.decision_tree = (
            DecisionTreeGenerator()
        )
        self.worst_case = (
            WorstCaseAnalyzer()
        )
        self.best_case = (
            BestCaseOptimizer()
        )
        self.recommender = (
            StrategicRecommender()
        )
        self.war_game = (
            WarGameSimulator()
        )
        self._stats = {
            "pipelines_run": 0,
            "decisions_supported": 0,
        }

        logger.info(
            "ScenarioOrchestrator "
            "baslatildi",
        )

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def decision_count(self) -> int:
        """Desteklenen karar sayısı."""
        return self._stats[
            "decisions_supported"
        ]

    def full_scenario_analysis(
        self,
        name: str,
        scenario_type: str = "realistic",
        potential_gain: float = 50000.0,
        potential_loss: float = 20000.0,
        probability: float = 0.5,
    ) -> dict[str, Any]:
        """Tam senaryo analizi yapar.

        Build → Probability → Impact →
        Worst/Best Case → Recommend.

        Args:
            name: Senaryo adı.
            scenario_type: Senaryo tipi.
            potential_gain: Potansiyel kazanç.
            potential_loss: Potansiyel kayıp.
            probability: Olasılık.

        Returns:
            Tam analiz bilgisi.
        """
        # 1. Senaryo oluştur
        scenario = (
            self.builder.create_scenario(
                name, scenario_type,
            )
        )
        sid = scenario["scenario_id"]

        # 2. Olasılık değerlendir
        prob = (
            self.probability
            .assess_probability(
                sid, probability,
            )
        )

        # 3. Etki hesapla
        fin_impact = (
            self.impact
            .calculate_financial(
                sid,
                revenue_change=(
                    potential_gain
                ),
                cost_change=potential_loss,
            )
        )

        # 4. En kötü durum
        worst = (
            self.worst_case
            .analyze_downside(
                sid, potential_loss,
                probability,
            )
        )

        # 5. En iyi durum
        best = (
            self.best_case
            .analyze_upside(
                sid, potential_gain,
                probability,
            )
        )

        # 6. Strateji öner
        risk_level = (
            "high"
            if worst["severity"]
            in ("catastrophic", "severe")
            else "medium"
        )
        opp_level = (
            "high"
            if best["opportunity"]
            in ("exceptional", "significant")
            else "medium"
        )
        rec = (
            self.recommender
            .suggest_strategy(
                sid, risk_level,
                opp_level,
            )
        )

        self._stats[
            "pipelines_run"
        ] += 1

        return {
            "scenario_id": sid,
            "name": name,
            "probability": prob[
                "probability"
            ],
            "financial_impact": (
                fin_impact["net_impact"]
            ),
            "worst_case_severity": worst[
                "severity"
            ],
            "best_case_opportunity": best[
                "opportunity"
            ],
            "recommended_strategy": rec[
                "strategy"
            ],
            "pipeline_complete": True,
        }

    def strategic_decision(
        self,
        decision_name: str,
        options: list[str]
        | None = None,
        risk_tolerance: float = 0.5,
    ) -> dict[str, Any]:
        """Stratejik karar desteği sağlar.

        Args:
            decision_name: Karar adı.
            options: Seçenekler.
            risk_tolerance: Risk toleransı.

        Returns:
            Karar desteği bilgisi.
        """
        if options is None:
            options = [
                "option_a",
                "option_b",
            ]

        # 1. Karar ağacı oluştur
        tree = (
            self.decision_tree.build_tree(
                decision_name, options,
            )
        )

        # 2. Risk-getiri dengesi
        balance = (
            self.recommender
            .balance_risk_reward(
                tree["tree_id"],
                potential_reward=100.0,
                potential_risk=50.0,
                risk_tolerance=(
                    risk_tolerance
                ),
            )
        )

        self._stats[
            "decisions_supported"
        ] += 1

        return {
            "tree_id": tree["tree_id"],
            "decision": decision_name,
            "option_count": len(options),
            "risk_reward_ratio": balance[
                "risk_reward_ratio"
            ],
            "verdict": balance["verdict"],
            "proceed": balance["proceed"],
            "supported": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "decisions_supported": (
                self._stats[
                    "decisions_supported"
                ]
            ),
            "scenarios_created": (
                self.builder.scenario_count
            ),
            "assessments_made": (
                self.probability
                .assessment_count
            ),
            "impact_calculations": (
                self.impact
                .calculation_count
            ),
            "trees_built": (
                self.decision_tree
                .tree_count
            ),
            "worst_case_analyses": (
                self.worst_case
                .analysis_count
            ),
            "best_case_analyses": (
                self.best_case
                .analysis_count
            ),
            "recommendations": (
                self.recommender
                .recommendation_count
            ),
            "war_games": (
                self.war_game
                .simulation_count
            ),
        }
