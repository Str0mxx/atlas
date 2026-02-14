"""ATLAS Proaktif Yardimci modulu.

Sormadan oneri, hatirlama sistemi,
teslim tarihi uyarilari, firsat bildirimleri
ve sorun onleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import ProactiveAction, ProactiveType

logger = logging.getLogger(__name__)


class ProactiveHelper:
    """Proaktif yardimci.

    Kullaniciyi beklemeden oneri sunar,
    hatirlama ve uyari sistemi yonetir.

    Attributes:
        _actions: Proaktif aksiyonlar.
        _reminders: Hatirlatmalar.
        _deadlines: Teslim tarihleri.
        _rules: Proaktif kurallar.
        _dismissed: Reddedilen aksiyon IDleri.
    """

    def __init__(self) -> None:
        """Proaktif yardimciyi baslatir."""
        self._actions: list[ProactiveAction] = []
        self._reminders: list[dict[str, Any]] = []
        self._deadlines: list[dict[str, Any]] = []
        self._rules: list[dict[str, Any]] = []
        self._dismissed: set[str] = set()

        logger.info("ProactiveHelper baslatildi")

    def suggest(
        self,
        title: str,
        description: str,
        urgency: float = 0.5,
        relevance: float = 0.5,
    ) -> ProactiveAction:
        """Oneri olusturur.

        Args:
            title: Baslik.
            description: Aciklama.
            urgency: Aciliyet (0-1).
            relevance: Ilgililik (0-1).

        Returns:
            ProactiveAction nesnesi.
        """
        action = ProactiveAction(
            action_type=ProactiveType.SUGGESTION,
            title=title,
            description=description,
            urgency=urgency,
            relevance=relevance,
        )
        self._actions.append(action)

        logger.info("Oneri olusturuldu: %s", title)
        return action

    def add_reminder(
        self,
        title: str,
        description: str,
        remind_at: datetime | None = None,
        recurring: bool = False,
    ) -> ProactiveAction:
        """Hatirlama ekler.

        Args:
            title: Baslik.
            description: Aciklama.
            remind_at: Hatirlama zamani.
            recurring: Tekrarli mi.

        Returns:
            ProactiveAction nesnesi.
        """
        action = ProactiveAction(
            action_type=ProactiveType.REMINDER,
            title=title,
            description=description,
            urgency=0.6,
            relevance=0.7,
        )
        self._actions.append(action)

        reminder = {
            "action_id": action.action_id,
            "title": title,
            "description": description,
            "remind_at": (
                remind_at.isoformat()
                if remind_at
                else None
            ),
            "recurring": recurring,
            "triggered": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._reminders.append(reminder)

        logger.info("Hatirlama eklendi: %s", title)
        return action

    def add_deadline(
        self,
        title: str,
        deadline: datetime,
        description: str = "",
        alert_before_hours: int = 24,
    ) -> ProactiveAction:
        """Teslim tarihi ekler.

        Args:
            title: Baslik.
            deadline: Teslim tarihi.
            description: Aciklama.
            alert_before_hours: Oncesinden uyari saati.

        Returns:
            ProactiveAction nesnesi.
        """
        now = datetime.now(timezone.utc)
        remaining = (deadline - now).total_seconds() / 3600
        urgency = min(1.0, max(0.0, 1.0 - remaining / (alert_before_hours * 2)))

        action = ProactiveAction(
            action_type=ProactiveType.ALERT,
            title=title,
            description=description or f"Teslim: {deadline.isoformat()}",
            urgency=urgency,
            relevance=0.9,
        )
        self._actions.append(action)

        deadline_record = {
            "action_id": action.action_id,
            "title": title,
            "deadline": deadline.isoformat(),
            "alert_before_hours": alert_before_hours,
            "remaining_hours": round(remaining, 1),
            "alerted": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._deadlines.append(deadline_record)

        logger.info(
            "Teslim tarihi eklendi: %s (%.1f saat kaldi)",
            title, remaining,
        )
        return action

    def notify_opportunity(
        self,
        title: str,
        description: str,
        relevance: float = 0.7,
    ) -> ProactiveAction:
        """Firsat bildirimi olusturur.

        Args:
            title: Baslik.
            description: Aciklama.
            relevance: Ilgililik (0-1).

        Returns:
            ProactiveAction nesnesi.
        """
        action = ProactiveAction(
            action_type=ProactiveType.OPPORTUNITY,
            title=title,
            description=description,
            urgency=0.4,
            relevance=relevance,
        )
        self._actions.append(action)

        logger.info("Firsat bildirimi: %s", title)
        return action

    def prevent_problem(
        self,
        title: str,
        description: str,
        urgency: float = 0.7,
    ) -> ProactiveAction:
        """Sorun onleme aksiyonu olusturur.

        Args:
            title: Baslik.
            description: Aciklama.
            urgency: Aciliyet (0-1).

        Returns:
            ProactiveAction nesnesi.
        """
        action = ProactiveAction(
            action_type=ProactiveType.PREVENTION,
            title=title,
            description=description,
            urgency=urgency,
            relevance=0.8,
        )
        self._actions.append(action)

        logger.info("Sorun onleme: %s", title)
        return action

    def add_rule(
        self,
        condition: str,
        action_type: ProactiveType,
        title: str,
        description: str,
    ) -> dict[str, Any]:
        """Proaktif kural ekler.

        Args:
            condition: Kosul tanimi.
            action_type: Aksiyon turu.
            title: Baslik.
            description: Aciklama.

        Returns:
            Kural kaydi.
        """
        rule = {
            "condition": condition,
            "action_type": action_type.value,
            "title": title,
            "description": description,
            "triggered_count": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._rules.append(rule)

        return rule

    def evaluate_rules(
        self,
        context: dict[str, Any],
    ) -> list[ProactiveAction]:
        """Kurallari degerlendirir.

        Args:
            context: Mevcut baglam.

        Returns:
            Tetiklenen aksiyonlar.
        """
        triggered: list[ProactiveAction] = []
        context_str = str(context).lower()

        for rule in self._rules:
            condition = rule["condition"].lower()
            if condition in context_str:
                action_type = ProactiveType(rule["action_type"])
                action = ProactiveAction(
                    action_type=action_type,
                    title=rule["title"],
                    description=rule["description"],
                    urgency=0.6,
                    relevance=0.7,
                )
                self._actions.append(action)
                triggered.append(action)
                rule["triggered_count"] += 1

        return triggered

    def check_deadlines(self) -> list[dict[str, Any]]:
        """Teslim tarihlerini kontrol eder.

        Returns:
            Yaklasan teslim tarihleri.
        """
        now = datetime.now(timezone.utc)
        approaching: list[dict[str, Any]] = []

        for dl in self._deadlines:
            if dl["alerted"]:
                continue

            deadline = datetime.fromisoformat(dl["deadline"])
            remaining = (deadline - now).total_seconds() / 3600

            if remaining <= dl["alert_before_hours"]:
                dl["alerted"] = True
                dl["remaining_hours"] = round(remaining, 1)
                approaching.append(dl)

        return approaching

    def check_reminders(self) -> list[dict[str, Any]]:
        """Hatirlatalari kontrol eder.

        Returns:
            Tetiklenen hatirlamalar.
        """
        now = datetime.now(timezone.utc)
        triggered: list[dict[str, Any]] = []

        for reminder in self._reminders:
            if reminder["triggered"] and not reminder["recurring"]:
                continue

            if reminder["remind_at"]:
                remind_time = datetime.fromisoformat(reminder["remind_at"])
                if now >= remind_time:
                    reminder["triggered"] = True
                    triggered.append(reminder)

        return triggered

    def dismiss_action(self, action_id: str) -> bool:
        """Aksiyonu reddeder.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Basarili ise True.
        """
        for action in self._actions:
            if action.action_id == action_id:
                self._dismissed.add(action_id)
                return True
        return False

    def get_pending_actions(
        self,
        min_urgency: float = 0.0,
    ) -> list[ProactiveAction]:
        """Bekleyen aksiyonlari getirir.

        Args:
            min_urgency: Min aciliyet.

        Returns:
            Aksiyon listesi.
        """
        return [
            a for a in self._actions
            if a.action_id not in self._dismissed
            and a.urgency >= min_urgency
        ]

    def get_actions_by_type(
        self,
        action_type: ProactiveType,
    ) -> list[ProactiveAction]:
        """Ture gore aksiyonlari getirir.

        Args:
            action_type: Aksiyon turu.

        Returns:
            Aksiyon listesi.
        """
        return [
            a for a in self._actions
            if a.action_type == action_type
        ]

    @property
    def action_count(self) -> int:
        """Aksiyon sayisi."""
        return len(self._actions)

    @property
    def reminder_count(self) -> int:
        """Hatirlama sayisi."""
        return len(self._reminders)

    @property
    def deadline_count(self) -> int:
        """Teslim tarihi sayisi."""
        return len(self._deadlines)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def pending_count(self) -> int:
        """Bekleyen aksiyon sayisi."""
        return len(self.get_pending_actions())
