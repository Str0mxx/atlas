"""ATLAS Patent Tarayıcı modülü.

Patent arama, başvuru trendleri,
inovasyon haritalama, özgürlük analizi,
rakip patentleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PatentScanner:
    """Patent tarayıcı.

    Patent verilerini tarar ve analiz eder.

    Attributes:
        _patents: Patent kayıtları.
    """

    def __init__(self) -> None:
        """Tarayıcıyı başlatır."""
        self._patents: dict[
            str, dict[str, Any]
        ] = {}
        self._searches: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "patents_scanned": 0,
            "searches_done": 0,
            "fto_analyses": 0,
        }

        logger.info(
            "PatentScanner baslatildi",
        )

    def scan_patent(
        self,
        title: str,
        assignee: str = "",
        filing_date: str = "",
        status: str = "filed",
        keywords: list[str] | None = None,
        classification: str = "",
    ) -> dict[str, Any]:
        """Patent tarar.

        Args:
            title: Başlık.
            assignee: Hak sahibi.
            filing_date: Başvuru tarihi.
            status: Durum.
            keywords: Anahtar kelimeler.
            classification: Sınıflandırma.

        Returns:
            Tarama bilgisi.
        """
        self._counter += 1
        pid = f"pat_{self._counter}"

        patent = {
            "patent_id": pid,
            "title": title,
            "assignee": assignee,
            "filing_date": filing_date,
            "status": status,
            "keywords": keywords or [],
            "classification": classification,
            "scanned_at": time.time(),
        }
        self._patents[pid] = patent
        self._stats["patents_scanned"] += 1

        return {
            "patent_id": pid,
            "title": title,
            "assignee": assignee,
            "status": status,
            "scanned": True,
        }

    def search_patents(
        self,
        query: str,
        assignee: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Patent arar.

        Args:
            query: Arama sorgusu.
            assignee: Hak sahibi filtresi.
            status: Durum filtresi.
            limit: Maks kayıt.

        Returns:
            Arama bilgisi.
        """
        query_lower = query.lower()
        results = []

        for patent in self._patents.values():
            match = (
                query_lower
                in patent["title"].lower()
                or any(
                    query_lower in kw.lower()
                    for kw in patent[
                        "keywords"
                    ]
                )
            )
            if assignee:
                match = match and (
                    patent["assignee"]
                    == assignee
                )
            if status:
                match = match and (
                    patent["status"] == status
                )
            if match:
                results.append(
                    dict(patent),
                )

        self._stats["searches_done"] += 1
        self._searches.append({
            "query": query,
            "results": len(results),
            "ts": time.time(),
        })

        return {
            "query": query,
            "results": results[:limit],
            "total": len(results),
        }

    def analyze_filing_trends(
        self,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Başvuru trendlerini analiz eder.

        Args:
            assignee: Hak sahibi filtresi.

        Returns:
            Analiz bilgisi.
        """
        patents = list(
            self._patents.values(),
        )
        if assignee:
            patents = [
                p for p in patents
                if p["assignee"] == assignee
            ]

        status_dist: dict[str, int] = {}
        for p in patents:
            s = p["status"]
            status_dist[s] = (
                status_dist.get(s, 0) + 1
            )

        return {
            "total_patents": len(patents),
            "status_distribution": status_dist,
            "assignee_filter": assignee,
        }

    def map_innovation(
        self,
        classification: str | None = None,
    ) -> dict[str, Any]:
        """İnovasyon haritalar.

        Args:
            classification: Sınıf filtresi.

        Returns:
            Haritalama bilgisi.
        """
        patents = list(
            self._patents.values(),
        )
        if classification:
            patents = [
                p for p in patents
                if p["classification"]
                == classification
            ]

        # Anahtar kelime frekansı
        kw_freq: dict[str, int] = {}
        for p in patents:
            for kw in p["keywords"]:
                kw_freq[kw] = (
                    kw_freq.get(kw, 0) + 1
                )

        top_keywords = sorted(
            kw_freq.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "total_patents": len(patents),
            "top_keywords": dict(
                top_keywords,
            ),
            "classification": classification,
        }

    def check_freedom_to_operate(
        self,
        technology: str,
        keywords: list[str],
    ) -> dict[str, Any]:
        """Özgürlük analizi yapar.

        Args:
            technology: Teknoloji.
            keywords: Anahtar kelimeler.

        Returns:
            Analiz bilgisi.
        """
        blocking = []
        for patent in self._patents.values():
            if patent["status"] not in (
                "granted", "pending",
            ):
                continue
            overlap = set(
                kw.lower()
                for kw in patent["keywords"]
            ) & set(
                kw.lower() for kw in keywords
            )
            if overlap:
                blocking.append({
                    "patent_id": patent[
                        "patent_id"
                    ],
                    "title": patent["title"],
                    "assignee": patent[
                        "assignee"
                    ],
                    "overlap": list(overlap),
                })

        self._stats["fto_analyses"] += 1

        risk = (
            "high" if len(blocking) > 3
            else "medium" if blocking
            else "low"
        )

        return {
            "technology": technology,
            "blocking_patents": blocking,
            "blocking_count": len(blocking),
            "risk_level": risk,
            "freedom": len(blocking) == 0,
        }

    def get_competitor_patents(
        self,
        assignee: str,
    ) -> list[dict[str, Any]]:
        """Rakip patentlerini getirir.

        Args:
            assignee: Hak sahibi.

        Returns:
            Patent listesi.
        """
        return [
            dict(p)
            for p in self._patents.values()
            if p["assignee"] == assignee
        ]

    @property
    def patent_count(self) -> int:
        """Patent sayısı."""
        return len(self._patents)

    @property
    def search_count(self) -> int:
        """Arama sayısı."""
        return self._stats["searches_done"]
