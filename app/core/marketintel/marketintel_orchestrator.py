"""ATLAS Pazar İstihbaratı Orkestratörü modülü.

Tam pazar istihbaratı pipeline'ı,
Scan → Analyze → Predict → Alert,
sürekli izleme, analitik.
"""

import logging
from typing import Any

from app.core.marketintel.academic_tracker import (
    AcademicTracker,
)
from app.core.marketintel.competitor_mapper import (
    CompetitorMapper,
)
from app.core.marketintel.investment_analyzer import (
    InvestmentAnalyzer,
)
from app.core.marketintel.market_size_estimator import (
    MarketSizeEstimator,
)
from app.core.marketintel.patent_scanner import (
    PatentScanner,
)
from app.core.marketintel.regulation_monitor import (
    RegulationMonitor,
)
from app.core.marketintel.signal_aggregator import (
    SignalAggregator,
)
from app.core.marketintel.trend_tracker import (
    TrendTracker,
)

logger = logging.getLogger(__name__)


class MarketIntelOrchestrator:
    """Pazar istihbaratı orkestratörü.

    Tüm pazar istihbaratı bileşenlerini koordine eder.

    Attributes:
        trends: Trend takipçisi.
        investments: Yatırım analizcisi.
        competitors: Rakip haritacısı.
        patents: Patent tarayıcı.
        academic: Akademik takipçi.
        regulations: Düzenleme izleyici.
        market_size: Pazar tahmincisi.
        signals: Sinyal toplayıcı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.trends = TrendTracker()
        self.investments = (
            InvestmentAnalyzer()
        )
        self.competitors = CompetitorMapper()
        self.patents = PatentScanner()
        self.academic = AcademicTracker()
        self.regulations = (
            RegulationMonitor()
        )
        self.market_size = (
            MarketSizeEstimator()
        )
        self.signals = SignalAggregator()

        self._stats = {
            "scans_completed": 0,
            "analyses_run": 0,
            "alerts_generated": 0,
        }

        logger.info(
            "MarketIntelOrchestrator "
            "baslatildi",
        )

    def scan_market(
        self,
        market_name: str,
        data_points: list[float] | None = None,
        competitors: (
            list[dict[str, Any]] | None
        ) = None,
        tam: float | None = None,
    ) -> dict[str, Any]:
        """Pazar taraması yapar.

        Args:
            market_name: Pazar adı.
            data_points: Trend verileri.
            competitors: Rakip verileri.
            tam: TAM değeri.

        Returns:
            Tarama bilgisi.
        """
        results: dict[str, Any] = {
            "market": market_name,
        }

        # 1) Trend tespit
        if data_points:
            trend = self.trends.detect_trend(
                name=f"{market_name} trend",
                data_points=data_points,
                category="market",
            )
            results["trend"] = trend

            # Sinyal ekle
            self.signals.collect_signal(
                source_type="market",
                title=(
                    f"{market_name} "
                    f"trend: {trend['stage']}"
                ),
                strength=abs(
                    trend["momentum"],
                ),
            )

        # 2) Rakipleri ekle
        comp_ids = []
        if competitors:
            for c in competitors:
                added = (
                    self.competitors.add_competitor(
                        name=c.get("name", ""),
                        market=market_name,
                        market_share=c.get(
                            "market_share", 0,
                        ),
                    )
                )
                comp_ids.append(
                    added["competitor_id"],
                )
            results["competitors_added"] = (
                len(comp_ids)
            )

        # 3) Pazar tahmini
        if tam:
            est = (
                self.market_size
                .estimate_tam_sam_som(
                    market_name=market_name,
                    tam=tam,
                )
            )
            results["market_estimate"] = est

        self._stats["scans_completed"] += 1

        return {
            "success": True,
            "market": market_name,
            "trend_detected": (
                "trend" in results
            ),
            "competitors_added": len(
                comp_ids,
            ),
            "market_estimated": (
                "market_estimate" in results
            ),
            **results,
        }

    def analyze_competitive_landscape(
        self,
        market: str,
    ) -> dict[str, Any]:
        """Rekabet ortamını analiz eder.

        Args:
            market: Pazar.

        Returns:
            Analiz bilgisi.
        """
        comps = (
            self.competitors.get_competitors(
                market=market,
            )
        )

        analyses = []
        for comp in comps:
            pos = (
                self.competitors
                .analyze_positioning(
                    comp["competitor_id"],
                )
            )
            analyses.append(pos)

        total_share = sum(
            c.get("market_share", 0)
            for c in comps
        )

        self._stats["analyses_run"] += 1

        return {
            "market": market,
            "competitors": len(comps),
            "total_market_share": round(
                total_share, 1,
            ),
            "analyses": analyses,
        }

    def predict_trends(
        self,
        periods: int = 3,
    ) -> dict[str, Any]:
        """Tüm trendleri tahmin eder.

        Args:
            periods: Tahmin periyodu.

        Returns:
            Tahmin bilgisi.
        """
        trends = self.trends.get_trends()
        predictions = []

        for trend in trends:
            pred = self.trends.predict(
                trend["trend_id"],
                periods=periods,
            )
            if "error" not in pred:
                predictions.append(pred)

        return {
            "trends": len(trends),
            "predictions": predictions,
            "periods": periods,
        }

    def generate_alerts(
        self,
    ) -> dict[str, Any]:
        """Uyarılar üretir.

        Returns:
            Uyarı bilgisi.
        """
        alerts = []

        # Trend uyarıları
        trends = self.trends.get_trends()
        for trend in trends:
            if abs(trend.get(
                "momentum", 0,
            )) > 0.3:
                alert = (
                    self.trends
                    .generate_alert(
                        trend["trend_id"],
                        alert_type=(
                            "strong_momentum"
                        ),
                    )
                )
                alerts.append(alert)

        # Aksiyon sinyalleri
        actionable = (
            self.signals
            .get_actionable_signals(
                limit=5,
            )
        )
        for sig in actionable:
            alerts.append({
                "type": "actionable_signal",
                "signal_id": sig[
                    "signal_id"
                ],
                "title": sig["title"],
                "strength": sig[
                    "weighted_strength"
                ],
            })

        self._stats[
            "alerts_generated"
        ] += len(alerts)

        return {
            "alerts": alerts,
            "count": len(alerts),
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "scans_completed": (
                self._stats[
                    "scans_completed"
                ]
            ),
            "analyses_run": self._stats[
                "analyses_run"
            ],
            "alerts_generated": (
                self._stats[
                    "alerts_generated"
                ]
            ),
            "trends_tracked": (
                self.trends.trend_count
            ),
            "investments_tracked": (
                self.investments
                .investment_count
            ),
            "competitors_mapped": (
                self.competitors
                .competitor_count
            ),
            "patents_scanned": (
                self.patents.patent_count
            ),
            "publications_tracked": (
                self.academic
                .publication_count
            ),
            "regulations_monitored": (
                self.regulations
                .regulation_count
            ),
            "market_estimates": (
                self.market_size
                .estimate_count
            ),
            "signals_collected": (
                self.signals.signal_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "scans_completed": (
                self._stats[
                    "scans_completed"
                ]
            ),
            "trends": (
                self.trends.trend_count
            ),
            "competitors": (
                self.competitors
                .competitor_count
            ),
            "signals": (
                self.signals.signal_count
            ),
            "actionable_signals": (
                self.signals
                .actionable_count
            ),
        }

    @property
    def scan_count(self) -> int:
        """Tarama sayısı."""
        return self._stats[
            "scans_completed"
        ]
