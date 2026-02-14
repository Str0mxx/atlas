"""ATLAS Takvim Yoneticisi modulu.

Etkinlik yonetimi, musaitlik takibi,
catisma tespiti, saat dilimi islemleri
ve tatil farkindaligi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.scheduler import CalendarEvent

logger = logging.getLogger(__name__)


class CalendarManager:
    """Takvim yoneticisi.

    Etkinlikleri yonetir, catismalari tespit
    eder ve musaitlik bilgisi saglar.

    Attributes:
        _events: Takvim etkinlikleri.
        _holidays: Tatil gunleri.
        _working_hours: Calisma saatleri.
    """

    def __init__(
        self,
        workday_start: str = "09:00",
        workday_end: str = "18:00",
    ) -> None:
        """Takvim yoneticisini baslatir.

        Args:
            workday_start: Is gunu baslangici.
            workday_end: Is gunu bitisi.
        """
        self._events: dict[str, CalendarEvent] = {}
        self._holidays: dict[str, str] = {}
        self._workday_start = workday_start
        self._workday_end = workday_end

        logger.info("CalendarManager baslatildi")

    def add_event(
        self,
        title: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        tz: str = "UTC",
        tags: list[str] | None = None,
    ) -> CalendarEvent:
        """Etkinlik ekler.

        Args:
            title: Etkinlik basligi.
            start_time: Baslama zamani.
            end_time: Bitis zamani.
            tz: Saat dilimi.
            tags: Etiketler.

        Returns:
            Olusturulan etkinlik.
        """
        event = CalendarEvent(
            title=title,
            start_time=start_time or datetime.now(timezone.utc),
            end_time=end_time,
            timezone=tz,
            tags=tags or [],
        )
        self._events[event.event_id] = event
        logger.info("Etkinlik eklendi: %s", title)
        return event

    def remove_event(self, event_id: str) -> bool:
        """Etkinlik siler.

        Args:
            event_id: Etkinlik ID.

        Returns:
            Basarili ise True.
        """
        if event_id in self._events:
            del self._events[event_id]
            return True
        return False

    def get_event(
        self,
        event_id: str,
    ) -> CalendarEvent | None:
        """Etkinlik getirir.

        Args:
            event_id: Etkinlik ID.

        Returns:
            Etkinlik veya None.
        """
        return self._events.get(event_id)

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        """Belirli araliktaki etkinlikleri getirir.

        Args:
            start: Baslangic.
            end: Bitis.

        Returns:
            Etkinlik listesi.
        """
        result: list[CalendarEvent] = []
        for event in self._events.values():
            if start <= event.start_time <= end:
                result.append(event)
        return sorted(
            result, key=lambda e: e.start_time,
        )

    def detect_conflicts(
        self,
        event: CalendarEvent,
    ) -> list[CalendarEvent]:
        """Catismalari tespit eder.

        Args:
            event: Kontrol edilecek etkinlik.

        Returns:
            Catisan etkinlikler.
        """
        conflicts: list[CalendarEvent] = []
        if not event.end_time:
            return conflicts

        for existing in self._events.values():
            if existing.event_id == event.event_id:
                continue
            if not existing.end_time:
                continue
            # Zaman araligi cakismasi
            if (
                event.start_time < existing.end_time
                and event.end_time > existing.start_time
            ):
                conflicts.append(existing)
        return conflicts

    def check_availability(
        self,
        start: datetime,
        end: datetime,
    ) -> bool:
        """Musaitlik kontrol eder.

        Args:
            start: Baslangic.
            end: Bitis.

        Returns:
            Musait ise True.
        """
        test_event = CalendarEvent(
            title="_check",
            start_time=start,
            end_time=end,
        )
        conflicts = self.detect_conflicts(test_event)
        return len(conflicts) == 0

    def add_holiday(
        self,
        date_str: str,
        name: str,
    ) -> None:
        """Tatil gunu ekler.

        Args:
            date_str: Tarih (YYYY-MM-DD).
            name: Tatil adi.
        """
        self._holidays[date_str] = name

    def is_holiday(self, date_str: str) -> bool:
        """Tatil gunu kontrol eder.

        Args:
            date_str: Tarih (YYYY-MM-DD).

        Returns:
            Tatil ise True.
        """
        return date_str in self._holidays

    def is_working_hours(
        self,
        hour: int,
    ) -> bool:
        """Calisma saati kontrol eder.

        Args:
            hour: Saat (0-23).

        Returns:
            Calisma saatinde ise True.
        """
        start_h = int(self._workday_start.split(":")[0])
        end_h = int(self._workday_end.split(":")[0])
        return start_h <= hour < end_h

    def get_events_by_tag(
        self,
        tag: str,
    ) -> list[CalendarEvent]:
        """Etikete gore etkinlikleri getirir.

        Args:
            tag: Etiket.

        Returns:
            Etkinlik listesi.
        """
        return [
            e for e in self._events.values()
            if tag in e.tags
        ]

    @property
    def event_count(self) -> int:
        """Etkinlik sayisi."""
        return len(self._events)

    @property
    def holiday_count(self) -> int:
        """Tatil sayisi."""
        return len(self._holidays)
