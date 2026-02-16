"""ATLAS Doğum Günü Hatırlatıcı modülü.

Tarih takibi, ön hatırlatma,
hediye önerileri, mesaj şablonları,
kutlama takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BirthdayReminder:
    """Doğum günü hatırlatıcı.

    Doğum günlerini takip ve hatırlatır.

    Attributes:
        _birthdays: Doğum günü kayıtları.
        _celebrations: Kutlama kayıtları.
    """

    def __init__(self) -> None:
        """Hatırlatıcıyı başlatır."""
        self._birthdays: dict[
            str, dict[str, Any]
        ] = {}
        self._celebrations: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "birthdays_tracked": 0,
            "reminders_sent": 0,
            "celebrations_done": 0,
        }

        logger.info(
            "BirthdayReminder baslatildi",
        )

    def track_birthday(
        self,
        contact_id: str,
        name: str,
        month: int,
        day: int,
        year: int = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        """Doğum günü takip eder.

        Args:
            contact_id: Kişi ID.
            name: İsim.
            month: Ay.
            day: Gün.
            year: Yıl (opsiyonel).
            notes: Notlar.

        Returns:
            Takip bilgisi.
        """
        self._birthdays[contact_id] = {
            "contact_id": contact_id,
            "name": name,
            "month": month,
            "day": day,
            "year": year,
            "notes": notes,
        }
        self._stats[
            "birthdays_tracked"
        ] += 1

        return {
            "contact_id": contact_id,
            "name": name,
            "date": f"{month:02d}-{day:02d}",
            "tracked": True,
        }

    def check_upcoming(
        self,
        current_month: int,
        current_day: int,
        days_ahead: int = 7,
    ) -> list[dict[str, Any]]:
        """Yaklaşan doğum günlerini kontrol eder.

        Args:
            current_month: Mevcut ay.
            current_day: Mevcut gün.
            days_ahead: Gün ileride.

        Returns:
            Yaklaşan doğum günleri.
        """
        upcoming = []

        for bd in self._birthdays.values():
            # Basit gün farkı hesabı
            bd_day_of_year = (
                bd["month"] * 30 + bd["day"]
            )
            curr_day_of_year = (
                current_month * 30
                + current_day
            )

            diff = (
                bd_day_of_year
                - curr_day_of_year
            )
            if diff < 0:
                diff += 365

            if diff <= days_ahead:
                upcoming.append({
                    "contact_id": bd[
                        "contact_id"
                    ],
                    "name": bd["name"],
                    "month": bd["month"],
                    "day": bd["day"],
                    "days_until": diff,
                })

        upcoming.sort(
            key=lambda x: x["days_until"],
        )
        return upcoming

    def suggest_gift(
        self,
        contact_id: str,
        budget: float = 50.0,
        relationship: str = "colleague",
    ) -> dict[str, Any]:
        """Hediye önerir.

        Args:
            contact_id: Kişi ID.
            budget: Bütçe.
            relationship: İlişki tipi.

        Returns:
            Hediye önerileri.
        """
        suggestions = []

        if relationship in (
            "client", "partner",
        ):
            if budget >= 100:
                suggestions = [
                    "Premium gift box",
                    "Experience voucher",
                    "Personalized item",
                ]
            else:
                suggestions = [
                    "Quality chocolate box",
                    "Book",
                    "Gift card",
                ]
        elif relationship == "colleague":
            suggestions = [
                "Coffee mug",
                "Desk accessory",
                "Gift card",
            ]
        else:
            suggestions = [
                "Card with message",
                "Flowers",
                "Small gift",
            ]

        return {
            "contact_id": contact_id,
            "budget": budget,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    def get_message_template(
        self,
        contact_id: str,
        tone: str = "professional",
    ) -> dict[str, Any]:
        """Mesaj şablonu döndürür.

        Args:
            contact_id: Kişi ID.
            tone: Ton.

        Returns:
            Şablon bilgisi.
        """
        bd = self._birthdays.get(
            contact_id,
        )
        name = bd["name"] if bd else "Friend"

        templates = {
            "professional": (
                f"Dear {name}, wishing you "
                f"a wonderful birthday! "
                f"Best regards."
            ),
            "friendly": (
                f"Happy Birthday {name}! "
                f"Hope you have an amazing "
                f"day!"
            ),
            "formal": (
                f"Dear {name}, on behalf of "
                f"the team, we wish you a "
                f"very happy birthday."
            ),
        }

        template = templates.get(
            tone,
            templates["professional"],
        )

        return {
            "contact_id": contact_id,
            "tone": tone,
            "message": template,
        }

    def record_celebration(
        self,
        contact_id: str,
        action: str = "",
        gift: str = "",
        message_sent: bool = False,
    ) -> dict[str, Any]:
        """Kutlama kaydeder.

        Args:
            contact_id: Kişi ID.
            action: Aksiyon.
            gift: Hediye.
            message_sent: Mesaj gönderildi mi.

        Returns:
            Kutlama bilgisi.
        """
        celebration = {
            "contact_id": contact_id,
            "action": action,
            "gift": gift,
            "message_sent": message_sent,
            "timestamp": time.time(),
        }
        self._celebrations.append(
            celebration,
        )
        self._stats[
            "celebrations_done"
        ] += 1

        return {
            "contact_id": contact_id,
            "recorded": True,
        }

    def get_birthday(
        self,
        contact_id: str,
    ) -> dict[str, Any] | None:
        """Doğum günü döndürür."""
        return self._birthdays.get(
            contact_id,
        )

    @property
    def tracked_count(self) -> int:
        """Takip edilen sayısı."""
        return self._stats[
            "birthdays_tracked"
        ]

    @property
    def celebration_count(self) -> int:
        """Kutlama sayısı."""
        return self._stats[
            "celebrations_done"
        ]
