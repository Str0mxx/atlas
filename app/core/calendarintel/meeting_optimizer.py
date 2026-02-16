"""ATLAS Toplantı Optimizasyonu modülü.

Optimal zaman bulma, süre optimizasyonu,
katılımcı müsaitliği, oda ayırma,
tampon zaman.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MeetingOptimizer:
    """Toplantı optimizasyonu.

    Toplantıları optimize eder.

    Attributes:
        _meetings: Toplantı kayıtları.
        _rooms: Oda kayıtları.
    """

    def __init__(self) -> None:
        """Optimizasyonu başlatır."""
        self._meetings: list[
            dict[str, Any]
        ] = []
        self._rooms: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "meetings_optimized": 0,
            "rooms_booked": 0,
        }

        logger.info(
            "MeetingOptimizer baslatildi",
        )

    def find_optimal_time(
        self,
        participants: list[str]
        | None = None,
        duration_minutes: int = 60,
        preferred_hour: int = 10,
        date: str = "",
    ) -> dict[str, Any]:
        """Optimal zaman bulur.

        Args:
            participants: Katılımcılar.
            duration_minutes: Süre (dk).
            preferred_hour: Tercih saati.
            date: Tarih.

        Returns:
            Bulunan zaman bilgisi.
        """
        participants = participants or []
        self._counter += 1
        mid = f"opt_{self._counter}"

        # Tercih saatine en yakın slot
        best_hour = preferred_hour
        if best_hour < 9:
            best_hour = 9
        elif best_hour > 17:
            best_hour = 17

        suggested_start = (
            f"{date} {best_hour:02d}:00"
            if date
            else f"{best_hour:02d}:00"
        )

        end_hour = best_hour + (
            duration_minutes // 60
        )
        end_min = duration_minutes % 60
        suggested_end = (
            f"{date} {end_hour:02d}"
            f":{end_min:02d}"
            if date
            else (
                f"{end_hour:02d}"
                f":{end_min:02d}"
            )
        )

        self._stats[
            "meetings_optimized"
        ] += 1

        return {
            "optimization_id": mid,
            "suggested_start": (
                suggested_start
            ),
            "suggested_end": suggested_end,
            "duration_minutes": (
                duration_minutes
            ),
            "participants": len(
                participants,
            ),
            "found": True,
        }

    def optimize_duration(
        self,
        meeting_type: str = "review",
        participant_count: int = 1,
        topics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Süre optimize eder.

        Args:
            meeting_type: Toplantı tipi.
            participant_count: Katılımcı sayısı.
            topics: Konular.

        Returns:
            Optimizasyon bilgisi.
        """
        topics = topics or []

        base_durations = {
            "standup": 15,
            "one_on_one": 30,
            "review": 45,
            "planning": 60,
        }

        base = base_durations.get(
            meeting_type, 45,
        )

        # Konu ve katılımcıya göre ayarla
        topic_add = len(topics) * 5
        participant_add = max(
            0, (participant_count - 3) * 5,
        )

        optimal = min(
            base + topic_add
            + participant_add,
            120,
        )

        return {
            "meeting_type": meeting_type,
            "base_duration": base,
            "optimal_duration": optimal,
            "topics_count": len(topics),
            "optimized": True,
        }

    def check_availability(
        self,
        participants: list[str]
        | None = None,
        hour: int = 10,
    ) -> dict[str, Any]:
        """Katılımcı müsaitliği kontrol eder.

        Args:
            participants: Katılımcılar.
            hour: Saat.

        Returns:
            Müsaitlik bilgisi.
        """
        participants = participants or []

        available = []
        unavailable = []

        for p in participants:
            # Basit simülasyon
            is_avail = 9 <= hour <= 17
            if is_avail:
                available.append(p)
            else:
                unavailable.append(p)

        return {
            "hour": hour,
            "available": available,
            "unavailable": unavailable,
            "all_available": len(
                unavailable,
            ) == 0,
            "checked": True,
        }

    def book_room(
        self,
        room_name: str = "",
        capacity: int = 10,
        hour: int = 10,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Oda ayırır.

        Args:
            room_name: Oda adı.
            capacity: Kapasite.
            hour: Saat.
            duration_minutes: Süre.

        Returns:
            Ayırma bilgisi.
        """
        self._counter += 1
        bid = f"rm_{self._counter}"

        self._rooms[bid] = {
            "booking_id": bid,
            "room_name": room_name,
            "capacity": capacity,
            "hour": hour,
            "duration": duration_minutes,
            "timestamp": time.time(),
        }
        self._stats["rooms_booked"] += 1

        return {
            "booking_id": bid,
            "room_name": room_name,
            "hour": hour,
            "booked": True,
        }

    def add_buffer_time(
        self,
        meetings: list[dict[str, Any]]
        | None = None,
        buffer_minutes: int = 15,
    ) -> dict[str, Any]:
        """Tampon zaman ekler.

        Args:
            meetings: Toplantılar.
            buffer_minutes: Tampon (dk).

        Returns:
            Ekleme bilgisi.
        """
        meetings = meetings or []

        adjusted = []
        for i, m in enumerate(meetings):
            entry = dict(m)
            if i > 0:
                entry["buffer_before"] = (
                    buffer_minutes
                )
            else:
                entry["buffer_before"] = 0
            adjusted.append(entry)

        total_buffer = (
            buffer_minutes
            * max(len(meetings) - 1, 0)
        )

        return {
            "meetings": adjusted,
            "buffer_minutes": buffer_minutes,
            "total_buffer": total_buffer,
            "adjusted": True,
        }

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "meetings_optimized"
        ]

    @property
    def booking_count(self) -> int:
        """Ayırma sayısı."""
        return self._stats[
            "rooms_booked"
        ]
