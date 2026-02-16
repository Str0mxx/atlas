"""ATLAS Savaş Odası Orkestratörü.

Tam rekabet istihbaratı pipeline,
Monitor → Analyze → Alert → Respond,
gerçek zamanlı savaş odası, analitik.
"""

import logging
from typing import Any

from app.core.warroom.competitive_intel_aggregator import (
    CompetitiveIntelAggregator,
)
from app.core.warroom.competitor_profile_card import (
    CompetitorProfileCard,
)
from app.core.warroom.competitor_tracker import (
    CompetitorTracker,
)
from app.core.warroom.hiring_signal_analyzer import (
    HiringSignalAnalyzer,
)
from app.core.warroom.patent_monitor import (
    CompetitorPatentMonitor,
)
from app.core.warroom.price_watcher import (
    PriceWatcher,
)
from app.core.warroom.product_launch_detector import (
    ProductLaunchDetector,
)
from app.core.warroom.threat_assessor import (
    ThreatAssessor,
)

logger = logging.getLogger(__name__)


class WarRoomOrchestrator:
    """Savaş odası orkestratörü.

    Tüm rekabet istihbaratı bileşenlerini
    koordine eder.

    Attributes:
        tracker: Rakip takipçisi.
        prices: Fiyat izleyici.
        launches: Lansman tespitçisi.
        hiring: İşe alım analizcisi.
        patents: Patent izleyici.
        profiles: Profil kartı.
        threats: Tehdit değerlendiricisi.
        intel: İstihbarat toplayıcı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.tracker = CompetitorTracker()
        self.prices = PriceWatcher()
        self.launches = (
            ProductLaunchDetector()
        )
        self.hiring = (
            HiringSignalAnalyzer()
        )
        self.patents = (
            CompetitorPatentMonitor()
        )
        self.profiles = (
            CompetitorProfileCard()
        )
        self.threats = ThreatAssessor()
        self.intel = (
            CompetitiveIntelAggregator()
        )
        self._stats = {
            "pipelines_run": 0,
            "competitors_analyzed": 0,
        }

        logger.info(
            "WarRoomOrchestrator "
            "baslatildi",
        )

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def analyzed_count(self) -> int:
        """Analiz edilen rakip sayısı."""
        return self._stats[
            "competitors_analyzed"
        ]

    def full_competitor_analysis(
        self,
        name: str,
        industry: str = "",
        market_share: float = 0.1,
    ) -> dict[str, Any]:
        """Tam rakip analizi yapar.

        Monitor → Profile → Threat → Intel.

        Args:
            name: Rakip adı.
            industry: Sektör.
            market_share: Pazar payı.

        Returns:
            Tam analiz bilgisi.
        """
        # 1. Rakibi takibe al
        comp = self.tracker.monitor_competitor(
            name, industry,
        )
        cid = comp["competitor_id"]

        # 2. Profil derle
        profile = self.profiles.compile_profile(
            cid, name, industry,
        )

        # 3. Tehdit puanla
        threat = self.threats.score_threat(
            cid,
            market_share=market_share,
            growth_rate=0.3,
            innovation_score=0.5,
        )

        # 4. İstihbarat topla
        intel = self.intel.collect_intel(
            cid, "analysis",
            f"Initial analysis of {name}",
            0.7,
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "competitors_analyzed"
        ] += 1

        return {
            "competitor_id": cid,
            "name": name,
            "threat_level": threat["level"],
            "threat_score": threat[
                "threat_score"
            ],
            "intel_reliability": intel[
                "reliability"
            ],
            "pipeline_complete": True,
        }

    def monitor_and_alert(
        self,
        competitor_id: str,
        check_prices: bool = True,
        check_launches: bool = True,
    ) -> dict[str, Any]:
        """İzleme ve uyarı pipeline.

        Args:
            competitor_id: Rakip kimliği.
            check_prices: Fiyat kontrolü.
            check_launches: Lansman kontrolü.

        Returns:
            İzleme bilgisi.
        """
        alerts = []

        if check_prices:
            price = (
                self.prices.monitor_price(
                    competitor_id,
                    "main_product",
                    99.99,
                )
            )
            alerts.append(
                {
                    "type": "price",
                    "result": "monitored",
                },
            )

        if check_launches:
            launch = (
                self.launches.detect_launch(
                    competitor_id,
                    "new_product",
                )
            )
            alerts.append(
                {
                    "type": "launch",
                    "confidence": launch[
                        "confidence"
                    ],
                },
            )

        self._stats[
            "pipelines_run"
        ] += 1

        return {
            "competitor_id": competitor_id,
            "alerts": alerts,
            "alert_count": len(alerts),
            "monitored": True,
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
            "competitors_analyzed": (
                self._stats[
                    "competitors_analyzed"
                ]
            ),
            "competitors_tracked": (
                self.tracker
                .competitor_count
            ),
            "prices_monitored": (
                self.prices.monitor_count
            ),
            "launches_detected": (
                self.launches.launch_count
            ),
            "hiring_analyses": (
                self.hiring.analysis_count
            ),
            "patents_tracked": (
                self.patents.patent_count
            ),
            "profiles_compiled": (
                self.profiles.profile_count
            ),
            "threats_scored": (
                self.threats
                .assessment_count
            ),
            "intel_collected": (
                self.intel.intel_count
            ),
        }
