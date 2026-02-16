"""ATLAS Sosyal Medya Orkestratörü.

Tam sosyal medya yönetim pipeline,
Listen → Analyze → Create → Publish → Engage,
çoklu platform desteği, analitik.
"""

import logging
from typing import Any

from app.core.socialmedia.campaign_tracker import (
    SocialCampaignTracker,
)
from app.core.socialmedia.comment_manager import (
    CommentManager,
)
from app.core.socialmedia.content_scheduler import (
    SocialContentScheduler,
)
from app.core.socialmedia.engagement_analyzer import (
    EngagementAnalyzer,
)
from app.core.socialmedia.influencer_finder import (
    SocialInfluencerFinder,
)
from app.core.socialmedia.platform_connector import (
    SocialPlatformConnector,
)
from app.core.socialmedia.social_listening import (
    SocialListening,
)
from app.core.socialmedia.social_trend_detector import (
    SocialTrendDetector,
)

logger = logging.getLogger(__name__)


class SocialMediaOrchestrator:
    """Sosyal medya orkestratörü.

    Tüm sosyal medya bileşenlerini koordine eder.

    Attributes:
        connector: Platform bağlayıcı.
        scheduler: İçerik zamanlayıcı.
        engagement: Etkileşim analizcisi.
        trends: Trend tespitçisi.
        influencer: Influencer bulucu.
        comments: Yorum yöneticisi.
        listening: Sosyal dinleme.
        campaigns: Kampanya takipçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.connector = (
            SocialPlatformConnector()
        )
        self.scheduler = (
            SocialContentScheduler()
        )
        self.engagement = EngagementAnalyzer()
        self.trends = SocialTrendDetector()
        self.influencer = (
            SocialInfluencerFinder()
        )
        self.comments = CommentManager()
        self.listening = SocialListening()
        self.campaigns = (
            SocialCampaignTracker()
        )
        self._stats = {
            "pipelines_run": 0,
            "platforms_managed": 0,
        }

        logger.info(
            "SocialMediaOrchestrator "
            "baslatildi",
        )

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats["pipelines_run"]

    @property
    def platform_managed_count(self) -> int:
        """Yönetilen platform sayısı."""
        return self._stats[
            "platforms_managed"
        ]

    def publish_content(
        self,
        content: str,
        platform: str = "instagram",
        schedule: bool = False,
    ) -> dict[str, Any]:
        """Listen → Analyze → Create → Publish pipeline.

        Args:
            content: Gönderi içeriği.
            platform: Hedef platform.
            schedule: Zamanla mı yayınla mı.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Platform bağlantı kontrolü
        self.connector.connect_platform(
            platform,
        )

        # 2. En iyi zaman analizi
        best_time = (
            self.scheduler.get_best_time(
                platform,
            )
        )

        # 3. Trend kontrolü
        self.trends.detect_trending(
            platform,
        )

        # 4. İçerik zamanla
        post = self.scheduler.schedule_post(
            content, platform,
        )

        # 5. Duygu analizi
        sentiment = (
            self.listening.analyze_sentiment(
                content,
            )
        )

        self._stats["pipelines_run"] += 1

        return {
            "content_preview": content[:50],
            "platform": platform,
            "post_id": post["post_id"],
            "best_hour": best_time[
                "recommended"
            ],
            "sentiment": sentiment[
                "sentiment"
            ],
            "pipeline_complete": True,
        }

    def manage_platform(
        self,
        platform: str,
        api_key: str = "",
    ) -> dict[str, Any]:
        """Platform yönetimi yapar.

        Args:
            platform: Platform adı.
            api_key: API anahtarı.

        Returns:
            Yönetim bilgisi.
        """
        conn = (
            self.connector.connect_platform(
                platform, api_key,
            )
        )

        self.listening.track_keyword(
            platform, [platform],
        )

        self._stats[
            "platforms_managed"
        ] += 1

        return {
            "platform": platform,
            "connected": conn["connected"],
            "listening": True,
            "managed": True,
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
            "platforms_managed": self._stats[
                "platforms_managed"
            ],
            "platforms_connected": (
                self.connector.platform_count
            ),
            "posts_scheduled": (
                self.scheduler.scheduled_count
            ),
            "analyses_done": (
                self.engagement.analysis_count
            ),
            "trends_detected": (
                self.trends.trend_count
            ),
            "influencers_found": (
                self.influencer.found_count
            ),
            "comments_monitored": (
                self.comments.monitored_count
            ),
            "mentions_tracked": (
                self.listening.mention_count
            ),
            "campaigns_created": (
                self.campaigns.campaign_count
            ),
        }
