"""
Tehdit istihbarat akisi modulu.

Tehdit akislari, IOC esleme,
itibar puanlama, gercek zamanli
guncellemeler, entegrasyon.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ThreatIntelFeed:
    """Tehdit istihbarat akisi.

    Attributes:
        _feeds: Akis kayitlari.
        _iocs: IOC kayitlari.
        _reputation: Itibar kayitlari.
        _matches: Esleme kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Akisi baslatir."""
        self._feeds: list[dict] = []
        self._iocs: list[dict] = []
        self._reputation: dict[
            str, dict
        ] = {}
        self._matches: list[dict] = []
        self._stats: dict[str, int] = {
            "feeds_added": 0,
            "iocs_tracked": 0,
            "matches_found": 0,
        }
        logger.info(
            "ThreatIntelFeed baslatildi"
        )

    @property
    def ioc_count(self) -> int:
        """IOC sayisi."""
        return len(self._iocs)

    def add_feed(
        self,
        name: str = "",
        url: str = "",
        feed_type: str = "ip",
        update_frequency: str = "hourly",
    ) -> dict[str, Any]:
        """Akis ekler.

        Args:
            name: Akis adi.
            url: Akis URL'i.
            feed_type: Akis turu.
            update_frequency: Guncelleme sikligi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            fid = f"tf_{uuid4()!s:.8}"
            feed = {
                "feed_id": fid,
                "name": name,
                "url": url,
                "feed_type": feed_type,
                "update_frequency": (
                    update_frequency
                ),
                "active": True,
                "last_updated": None,
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._feeds.append(feed)
            self._stats["feeds_added"] += 1

            return {
                "feed_id": fid,
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def add_ioc(
        self,
        ioc_type: str = "",
        value: str = "",
        severity: str = "high",
        source: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """IOC ekler.

        Args:
            ioc_type: IOC turu (ip/domain/hash/url).
            value: IOC degeri.
            severity: Ciddiyet.
            source: Kaynak.
            description: Aciklama.

        Returns:
            Ekleme bilgisi.
        """
        try:
            iid = f"io_{uuid4()!s:.8}"
            ioc = {
                "ioc_id": iid,
                "type": ioc_type,
                "value": value,
                "severity": severity,
                "source": source,
                "description": description,
                "active": True,
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._iocs.append(ioc)
            self._stats["iocs_tracked"] += 1

            return {
                "ioc_id": iid,
                "type": ioc_type,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def check_ioc(
        self,
        value: str = "",
    ) -> dict[str, Any]:
        """IOC esleme kontrol eder.

        Args:
            value: Kontrol edilecek deger.

        Returns:
            Esleme bilgisi.
        """
        try:
            matches = [
                {
                    "ioc_id": i["ioc_id"],
                    "type": i["type"],
                    "severity": i["severity"],
                    "source": i["source"],
                }
                for i in self._iocs
                if i["value"] == value
                and i["active"]
            ]

            if matches:
                mid = f"im_{uuid4()!s:.8}"
                record = {
                    "match_id": mid,
                    "value": value,
                    "matches": matches,
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                self._matches.append(record)
                self._stats[
                    "matches_found"
                ] += len(matches)

            return {
                "value": value,
                "matched": len(matches) > 0,
                "matches": matches,
                "match_count": len(matches),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def set_reputation(
        self,
        entity: str = "",
        score: float = 0.0,
        category: str = "",
        details: str = "",
    ) -> dict[str, Any]:
        """Itibar puani ayarlar.

        Args:
            entity: Varlik (IP/domain).
            score: Puan (0-100, yuksek=guvenli).
            category: Kategori.
            details: Detaylar.

        Returns:
            Ayar bilgisi.
        """
        try:
            self._reputation[entity] = {
                "score": score,
                "category": category,
                "details": details,
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            return {
                "entity": entity,
                "score": score,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def get_reputation(
        self,
        entity: str = "",
    ) -> dict[str, Any]:
        """Itibar puani getirir.

        Args:
            entity: Varlik.

        Returns:
            Puan bilgisi.
        """
        try:
            rep = self._reputation.get(
                entity
            )
            if not rep:
                return {
                    "entity": entity,
                    "score": 50.0,
                    "category": "unknown",
                    "found": False,
                    "retrieved": True,
                }

            return {
                "entity": entity,
                "score": rep["score"],
                "category": rep["category"],
                "found": True,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def update_feed(
        self,
        feed_id: str = "",
    ) -> dict[str, Any]:
        """Akisi gunceller.

        Args:
            feed_id: Akis ID.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            for f in self._feeds:
                if f["feed_id"] == feed_id:
                    f[
                        "last_updated"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    return {
                        "feed_id": feed_id,
                        "updated": True,
                    }

            return {
                "updated": False,
                "error": "Akis bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            return {
                "total_feeds": len(
                    self._feeds
                ),
                "total_iocs": len(
                    self._iocs
                ),
                "total_matches": len(
                    self._matches
                ),
                "reputation_entries": len(
                    self._reputation
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
