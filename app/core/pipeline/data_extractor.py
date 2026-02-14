"""ATLAS Veri Cikarici modulu.

Veritabani, API, dosya, web
ve akis kaynaklarindan veri
cikarma islemleri.
"""

import logging
import time
from typing import Any

from app.models.pipeline import SourceType

logger = logging.getLogger(__name__)


class DataExtractor:
    """Veri cikarici.

    Cesitli kaynaklardan veri cikarir
    ve pipeline icin hazirlar.

    Attributes:
        _sources: Kayitli kaynaklar.
        _extractions: Cikarma gecmisi.
    """

    def __init__(self) -> None:
        """Veri cikariciyi baslatir."""
        self._sources: dict[str, dict[str, Any]] = {}
        self._extractions: list[dict[str, Any]] = []

        logger.info("DataExtractor baslatildi")

    def register_source(
        self,
        name: str,
        source_type: SourceType,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kaynak kaydeder.

        Args:
            name: Kaynak adi.
            source_type: Kaynak turu.
            config: Yapilandirma.

        Returns:
            Kaynak bilgisi.
        """
        source = {
            "name": name,
            "type": source_type.value,
            "config": config or {},
            "enabled": True,
        }
        self._sources[name] = source
        return source

    def extract(
        self,
        source_name: str,
        query: str = "",
        limit: int = 0,
    ) -> dict[str, Any]:
        """Veri cikarir.

        Args:
            source_name: Kaynak adi.
            query: Sorgu.
            limit: Limit.

        Returns:
            Cikarma sonucu.
        """
        source = self._sources.get(source_name)
        if not source or not source["enabled"]:
            return {
                "success": False,
                "source": source_name,
                "reason": "source_not_found",
                "data": [],
            }

        start = time.time()
        # Simule edilmis veri cikarma
        data = self._simulate_extract(
            source, query, limit,
        )
        duration = time.time() - start

        result = {
            "success": True,
            "source": source_name,
            "type": source["type"],
            "record_count": len(data),
            "data": data,
            "duration": round(duration, 4),
        }
        self._extractions.append(result)

        logger.info(
            "Veri cikarildi: %s (%d kayit)",
            source_name, len(data),
        )
        return result

    def extract_batch(
        self,
        source_name: str,
        queries: list[str],
    ) -> list[dict[str, Any]]:
        """Toplu veri cikarir.

        Args:
            source_name: Kaynak adi.
            queries: Sorgu listesi.

        Returns:
            Cikarma sonuclari.
        """
        results: list[dict[str, Any]] = []
        for query in queries:
            result = self.extract(source_name, query)
            results.append(result)
        return results

    def extract_incremental(
        self,
        source_name: str,
        since: str = "",
        key_field: str = "id",
    ) -> dict[str, Any]:
        """Artimsal veri cikarir.

        Args:
            source_name: Kaynak adi.
            since: Son tarih/deger.
            key_field: Anahtar alan.

        Returns:
            Cikarma sonucu.
        """
        source = self._sources.get(source_name)
        if not source:
            return {
                "success": False,
                "source": source_name,
                "reason": "source_not_found",
                "data": [],
            }

        result = self.extract(
            source_name,
            f"incremental:{key_field}>{since}",
        )
        result["incremental"] = True
        result["since"] = since
        result["key_field"] = key_field
        return result

    def enable_source(self, name: str) -> bool:
        """Kaynak aktif eder.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili ise True.
        """
        source = self._sources.get(name)
        if source:
            source["enabled"] = True
            return True
        return False

    def disable_source(self, name: str) -> bool:
        """Kaynak devre disi birakir.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili ise True.
        """
        source = self._sources.get(name)
        if source:
            source["enabled"] = False
            return True
        return False

    def remove_source(self, name: str) -> bool:
        """Kaynak kaldirir.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili ise True.
        """
        if name in self._sources:
            del self._sources[name]
            return True
        return False

    def _simulate_extract(
        self,
        source: dict[str, Any],
        query: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Simule edilmis cikarma.

        Args:
            source: Kaynak.
            query: Sorgu.
            limit: Limit.

        Returns:
            Simule veri.
        """
        count = limit if limit > 0 else 5
        return [
            {
                "id": i + 1,
                "source": source["name"],
                "query": query,
            }
            for i in range(count)
        ]

    @property
    def source_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._sources)

    @property
    def extraction_count(self) -> int:
        """Cikarma sayisi."""
        return len(self._extractions)

    @property
    def total_records(self) -> int:
        """Toplam cikarilan kayit."""
        return sum(
            e["record_count"]
            for e in self._extractions
            if e.get("success")
        )
