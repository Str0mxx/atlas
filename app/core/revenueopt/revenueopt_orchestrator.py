"""ATLAS Gelir Optimizasyon Orkestratörü.

Tam gelir optimizasyon pipeline,
Track → Analyze → Predict → Optimize → Grow,
otonom çalışma, analitik.
"""

import logging
import time
from typing import Any

from app.core.revenueopt.campaign_roi_analyzer import (
    CampaignROIAnalyzer,
)
from app.core.revenueopt.churn_predictor import (
    ChurnPredictor,
)
from app.core.revenueopt.ltv_calculator import (
    LTVCalculator,
)
from app.core.revenueopt.monetization_advisor import (
    MonetizationAdvisor,
)
from app.core.revenueopt.pricing_optimizer import (
    PricingOptimizer,
)
from app.core.revenueopt.revenue_forecaster import (
    RevenueForecaster,
)
from app.core.revenueopt.revenue_tracker import (
    RevenueTracker,
)
from app.core.revenueopt.upsell_detector import (
    UpsellDetector,
)

logger = logging.getLogger(__name__)


class RevenueOptOrchestrator:
    """Gelir optimizasyon orkestratörü.

    Tüm gelir optimizasyonu bileşenlerini
    koordine eder.

    Attributes:
        tracker: Gelir takipçisi.
        pricing: Fiyat optimizatörü.
        upsell: Upsell tespitçisi.
        churn: Kayıp tahmincisi.
        ltv: LTV hesaplayıcı.
        roi: Kampanya ROI analizcisi.
        forecaster: Gelir tahmin edici.
        advisor: Monetizasyon danışmanı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.tracker = RevenueTracker()
        self.pricing = PricingOptimizer()
        self.upsell = UpsellDetector()
        self.churn = ChurnPredictor()
        self.ltv = LTVCalculator()
        self.roi = CampaignROIAnalyzer()
        self.forecaster = (
            RevenueForecaster()
        )
        self.advisor = (
            MonetizationAdvisor()
        )
        self._stats = {
            "pipelines_run": 0,
            "optimizations_done": 0,
        }

        logger.info(
            "RevenueOptOrchestrator "
            "baslatildi",
        )

    def optimize_revenue(
        self,
        stream: str = "product",
        amount: float = 0.0,
        customer_id: str = "",
        historical: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Track → Analyze → Predict → Optimize.

        Args:
            stream: Gelir akışı.
            amount: Miktar.
            customer_id: Müşteri kimliği.
            historical: Geçmiş veriler.

        Returns:
            Pipeline bilgisi.
        """
        historical = historical or []

        # 1. Track
        track = self.tracker.monitor_revenue(
            stream=stream,
            amount=amount,
        )

        # 2. Analyze - LTV
        ltv_result = None
        if customer_id:
            ltv_result = (
                self.ltv.calculate_ltv(
                    customer_id=customer_id,
                    avg_purchase=amount,
                    purchase_frequency=1.0,
                )
            )

        # 3. Predict
        forecast = None
        if historical:
            forecast = (
                self.forecaster
                .forecast_revenue(
                    historical=historical,
                    periods_ahead=3,
                )
            )

        # 4. Advise
        advice = self.advisor.recommend(
            context={
                "monthly_revenue": amount,
            },
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "optimizations_done"
        ] += 1

        return {
            "stream": stream,
            "amount": amount,
            "tracked": True,
            "ltv": (
                ltv_result["ltv"]
                if ltv_result
                else None
            ),
            "forecast": (
                forecast["predictions"]
                if forecast
                else []
            ),
            "recommendations": (
                advice["count"]
            ),
            "pipeline_complete": True,
        }

    def quick_analysis(
        self,
        customer_id: str,
        days_inactive: int = 0,
    ) -> dict[str, Any]:
        """Hızlı müşteri analizi yapar.

        Args:
            customer_id: Müşteri kimliği.
            days_inactive: İnaktif gün.

        Returns:
            Analiz bilgisi.
        """
        churn = self.churn.score_churn_risk(
            customer_id=customer_id,
            days_inactive=days_inactive,
        )

        upsell = (
            self.upsell.score_propensity(
                customer_id=customer_id,
                engagement_score=(
                    max(
                        0,
                        100
                        - days_inactive * 2,
                    )
                ),
            )
        )

        return {
            "customer_id": customer_id,
            "churn_risk": churn[
                "risk_level"
            ],
            "churn_score": churn[
                "risk_score"
            ],
            "upsell_likelihood": upsell[
                "likelihood"
            ],
            "upsell_score": upsell[
                "propensity_score"
            ],
            "analyzed": True,
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
            "optimizations_done": (
                self._stats[
                    "optimizations_done"
                ]
            ),
            "revenues_tracked": (
                self.tracker.record_count
            ),
            "prices_optimized": (
                self.pricing.optimized_count
            ),
            "upsells_found": (
                self.upsell
                .opportunity_count
            ),
            "churn_risks_scored": (
                self.churn.risk_count
            ),
            "ltvs_calculated": (
                self.ltv.ltv_count
            ),
            "rois_calculated": (
                self.roi.roi_count
            ),
            "forecasts_made": (
                self.forecaster
                .forecast_count
            ),
            "advice_given": (
                self.advisor
                .recommendation_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "optimizations_done"
        ]
