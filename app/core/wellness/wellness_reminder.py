"""
Wellness hatırlatıcı modülü.

Su içme, duruş kontrolü, mola, esneme
ve özel hatırlatmalar yönetir.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WellnessReminder:
    """Wellness hatırlatıcı.

    Attributes:
        _reminders: Hatırlatma kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hatırlatıcıyı başlatır."""
        self._reminders: list[dict] = []
        self._stats: dict[str, int] = {
            "reminders_created": 0,
        }
        logger.info(
            "WellnessReminder baslatildi"
        )

    @property
    def reminder_count(self) -> int:
        """Hatırlatma sayısı."""
        return len(self._reminders)

    def add_hydration(
        self,
        interval_min: int = 60,
        daily_goal_ml: int = 2500,
    ) -> dict[str, Any]:
        """Su içme hatırlatması ekler.

        Args:
            interval_min: Aralık (dakika).
            daily_goal_ml: Günlük hedef (ml).

        Returns:
            Hatırlatma bilgisi.
        """
        try:
            rid = f"rem_{uuid4()!s:.8}"
            reminder = {
                "reminder_id": rid,
                "type": "hydration",
                "interval_min": interval_min,
                "daily_goal_ml": daily_goal_ml,
                "active": True,
            }
            self._reminders.append(reminder)
            self._stats[
                "reminders_created"
            ] += 1

            glasses = daily_goal_ml // 250
            return {
                "reminder_id": rid,
                "type": "hydration",
                "interval_min": interval_min,
                "daily_glasses": glasses,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {"added": False, "error": str(e)}

    def add_posture_check(
        self,
        interval_min: int = 30,
    ) -> dict[str, Any]:
        """Duruş kontrolü hatırlatması.

        Args:
            interval_min: Aralık (dakika).

        Returns:
            Hatırlatma bilgisi.
        """
        try:
            rid = f"rem_{uuid4()!s:.8}"
            tips = [
                "shoulders_back",
                "screen_eye_level",
                "feet_flat_floor",
            ]
            self._reminders.append({
                "reminder_id": rid,
                "type": "posture",
                "interval_min": interval_min,
                "active": True,
            })
            self._stats[
                "reminders_created"
            ] += 1

            return {
                "reminder_id": rid,
                "type": "posture",
                "interval_min": interval_min,
                "tips": tips,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {"added": False, "error": str(e)}

    def add_break_reminder(
        self,
        work_min: int = 50,
        break_min: int = 10,
    ) -> dict[str, Any]:
        """Mola hatırlatması ekler.

        Args:
            work_min: Çalışma süresi.
            break_min: Mola süresi.

        Returns:
            Hatırlatma bilgisi.
        """
        try:
            rid = f"rem_{uuid4()!s:.8}"
            daily_breaks = (
                480 // (work_min + break_min)
            )
            self._reminders.append({
                "reminder_id": rid,
                "type": "break_time",
                "work_min": work_min,
                "break_min": break_min,
                "active": True,
            })
            self._stats[
                "reminders_created"
            ] += 1

            return {
                "reminder_id": rid,
                "type": "break_time",
                "work_min": work_min,
                "break_min": break_min,
                "daily_breaks": daily_breaks,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {"added": False, "error": str(e)}

    def add_stretch_prompt(
        self,
        interval_min: int = 90,
    ) -> dict[str, Any]:
        """Esneme hatırlatması ekler.

        Args:
            interval_min: Aralık (dakika).

        Returns:
            Hatırlatma bilgisi.
        """
        try:
            rid = f"rem_{uuid4()!s:.8}"
            stretches = [
                "neck_rolls",
                "shoulder_shrugs",
                "wrist_circles",
                "back_stretch",
            ]
            self._reminders.append({
                "reminder_id": rid,
                "type": "stretch",
                "interval_min": interval_min,
                "active": True,
            })
            self._stats[
                "reminders_created"
            ] += 1

            return {
                "reminder_id": rid,
                "type": "stretch",
                "interval_min": interval_min,
                "stretches": stretches,
                "stretch_count": len(
                    stretches
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {"added": False, "error": str(e)}

    def add_custom_reminder(
        self,
        name: str = "Custom",
        interval_min: int = 120,
        message: str = "",
    ) -> dict[str, Any]:
        """Özel hatırlatma ekler.

        Args:
            name: Hatırlatma adı.
            interval_min: Aralık (dakika).
            message: Mesaj.

        Returns:
            Hatırlatma bilgisi.
        """
        try:
            rid = f"rem_{uuid4()!s:.8}"
            self._reminders.append({
                "reminder_id": rid,
                "type": "custom",
                "name": name,
                "interval_min": interval_min,
                "message": message,
                "active": True,
            })
            self._stats[
                "reminders_created"
            ] += 1

            return {
                "reminder_id": rid,
                "type": "custom",
                "name": name,
                "interval_min": interval_min,
                "message": message,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {"added": False, "error": str(e)}
