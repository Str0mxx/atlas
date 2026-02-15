"""ATLAS Uyku Döngüsü Yöneticisi modülü.

Kullanıcı müsaitliği, sessiz saatler,
uyanma tetikleyicileri, acil durum override,
saat dilimi farkındalığı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SleepCycleManager:
    """Uyku döngüsü yöneticisi.

    Kullanıcı müsaitliğine göre davranışı yönetir.

    Attributes:
        _quiet_start: Sessiz saat başlangıcı.
        _quiet_end: Sessiz saat bitişi.
        _timezone_offset: Saat dilimi farkı.
        _wake_triggers: Uyanma tetikleyicileri.
    """

    def __init__(
        self,
        quiet_start: int = 23,
        quiet_end: int = 7,
        timezone_offset: int = 3,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            quiet_start: Sessiz saat başlangıcı.
            quiet_end: Sessiz saat bitişi.
            timezone_offset: UTC saat farkı.
        """
        self._quiet_start = quiet_start
        self._quiet_end = quiet_end
        self._timezone_offset = timezone_offset
        self._wake_triggers: list[
            dict[str, Any]
        ] = []
        self._overrides: list[
            dict[str, Any]
        ] = []
        self._availability: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "quiet_checks": 0,
            "overrides_used": 0,
            "wake_triggers_fired": 0,
        }

        logger.info(
            "SleepCycleManager baslatildi",
        )

    def is_quiet_hours(
        self,
        current_hour: int | None = None,
    ) -> dict[str, Any]:
        """Sessiz saat kontrolü yapar.

        Args:
            current_hour: Güncel saat (None=otomatik).

        Returns:
            Kontrol bilgisi.
        """
        if current_hour is None:
            import datetime

            utc_now = datetime.datetime.now(
                datetime.timezone.utc,
            )
            current_hour = (
                utc_now.hour
                + self._timezone_offset
            ) % 24

        self._stats["quiet_checks"] += 1

        if self._quiet_start > self._quiet_end:
            # Gece yarısını kapsayan durum
            is_quiet = (
                current_hour >= self._quiet_start
                or current_hour < self._quiet_end
            )
        else:
            is_quiet = (
                self._quiet_start
                <= current_hour
                < self._quiet_end
            )

        return {
            "is_quiet": is_quiet,
            "current_hour": current_hour,
            "quiet_start": self._quiet_start,
            "quiet_end": self._quiet_end,
        }

    def set_quiet_hours(
        self,
        start: int,
        end: int,
    ) -> dict[str, Any]:
        """Sessiz saatleri ayarlar.

        Args:
            start: Başlangıç saati (0-23).
            end: Bitiş saati (0-23).

        Returns:
            Ayar bilgisi.
        """
        self._quiet_start = start % 24
        self._quiet_end = end % 24

        return {
            "quiet_start": self._quiet_start,
            "quiet_end": self._quiet_end,
            "updated": True,
        }

    def set_timezone(
        self,
        offset: int,
    ) -> dict[str, Any]:
        """Saat dilimi ayarlar.

        Args:
            offset: UTC saat farkı.

        Returns:
            Ayar bilgisi.
        """
        self._timezone_offset = offset
        return {
            "timezone_offset": offset,
            "updated": True,
        }

    def set_availability(
        self,
        user_id: str,
        available: bool = True,
        until: float | None = None,
    ) -> dict[str, Any]:
        """Kullanıcı müsaitliği ayarlar.

        Args:
            user_id: Kullanıcı ID.
            available: Müsait mi.
            until: Ne zamana kadar (timestamp).

        Returns:
            Ayar bilgisi.
        """
        self._availability[user_id] = {
            "available": available,
            "until": until,
            "set_at": time.time(),
        }

        return {
            "user_id": user_id,
            "available": available,
            "until": until,
        }

    def check_availability(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Kullanıcı müsaitliğini kontrol eder.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Müsaitlik bilgisi.
        """
        avail = self._availability.get(user_id)
        if not avail:
            return {
                "user_id": user_id,
                "available": True,
                "reason": "no_availability_set",
            }

        now = time.time()
        if avail.get("until") and avail["until"] < now:
            # Süre dolmuş, müsait
            return {
                "user_id": user_id,
                "available": True,
                "reason": "period_expired",
            }

        return {
            "user_id": user_id,
            "available": avail["available"],
        }

    def add_wake_trigger(
        self,
        name: str,
        condition: str,
        priority_min: int = 8,
    ) -> dict[str, Any]:
        """Uyanma tetikleyicisi ekler.

        Args:
            name: Tetikleyici adı.
            condition: Koşul açıklaması.
            priority_min: Min öncelik eşiği.

        Returns:
            Ekleme bilgisi.
        """
        trigger = {
            "name": name,
            "condition": condition,
            "priority_min": priority_min,
            "active": True,
            "created_at": time.time(),
        }
        self._wake_triggers.append(trigger)

        return {
            "name": name,
            "added": True,
        }

    def check_wake_trigger(
        self,
        event_type: str,
        priority: int,
    ) -> dict[str, Any]:
        """Uyanma tetikleyicisini kontrol eder.

        Args:
            event_type: Olay tipi.
            priority: Olay önceliği.

        Returns:
            Kontrol bilgisi.
        """
        should_wake = False
        matched_triggers = []

        for trigger in self._wake_triggers:
            if not trigger.get("active"):
                continue
            if priority >= trigger["priority_min"]:
                should_wake = True
                matched_triggers.append(
                    trigger["name"],
                )

        if should_wake:
            self._stats[
                "wake_triggers_fired"
            ] += 1

        return {
            "should_wake": should_wake,
            "event_type": event_type,
            "priority": priority,
            "matched_triggers": matched_triggers,
        }

    def emergency_override(
        self,
        reason: str,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Acil durum override yapar.

        Args:
            reason: Neden.
            duration_minutes: Süre (dakika).

        Returns:
            Override bilgisi.
        """
        override = {
            "reason": reason,
            "duration_minutes": duration_minutes,
            "start_at": time.time(),
            "end_at": (
                time.time()
                + duration_minutes * 60
            ),
            "active": True,
        }
        self._overrides.append(override)
        self._stats["overrides_used"] += 1

        return {
            "override": True,
            "reason": reason,
            "duration_minutes": duration_minutes,
        }

    def has_active_override(self) -> bool:
        """Aktif override var mı kontrol eder.

        Returns:
            Override durumu.
        """
        now = time.time()
        for override in self._overrides:
            if (
                override.get("active")
                and override.get("end_at", 0) > now
            ):
                return True
        return False

    def should_notify(
        self,
        priority: int,
        current_hour: int | None = None,
    ) -> dict[str, Any]:
        """Bildirim gönderilmeli mi kontrol eder.

        Args:
            priority: Bildirim önceliği.
            current_hour: Güncel saat.

        Returns:
            Karar bilgisi.
        """
        quiet = self.is_quiet_hours(current_hour)

        if not quiet["is_quiet"]:
            return {
                "should_notify": True,
                "reason": "not_quiet_hours",
            }

        # Acil durum override
        if self.has_active_override():
            return {
                "should_notify": True,
                "reason": "emergency_override",
            }

        # Yüksek öncelik ise
        if priority >= 8:
            return {
                "should_notify": True,
                "reason": "high_priority",
            }

        return {
            "should_notify": False,
            "reason": "quiet_hours",
        }

    @property
    def quiet_hours(self) -> tuple[int, int]:
        """Sessiz saatler."""
        return (
            self._quiet_start,
            self._quiet_end,
        )

    @property
    def trigger_count(self) -> int:
        """Tetikleyici sayısı."""
        return len(self._wake_triggers)
