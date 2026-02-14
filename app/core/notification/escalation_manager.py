"""ATLAS Eskalasyon Yoneticisi modulu.

Eskalasyon kurallari, zaman asimi
islemleri, onaylama takibi, cok
seviyeli eskalasyon ve nobetci
rotasyonu.
"""

import logging
import time
from typing import Any

from app.models.notification_system import (
    EscalationLevel,
    NotificationPriority,
)

logger = logging.getLogger(__name__)


class EscalationManager:
    """Eskalasyon yoneticisi.

    Uyarilarin eskalasyon surecini
    yonetir ve nobetci rotasyonu saglar.

    Attributes:
        _rules: Eskalasyon kurallari.
        _active: Aktif eskalasyonlar.
        _on_call: Nobetci listesi.
        _ack_log: Onaylama gecmisi.
    """

    def __init__(self) -> None:
        """Eskalasyon yoneticisini baslatir."""
        self._rules: dict[str, dict[str, Any]] = {}
        self._active: dict[str, dict[str, Any]] = {}
        self._on_call: list[dict[str, Any]] = []
        self._ack_log: list[dict[str, Any]] = []
        self._current_on_call: int = 0

        logger.info("EscalationManager baslatildi")

    def add_rule(
        self,
        name: str,
        levels: list[EscalationLevel],
        timeout_seconds: int = 300,
        min_severity: NotificationPriority = NotificationPriority.HIGH,
    ) -> dict[str, Any]:
        """Eskalasyon kurali ekler.

        Args:
            name: Kural adi.
            levels: Eskalasyon seviyeleri.
            timeout_seconds: Zaman asimi.
            min_severity: Minimum onem derecesi.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "levels": [l.value for l in levels],
            "timeout_seconds": timeout_seconds,
            "min_severity": min_severity.value,
            "enabled": True,
        }
        self._rules[name] = rule
        return rule

    def escalate(
        self,
        alert_id: str,
        rule_name: str,
    ) -> dict[str, Any]:
        """Eskalasyon baslatir.

        Args:
            alert_id: Uyari ID.
            rule_name: Kural adi.

        Returns:
            Eskalasyon bilgisi.
        """
        rule = self._rules.get(rule_name)
        if not rule or not rule["enabled"]:
            return {
                "alert_id": alert_id,
                "escalated": False,
                "reason": "rule_not_found",
            }

        levels = rule["levels"]
        current_level = 0

        # Mevcut eskalasyonu kontrol et
        existing = self._active.get(alert_id)
        if existing:
            current_level = existing["current_level"] + 1
            if current_level >= len(levels):
                return {
                    "alert_id": alert_id,
                    "escalated": False,
                    "reason": "max_level_reached",
                }

        escalation = {
            "alert_id": alert_id,
            "rule_name": rule_name,
            "current_level": current_level,
            "level": levels[current_level],
            "escalated": True,
            "started_at": time.time(),
            "timeout": rule["timeout_seconds"],
            "acknowledged": False,
        }
        self._active[alert_id] = escalation
        logger.warning(
            "Eskalasyon: %s -> %s",
            alert_id, levels[current_level],
        )
        return escalation

    def acknowledge(
        self,
        alert_id: str,
        by: str = "",
    ) -> bool:
        """Eskalasyonu onaylar.

        Args:
            alert_id: Uyari ID.
            by: Onaylayan.

        Returns:
            Basarili ise True.
        """
        esc = self._active.get(alert_id)
        if not esc:
            return False
        esc["acknowledged"] = True
        self._ack_log.append({
            "alert_id": alert_id,
            "by": by,
            "at": time.time(),
            "level": esc["level"],
        })
        return True

    def check_timeouts(self) -> list[str]:
        """Zaman asimlarini kontrol eder.

        Returns:
            Zamani asmis uyari ID listesi.
        """
        now = time.time()
        timed_out: list[str] = []

        for alert_id, esc in self._active.items():
            if esc["acknowledged"]:
                continue
            elapsed = now - esc["started_at"]
            if elapsed > esc["timeout"]:
                timed_out.append(alert_id)

        return timed_out

    def add_on_call(
        self,
        person: str,
        level: EscalationLevel,
        contact: str = "",
    ) -> dict[str, Any]:
        """Nobetci ekler.

        Args:
            person: Kisi adi.
            level: Seviye.
            contact: Iletisim.

        Returns:
            Nobetci bilgisi.
        """
        entry = {
            "person": person,
            "level": level.value,
            "contact": contact,
        }
        self._on_call.append(entry)
        return entry

    def get_current_on_call(self) -> dict[str, Any] | None:
        """Mevcut nobetciyi getirir.

        Returns:
            Nobetci bilgisi veya None.
        """
        if not self._on_call:
            return None
        idx = self._current_on_call % len(self._on_call)
        return self._on_call[idx]

    def rotate_on_call(self) -> dict[str, Any] | None:
        """Nobetci rotasyonu yapar.

        Returns:
            Yeni nobetci veya None.
        """
        if not self._on_call:
            return None
        self._current_on_call += 1
        return self.get_current_on_call()

    def get_active(self) -> list[dict[str, Any]]:
        """Aktif eskalasyonlari getirir.

        Returns:
            Aktif eskalasyonlar.
        """
        return [
            e for e in self._active.values()
            if not e["acknowledged"]
        ]

    def resolve(self, alert_id: str) -> bool:
        """Eskalasyonu cozumler.

        Args:
            alert_id: Uyari ID.

        Returns:
            Basarili ise True.
        """
        if alert_id in self._active:
            del self._active[alert_id]
            return True
        return False

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def active_count(self) -> int:
        """Aktif eskalasyon sayisi."""
        return sum(
            1 for e in self._active.values()
            if not e["acknowledged"]
        )

    @property
    def on_call_count(self) -> int:
        """Nobetci sayisi."""
        return len(self._on_call)

    @property
    def ack_count(self) -> int:
        """Onaylama sayisi."""
        return len(self._ack_log)
