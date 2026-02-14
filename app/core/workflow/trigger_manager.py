"""ATLAS Tetikleyici Yoneticisi modulu.

Olay, zamanlama, webhook, manuel
ve kosullu tetikleyiciler.
"""

import logging
import time
from typing import Any

from app.models.workflow_engine import (
    TriggerRecord,
    TriggerType,
)

logger = logging.getLogger(__name__)


class TriggerManager:
    """Tetikleyici yoneticisi.

    Is akisi tetikleyicilerini
    yonetir ve izler.

    Attributes:
        _triggers: Kayitli tetikleyiciler.
        _fired: Ateslenme gecmisi.
    """

    def __init__(self) -> None:
        """Tetikleyici yoneticisini baslatir."""
        self._triggers: dict[
            str, TriggerRecord
        ] = {}
        self._fired: list[dict[str, Any]] = []
        self._event_map: dict[
            str, list[str]
        ] = {}

        logger.info("TriggerManager baslatildi")

    def create_trigger(
        self,
        workflow_id: str,
        trigger_type: TriggerType,
        config: dict[str, Any] | None = None,
    ) -> TriggerRecord:
        """Tetikleyici olusturur.

        Args:
            workflow_id: Is akisi ID.
            trigger_type: Tetikleyici turu.
            config: Yapilandirma.

        Returns:
            Tetikleyici kaydi.
        """
        trigger = TriggerRecord(
            workflow_id=workflow_id,
            trigger_type=trigger_type,
            config=config or {},
        )
        self._triggers[trigger.trigger_id] = trigger

        # Olay esleme
        if trigger_type == TriggerType.EVENT:
            event_name = (config or {}).get(
                "event", "",
            )
            if event_name:
                if event_name not in self._event_map:
                    self._event_map[event_name] = []
                self._event_map[event_name].append(
                    trigger.trigger_id,
                )

        logger.info(
            "Tetikleyici olusturuldu: %s (%s)",
            trigger.trigger_id, trigger_type.value,
        )
        return trigger

    def fire_event(
        self,
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> list[str]:
        """Olay atesler.

        Args:
            event_name: Olay adi.
            data: Olay verisi.

        Returns:
            Tetiklenen is akisi ID listesi.
        """
        trigger_ids = self._event_map.get(
            event_name, [],
        )
        triggered: list[str] = []

        for tid in trigger_ids:
            trigger = self._triggers.get(tid)
            if trigger and trigger.enabled:
                triggered.append(
                    trigger.workflow_id,
                )
                self._fired.append({
                    "trigger_id": tid,
                    "workflow_id": (
                        trigger.workflow_id
                    ),
                    "event": event_name,
                    "data": data or {},
                    "at": time.time(),
                })

        return triggered

    def check_schedule(
        self,
        current_time: float | None = None,
    ) -> list[str]:
        """Zamanlama kontrolu.

        Args:
            current_time: Mevcut zaman.

        Returns:
            Tetiklenen is akisi ID listesi.
        """
        now = current_time or time.time()
        triggered: list[str] = []

        for trigger in self._triggers.values():
            if (
                trigger.trigger_type
                != TriggerType.SCHEDULE
                or not trigger.enabled
            ):
                continue
            interval = trigger.config.get(
                "interval_seconds", 0,
            )
            last_run = trigger.config.get(
                "last_run", 0,
            )
            if interval > 0 and (
                now - last_run >= interval
            ):
                triggered.append(
                    trigger.workflow_id,
                )
                trigger.config["last_run"] = now
                self._fired.append({
                    "trigger_id": trigger.trigger_id,
                    "workflow_id": (
                        trigger.workflow_id
                    ),
                    "type": "schedule",
                    "at": now,
                })

        return triggered

    def fire_webhook(
        self,
        webhook_id: str,
        payload: dict[str, Any] | None = None,
    ) -> list[str]:
        """Webhook atesler.

        Args:
            webhook_id: Webhook ID.
            payload: Payload.

        Returns:
            Tetiklenen is akisi ID listesi.
        """
        triggered: list[str] = []

        for trigger in self._triggers.values():
            if (
                trigger.trigger_type
                != TriggerType.WEBHOOK
                or not trigger.enabled
            ):
                continue
            if trigger.config.get(
                "webhook_id",
            ) == webhook_id:
                triggered.append(
                    trigger.workflow_id,
                )
                self._fired.append({
                    "trigger_id": trigger.trigger_id,
                    "workflow_id": (
                        trigger.workflow_id
                    ),
                    "type": "webhook",
                    "webhook_id": webhook_id,
                    "at": time.time(),
                })

        return triggered

    def fire_manual(
        self,
        trigger_id: str,
    ) -> str | None:
        """Manuel atesler.

        Args:
            trigger_id: Tetikleyici ID.

        Returns:
            Is akisi ID veya None.
        """
        trigger = self._triggers.get(trigger_id)
        if not trigger or not trigger.enabled:
            return None

        self._fired.append({
            "trigger_id": trigger_id,
            "workflow_id": trigger.workflow_id,
            "type": "manual",
            "at": time.time(),
        })
        return trigger.workflow_id

    def enable_trigger(
        self,
        trigger_id: str,
    ) -> bool:
        """Tetikleyici aktif eder.

        Args:
            trigger_id: Tetikleyici ID.

        Returns:
            Basarili ise True.
        """
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.enabled = True
            return True
        return False

    def disable_trigger(
        self,
        trigger_id: str,
    ) -> bool:
        """Tetikleyici devre disi birakir.

        Args:
            trigger_id: Tetikleyici ID.

        Returns:
            Basarili ise True.
        """
        trigger = self._triggers.get(trigger_id)
        if trigger:
            trigger.enabled = False
            return True
        return False

    def remove_trigger(
        self,
        trigger_id: str,
    ) -> bool:
        """Tetikleyici kaldirir.

        Args:
            trigger_id: Tetikleyici ID.

        Returns:
            Basarili ise True.
        """
        if trigger_id in self._triggers:
            del self._triggers[trigger_id]
            return True
        return False

    @property
    def trigger_count(self) -> int:
        """Tetikleyici sayisi."""
        return len(self._triggers)

    @property
    def active_count(self) -> int:
        """Aktif tetikleyici sayisi."""
        return sum(
            1 for t in self._triggers.values()
            if t.enabled
        )

    @property
    def fired_count(self) -> int:
        """Ateslenme sayisi."""
        return len(self._fired)
