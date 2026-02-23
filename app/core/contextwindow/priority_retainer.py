"""Oncelik koruyucu.

Onemli mesaj tespiti, sistem prompt
korumasi ve kullanici tercihi.
"""

import logging
import time
from typing import Any

from app.models.contextwindow_models import (
    MessagePriority,
    RetentionRule,
)

logger = logging.getLogger(__name__)

# Varsayilan ayarlar
_MAX_RULES = 200
_MAX_PINNED = 500
_PRIORITY_WEIGHTS: dict[str, float] = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.3,
    "disposable": 0.1,
}


class PriorityRetainer:
    """Oncelik koruyucu.

    Onemli mesaj tespiti, sistem prompt
    korumasi ve kullanici tercihi.

    Attributes:
        _rules: Saklama kurallari.
        _pinned: Sabitlenmis mesajlar.
        _role_priorities: Rol oncelikleri.
    """

    def __init__(self) -> None:
        """PriorityRetainer baslatir."""
        self._rules: dict[
            str, RetentionRule
        ] = {}
        self._pinned: dict[
            str, dict[str, Any]
        ] = {}
        self._role_priorities: dict[
            str, MessagePriority
        ] = {
            "system": MessagePriority.CRITICAL,
            "user": MessagePriority.HIGH,
            "assistant": MessagePriority.MEDIUM,
            "tool": MessagePriority.LOW,
        }
        self._keyword_priorities: dict[
            str, MessagePriority
        ] = {}
        self._total_evaluated: int = 0
        self._total_retained: int = 0
        self._total_dropped: int = 0

        logger.info(
            "PriorityRetainer baslatildi",
        )

    # ---- Kural Yonetimi ----

    def add_rule(
        self,
        name: str,
        priority: MessagePriority = (
            MessagePriority.MEDIUM
        ),
        pattern: str = "",
        role: str = "",
        is_pinned: bool = False,
        max_age_seconds: float = 0.0,
    ) -> RetentionRule | None:
        """Saklama kurali ekler.

        Args:
            name: Kural adi.
            priority: Oncelik.
            pattern: Icerik kalıbı.
            role: Rol filtresi.
            is_pinned: Sabitleme.
            max_age_seconds: Maks yas.

        Returns:
            Kural veya None.
        """
        if not name:
            return None

        if len(self._rules) >= _MAX_RULES:
            return None

        rule = RetentionRule(
            name=name,
            priority=priority,
            pattern=pattern,
            role=role,
            is_pinned=is_pinned,
            max_age_seconds=max_age_seconds,
        )

        self._rules[rule.rule_id] = rule
        return rule

    def get_rule(
        self, rule_id: str,
    ) -> RetentionRule | None:
        """Kural dondurur.

        Args:
            rule_id: Kural ID.

        Returns:
            Kural veya None.
        """
        return self._rules.get(rule_id)

    def remove_rule(
        self, rule_id: str,
    ) -> bool:
        """Kural siler.

        Args:
            rule_id: Kural ID.

        Returns:
            Silindi ise True.
        """
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        return True

    def update_rule(
        self,
        rule_id: str,
        priority: (
            MessagePriority | None
        ) = None,
        enabled: bool | None = None,
    ) -> bool:
        """Kural gunceller.

        Args:
            rule_id: Kural ID.
            priority: Yeni oncelik.
            enabled: Yeni durum.

        Returns:
            Guncellendi ise True.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return False

        if priority is not None:
            rule.priority = priority
        if enabled is not None:
            rule.enabled = enabled
        return True

    def list_rules(
        self,
    ) -> list[RetentionRule]:
        """Kurallari listeler.

        Returns:
            Kural listesi.
        """
        return list(self._rules.values())

    # ---- Oncelik Degerlendirme ----

    def evaluate_priority(
        self,
        message: dict[str, Any],
    ) -> MessagePriority:
        """Mesaj onceligi belirler.

        Args:
            message: Mesaj (role, content,
                timestamp, metadata).

        Returns:
            Oncelik.
        """
        self._total_evaluated += 1

        role = message.get("role", "")
        content = message.get("content", "")
        msg_id = message.get("id", "")

        # Sabitlenmis mi?
        if msg_id and msg_id in self._pinned:
            return MessagePriority.CRITICAL

        # Kural kontrolu
        rule_priority = (
            self._check_rules(message)
        )
        if rule_priority is not None:
            return rule_priority

        # Anahtar kelime kontrolu
        kw_priority = (
            self._check_keywords(content)
        )
        if kw_priority is not None:
            return kw_priority

        # Rol bazli varsayilan
        return self._role_priorities.get(
            role, MessagePriority.MEDIUM,
        )

    def evaluate_batch(
        self,
        messages: list[dict[str, Any]],
    ) -> list[
        tuple[dict[str, Any], MessagePriority]
    ]:
        """Toplu oncelik degerlendirme.

        Args:
            messages: Mesaj listesi.

        Returns:
            (mesaj, oncelik) listesi.
        """
        return [
            (m, self.evaluate_priority(m))
            for m in messages
        ]

    def filter_by_priority(
        self,
        messages: list[dict[str, Any]],
        min_priority: MessagePriority = (
            MessagePriority.LOW
        ),
    ) -> list[dict[str, Any]]:
        """Oncelik filtresi uygular.

        Args:
            messages: Mesaj listesi.
            min_priority: Min oncelik.

        Returns:
            Filtreli mesajlar.
        """
        min_weight = _PRIORITY_WEIGHTS.get(
            min_priority.value, 0.0,
        )

        result: list[dict[str, Any]] = []
        for m in messages:
            p = self.evaluate_priority(m)
            w = _PRIORITY_WEIGHTS.get(
                p.value, 0.0,
            )
            if w >= min_weight:
                result.append(m)
                self._total_retained += 1
            else:
                self._total_dropped += 1

        return result

    def sort_by_priority(
        self,
        messages: list[dict[str, Any]],
        reverse: bool = True,
    ) -> list[dict[str, Any]]:
        """Oncelik sirasina gore siralar.

        Args:
            messages: Mesaj listesi.
            reverse: Yuksekten dusuge.

        Returns:
            Sirali mesajlar.
        """
        evaluated = self.evaluate_batch(
            messages,
        )
        evaluated.sort(
            key=lambda x: (
                _PRIORITY_WEIGHTS.get(
                    x[1].value, 0.0,
                )
            ),
            reverse=reverse,
        )
        return [m for m, _ in evaluated]

    def select_for_budget(
        self,
        messages: list[dict[str, Any]],
        token_budget: int,
        estimate_fn: Any = None,
    ) -> list[dict[str, Any]]:
        """Butceye gore secer.

        Args:
            messages: Mesaj listesi.
            token_budget: Token butcesi.
            estimate_fn: Token tahmin
                fonksiyonu.

        Returns:
            Secilen mesajlar.
        """
        if estimate_fn is None:
            estimate_fn = lambda m: max(
                1,
                len(
                    m.get("content", ""),
                ) // 4,
            )

        sorted_msgs = self.sort_by_priority(
            messages,
        )

        selected: list[dict[str, Any]] = []
        used = 0

        for m in sorted_msgs:
            tokens = estimate_fn(m)
            if used + tokens <= token_budget:
                selected.append(m)
                used += tokens
                self._total_retained += 1
            else:
                self._total_dropped += 1

        return selected

    # ---- Sabitleme ----

    def pin_message(
        self,
        message_id: str,
        reason: str = "",
    ) -> bool:
        """Mesaj sabitler.

        Args:
            message_id: Mesaj ID.
            reason: Sebep.

        Returns:
            Sabitlendi ise True.
        """
        if not message_id:
            return False

        if len(self._pinned) >= _MAX_PINNED:
            return False

        self._pinned[message_id] = {
            "reason": reason,
            "timestamp": time.time(),
        }
        return True

    def unpin_message(
        self, message_id: str,
    ) -> bool:
        """Sabitlemeyi kaldirir.

        Args:
            message_id: Mesaj ID.

        Returns:
            Kaldirildi ise True.
        """
        if message_id not in self._pinned:
            return False
        del self._pinned[message_id]
        return True

    def is_pinned(
        self, message_id: str,
    ) -> bool:
        """Sabitlenme durumu.

        Args:
            message_id: Mesaj ID.

        Returns:
            Sabitlendiyse True.
        """
        return message_id in self._pinned

    def list_pinned(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Sabitlenmisleri listeler.

        Returns:
            Sabitlenmis mesajlar.
        """
        return dict(self._pinned)

    def clear_pinned(self) -> int:
        """Sabitlemeleri temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._pinned)
        self._pinned = {}
        return count

    # ---- Rol/Kelime Onceligi ----

    def set_role_priority(
        self,
        role: str,
        priority: MessagePriority,
    ) -> None:
        """Rol onceligi ayarlar.

        Args:
            role: Rol.
            priority: Oncelik.
        """
        if role:
            self._role_priorities[role] = (
                priority
            )

    def get_role_priority(
        self, role: str,
    ) -> MessagePriority:
        """Rol onceligi dondurur.

        Args:
            role: Rol.

        Returns:
            Oncelik.
        """
        return self._role_priorities.get(
            role, MessagePriority.MEDIUM,
        )

    def add_keyword_priority(
        self,
        keyword: str,
        priority: MessagePriority,
    ) -> bool:
        """Anahtar kelime onceligi ekler.

        Args:
            keyword: Anahtar kelime.
            priority: Oncelik.

        Returns:
            Eklendi ise True.
        """
        if not keyword:
            return False
        self._keyword_priorities[
            keyword.lower()
        ] = priority
        return True

    def remove_keyword_priority(
        self, keyword: str,
    ) -> bool:
        """Anahtar kelime onceligi siler.

        Args:
            keyword: Anahtar kelime.

        Returns:
            Silindi ise True.
        """
        key = keyword.lower()
        if key not in self._keyword_priorities:
            return False
        del self._keyword_priorities[key]
        return True

    # ---- Yardimci ----

    def _check_rules(
        self,
        message: dict[str, Any],
    ) -> MessagePriority | None:
        """Kurallari kontrol eder.

        Args:
            message: Mesaj.

        Returns:
            Oncelik veya None.
        """
        role = message.get("role", "")
        content = message.get("content", "")
        lower_content = content.lower()

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Rol filtresi
            if rule.role and rule.role != role:
                continue

            # Kalip filtresi
            if rule.pattern:
                if (
                    rule.pattern.lower()
                    not in lower_content
                ):
                    continue

            return rule.priority

        return None

    def _check_keywords(
        self, content: str,
    ) -> MessagePriority | None:
        """Anahtar kelime kontrolu.

        Args:
            content: Icerik.

        Returns:
            Oncelik veya None.
        """
        if not content:
            return None

        lower = content.lower()
        best: MessagePriority | None = None
        best_weight = 0.0

        for kw, priority in (
            self._keyword_priorities.items()
        ):
            if kw in lower:
                w = _PRIORITY_WEIGHTS.get(
                    priority.value, 0.0,
                )
                if w > best_weight:
                    best = priority
                    best_weight = w

        return best

    # ---- Istatistikler ----

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "total_rules": len(self._rules),
            "total_pinned": len(
                self._pinned,
            ),
            "total_evaluated": (
                self._total_evaluated
            ),
            "total_retained": (
                self._total_retained
            ),
            "total_dropped": (
                self._total_dropped
            ),
            "role_priorities": {
                k: v.value
                for k, v in (
                    self._role_priorities.items()
                )
            },
            "keyword_count": len(
                self._keyword_priorities,
            ),
        }
