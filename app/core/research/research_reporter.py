"""ATLAS Araştırma Raporlayıcı modülü.

Rapor üretme, çoklu format,
atıf yönetimi, görsel öğeler,
dışa aktarma seçenekleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResearchReporter:
    """Araştırma raporlayıcı.

    Araştırma sonuçlarını raporlar halinde
    üretir.

    Attributes:
        _reports: Rapor geçmişi.
        _citations: Atıf kayıtları.
    """

    def __init__(
        self,
        default_format: str = "markdown",
    ) -> None:
        """Raporlayıcıyı başlatır.

        Args:
            default_format: Varsayılan format.
        """
        self._reports: list[
            dict[str, Any]
        ] = []
        self._citations: list[
            dict[str, Any]
        ] = []
        self._templates: dict[str, str] = {
            "markdown": "# {title}\n\n{body}",
            "html": (
                "<h1>{title}</h1>"
                "<div>{body}</div>"
            ),
            "text": "{title}\n\n{body}",
            "executive": (
                "EXECUTIVE SUMMARY: {title}"
                "\n\n{body}"
            ),
        }
        self._default_format = default_format
        self._counter = 0
        self._stats = {
            "reports_generated": 0,
            "citations_managed": 0,
            "exports": 0,
        }

        logger.info(
            "ResearchReporter baslatildi",
        )

    def generate_report(
        self,
        title: str,
        synthesis: dict[str, Any],
        report_format: str | None = None,
        include_citations: bool = True,
    ) -> dict[str, Any]:
        """Rapor üretir.

        Args:
            title: Rapor başlığı.
            synthesis: Sentez verisi.
            report_format: Rapor formatı.
            include_citations: Atıf dahil.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"rpt_{self._counter}"
        fmt = (
            report_format or self._default_format
        )

        # İçerik oluştur
        body_parts = []

        # Anlatı
        narrative = synthesis.get(
            "narrative", "",
        )
        if narrative:
            body_parts.append(narrative)

        # Çıkarımlar
        insights = synthesis.get("insights", [])
        if insights:
            body_parts.append(
                "\n## Key Insights\n"
                if fmt == "markdown"
                else "\nKey Insights:\n"
            )
            for insight in insights:
                content = insight.get(
                    "content", "",
                )
                body_parts.append(
                    f"- {content}"
                    if fmt == "markdown"
                    else f"* {content}"
                )

        # Boşluklar
        gaps = synthesis.get("gaps", [])
        if gaps:
            body_parts.append(
                "\n## Knowledge Gaps\n"
                if fmt == "markdown"
                else "\nKnowledge Gaps:\n"
            )
            for gap in gaps:
                suggestion = gap.get(
                    "suggestion", "",
                )
                body_parts.append(
                    f"- {suggestion}"
                )

        body = "\n".join(body_parts)

        # Şablona uygula
        template = self._templates.get(
            fmt, self._templates["text"],
        )
        content = template.format(
            title=title, body=body,
        )

        # Atıflar
        citations = []
        if include_citations:
            facts = synthesis.get(
                "fused_facts", [],
            )
            for fact in facts:
                source_id = fact.get(
                    "source_id", "",
                )
                if source_id:
                    citation = {
                        "source_id": source_id,
                        "fact": fact.get(
                            "content", "",
                        )[:100],
                    }
                    citations.append(citation)
                    self._citations.append(
                        citation,
                    )
                    self._stats[
                        "citations_managed"
                    ] += 1

        report = {
            "report_id": rid,
            "title": title,
            "format": fmt,
            "content": content,
            "word_count": len(content.split()),
            "citations": citations,
            "citation_count": len(citations),
            "insights_count": len(insights),
            "gaps_count": len(gaps),
            "timestamp": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def add_citation(
        self,
        source_id: str,
        title: str = "",
        url: str = "",
        author: str = "",
    ) -> dict[str, Any]:
        """Atıf ekler.

        Args:
            source_id: Kaynak ID.
            title: Başlık.
            url: URL.
            author: Yazar.

        Returns:
            Atıf bilgisi.
        """
        citation = {
            "source_id": source_id,
            "title": title,
            "url": url,
            "author": author,
            "added_at": time.time(),
        }
        self._citations.append(citation)
        self._stats["citations_managed"] += 1

        return {
            "source_id": source_id,
            "added": True,
        }

    def export(
        self,
        report_id: str,
        export_format: str = "markdown",
    ) -> dict[str, Any]:
        """Raporu dışa aktarır.

        Args:
            report_id: Rapor ID.
            export_format: Dışa aktarma formatı.

        Returns:
            Dışa aktarma bilgisi.
        """
        report = None
        for r in self._reports:
            if r["report_id"] == report_id:
                report = r
                break

        if not report:
            return {"error": "report_not_found"}

        self._stats["exports"] += 1

        return {
            "report_id": report_id,
            "format": export_format,
            "content": report["content"],
            "exported": True,
        }

    def get_report(
        self,
        report_id: str,
    ) -> dict[str, Any]:
        """Rapor getirir.

        Args:
            report_id: Rapor ID.

        Returns:
            Rapor bilgisi.
        """
        for r in self._reports:
            if r["report_id"] == report_id:
                return dict(r)
        return {"error": "report_not_found"}

    def get_reports(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Raporları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Rapor listesi.
        """
        return list(self._reports[-limit:])

    def get_citations(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Atıfları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Atıf listesi.
        """
        return list(self._citations[-limit:])

    @property
    def report_count(self) -> int:
        """Rapor sayısı."""
        return self._stats["reports_generated"]

    @property
    def citation_count(self) -> int:
        """Atıf sayısı."""
        return self._stats["citations_managed"]

    @property
    def export_count(self) -> int:
        """Dışa aktarma sayısı."""
        return self._stats["exports"]
