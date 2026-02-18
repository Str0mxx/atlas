"""
Aktivite zaman cizelgesi modulu.

Kronolojik olay kaydi, kategorilendirme,
aktor takibi, zaman damgasi,
sonsuz kaydirma destegi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ActivityTimeline:
    """Aktivite zaman cizelgesi.

    Attributes:
        _events: Olay kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Zaman cizelgesini baslatir."""
        self._events: list[dict] = []
        self._stats: dict[str, int] = {
            "events_recorded": 0,
            "events_archived": 0,
        }
        logger.info(
            "ActivityTimeline baslatildi"
        )

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)

    def record_event(
        self,
        event_type: str = "action",
        actor: str = "",
        description: str = "",
        category: str = "system",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Olay kaydeder.

        Args:
            event_type: Olay turu.
            actor: Aktor.
            description: Aciklama.
            category: Kategori.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            eid = f"ev_{uuid4()!s:.8}"
            event = {
                "event_id": eid,
                "event_type": event_type,
                "actor": actor,
                "description": description,
                "category": category,
                "metadata": metadata or {},
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "status": "active",
            }
            self._events.append(event)
            self._stats["events_recorded"] += 1

            return {
                "event_id": eid,
                "event_type": event_type,
                "actor": actor,
                "category": category,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_timeline(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Zaman cizelgesi getirir.

        Args:
            page: Sayfa numarasi.
            page_size: Sayfa boyutu.

        Returns:
            Zaman cizelgesi.
        """
        try:
            sorted_events = sorted(
                self._events,
                key=lambda x: x.get(
                    "timestamp", ""
                ),
                reverse=True,
            )

            start = (page - 1) * page_size
            end = start + page_size
            page_events = sorted_events[
                start:end
            ]

            total_pages = max(
                1,
                (len(sorted_events) + page_size - 1)
                // page_size,
            )

            return {
                "events": page_events,
                "page": page,
                "page_size": page_size,
                "total_events": len(
                    sorted_events
                ),
                "total_pages": total_pages,
                "has_more": page < total_pages,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_by_actor(
        self,
        actor: str = "",
    ) -> dict[str, Any]:
        """Aktore gore olaylari getirir.

        Args:
            actor: Aktor adi.

        Returns:
            Olay listesi.
        """
        try:
            events = [
                e
                for e in self._events
                if e["actor"] == actor
            ]

            return {
                "actor": actor,
                "events": events,
                "event_count": len(events),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_by_category(
        self,
        category: str = "system",
    ) -> dict[str, Any]:
        """Kategoriye gore olaylari getirir.

        Args:
            category: Kategori.

        Returns:
            Olay listesi.
        """
        try:
            events = [
                e
                for e in self._events
                if e["category"] == category
            ]

            return {
                "category": category,
                "events": events,
                "event_count": len(events),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_by_type(
        self,
        event_type: str = "action",
    ) -> dict[str, Any]:
        """Ture gore olaylari getirir.

        Args:
            event_type: Olay turu.

        Returns:
            Olay listesi.
        """
        try:
            events = [
                e
                for e in self._events
                if e["event_type"] == event_type
            ]

            return {
                "event_type": event_type,
                "events": events,
                "event_count": len(events),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def archive_old_events(
        self,
        max_age_days: int = 90,
    ) -> dict[str, Any]:
        """Eski olaylari arsivler.

        Args:
            max_age_days: Maksimum yas (gun).

        Returns:
            Arsivleme bilgisi.
        """
        try:
            now = datetime.now(timezone.utc)
            archived = []
            remaining = []

            for event in self._events:
                ts = event.get("timestamp", "")
                if ts:
                    try:
                        evt_time = (
                            datetime.fromisoformat(
                                ts
                            )
                        )
                        age = (
                            now - evt_time
                        ).days
                        if age > max_age_days:
                            event["status"] = (
                                "archived"
                            )
                            archived.append(
                                event
                            )
                            continue
                    except (ValueError, TypeError):
                        pass
                remaining.append(event)

            self._events = remaining
            self._stats[
                "events_archived"
            ] += len(archived)

            return {
                "archived_count": len(
                    archived
                ),
                "remaining_count": len(
                    remaining
                ),
                "max_age_days": max_age_days,
                "archived": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "archived": False,
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
            categories: dict[str, int] = {}
            actors: dict[str, int] = {}
            types: dict[str, int] = {}

            for event in self._events:
                cat = event.get(
                    "category", "unknown"
                )
                categories[cat] = (
                    categories.get(cat, 0) + 1
                )

                actor = event.get(
                    "actor", "unknown"
                )
                actors[actor] = (
                    actors.get(actor, 0) + 1
                )

                etype = event.get(
                    "event_type", "unknown"
                )
                types[etype] = (
                    types.get(etype, 0) + 1
                )

            return {
                "total_events": len(
                    self._events
                ),
                "categories": categories,
                "actors": actors,
                "event_types": types,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
