"""ATLAS Araştırma Orkestratörü modülü.

Tam araştırma pipeline'ı,
Query → Crawl → Extract → Validate →
Synthesize → Report,
sürekli izleme, analitik.
"""

import logging
from typing import Any

from app.core.research.continuous_tracker import (
    ContinuousTracker,
)
from app.core.research.cross_validator import (
    CrossValidator,
)
from app.core.research.information_extractor import (
    InformationExtractor,
)
from app.core.research.multi_source_crawler import (
    MultiSourceCrawler,
)
from app.core.research.query_expander import (
    QueryExpander,
)
from app.core.research.research_reporter import (
    ResearchReporter,
)
from app.core.research.research_synthesizer import (
    ResearchSynthesizer,
)
from app.core.research.source_ranker import (
    SourceRanker,
)

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """Araştırma orkestratörü.

    Tüm araştırma bileşenlerini koordine eder.

    Attributes:
        crawler: Çoklu kaynak tarayıcı.
        expander: Sorgu genişletici.
        ranker: Kaynak sıralayıcı.
        extractor: Bilgi çıkarıcı.
        validator: Çapraz doğrulayıcı.
        synthesizer: Araştırma sentezleyici.
        tracker: Sürekli takipçi.
        reporter: Araştırma raporlayıcı.
    """

    def __init__(
        self,
        max_sources: int = 10,
        min_credibility: float = 0.3,
        report_format: str = "markdown",
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            max_sources: Maks kaynak sayısı.
            min_credibility: Min güvenilirlik.
            report_format: Rapor formatı.
        """
        self.crawler = MultiSourceCrawler()
        self.expander = QueryExpander()
        self.ranker = SourceRanker(
            min_credibility=min_credibility,
        )
        self.extractor = InformationExtractor()
        self.validator = CrossValidator()
        self.synthesizer = ResearchSynthesizer()
        self.tracker = ContinuousTracker()
        self.reporter = ResearchReporter(
            default_format=report_format,
        )

        self._max_sources = max_sources
        self._stats = {
            "research_completed": 0,
            "pipeline_runs": 0,
        }

        logger.info(
            "ResearchOrchestrator baslatildi",
        )

    def research(
        self,
        query: str,
        expand_query: bool = True,
        max_sources: int | None = None,
        report_format: str | None = None,
    ) -> dict[str, Any]:
        """Tam araştırma pipeline'ı çalıştırır.

        Args:
            query: Araştırma sorgusu.
            expand_query: Sorgu genişletme.
            max_sources: Maks kaynak.
            report_format: Rapor formatı.

        Returns:
            Araştırma sonucu.
        """
        self._stats["pipeline_runs"] += 1
        sources_limit = (
            max_sources or self._max_sources
        )

        # 1) Query Expansion
        expanded = None
        search_query = query
        if expand_query:
            expanded = self.expander.expand(query)
            # Ana sorguyu kullan
            search_query = query

        # 2) Crawl
        crawl_result = self.crawler.crawl(
            query=search_query,
            max_results=sources_limit,
        )
        raw_sources = crawl_result.get(
            "results", [],
        )

        # 3) Rank Sources
        ranked_sources = self.ranker.rank(
            raw_sources,
        )

        # 4) Extract Information
        all_facts = []
        for source in ranked_sources:
            snippet = source.get("snippet", "")
            if snippet:
                extraction = (
                    self.extractor.extract_facts(
                        content=snippet,
                        source_id=source.get(
                            "source_id", "",
                        ),
                    )
                )
                all_facts.extend(
                    extraction.get("facts", []),
                )

        # 5) Validate
        validation = None
        if all_facts and ranked_sources:
            validation = (
                self.validator.validate_fact(
                    fact=all_facts[0].get(
                        "content", "",
                    ),
                    sources=ranked_sources,
                )
            )

        # 6) Synthesize
        synthesis = self.synthesizer.synthesize(
            facts=all_facts,
            topic=query,
        )

        # 7) Report
        report = self.reporter.generate_report(
            title=f"Research: {query}",
            synthesis=synthesis,
            report_format=report_format,
        )

        self._stats["research_completed"] += 1

        return {
            "success": True,
            "query": query,
            "expanded_queries": (
                expanded["total_queries"]
                if expanded else 1
            ),
            "sources_found": len(raw_sources),
            "sources_ranked": len(
                ranked_sources,
            ),
            "facts_extracted": len(all_facts),
            "validation": validation,
            "synthesis_id": synthesis[
                "synthesis_id"
            ],
            "report_id": report["report_id"],
            "report_format": report["format"],
        }

    def track_topic(
        self,
        topic: str,
        frequency: str = "daily",
    ) -> dict[str, Any]:
        """Konuyu sürekli izlemeye alır.

        Args:
            topic: Konu.
            frequency: Sıklık.

        Returns:
            İzleme bilgisi.
        """
        return self.tracker.track_topic(
            topic=topic,
            frequency=frequency,
        )

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "research_completed": self._stats[
                "research_completed"
            ],
            "pipeline_runs": self._stats[
                "pipeline_runs"
            ],
            "total_crawls": (
                self.crawler.crawl_count
            ),
            "sources_crawled": (
                self.crawler.source_count
            ),
            "queries_expanded": (
                self.expander.expansion_count
            ),
            "sources_ranked": (
                self.ranker.ranked_count
            ),
            "facts_extracted": (
                self.extractor.fact_count
            ),
            "validations": (
                self.validator.validation_count
            ),
            "syntheses": (
                self.synthesizer.synthesis_count
            ),
            "reports_generated": (
                self.reporter.report_count
            ),
            "topics_tracked": (
                self.tracker.topic_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "research_completed": self._stats[
                "research_completed"
            ],
            "pipeline_runs": self._stats[
                "pipeline_runs"
            ],
            "topics_tracked": (
                self.tracker.topic_count
            ),
            "reports_generated": (
                self.reporter.report_count
            ),
        }

    @property
    def research_count(self) -> int:
        """Tamamlanan araştırma sayısı."""
        return self._stats[
            "research_completed"
        ]
