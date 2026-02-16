"""ATLAS Konuşmacı Takipçisi.

Konuşmacı veritabanı, konu uzmanlığı,
uygunluk takibi, rezervasyon ve değerlendirme.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SpeakerTracker:
    """Konuşmacı takipçisi.

    Konuşmacıları takip eder, uzmanlık
    alanlarını eşler ve rezervasyon yönetir.

    Attributes:
        _speakers: Konuşmacı kayıtları.
        _bookings: Rezervasyon kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._speakers: dict[str, dict] = {}
        self._bookings: dict[str, dict] = {}
        self._stats = {
            "speakers_tracked": 0,
            "bookings_made": 0,
        }
        logger.info(
            "SpeakerTracker baslatildi",
        )

    @property
    def tracked_count(self) -> int:
        """Takip edilen konuşmacı sayısı."""
        return self._stats[
            "speakers_tracked"
        ]

    @property
    def booking_count(self) -> int:
        """Yapılan rezervasyon sayısı."""
        return self._stats["bookings_made"]

    def add_speaker(
        self,
        name: str,
        topics: list[str] | None = None,
        tier: str = "regular",
    ) -> dict[str, Any]:
        """Konuşmacı ekler.

        Args:
            name: Konuşmacı adı.
            topics: Uzmanlık konuları.
            tier: Konuşmacı seviyesi.

        Returns:
            Konuşmacı bilgisi.
        """
        if topics is None:
            topics = []

        sid = (
            f"spk_{len(self._speakers)}"
        )
        self._speakers[sid] = {
            "name": name,
            "topics": topics,
            "tier": tier,
            "available": True,
            "ratings": [],
        }
        self._stats[
            "speakers_tracked"
        ] += 1

        logger.info(
            "Konusmaci eklendi: %s (%s)",
            name,
            tier,
        )

        return {
            "speaker_id": sid,
            "name": name,
            "tier": tier,
            "topic_count": len(topics),
            "added": True,
        }

    def find_by_topic(
        self,
        topic: str,
    ) -> dict[str, Any]:
        """Konuya göre konuşmacı bulur.

        Args:
            topic: Konu.

        Returns:
            Arama bilgisi.
        """
        matches = [
            sid
            for sid, s in (
                self._speakers.items()
            )
            if topic.lower()
            in [t.lower() for t in s["topics"]]
        ]

        return {
            "topic": topic,
            "match_count": len(matches),
            "speaker_ids": matches,
            "found": True,
        }

    def check_availability(
        self,
        speaker_id: str,
    ) -> dict[str, Any]:
        """Uygunluk kontrol eder.

        Args:
            speaker_id: Konuşmacı kimliği.

        Returns:
            Uygunluk bilgisi.
        """
        if speaker_id not in self._speakers:
            return {
                "speaker_id": speaker_id,
                "available": False,
                "found": False,
            }

        available = self._speakers[
            speaker_id
        ]["available"]

        return {
            "speaker_id": speaker_id,
            "available": available,
            "found": True,
        }

    def book_speaker(
        self,
        speaker_id: str,
        event_id: str = "",
        date: str = "",
    ) -> dict[str, Any]:
        """Konuşmacı rezervasyonu yapar.

        Args:
            speaker_id: Konuşmacı kimliği.
            event_id: Etkinlik kimliği.
            date: Tarih.

        Returns:
            Rezervasyon bilgisi.
        """
        if speaker_id not in self._speakers:
            return {
                "speaker_id": speaker_id,
                "booked": False,
            }

        bid = (
            f"bk_{len(self._bookings)}"
        )
        self._bookings[bid] = {
            "speaker_id": speaker_id,
            "event_id": event_id,
            "date": date,
        }
        self._speakers[speaker_id][
            "available"
        ] = False
        self._stats["bookings_made"] += 1

        return {
            "booking_id": bid,
            "speaker_id": speaker_id,
            "event_id": event_id,
            "booked": True,
        }

    def rate_speaker(
        self,
        speaker_id: str,
        rating: float = 0.0,
        feedback: str = "",
    ) -> dict[str, Any]:
        """Konuşmacı değerlendirir.

        Args:
            speaker_id: Konuşmacı kimliği.
            rating: Puan (0-5).
            feedback: Geri bildirim.

        Returns:
            Değerlendirme bilgisi.
        """
        if speaker_id not in self._speakers:
            return {
                "speaker_id": speaker_id,
                "rated": False,
            }

        self._speakers[speaker_id][
            "ratings"
        ].append(rating)
        ratings = self._speakers[
            speaker_id
        ]["ratings"]
        avg = round(
            sum(ratings) / len(ratings), 1,
        )

        return {
            "speaker_id": speaker_id,
            "rating": rating,
            "average_rating": avg,
            "total_ratings": len(ratings),
            "rated": True,
        }
