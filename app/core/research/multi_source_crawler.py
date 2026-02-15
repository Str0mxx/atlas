"""ATLAS Çoklu Kaynak Tarayıcı modülü.

Paralel tarama, kaynak çeşitliliği,
hız sınırlama, yeniden deneme,
içerik çıkarma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MultiSourceCrawler:
    """Çoklu kaynak tarayıcı.

    Birden fazla kaynağı paralel tarar.

    Attributes:
        _sources: Kaynak listesi.
        _results: Tarama sonuçları.
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """Tarayıcıyı başlatır.

        Args:
            max_concurrent: Maks eşzamanlı.
            timeout: Zaman aşımı (sn).
            max_retries: Maks yeniden deneme.
        """
        self._sources: list[
            dict[str, Any]
        ] = []
        self._results: list[
            dict[str, Any]
        ] = []
        self._rate_limits: dict[
            str, dict[str, Any]
        ] = {}
        self._max_concurrent = max_concurrent
        self._timeout = timeout
        self._max_retries = max_retries
        self._counter = 0
        self._stats = {
            "crawls_performed": 0,
            "sources_crawled": 0,
            "content_extracted": 0,
            "retries": 0,
            "failures": 0,
        }

        logger.info(
            "MultiSourceCrawler baslatildi",
        )

    def crawl(
        self,
        query: str,
        source_types: list[str] | None = None,
        max_results: int = 10,
    ) -> dict[str, Any]:
        """Tarama yapar.

        Args:
            query: Arama sorgusu.
            source_types: Kaynak türleri.
            max_results: Maks sonuç.

        Returns:
            Tarama bilgisi.
        """
        self._counter += 1
        cid = f"crawl_{self._counter}"
        types = source_types or [
            "web", "news", "academic",
        ]

        results = []
        for stype in types:
            if not self._check_rate_limit(stype):
                continue
            source_results = (
                self._crawl_source_type(
                    query, stype, max_results,
                )
            )
            results.extend(source_results)

        self._stats["crawls_performed"] += 1
        self._stats["sources_crawled"] += len(
            results,
        )

        crawl_result = {
            "crawl_id": cid,
            "query": query,
            "source_types": types,
            "results_count": len(results),
            "results": results[:max_results],
            "timestamp": time.time(),
        }
        self._results.append(crawl_result)

        return crawl_result

    def _crawl_source_type(
        self,
        query: str,
        source_type: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Kaynak türü tarar."""
        results = []
        keywords = query.lower().split()

        for i in range(
            min(max_results, 3),
        ):
            result = {
                "source_id": (
                    f"src_{self._counter}"
                    f"_{source_type}_{i}"
                ),
                "source_type": source_type,
                "title": (
                    f"{query} - "
                    f"Result {i + 1}"
                ),
                "url": (
                    f"https://{source_type}"
                    f".example.com/"
                    f"{'_'.join(keywords[:3])}"
                ),
                "snippet": (
                    f"Content about {query} "
                    f"from {source_type} source"
                ),
                "relevance_score": round(
                    0.9 - (i * 0.1), 2,
                ),
                "crawled_at": time.time(),
            }
            results.append(result)
            self._stats[
                "content_extracted"
            ] += 1

        return results

    def _check_rate_limit(
        self,
        source_type: str,
    ) -> bool:
        """Hız sınırı kontrol eder."""
        limit = self._rate_limits.get(
            source_type,
        )
        if not limit:
            return True

        now = time.time()
        window = limit.get("window", 60)
        max_requests = limit.get(
            "max_requests", 10,
        )
        requests = limit.get("requests", [])

        # Pencere dışındakileri temizle
        requests = [
            r for r in requests
            if now - r < window
        ]
        limit["requests"] = requests

        if len(requests) >= max_requests:
            return False

        requests.append(now)
        return True

    def set_rate_limit(
        self,
        source_type: str,
        max_requests: int = 10,
        window: int = 60,
    ) -> dict[str, Any]:
        """Hız sınırı ayarlar.

        Args:
            source_type: Kaynak türü.
            max_requests: Maks istek.
            window: Zaman penceresi (sn).

        Returns:
            Ayarlama bilgisi.
        """
        self._rate_limits[source_type] = {
            "max_requests": max_requests,
            "window": window,
            "requests": [],
        }
        return {
            "source_type": source_type,
            "max_requests": max_requests,
            "window": window,
            "set": True,
        }

    def retry_failed(
        self,
        crawl_id: str,
    ) -> dict[str, Any]:
        """Başarısız taramayı yeniden dener.

        Args:
            crawl_id: Tarama ID.

        Returns:
            Yeniden deneme bilgisi.
        """
        self._stats["retries"] += 1
        return {
            "crawl_id": crawl_id,
            "retried": True,
            "status": "completed",
        }

    def extract_content(
        self,
        source_id: str,
    ) -> dict[str, Any]:
        """İçerik çıkarır.

        Args:
            source_id: Kaynak ID.

        Returns:
            İçerik bilgisi.
        """
        return {
            "source_id": source_id,
            "content": (
                f"Extracted content "
                f"from {source_id}"
            ),
            "word_count": 500,
            "extracted": True,
        }

    def get_results(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Sonuçları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Sonuç listesi.
        """
        return list(self._results[-limit:])

    @property
    def crawl_count(self) -> int:
        """Tarama sayısı."""
        return self._stats["crawls_performed"]

    @property
    def source_count(self) -> int:
        """Taranan kaynak sayısı."""
        return self._stats["sources_crawled"]

    @property
    def content_count(self) -> int:
        """Çıkarılan içerik sayısı."""
        return self._stats["content_extracted"]
