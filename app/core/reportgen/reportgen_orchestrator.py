"""ATLAS Rapor Üretici Orkestratörü modülü.

Tam rapor üretim pipeline'ı,
Data → Analyze → Visualize → Format → Export,
şablon kütüphanesi, analitik.
"""

import logging
from typing import Any

from app.core.reportgen.actionable_insights import (
    ActionableInsights,
)
from app.core.reportgen.comparison_matrix import (
    ComparisonMatrix,
)
from app.core.reportgen.executive_summary import (
    ExecutiveSummary,
)
from app.core.reportgen.export_manager import (
    ExportManager,
)
from app.core.reportgen.opportunity_scorer import (
    OpportunityScorer,
)
from app.core.reportgen.report_builder import (
    ReportBuilder,
)
from app.core.reportgen.telegram_formatter import (
    TelegramFormatter,
)
from app.core.reportgen.visual_presenter import (
    VisualPresenter,
)

logger = logging.getLogger(__name__)


class ReportGenOrchestrator:
    """Rapor üretici orkestratörü.

    Tüm rapor bileşenlerini koordine eder.

    Attributes:
        builder: Rapor oluşturucu.
        summary: Yönetici özeti.
        comparison: Karşılaştırma matrisi.
        scorer: Fırsat puanlayıcı.
        visual: Görsel sunucu.
        insights: İçgörü üretici.
        telegram: Telegram biçimleyici.
        exporter: Dışa aktarma yöneticisi.
    """

    def __init__(
        self,
        use_emoji: bool = True,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            use_emoji: Emoji kullan.
        """
        self.builder = ReportBuilder()
        self.summary = ExecutiveSummary()
        self.comparison = ComparisonMatrix()
        self.scorer = OpportunityScorer()
        self.visual = VisualPresenter()
        self.insights = ActionableInsights()
        self.telegram = TelegramFormatter(
            use_emoji=use_emoji,
        )
        self.exporter = ExportManager()

        self._stats = {
            "reports_generated": 0,
            "pipelines_completed": 0,
            "errors": 0,
        }

        logger.info(
            "ReportGenOrchestrator baslatildi",
        )

    def generate_report(
        self,
        title: str,
        data: dict[str, Any],
        include_visuals: bool = True,
        include_insights: bool = True,
        output_format: str = "markdown",
        telegram_friendly: bool = False,
    ) -> dict[str, Any]:
        """Tam rapor üretir.

        Args:
            title: Başlık.
            data: Kaynak veri.
            include_visuals: Görsel ekle.
            include_insights: İçgörü ekle.
            output_format: Çıktı formatı.
            telegram_friendly: Telegram uyumlu.

        Returns:
            Rapor bilgisi.
        """
        # 1) Rapor oluştur
        report = self.builder.create_report(
            title=title,
        )
        report_id = report["report_id"]

        # 2) İçgörü çıkar
        insight_result = None
        if include_insights:
            insight_result = (
                self.insights.extract_insights(
                    data, context=title,
                )
            )
            recs = (
                self.insights.recommend_actions(
                    insight_result["insights"],
                )
            )

            self.builder.add_section(
                report_id,
                "Insights",
                "\n".join(
                    i["description"]
                    for i in insight_result[
                        "insights"
                    ]
                ),
            )

            self.builder.add_section(
                report_id,
                "Recommendations",
                "\n".join(
                    r["recommendation"]
                    for r in recs[
                        "recommendations"
                    ]
                ),
            )

        # 3) Özet oluştur
        content = "\n".join(
            f"{k}: {v}"
            for k, v in data.items()
        )
        summary = self.summary.create_summary(
            report_id=report_id,
            content=content,
            data=data,
            insights=(
                insight_result["insights"]
                if insight_result
                else []
            ),
        )

        self.builder.add_section(
            report_id,
            "Executive Summary",
            summary["tldr"],
        )

        # 4) Görsel ekle
        visual_ids = []
        if include_visuals and data:
            keys = list(data.keys())
            vals = [
                float(v)
                for v in data.values()
                if isinstance(
                    v, (int, float),
                )
            ]
            if vals:
                chart = (
                    self.visual.create_bar_chart(
                        labels=keys[: len(vals)],
                        values=vals,
                        title=f"{title} Overview",
                    )
                )
                visual_ids.append(
                    chart["visual_id"],
                )

        # 5) Sonuçlandır
        finalized = self.builder.finalize(
            report_id,
            output_format=output_format,
        )

        # 6) Telegram biçimlendirme
        telegram_msg = None
        if telegram_friendly:
            sections = [
                {"title": "Summary",
                 "content": summary["tldr"]},
            ]
            if insight_result:
                sections.append({
                    "title": "Key Insights",
                    "content": "\n".join(
                        i["description"]
                        for i in (
                            insight_result[
                                "insights"
                            ][:3]
                        )
                    ),
                })
            telegram_msg = (
                self.telegram.format_report(
                    title=title,
                    sections=sections,
                )
            )

        self._stats[
            "reports_generated"
        ] += 1
        self._stats[
            "pipelines_completed"
        ] += 1

        return {
            "success": True,
            "report_id": report_id,
            "title": title,
            "format": output_format,
            "sections": finalized["sections"],
            "content_length": finalized[
                "content_length"
            ],
            "insights_count": (
                insight_result["count"]
                if insight_result
                else 0
            ),
            "visuals": visual_ids,
            "telegram_message": (
                telegram_msg["text"]
                if telegram_msg
                else None
            ),
            "summary_id": summary[
                "summary_id"
            ],
        }

    def export_report(
        self,
        report_id: str,
        formats: list[str] | None = None,
    ) -> dict[str, Any]:
        """Raporu aktarır.

        Args:
            report_id: Rapor ID.
            formats: Aktarma formatları.

        Returns:
            Aktarma bilgisi.
        """
        report = self.builder.get_report(
            report_id,
        )
        if "error" in report:
            return report

        content = report.get("content", "")
        title = report.get("title", "")
        target_formats = formats or [
            "markdown",
        ]

        exports = []
        for fmt in target_formats:
            if fmt == "json":
                result = (
                    self.exporter.export_json(
                        report_id,
                        report,
                        title,
                    )
                )
            elif fmt == "pdf":
                result = (
                    self.exporter.export_pdf(
                        report_id,
                        content,
                        title,
                    )
                )
            elif fmt == "html":
                result = (
                    self.exporter.export_html(
                        report_id,
                        content,
                        title,
                    )
                )
            elif fmt == "word":
                result = (
                    self.exporter.export_word(
                        report_id,
                        content,
                        title,
                    )
                )
            else:
                result = (
                    self.exporter.export_markdown(
                        report_id,
                        content,
                        title,
                    )
                )
            exports.append(result)

        return {
            "report_id": report_id,
            "exports": exports,
            "count": len(exports),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "reports_generated": (
                self._stats[
                    "reports_generated"
                ]
            ),
            "pipelines_completed": (
                self._stats[
                    "pipelines_completed"
                ]
            ),
            "reports_created": (
                self.builder.report_count
            ),
            "templates": (
                self.builder.template_count
            ),
            "summaries": (
                self.summary.summary_count
            ),
            "comparisons": (
                self.comparison.comparison_count
            ),
            "opportunities_scored": (
                self.scorer.scored_count
            ),
            "visuals": (
                self.visual.visual_count
            ),
            "insights": (
                self.insights.insight_count
            ),
            "exports": (
                self.exporter.export_count
            ),
            "telegram_messages": (
                self.telegram.message_count
            ),
            "errors": self._stats["errors"],
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "reports_generated": (
                self._stats[
                    "reports_generated"
                ]
            ),
            "total_reports": (
                self.builder.report_count
            ),
            "total_exports": (
                self.exporter.export_count
            ),
            "total_insights": (
                self.insights.insight_count
            ),
        }

    @property
    def report_count(self) -> int:
        """Üretilen rapor sayısı."""
        return self._stats[
            "reports_generated"
        ]
