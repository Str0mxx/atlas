"""Quiet Hours - sessiz saat yonetimi modulu.

Belirli zaman dilimlerinde bildirimleri bastirarak gereksiz
rahatsizliklari onler.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.models.heartbeat_models import ImportanceLevel, QuietHoursConfig

logger = logging.getLogger(__name__)


class HeartbeatQuietHours:
    """Sessiz saat yonetimi sinifi."""

    def __init__(self, config: Optional[QuietHoursConfig] = None) -> None:
        """HeartbeatQuietHours baslatici."""
        self.config = config or QuietHoursConfig()
        self._exceptions: list[str] = []
        self._history: list[dict] = []

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina yeni bir giris ekler."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details or {}})

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Sessiz saat istatistiklerini dondurur."""
        return {"enabled": self.config.enabled, "start_hour": self.config.start_hour, "end_hour": self.config.end_hour, "exception_count": len(self._exceptions)}

    def is_quiet_time(self) -> bool:
        """Suanki zamanin sessiz saat diliminde olup olmadigini kontrol eder."""
        if not self.config.enabled:
            return False
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        today_str = now.strftime("%Y-%m-%d")
        if today_str in self._exceptions:
            return False
        day_name = now.strftime("%a").lower()
        if day_name not in self.config.days:
            return False
        start = self.config.start_hour
        end = self.config.end_hour
        if start < end:
            is_quiet = start <= current_hour < end
        else:
            is_quiet = current_hour >= start or current_hour < end
        self._record_history("is_quiet_time", {"result": is_quiet, "hour": current_hour})
        return is_quiet

    def set_quiet_hours(self, start: int, end: int, tz: str = "UTC") -> None:
        """Sessiz saat araligini ayarlar."""
        self.config.start_hour = max(0, min(23, start))
        self.config.end_hour = max(0, min(23, end))
        self.config.timezone = tz
        self.config.enabled = True
        self._record_history("set_quiet_hours", {"start": start, "end": end, "tz": tz})

    def get_config(self) -> QuietHoursConfig:
        """Mevcut sessiz saat yapilandirmasini dondurur."""
        return self.config

    def should_override(self, importance: ImportanceLevel) -> bool:
        """Kritik durumlarda sessiz saatin gecersiz kilinip kilinmayacagini belirler."""
        if not self.config.override_critical:
            return False
        override = importance == ImportanceLevel.CRITICAL
        self._record_history("should_override", {"importance": importance.value, "override": override})
        return override

    def next_active_time(self) -> Optional[int]:
        """Sessiz saatlerin ne zaman bitecegini hesaplar."""
        if not self.config.enabled:
            return None
        return self.config.end_hour

    def add_exception(self, date: str) -> None:
        """Istisna tarihi ekler."""
        if date not in self._exceptions:
            self._exceptions.append(date)
            self._record_history("add_exception", {"date": date})
