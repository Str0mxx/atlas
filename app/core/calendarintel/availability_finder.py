"""ATLAS Müsaitlik Bulucu modülü.

Boş slot tespiti, çoklu kişi müsaitliği,
tercih eşleştirme, çakışma önleme,
öneri sıralama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CalendarAvailabilityFinder:
    """Müsaitlik bulucu.

    Takvimde boş zamanları bulur.

    Attributes:
        _calendars: Takvim kayıtları.
        _preferences: Tercih kayıtları.
    """

    def __init__(self) -> None:
        """Bulucuyu başlatır."""
        self._calendars: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._preferences: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "slots_found": 0,
            "searches_performed": 0,
        }

        logger.info(
            "CalendarAvailabilityFinder "
            "baslatildi",
        )

    def add_event(
        self,
        person: str,
        start_hour: int = 9,
        end_hour: int = 10,
        title: str = "",
    ) -> dict[str, Any]:
        """Etkinlik ekler.

        Args:
            person: Kişi.
            start_hour: Başlangıç saati.
            end_hour: Bitiş saati.
            title: Başlık.

        Returns:
            Ekleme bilgisi.
        """
        if person not in self._calendars:
            self._calendars[person] = []

        self._calendars[person].append({
            "start_hour": start_hour,
            "end_hour": end_hour,
            "title": title,
        })

        return {
            "person": person,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "added": True,
        }

    def find_free_slots(
        self,
        person: str,
        work_start: int = 9,
        work_end: int = 18,
    ) -> dict[str, Any]:
        """Boş slot tespit eder.

        Args:
            person: Kişi.
            work_start: İş başlangıcı.
            work_end: İş bitişi.

        Returns:
            Tespit bilgisi.
        """
        events = self._calendars.get(
            person, [],
        )

        busy_hours: set[int] = set()
        for e in events:
            for h in range(
                e["start_hour"],
                e["end_hour"],
            ):
                busy_hours.add(h)

        free_slots = []
        slot_start = None

        for h in range(work_start, work_end):
            if h not in busy_hours:
                if slot_start is None:
                    slot_start = h
            else:
                if slot_start is not None:
                    free_slots.append({
                        "start_hour": (
                            slot_start
                        ),
                        "end_hour": h,
                        "duration": (
                            h - slot_start
                        ),
                    })
                    slot_start = None

        if slot_start is not None:
            free_slots.append({
                "start_hour": slot_start,
                "end_hour": work_end,
                "duration": (
                    work_end - slot_start
                ),
            })

        self._stats["slots_found"] += len(
            free_slots,
        )
        self._stats[
            "searches_performed"
        ] += 1

        return {
            "person": person,
            "free_slots": free_slots,
            "count": len(free_slots),
            "found": len(free_slots) > 0,
        }

    def find_multi_person(
        self,
        persons: list[str] | None = None,
        duration_hours: int = 1,
        work_start: int = 9,
        work_end: int = 18,
    ) -> dict[str, Any]:
        """Çoklu kişi müsaitliği bulur.

        Args:
            persons: Kişiler.
            duration_hours: Süre (saat).
            work_start: İş başlangıcı.
            work_end: İş bitişi.

        Returns:
            Bulunan bilgisi.
        """
        persons = persons or []

        all_busy: set[int] = set()
        for person in persons:
            events = self._calendars.get(
                person, [],
            )
            for e in events:
                for h in range(
                    e["start_hour"],
                    e["end_hour"],
                ):
                    all_busy.add(h)

        common_slots = []
        slot_start = None
        consecutive = 0

        for h in range(work_start, work_end):
            if h not in all_busy:
                if slot_start is None:
                    slot_start = h
                consecutive += 1
            else:
                if (
                    slot_start is not None
                    and consecutive
                    >= duration_hours
                ):
                    common_slots.append({
                        "start_hour": (
                            slot_start
                        ),
                        "end_hour": (
                            slot_start
                            + consecutive
                        ),
                        "duration": (
                            consecutive
                        ),
                    })
                slot_start = None
                consecutive = 0

        if (
            slot_start is not None
            and consecutive >= duration_hours
        ):
            common_slots.append({
                "start_hour": slot_start,
                "end_hour": (
                    slot_start + consecutive
                ),
                "duration": consecutive,
            })

        return {
            "persons": persons,
            "common_slots": common_slots,
            "count": len(common_slots),
            "found": len(
                common_slots,
            ) > 0,
        }

    def match_preferences(
        self,
        person: str,
        preferred_hours: list[int]
        | None = None,
    ) -> dict[str, Any]:
        """Tercih eşleştirme yapar.

        Args:
            person: Kişi.
            preferred_hours: Tercih saatleri.

        Returns:
            Eşleştirme bilgisi.
        """
        preferred_hours = (
            preferred_hours or [10, 14]
        )

        self._preferences[person] = {
            "preferred_hours": (
                preferred_hours
            ),
        }

        free = self.find_free_slots(person)
        matched = []

        for slot in free.get(
            "free_slots", [],
        ):
            for ph in preferred_hours:
                if (
                    slot["start_hour"] <= ph
                    < slot["end_hour"]
                ):
                    matched.append({
                        "hour": ph,
                        "slot": slot,
                    })
                    break

        return {
            "person": person,
            "matched_slots": matched,
            "count": len(matched),
            "matched": len(matched) > 0,
        }

    def rank_suggestions(
        self,
        slots: list[dict[str, Any]]
        | None = None,
        preferred_hour: int = 10,
    ) -> dict[str, Any]:
        """Öneri sıralar.

        Args:
            slots: Slotlar.
            preferred_hour: Tercih saati.

        Returns:
            Sıralama bilgisi.
        """
        slots = slots or []

        ranked = sorted(
            slots,
            key=lambda s: abs(
                s.get("start_hour", 12)
                - preferred_hour
            ),
        )

        for i, s in enumerate(ranked):
            s["rank"] = i + 1

        return {
            "ranked_slots": ranked,
            "count": len(ranked),
            "ranked": True,
        }

    @property
    def search_count(self) -> int:
        """Arama sayısı."""
        return self._stats[
            "searches_performed"
        ]

    @property
    def slots_found(self) -> int:
        """Bulunan slot sayısı."""
        return self._stats[
            "slots_found"
        ]
