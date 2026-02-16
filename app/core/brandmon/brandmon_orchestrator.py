"""ATLAS Marka İzleme Orkestratörü.

Tam marka izleme pipeline,
Track → Analyze → Alert → Respond,
dashboard entegrasyonu, analitik.
"""

import logging
import time
from typing import Any

from app.core.brandmon.brand_health_score import (
    BrandHealthScore,
)
from app.core.brandmon.competitor_brand_tracker import (
    CompetitorBrandTracker,
)
from app.core.brandmon.crisis_detector import (
    CrisisDetector,
)
from app.core.brandmon.influencer_tracker import (
    InfluencerTracker,
)
from app.core.brandmon.mention_tracker import (
    MentionTracker,
)
from app.core.brandmon.response_suggester import (
    ResponseSuggester,
)
from app.core.brandmon.review_monitor import (
    ReviewMonitor,
)
from app.core.brandmon.sentiment_aggregator import (
    BrandSentimentAggregator,
)

logger = logging.getLogger(__name__)


class BrandMonOrchestrator:
    """Marka izleme orkestratörü.

    Tüm marka izleme bileşenlerini
    koordine eder.

    Attributes:
        mentions: Bahsedilme takipçisi.
        sentiment: Duygu toplayıcı.
        reviews: Yorum izleyici.
        crisis: Kriz tespitçisi.
        responder: Yanıt önerici.
        health: Sağlık puanı.
        competitors: Rakip takipçisi.
        influencers: Etkileyici takipçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.mentions = MentionTracker()
        self.sentiment = (
            BrandSentimentAggregator()
        )
        self.reviews = ReviewMonitor()
        self.crisis = CrisisDetector()
        self.responder = ResponseSuggester()
        self.health = BrandHealthScore()
        self.competitors = (
            CompetitorBrandTracker()
        )
        self.influencers = (
            InfluencerTracker()
        )
        self._stats = {
            "pipelines_run": 0,
            "alerts_generated": 0,
        }

        logger.info(
            "BrandMonOrchestrator "
            "baslatildi",
        )

    def run_brand_monitoring(
        self,
        brand: str,
        mentions: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Tam marka izleme pipeline çalıştırır.

        Args:
            brand: Marka.
            mentions: Bahsedilmeler.

        Returns:
            Pipeline bilgisi.
        """
        mentions = mentions or []

        # 1. Track mentions
        for m in mentions:
            source = m.get(
                "source", "social_media",
            )
            if source == "social_media":
                self.mentions.track_social_media(
                    brand,
                    platform=m.get(
                        "platform", "",
                    ),
                    content=m.get(
                        "content", "",
                    ),
                    sentiment=m.get(
                        "sentiment", "neutral",
                    ),
                )
            elif source == "news":
                self.mentions.track_news(
                    brand,
                    headline=m.get(
                        "content", "",
                    ),
                    sentiment=m.get(
                        "sentiment", "neutral",
                    ),
                )

        # 2. Analyze sentiment
        for m in mentions:
            self.sentiment.analyze_sentiment(
                brand,
                text=m.get("content", ""),
                source=m.get(
                    "source", "social_media",
                ),
            )

        # 3. Check for crisis
        neg_count = sum(
            1 for m in mentions
            if m.get("sentiment") == "negative"
        )
        spike = self.crisis.detect_negative_spike(
            brand,
            negative_count=neg_count,
            total_count=max(len(mentions), 1),
        )

        # 4. Calculate health
        weighted = (
            self.sentiment.weight_sources(
                brand,
            )
        )
        sent_score = weighted.get(
            "weighted_score", 0.5,
        ) * 100

        health = (
            self.health.calculate_health(
                brand,
                sentiment_score=sent_score,
                crisis_score=(
                    30.0 if spike["is_spike"]
                    else 100.0
                ),
            )
        )

        alert = spike["is_spike"]
        if alert:
            self._stats[
                "alerts_generated"
            ] += 1

        self._stats["pipelines_run"] += 1

        return {
            "brand": brand,
            "mentions_processed": len(
                mentions,
            ),
            "health_score": health.get(
                "overall", 0,
            ),
            "health_grade": health.get(
                "grade", "fair",
            ),
            "crisis_alert": alert,
            "pipeline_complete": True,
        }

    def track_analyze_alert_respond(
        self,
        brand: str,
        content: str = "",
        source: str = "social_media",
    ) -> dict[str, Any]:
        """Track → Analyze → Alert → Respond.

        Args:
            brand: Marka.
            content: İçerik.
            source: Kaynak.

        Returns:
            İşlem bilgisi.
        """
        # Track
        self.mentions.track_social_media(
            brand,
            content=content,
        )

        # Analyze
        analysis = (
            self.sentiment.analyze_sentiment(
                brand,
                text=content,
                source=source,
            )
        )

        # Alert
        needs_response = (
            analysis["sentiment"] == "negative"
        )

        # Respond
        response = None
        if needs_response:
            response = (
                self.responder
                .suggest_response(
                    sentiment="negative",
                    context=content[:50],
                )
            )

        return {
            "brand": brand,
            "sentiment": analysis[
                "sentiment"
            ],
            "needs_response": needs_response,
            "response_suggested": (
                response is not None
            ),
            "processed": True,
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
            "alerts_generated": self._stats[
                "alerts_generated"
            ],
            "mentions": (
                self.mentions.mention_count
            ),
            "sentiment_analyses": (
                self.sentiment.analysis_count
            ),
            "reviews": (
                self.reviews.review_count
            ),
            "crises": (
                self.crisis.crisis_count
            ),
            "suggestions": (
                self.responder
                .suggestion_count
            ),
            "health_scores": (
                self.health.score_count
            ),
            "competitors": (
                self.competitors
                .competitor_count
            ),
            "influencers": (
                self.influencers
                .influencer_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]
