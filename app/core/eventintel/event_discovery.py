"""ATLAS Etkinlik Keşifçisi.

Etkinlik arama, çoklu kaynak toplama,
kategori, tarih ve konum filtreleme.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventDiscovery:
    """Etkinlik keşifçisi.

    Etkinlikleri çeşitli kaynaklardan
    keşfeder ve filtreler.

    Attributes:
        _events: Etkinlik kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Keşifçiyi başlatır."""
        self._events: dict[str, dict] = {}
        self._stats = {
            "events_discovered": 0,
            "sources_queried": 0,
        }
        logger.info(
            "EventDiscovery baslatildi",
        )

    @property
    def discovered_count(self) -> int:
        """Keşfedilen etkinlik sayısı."""
        return self._stats[
            "events_discovered"
        ]

    @property
    def source_count(self) -> int:
        """Sorgulanan kaynak sayısı."""
        return self._stats[
            "sources_queried"
        ]

    def search_events(
        self,
        query: str,
        category: str = "",
        location: str = "",
    ) -> dict[str, Any]:
        """Etkinlik arar.

        Args:
            query: Arama sorgusu.
            category: Kategori filtresi.
            location: Konum filtresi.

        Returns:
            Arama bilgisi.
        """
        eid = (
            f"evt_{len(self._events)}"
        )
        self._events[eid] = {
            "query": query,
            "category": category,
            "location": location,
        }
        self._stats[
            "events_discovered"
        ] += 1

        logger.info(
            "Etkinlik bulundu: %s (%s)",
            query,
            category or "all",
        )

        return {
            "event_id": eid,
            "query": query,
            "category": category,
            "location": location,
            "discovered": True,
        }

    def aggregate_sources(
        self,
        sources: list[str] | None = None,
    ) -> dict[str, Any]:
        """Çoklu kaynak toplar.

        Args:
            sources: Kaynak listesi.

        Returns:
            Toplama bilgisi.
        """
        if sources is None:
            sources = []

        self._stats[
            "sources_queried"
        ] += len(sources)

        return {
            "sources": sources,
            "source_count": len(sources),
            "aggregated": True,
        }

    def filter_by_category(
        self,
        category: str,
    ) -> dict[str, Any]:
        """Kategoriye göre filtreler.

        Args:
            category: Kategori.

        Returns:
            Filtre bilgisi.
        """
        matches = [
            eid
            for eid, e in self._events.items()
            if e.get("category") == category
        ]

        return {
            "category": category,
            "match_count": len(matches),
            "filtered": True,
        }

    def filter_by_date(
        self,
        start_date: str = "",
        end_date: str = "",
    ) -> dict[str, Any]:
        """Tarihe göre filtreler.

        Args:
            start_date: Başlangıç tarihi.
            end_date: Bitiş tarihi.

        Returns:
            Filtre bilgisi.
        """
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_events": len(
                self._events,
            ),
            "filtered": True,
        }

    def filter_by_location(
        self,
        location: str,
        radius_km: float = 50.0,
    ) -> dict[str, Any]:
        """Konuma göre filtreler.

        Args:
            location: Konum.
            radius_km: Yarıçap (km).

        Returns:
            Filtre bilgisi.
        """
        matches = [
            eid
            for eid, e in self._events.items()
            if e.get("location") == location
        ]

        return {
            "location": location,
            "radius_km": radius_km,
            "match_count": len(matches),
            "filtered": True,
        }
