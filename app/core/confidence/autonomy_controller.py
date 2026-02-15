"""ATLAS Otonomi Kontrolcusu modulu.

Yuksek guven otomatik calistirma, orta guven onerme,
dusuk guven insana sorma, acil mudahale, denetim loglama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceAutonomyController:
    """Otonomi kontrolcusu.

    Guven seviyesine gore otonomi yonetir.

    Attributes:
        _decisions: Karar gecmisi.
        _overrides: Acil mudahale kayitlari.
    """

    def __init__(
        self,
        auto_threshold: float = 0.8,
        suggest_threshold: float = 0.5,
        ask_threshold: float = 0.3,
    ) -> None:
        """Otonomi kontrolcusunu baslatir.

        Args:
            auto_threshold: Otomatik esik.
            suggest_threshold: Onerme esigi.
            ask_threshold: Sorma esigi.
        """
        self._auto_threshold = auto_threshold
        self._suggest_threshold = suggest_threshold
        self._ask_threshold = ask_threshold
        self._decisions: list[
            dict[str, Any]
        ] = []
        self._overrides: list[
            dict[str, Any]
        ] = []
        self._audit_log: list[
            dict[str, Any]
        ] = []
        self._emergency_mode = False
        self._stats = {
            "auto_executed": 0,
            "suggested": 0,
            "asked_human": 0,
            "rejected": 0,
            "overrides": 0,
        }

        logger.info(
            "ConfidenceAutonomyController baslatildi",
        )

    def decide(
        self,
        action_id: str,
        confidence: float,
        action_type: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Karar verir.

        Args:
            action_id: Aksiyon ID.
            confidence: Guven puani.
            action_type: Aksiyon tipi.
            context: Baglam.

        Returns:
            Karar bilgisi.
        """
        # Acil modda her zaman insana sor
        if self._emergency_mode:
            decision = "ask_human"
            reason = "emergency_mode"
        elif confidence >= self._auto_threshold:
            decision = "auto_execute"
            reason = "high_confidence"
        elif confidence >= self._suggest_threshold:
            decision = "suggest"
            reason = "medium_confidence"
        elif confidence >= self._ask_threshold:
            decision = "ask_human"
            reason = "low_confidence"
        else:
            decision = "reject"
            reason = "very_low_confidence"

        record = {
            "action_id": action_id,
            "confidence": confidence,
            "decision": decision,
            "reason": reason,
            "action_type": action_type,
            "context": context or {},
            "timestamp": time.time(),
        }

        self._decisions.append(record)
        self._log_audit(record)

        self._stats[
            decision.replace("-", "_")
            if decision in self._stats
            else decision
        ] = self._stats.get(decision, 0) + 1

        return {
            "action_id": action_id,
            "decision": decision,
            "reason": reason,
            "confidence": confidence,
        }

    def emergency_override(
        self,
        reason: str = "",
        enable: bool = True,
    ) -> dict[str, Any]:
        """Acil mudahale.

        Args:
            reason: Neden.
            enable: Aktif/pasif.

        Returns:
            Mudahale bilgisi.
        """
        self._emergency_mode = enable

        override = {
            "action": (
                "enable" if enable else "disable"
            ),
            "reason": reason,
            "timestamp": time.time(),
        }
        self._overrides.append(override)
        self._stats["overrides"] += 1

        self._log_audit({
            "type": "emergency_override",
            "enable": enable,
            "reason": reason,
            "timestamp": time.time(),
        })

        return {
            "emergency_mode": enable,
            "reason": reason,
        }

    def get_decision_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Karar gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Karar listesi.
        """
        return list(self._decisions[-limit:])

    def get_audit_log(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Denetim logunu getirir.

        Args:
            limit: Limit.

        Returns:
            Log listesi.
        """
        return list(self._audit_log[-limit:])

    def _log_audit(
        self,
        record: dict[str, Any],
    ) -> None:
        """Denetim loglar.

        Args:
            record: Log kaydi.
        """
        self._audit_log.append({
            **record,
            "logged_at": time.time(),
        })

    @property
    def decision_count(self) -> int:
        """Karar sayisi."""
        return len(self._decisions)

    @property
    def is_emergency(self) -> bool:
        """Acil modda mi."""
        return self._emergency_mode
