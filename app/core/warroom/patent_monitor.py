"""ATLAS Rakip Patent İzleyici.

Patent takibi, başvuru analizi,
teknoloji trendleri, IP manzarası, tehdit.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CompetitorPatentMonitor:
    """Rakip patent izleyici.

    Rakip patent başvurularını izler,
    teknoloji trendlerini analiz eder.

    Attributes:
        _patents: Patent kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """İzleyiciyi başlatır."""
        self._patents: dict[
            str, list[dict]
        ] = {}
        self._stats = {
            "patents_tracked": 0,
            "threats_assessed": 0,
        }
        logger.info(
            "CompetitorPatentMonitor "
            "baslatildi",
        )

    @property
    def patent_count(self) -> int:
        """Takip edilen patent sayısı."""
        return self._stats[
            "patents_tracked"
        ]

    @property
    def threat_count(self) -> int:
        """Değerlendirilen tehdit sayısı."""
        return self._stats[
            "threats_assessed"
        ]

    def track_patent(
        self,
        competitor_id: str,
        title: str,
        technology: str = "",
        filed_year: int = 2024,
    ) -> dict[str, Any]:
        """Patent takip eder.

        Args:
            competitor_id: Rakip kimliği.
            title: Patent başlığı.
            technology: Teknoloji alanı.
            filed_year: Başvuru yılı.

        Returns:
            Takip bilgisi.
        """
        pid = f"pat_{str(uuid4())[:6]}"

        if competitor_id not in (
            self._patents
        ):
            self._patents[
                competitor_id
            ] = []

        self._patents[
            competitor_id
        ].append(
            {
                "patent_id": pid,
                "title": title,
                "technology": technology,
                "year": filed_year,
            },
        )
        self._stats[
            "patents_tracked"
        ] += 1

        return {
            "patent_id": pid,
            "competitor_id": competitor_id,
            "title": title,
            "technology": technology,
            "tracked": True,
        }

    def analyze_filings(
        self,
        competitor_id: str,
    ) -> dict[str, Any]:
        """Başvuru analizi yapar.

        Args:
            competitor_id: Rakip kimliği.

        Returns:
            Başvuru analizi bilgisi.
        """
        patents = self._patents.get(
            competitor_id, [],
        )
        total = len(patents)

        tech_counts: dict[str, int] = {}
        for p in patents:
            tech = p.get(
                "technology", "other",
            )
            tech_counts[tech] = (
                tech_counts.get(tech, 0)
                + 1
            )

        focus = (
            max(
                tech_counts,
                key=tech_counts.get,
            )
            if tech_counts
            else ""
        )

        if total >= 10:
            activity = "very_active"
        elif total >= 5:
            activity = "active"
        elif total >= 1:
            activity = "moderate"
        else:
            activity = "inactive"

        return {
            "competitor_id": competitor_id,
            "total_patents": total,
            "technologies": tech_counts,
            "primary_focus": focus,
            "activity_level": activity,
            "analyzed": True,
        }

    def identify_trends(
        self,
        patents: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Teknoloji trendlerini belirler.

        Args:
            patents: Patent listesi
                [{technology, year}].

        Returns:
            Trend bilgisi.
        """
        if patents is None:
            patents = []

        tech_by_year: dict[
            int, dict[str, int]
        ] = {}
        for p in patents:
            year = p.get("year", 2024)
            tech = p.get(
                "technology", "other",
            )
            if year not in tech_by_year:
                tech_by_year[year] = {}
            tech_by_year[year][tech] = (
                tech_by_year[year].get(
                    tech, 0,
                )
                + 1
            )

        all_techs: dict[str, int] = {}
        for techs in tech_by_year.values():
            for t, c in techs.items():
                all_techs[t] = (
                    all_techs.get(t, 0) + c
                )

        trending = sorted(
            all_techs.keys(),
            key=lambda t: all_techs[t],
            reverse=True,
        )[:3]

        return {
            "patent_count": len(patents),
            "trending_technologies": (
                trending
            ),
            "by_year": tech_by_year,
            "identified": True,
        }

    def map_ip_landscape(
        self,
        competitors: dict[str, int]
        | None = None,
        our_patents: int = 0,
    ) -> dict[str, Any]:
        """IP manzarasını haritalandırır.

        Args:
            competitors: Rakip patent sayıları.
            our_patents: Bizim patent sayısı.

        Returns:
            IP manzarası bilgisi.
        """
        if competitors is None:
            competitors = {}

        total_market = (
            our_patents
            + sum(competitors.values())
        )

        if total_market <= 0:
            our_share = 0.0
        else:
            our_share = round(
                our_patents
                / total_market
                * 100,
                1,
            )

        leader = "us"
        max_patents = our_patents
        for comp, count in (
            competitors.items()
        ):
            if count > max_patents:
                max_patents = count
                leader = comp

        return {
            "our_patents": our_patents,
            "total_market": total_market,
            "our_share": our_share,
            "leader": leader,
            "mapped": True,
        }

    def assess_threat(
        self,
        competitor_id: str,
        patent_overlap: float = 0.0,
        filing_velocity: int = 0,
        technology_relevance: float = 0.0,
    ) -> dict[str, Any]:
        """Patent tehdit değerlendirir.

        Args:
            competitor_id: Rakip kimliği.
            patent_overlap: Örtüşme (0-1).
            filing_velocity: Başvuru hızı.
            technology_relevance: Alaka (0-1).

        Returns:
            Tehdit bilgisi.
        """
        threat_score = round(
            patent_overlap * 0.4
            + min(filing_velocity / 10, 1.0)
            * 0.3
            + technology_relevance * 0.3,
            2,
        )

        if threat_score >= 0.7:
            level = "critical"
        elif threat_score >= 0.5:
            level = "high"
        elif threat_score >= 0.3:
            level = "moderate"
        else:
            level = "low"

        self._stats[
            "threats_assessed"
        ] += 1

        return {
            "competitor_id": competitor_id,
            "threat_score": threat_score,
            "level": level,
            "assessed": True,
        }
