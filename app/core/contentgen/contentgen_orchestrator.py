"""ATLAS İçerik Üretici Orkestratör modülü.

Tam içerik pipeline,
Create → Optimize → Adapt → Test → Analyze,
çoklu platform desteği, analitik.
"""

import logging
import time
from typing import Any

from app.core.contentgen.ab_test_copy import (
    ABTestCopy,
)
from app.core.contentgen.brand_voice_manager import (
    BrandVoiceManager,
)
from app.core.contentgen.content_calendar import (
    ContentCalendar,
)
from app.core.contentgen.copy_writer import (
    CopyWriter,
)
from app.core.contentgen.multilang_content import (
    MultiLangContent,
)
from app.core.contentgen.performance_analyzer import (
    ContentPerformanceAnalyzer,
)
from app.core.contentgen.platform_adapter import (
    PlatformAdapter,
)
from app.core.contentgen.seo_optimizer import (
    SEOOptimizer,
)

logger = logging.getLogger(__name__)


class ContentGenOrchestrator:
    """İçerik üretici orkestratör.

    Tüm içerik üretim bileşenlerini
    koordine eder.

    Attributes:
        writer: Metin yazıcı.
        seo: SEO optimize edici.
        multilang: Çok dilli içerik.
        ab_test: A/B test.
        brand: Marka sesi.
        calendar: İçerik takvimi.
        adapter: Platform adaptörü.
        performance: Performans analizcisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.writer = CopyWriter()
        self.seo = SEOOptimizer()
        self.multilang = MultiLangContent()
        self.ab_test = ABTestCopy()
        self.brand = BrandVoiceManager()
        self.calendar = ContentCalendar()
        self.adapter = PlatformAdapter()
        self.performance = (
            ContentPerformanceAnalyzer()
        )
        self._stats = {
            "pipelines_run": 0,
            "content_created": 0,
        }

        logger.info(
            "ContentGenOrchestrator "
            "baslatildi",
        )

    def create_content(
        self,
        product: str,
        platform: str = "website",
        tone: str = "professional",
        keywords: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """İçerik oluşturur.

        Create → Optimize → Adapt pipeline.

        Args:
            product: Ürün.
            platform: Platform.
            tone: Ton.
            keywords: Anahtar kelimeler.

        Returns:
            İçerik bilgisi.
        """
        keywords = keywords or []

        # 1. Write copy
        copy = self.writer.write_ad_copy(
            product=product,
            tone=tone,
        )

        # 2. SEO optimize
        seo_result = (
            self.seo.integrate_keywords(
                copy["text"],
                keywords=keywords,
            )
        )

        # 3. Adapt to platform
        adapted = self.adapter.adapt_format(
            copy["text"],
            platform=platform,
        )

        self._stats[
            "content_created"
        ] += 1

        return {
            "copy_id": copy["copy_id"],
            "text": adapted["adapted"],
            "platform": platform,
            "seo_keywords_found": (
                seo_result["present_count"]
            ),
            "within_platform_limit": (
                adapted["within_limit"]
            ),
            "created": True,
        }

    def run_full_pipeline(
        self,
        product: str,
        benefit: str = "",
        platforms: list[str]
        | None = None,
        keywords: list[str]
        | None = None,
        language: str = "en",
    ) -> dict[str, Any]:
        """Create → Optimize → Adapt → Test.

        Args:
            product: Ürün.
            benefit: Fayda.
            platforms: Platformlar.
            keywords: Anahtar kelimeler.
            language: Dil.

        Returns:
            Pipeline bilgisi.
        """
        platforms = platforms or ["website"]
        keywords = keywords or []

        # 1. Write copy
        copy = self.writer.write_ad_copy(
            product=product,
            benefit=benefit,
        )

        # 2. Create headline
        headline = (
            self.writer.create_headline(
                product=product,
                benefit=benefit,
            )
        )

        # 3. SEO score
        seo_score = (
            self.seo.calculate_score(
                copy["text"],
                keywords=keywords,
            )
        )

        # 4. Adapt to platforms
        platform_results = {}
        for plat in platforms:
            result = (
                self.adapter.adapt_format(
                    copy["text"],
                    platform=plat,
                )
            )
            platform_results[plat] = (
                result["within_limit"]
            )

        # 5. Translate if needed
        translation = None
        if language != "en":
            translation = (
                self.multilang.translate(
                    copy["text"],
                    target_lang=language,
                )
            )

        # 6. A/B variations
        variations = (
            self.ab_test.generate_variations(
                copy["text"],
            )
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "content_created"
        ] += 1

        return {
            "copy_id": copy["copy_id"],
            "text": copy["text"],
            "headline": headline[
                "headline"
            ],
            "seo_score": seo_score[
                "seo_score"
            ],
            "platforms": platform_results,
            "translated": (
                translation is not None
            ),
            "variations": variations[
                "count"
            ],
            "pipeline_complete": True,
        }

    def multi_platform_publish(
        self,
        product: str,
        platforms: list[str]
        | None = None,
        scheduled_date: str = "",
    ) -> dict[str, Any]:
        """Çoklu platform yayınlar.

        Args:
            product: Ürün.
            platforms: Platformlar.
            scheduled_date: Tarih.

        Returns:
            Yayın bilgisi.
        """
        platforms = platforms or [
            "website", "facebook",
        ]

        results = []
        for plat in platforms:
            content = self.create_content(
                product=product,
                platform=plat,
            )

            entry = (
                self.calendar.schedule_publish(
                    title=product,
                    platform=plat,
                    scheduled_date=(
                        scheduled_date
                    ),
                )
            )

            results.append({
                "platform": plat,
                "copy_id": content[
                    "copy_id"
                ],
                "entry_id": entry[
                    "entry_id"
                ],
                "scheduled": True,
            })

        return {
            "product": product,
            "platforms": platforms,
            "results": results,
            "platform_count": len(results),
            "published": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "content_created": (
                self._stats[
                    "content_created"
                ]
            ),
            "pipelines_run": (
                self._stats[
                    "pipelines_run"
                ]
            ),
            "copies_written": (
                self.writer.copy_count
            ),
            "headlines": (
                self.writer.headline_count
            ),
            "seo_optimizations": (
                self.seo.optimization_count
            ),
            "translations": (
                self.multilang
                .translation_count
            ),
            "ab_tests": (
                self.ab_test.test_count
            ),
            "brand_voices": (
                self.brand.voice_count
            ),
            "calendar_entries": (
                self.calendar.entry_count
            ),
            "adaptations": (
                self.adapter.adaptation_count
            ),
        }

    @property
    def content_count(self) -> int:
        """İçerik sayısı."""
        return self._stats[
            "content_created"
        ]

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]
