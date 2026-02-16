"""ATLAS Saat Dilimi Yöneticisi modülü.

Saat dilimi dönüşümü, DST yönetimi,
katılımcı saat dilimleri, en iyi zaman,
görüntü biçimlendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

TIMEZONE_OFFSETS: dict[str, int] = {
    "UTC": 0,
    "EST": -5,
    "CST": -6,
    "MST": -7,
    "PST": -8,
    "CET": 1,
    "EET": 2,
    "IST": 5,
    "JST": 9,
    "AEST": 10,
    "TR": 3,
}


class CalendarTimezoneManager:
    """Saat dilimi yöneticisi.

    Saat dilimi dönüşümlerini yönetir.

    Attributes:
        _participant_tz: Katılımcı saat dilimleri.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._participant_tz: dict[
            str, str
        ] = {}
        self._counter = 0
        self._stats = {
            "conversions": 0,
            "best_times_found": 0,
        }

        logger.info(
            "CalendarTimezoneManager "
            "baslatildi",
        )

    def convert_timezone(
        self,
        hour: int,
        from_tz: str = "UTC",
        to_tz: str = "UTC",
    ) -> dict[str, Any]:
        """Saat dilimi dönüşümü yapar.

        Args:
            hour: Saat.
            from_tz: Kaynak saat dilimi.
            to_tz: Hedef saat dilimi.

        Returns:
            Dönüşüm bilgisi.
        """
        from_offset = TIMEZONE_OFFSETS.get(
            from_tz, 0,
        )
        to_offset = TIMEZONE_OFFSETS.get(
            to_tz, 0,
        )

        utc_hour = hour - from_offset
        converted = (
            utc_hour + to_offset
        ) % 24

        self._stats["conversions"] += 1

        return {
            "original_hour": hour,
            "from_tz": from_tz,
            "to_tz": to_tz,
            "converted_hour": converted,
            "converted": True,
        }

    def handle_dst(
        self,
        hour: int,
        timezone: str = "UTC",
        is_dst: bool = False,
    ) -> dict[str, Any]:
        """DST yönetimi yapar.

        Args:
            hour: Saat.
            timezone: Saat dilimi.
            is_dst: DST aktif mi.

        Returns:
            Yönetim bilgisi.
        """
        offset = TIMEZONE_OFFSETS.get(
            timezone, 0,
        )

        if is_dst:
            offset += 1

        adjusted = (hour + offset) % 24

        return {
            "original_hour": hour,
            "timezone": timezone,
            "is_dst": is_dst,
            "adjusted_hour": adjusted,
            "handled": True,
        }

    def set_participant_timezone(
        self,
        person: str,
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        """Katılımcı saat dilimi ayarlar.

        Args:
            person: Kişi.
            timezone: Saat dilimi.

        Returns:
            Ayarlama bilgisi.
        """
        self._participant_tz[person] = (
            timezone
        )

        return {
            "person": person,
            "timezone": timezone,
            "set": True,
        }

    def find_best_time(
        self,
        participants: list[str]
        | None = None,
        work_start: int = 9,
        work_end: int = 18,
    ) -> dict[str, Any]:
        """En iyi zaman hesaplar.

        Args:
            participants: Katılımcılar.
            work_start: İş başlangıcı.
            work_end: İş bitişi.

        Returns:
            Hesaplama bilgisi.
        """
        participants = participants or []

        if not participants:
            return {
                "best_hour_utc": 12,
                "found": False,
            }

        best_hour = None
        best_score = -1

        for utc_hour in range(24):
            score = 0
            for p in participants:
                tz = self._participant_tz.get(
                    p, "UTC",
                )
                offset = (
                    TIMEZONE_OFFSETS.get(
                        tz, 0,
                    )
                )
                local_hour = (
                    utc_hour + offset
                ) % 24

                if (
                    work_start
                    <= local_hour
                    < work_end
                ):
                    score += 1

            if score > best_score:
                best_score = score
                best_hour = utc_hour

        self._stats[
            "best_times_found"
        ] += 1

        participant_times = {}
        for p in participants:
            tz = self._participant_tz.get(
                p, "UTC",
            )
            offset = TIMEZONE_OFFSETS.get(
                tz, 0,
            )
            participant_times[p] = (
                (best_hour or 0) + offset
            ) % 24

        return {
            "best_hour_utc": best_hour,
            "participant_times": (
                participant_times
            ),
            "all_in_work_hours": (
                best_score
                == len(participants)
            ),
            "found": True,
        }

    def format_display(
        self,
        hour: int,
        timezone: str = "UTC",
        format_24h: bool = True,
    ) -> dict[str, Any]:
        """Görüntü biçimlendirir.

        Args:
            hour: Saat.
            timezone: Saat dilimi.
            format_24h: 24 saat formatı.

        Returns:
            Biçimlendirme bilgisi.
        """
        if format_24h:
            display = f"{hour:02d}:00"
        else:
            period = (
                "AM" if hour < 12
                else "PM"
            )
            h12 = hour % 12
            if h12 == 0:
                h12 = 12
            display = (
                f"{h12}:00 {period}"
            )

        return {
            "display": display,
            "timezone": timezone,
            "full_display": (
                f"{display} ({timezone})"
            ),
            "formatted": True,
        }

    @property
    def conversion_count(self) -> int:
        """Dönüşüm sayısı."""
        return self._stats["conversions"]

    @property
    def best_time_count(self) -> int:
        """En iyi zaman sayısı."""
        return self._stats[
            "best_times_found"
        ]
