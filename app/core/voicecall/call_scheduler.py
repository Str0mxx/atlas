"""ATLAS Arama Zamanlayıcı modülü.

En iyi arama zamanı, saat dilimi,
yeniden deneme zamanlaması, hatırlatma aramaları,
toplu arama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CallScheduler:
    """Arama zamanlayıcı.

    Aramaları zamanlama ve optimize etme.

    Attributes:
        _schedules: Zamanlama kayıtları.
        _contact_prefs: İletişim tercihleri.
    """

    def __init__(
        self,
        default_timezone_offset: int = 3,
    ) -> None:
        """Zamanlayıcıyı başlatır.

        Args:
            default_timezone_offset: Varsayılan UTC farkı.
        """
        self._schedules: list[
            dict[str, Any]
        ] = []
        self._contact_prefs: dict[
            str, dict[str, Any]
        ] = {}
        self._reminders: list[
            dict[str, Any]
        ] = []
        self._batches: list[
            dict[str, Any]
        ] = []
        self._default_tz = default_timezone_offset
        self._counter = 0
        self._stats = {
            "scheduled": 0,
            "reminders_set": 0,
            "batches_created": 0,
        }

        logger.info(
            "CallScheduler baslatildi",
        )

    def schedule_call(
        self,
        callee: str,
        scheduled_time: float | None = None,
        purpose: str = "general",
        priority: int = 5,
        retry_on_fail: bool = True,
    ) -> dict[str, Any]:
        """Arama zamanlar.

        Args:
            callee: Aranan.
            scheduled_time: Zamanlanan vakit.
            purpose: Amaç.
            priority: Öncelik.
            retry_on_fail: Başarısızlıkta tekrar.

        Returns:
            Zamanlama bilgisi.
        """
        self._counter += 1
        sid = f"sched_{self._counter}"

        if scheduled_time is None:
            scheduled_time = (
                self._find_best_time(callee)
            )

        schedule = {
            "schedule_id": sid,
            "callee": callee,
            "scheduled_time": scheduled_time,
            "purpose": purpose,
            "priority": max(1, min(10, priority)),
            "retry_on_fail": retry_on_fail,
            "status": "pending",
            "created_at": time.time(),
        }
        self._schedules.append(schedule)
        self._stats["scheduled"] += 1

        return schedule

    def _find_best_time(
        self,
        callee: str,
    ) -> float:
        """En iyi arama zamanını bulur.

        Args:
            callee: Aranan.

        Returns:
            Timestamp.
        """
        prefs = self._contact_prefs.get(callee)
        if prefs:
            preferred_hour = prefs.get(
                "preferred_hour", 10,
            )
            tz_offset = prefs.get(
                "timezone_offset",
                self._default_tz,
            )
        else:
            preferred_hour = 10
            tz_offset = self._default_tz

        import datetime

        now = datetime.datetime.now(
            datetime.timezone.utc,
        )
        target = now.replace(
            hour=(
                (preferred_hour - tz_offset) % 24
            ),
            minute=0,
            second=0,
        )
        if target <= now:
            target += datetime.timedelta(days=1)

        return target.timestamp()

    def set_contact_preference(
        self,
        contact: str,
        preferred_hour: int = 10,
        timezone_offset: int = 3,
        do_not_call_hours: list[int]
        | None = None,
    ) -> dict[str, Any]:
        """İletişim tercihi ayarlar.

        Args:
            contact: İletişim kişisi.
            preferred_hour: Tercih edilen saat.
            timezone_offset: Saat dilimi.
            do_not_call_hours: Aranmayacak saatler.

        Returns:
            Ayar bilgisi.
        """
        self._contact_prefs[contact] = {
            "preferred_hour": preferred_hour,
            "timezone_offset": timezone_offset,
            "do_not_call_hours": (
                do_not_call_hours or []
            ),
        }
        return {
            "contact": contact,
            "preferences_set": True,
        }

    def check_timezone(
        self,
        contact: str,
    ) -> dict[str, Any]:
        """Saat dilimi kontrolü yapar.

        Args:
            contact: İletişim kişisi.

        Returns:
            Saat dilimi bilgisi.
        """
        prefs = self._contact_prefs.get(contact)
        tz_offset = (
            prefs.get(
                "timezone_offset",
                self._default_tz,
            )
            if prefs
            else self._default_tz
        )

        import datetime

        utc_now = datetime.datetime.now(
            datetime.timezone.utc,
        )
        local_hour = (
            utc_now.hour + tz_offset
        ) % 24

        is_business_hours = 9 <= local_hour < 18
        is_do_not_call = False
        if prefs:
            dnc = prefs.get(
                "do_not_call_hours", [],
            )
            is_do_not_call = local_hour in dnc

        return {
            "contact": contact,
            "timezone_offset": tz_offset,
            "local_hour": local_hour,
            "is_business_hours": is_business_hours,
            "is_do_not_call": is_do_not_call,
        }

    def schedule_retry(
        self,
        schedule_id: str,
        delay_minutes: int = 30,
    ) -> dict[str, Any]:
        """Yeniden deneme zamanlar.

        Args:
            schedule_id: Zamanlama ID.
            delay_minutes: Gecikme (dakika).

        Returns:
            Zamanlama bilgisi.
        """
        sched = None
        for s in self._schedules:
            if s["schedule_id"] == schedule_id:
                sched = s
                break

        if not sched:
            return {
                "error": "schedule_not_found",
            }

        retry = self.schedule_call(
            callee=sched["callee"],
            scheduled_time=(
                time.time() + delay_minutes * 60
            ),
            purpose=sched["purpose"],
            priority=sched["priority"],
        )
        retry["retry_of"] = schedule_id

        return retry

    def schedule_reminder(
        self,
        callee: str,
        message: str,
        remind_at: float | None = None,
        recurring: bool = False,
    ) -> dict[str, Any]:
        """Hatırlatma araması zamanlar.

        Args:
            callee: Aranan.
            message: Hatırlatma mesajı.
            remind_at: Hatırlatma zamanı.
            recurring: Tekrarlayan mı.

        Returns:
            Hatırlatma bilgisi.
        """
        reminder = {
            "callee": callee,
            "message": message,
            "remind_at": remind_at or (
                time.time() + 3600
            ),
            "recurring": recurring,
            "status": "pending",
            "created_at": time.time(),
        }
        self._reminders.append(reminder)
        self._stats["reminders_set"] += 1

        return {
            "reminder_set": True,
            "callee": callee,
            "recurring": recurring,
        }

    def create_batch(
        self,
        callees: list[str],
        purpose: str = "batch",
        interval_minutes: int = 5,
    ) -> dict[str, Any]:
        """Toplu arama oluşturur.

        Args:
            callees: Aranacaklar listesi.
            purpose: Amaç.
            interval_minutes: Aramalar arası süre.

        Returns:
            Toplu arama bilgisi.
        """
        batch_schedules = []
        base_time = time.time()

        for i, callee in enumerate(callees):
            sched = self.schedule_call(
                callee=callee,
                scheduled_time=(
                    base_time
                    + i * interval_minutes * 60
                ),
                purpose=purpose,
            )
            batch_schedules.append(sched)

        batch = {
            "batch_size": len(callees),
            "purpose": purpose,
            "schedules": batch_schedules,
            "interval_minutes": interval_minutes,
        }
        self._batches.append(batch)
        self._stats["batches_created"] += 1

        return batch

    def get_pending_schedules(
        self,
    ) -> list[dict[str, Any]]:
        """Bekleyen zamanlamaları getirir.

        Returns:
            Zamanlama listesi.
        """
        return [
            s for s in self._schedules
            if s["status"] == "pending"
        ]

    def cancel_schedule(
        self,
        schedule_id: str,
    ) -> dict[str, Any]:
        """Zamanlama iptal eder.

        Args:
            schedule_id: Zamanlama ID.

        Returns:
            İptal bilgisi.
        """
        for s in self._schedules:
            if s["schedule_id"] == schedule_id:
                s["status"] = "cancelled"
                return {
                    "schedule_id": schedule_id,
                    "cancelled": True,
                }
        return {"error": "schedule_not_found"}

    @property
    def schedule_count(self) -> int:
        """Zamanlama sayısı."""
        return self._stats["scheduled"]

    @property
    def pending_count(self) -> int:
        """Bekleyen zamanlama sayısı."""
        return len(self.get_pending_schedules())

    @property
    def reminder_count(self) -> int:
        """Hatırlatma sayısı."""
        return self._stats["reminders_set"]
