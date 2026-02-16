"""ATLAS Yatırım Analiz Orkestratörü.

Tam yatırım analizi pipeline,
Analyze → Model → Compare → Recommend,
karar desteği, analitik.
"""

import logging
from typing import Any

from app.core.investanalyzer.due_diligence_tracker import (
    DueDiligenceTracker,
)
from app.core.investanalyzer.investment_calculator import (
    InvestmentCalculator,
)
from app.core.investanalyzer.investment_recommender import (
    InvestmentRecommender,
)
from app.core.investanalyzer.irr_engine import (
    IRREngine,
)
from app.core.investanalyzer.opportunity_cost_calculator import (
    OpportunityCostCalculator,
)
from app.core.investanalyzer.payback_analyzer import (
    PaybackAnalyzer,
)
from app.core.investanalyzer.portfolio_optimizer import (
    InvestmentPortfolioOptimizer,
)
from app.core.investanalyzer.risk_return_mapper import (
    RiskReturnMapper,
)

logger = logging.getLogger(__name__)


class InvestAnalyzerOrchestrator:
    """Yatırım analiz orkestratörü.

    Tüm yatırım analiz bileşenlerini
    koordine eder.

    Attributes:
        calculator: Yatırım hesaplayıcı.
        irr: İç verim oranı motoru.
        payback: Geri ödeme analizcisi.
        risk_return: Risk-getiri haritacısı.
        opportunity: Fırsat maliyeti.
        portfolio: Portföy optimizasyonu.
        recommender: Yatırım önerici.
        due_diligence: DD takipçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.calculator = (
            InvestmentCalculator()
        )
        self.irr = IRREngine()
        self.payback = PaybackAnalyzer()
        self.risk_return = (
            RiskReturnMapper()
        )
        self.opportunity = (
            OpportunityCostCalculator()
        )
        self.portfolio = (
            InvestmentPortfolioOptimizer()
        )
        self.recommender = (
            InvestmentRecommender()
        )
        self.due_diligence = (
            DueDiligenceTracker()
        )
        self._stats = {
            "pipelines_run": 0,
            "decisions_supported": 0,
        }

        logger.info(
            "InvestAnalyzerOrchestrator "
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
        """Karar desteği sayısı."""
        return self._stats[
            "decisions_supported"
        ]

    def full_investment_analysis(
        self,
        name: str,
        initial_cost: float = 100000.0,
        annual_revenue: float = 40000.0,
        annual_cost: float = 15000.0,
        years: int = 5,
        discount_rate: float = 0.1,
    ) -> dict[str, Any]:
        """Tam yatırım analizi yapar.

        Analyze → Model → NPV/IRR → Recommend.

        Args:
            name: Yatırım adı.
            initial_cost: Başlangıç maliyeti.
            annual_revenue: Yıllık gelir.
            annual_cost: Yıllık maliyet.
            years: Yıl sayısı.
            discount_rate: İskonto oranı.

        Returns:
            Tam analiz bilgisi.
        """
        # 1. Yatırım modelle
        model = (
            self.calculator
            .model_investment(
                name,
                initial_cost,
                annual_revenue,
                annual_cost,
                years,
            )
        )

        # 2. Nakit akışı projekte et
        annual_cf = (
            annual_revenue - annual_cost
        )
        cash_flows = [annual_cf] * years
        npv_result = (
            self.calculator
            .project_cash_flow(
                initial_cost,
                cash_flows,
                discount_rate,
            )
        )

        # 3. IRR hesapla
        irr_result = (
            self.irr.calculate_irr(
                initial_cost, cash_flows,
            )
        )

        # 4. Geri ödeme süresi
        payback = (
            self.payback
            .calculate_payback(
                initial_cost, cash_flows,
            )
        )

        # 5. Öneri
        if (
            npv_result["npv"] > 0
            and irr_result["irr"] > 10
        ):
            recommendation = "invest"
        elif npv_result["npv"] > 0:
            recommendation = "consider"
        else:
            recommendation = "pass"

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "decisions_supported"
        ] += 1

        return {
            "investment_id": model[
                "investment_id"
            ],
            "name": name,
            "roi_pct": model["roi_pct"],
            "npv": npv_result["npv"],
            "irr": irr_result["irr"],
            "payback_period": payback[
                "payback_period"
            ],
            "recommendation": (
                recommendation
            ),
            "pipeline_complete": True,
        }

    def compare_investments(
        self,
        investments: list[
            dict[str, Any]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Yatırımları karşılaştırır.

        Args:
            investments: Yatırımlar
                [{name, npv, irr, risk}].

        Returns:
            Karşılaştırma bilgisi.
        """
        if investments is None:
            investments = []

        comparison = (
            self.calculator
            .compare_scenarios(
                investments,
            )
        )

        self._stats[
            "decisions_supported"
        ] += 1

        return {
            "best_investment": comparison[
                "best_scenario"
            ],
            "ranked": comparison["ranked"],
            "count": len(investments),
            "compared": True,
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
            "models_created": (
                self.calculator.model_count
            ),
            "valuations_done": (
                self.calculator
                .valuation_count
            ),
            "irr_calculated": (
                self.irr.calculation_count
            ),
            "paybacks_calculated": (
                self.payback.payback_count
            ),
            "risk_assessments": (
                self.risk_return
                .assessment_count
            ),
            "opportunity_costs": (
                self.opportunity
                .calculation_count
            ),
            "portfolios": (
                self.portfolio
                .portfolio_count
            ),
            "suggestions": (
                self.recommender
                .suggestion_count
            ),
            "dd_checklists": (
                self.due_diligence
                .checklist_count
            ),
        }
