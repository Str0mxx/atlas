"""ATLAS Kesme Kararıcı modülü.

Kesme eşiği, bağlam değerlendirme,
fayda-maliyet analizi, kullanıcı durum
farkındalığı, geçersiz kılma yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InterruptDecider:
    """Kesme kararıcı.

    Bir mesajın kullanıcıyı kesip kesmemesi
    gerektiğine karar verir.

    Attributes:
        _decisions: Karar geçmişi.
        _thresholds: Eşik değerleri.
    """

    def __init__(
        self,
        default_threshold: float = 0.6,
        quiet_threshold: float = 0.9,
        busy_threshold: float = 0.8,
    ) -> None:
        """Kararıcıyı başlatır.

        Args:
            default_threshold: Varsayılan eşik.
            quiet_threshold: Sessiz saat eşiği.
            busy_threshold: Meşgul eşiği.
        """
        self._thresholds = {
            "default": default_threshold,
            "quiet": quiet_threshold,
            "busy": busy_threshold,
            "available": 0.3,
            "away": 0.7,
            "dnd": 0.95,
        }
        self._decisions: list[
            dict[str, Any]
        ] = []
        self._overrides: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "decisions_made": 0,
            "interrupts_allowed": 0,
            "interrupts_blocked": 0,
            "overrides_used": 0,
        }

        logger.info(
            "InterruptDecider baslatildi",
        )

    def decide(
        self,
        priority_score: float,
        user_state: str = "available",
        is_quiet_hours: bool = False,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kesme kararı verir.

        Args:
            priority_score: Öncelik puanı (0-1).
            user_state: Kullanıcı durumu.
            is_quiet_hours: Sessiz saatte mi.
            context: Ek bağlam.

        Returns:
            Karar bilgisi.
        """
        self._counter += 1
        did = f"dec_{self._counter}"
        ctx = context or {}

        # Eşik belirleme
        if is_quiet_hours:
            threshold = self._thresholds["quiet"]
        elif user_state in self._thresholds:
            threshold = self._thresholds[
                user_state
            ]
        else:
            threshold = self._thresholds[
                "default"
            ]

        # Fayda-maliyet analizi
        benefit = self._calculate_benefit(
            priority_score, ctx,
        )
        cost = self._calculate_cost(
            user_state, is_quiet_hours,
        )

        # Karar
        should_interrupt = (
            priority_score >= threshold
        )
        net_value = round(benefit - cost, 3)

        # Override kontrolü
        override = self._check_override(ctx)
        if override:
            should_interrupt = override[
                "force_interrupt"
            ]
            self._stats["overrides_used"] += 1

        # Aksiyon belirleme
        action = self._determine_action(
            should_interrupt,
            priority_score,
            is_quiet_hours,
        )

        decision = {
            "decision_id": did,
            "should_interrupt": should_interrupt,
            "action": action,
            "priority_score": priority_score,
            "threshold": threshold,
            "user_state": user_state,
            "is_quiet_hours": is_quiet_hours,
            "benefit": benefit,
            "cost": cost,
            "net_value": net_value,
            "override_applied": override
            is not None,
            "timestamp": time.time(),
        }
        self._decisions.append(decision)
        self._stats["decisions_made"] += 1

        if should_interrupt:
            self._stats[
                "interrupts_allowed"
            ] += 1
        else:
            self._stats[
                "interrupts_blocked"
            ] += 1

        return decision

    def _calculate_benefit(
        self,
        priority_score: float,
        context: dict[str, Any],
    ) -> float:
        """Fayda hesaplar."""
        benefit = priority_score
        if context.get("time_sensitive"):
            benefit += 0.2
        if context.get("actionable"):
            benefit += 0.1
        return round(
            min(benefit, 1.0), 3,
        )

    def _calculate_cost(
        self,
        user_state: str,
        is_quiet_hours: bool,
    ) -> float:
        """Maliyet hesaplar."""
        cost = 0.2  # Temel kesme maliyeti
        state_costs = {
            "busy": 0.4,
            "dnd": 0.6,
            "sleeping": 0.7,
            "away": 0.2,
            "available": 0.0,
        }
        cost += state_costs.get(user_state, 0.1)
        if is_quiet_hours:
            cost += 0.3
        return round(min(cost, 1.0), 3)

    def _check_override(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Override kontrolü yapar."""
        if context.get("emergency"):
            return {
                "force_interrupt": True,
                "reason": "emergency",
            }
        if context.get("force_deliver"):
            return {
                "force_interrupt": True,
                "reason": "force_deliver",
            }
        return None

    def _determine_action(
        self,
        should_interrupt: bool,
        priority_score: float,
        is_quiet_hours: bool,
    ) -> str:
        """Aksiyon belirler."""
        if should_interrupt:
            return "deliver_now"
        if is_quiet_hours:
            if priority_score >= 0.5:
                return "digest"
            return "buffer"
        if priority_score >= 0.4:
            return "buffer"
        return "discard"

    def set_threshold(
        self,
        state: str,
        threshold: float,
    ) -> dict[str, Any]:
        """Eşik ayarlar.

        Args:
            state: Durum adı.
            threshold: Eşik değeri.

        Returns:
            Ayarlama bilgisi.
        """
        old = self._thresholds.get(state)
        self._thresholds[state] = round(
            min(max(threshold, 0.0), 1.0), 3,
        )
        return {
            "state": state,
            "old_threshold": old,
            "new_threshold": self._thresholds[
                state
            ],
            "set": True,
        }

    def add_override(
        self,
        name: str,
        condition: str,
        force_interrupt: bool = True,
    ) -> dict[str, Any]:
        """Override ekler.

        Args:
            name: Override adı.
            condition: Koşul.
            force_interrupt: Kesmeyi zorla.

        Returns:
            Ekleme bilgisi.
        """
        override = {
            "name": name,
            "condition": condition,
            "force_interrupt": force_interrupt,
            "active": True,
        }
        self._overrides.append(override)
        return {"name": name, "added": True}

    def get_decisions(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kararları getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Karar listesi.
        """
        return list(self._decisions[-limit:])

    @property
    def decisions_made(self) -> int:
        """Karar sayısı."""
        return self._stats["decisions_made"]

    @property
    def interrupt_rate(self) -> float:
        """Kesme oranı."""
        total = self._stats["decisions_made"]
        if total == 0:
            return 0.0
        return round(
            self._stats["interrupts_allowed"]
            / total
            * 100,
            1,
        )
