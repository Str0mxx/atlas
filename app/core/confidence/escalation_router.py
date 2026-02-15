"""ATLAS Eskalasyon Yonlendirici modulu.

Ne zaman eskale etme, kime eskale etme,
aciliyet seviyeleri, zaman asimi, varsayilan aksiyonlar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceEscalationRouter:
    """Eskalasyon yonlendirici.

    Dusuk guvenli kararlari eskale eder.

    Attributes:
        _routes: Eskalasyon yollari.
        _escalations: Eskalasyon kayitlari.
    """

    def __init__(
        self,
        default_timeout: int = 300,
        default_target: str = "admin",
    ) -> None:
        """Eskalasyon yonlendiriciyi baslatir.

        Args:
            default_timeout: Varsayilan zaman asimi (sn).
            default_target: Varsayilan hedef.
        """
        self._routes: dict[
            str, dict[str, Any]
        ] = {}
        self._escalations: list[
            dict[str, Any]
        ] = []
        self._pending: dict[
            str, dict[str, Any]
        ] = {}
        self._default_actions: dict[
            str, str
        ] = {}
        self._default_timeout = default_timeout
        self._default_target = default_target
        self._stats = {
            "escalated": 0,
            "resolved": 0,
            "timed_out": 0,
        }

        logger.info(
            "ConfidenceEscalationRouter baslatildi",
        )

    def add_route(
        self,
        domain: str,
        target: str,
        urgency: str = "medium",
        timeout: int | None = None,
        default_action: str = "reject",
    ) -> dict[str, Any]:
        """Eskalasyon yolu ekler.

        Args:
            domain: Alan.
            target: Hedef.
            urgency: Aciliyet.
            timeout: Zaman asimi.
            default_action: Varsayilan aksiyon.

        Returns:
            Yol bilgisi.
        """
        self._routes[domain] = {
            "domain": domain,
            "target": target,
            "urgency": urgency,
            "timeout": timeout if timeout is not None else self._default_timeout,
        }
        self._default_actions[domain] = (
            default_action
        )

        return {
            "domain": domain,
            "target": target,
            "added": True,
        }

    def escalate(
        self,
        action_id: str,
        domain: str = "",
        reason: str = "",
        urgency: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Eskale eder.

        Args:
            action_id: Aksiyon ID.
            domain: Alan.
            reason: Neden.
            urgency: Aciliyet.
            context: Baglam.

        Returns:
            Eskalasyon bilgisi.
        """
        route = self._routes.get(domain, {})
        target = route.get(
            "target", self._default_target,
        )
        urg = urgency or route.get(
            "urgency", "medium",
        )
        timeout = route.get(
            "timeout", self._default_timeout,
        )

        escalation = {
            "action_id": action_id,
            "domain": domain,
            "target": target,
            "urgency": urg,
            "reason": reason,
            "context": context or {},
            "status": "pending",
            "created_at": time.time(),
            "timeout_at": time.time() + timeout,
        }

        self._escalations.append(escalation)
        self._pending[action_id] = escalation
        self._stats["escalated"] += 1

        return {
            "action_id": action_id,
            "target": target,
            "urgency": urg,
            "timeout": timeout,
            "status": "escalated",
        }

    def resolve(
        self,
        action_id: str,
        decision: str = "approve",
        response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Eskalasyonu cozumler.

        Args:
            action_id: Aksiyon ID.
            decision: Karar.
            response: Yanit verisi.

        Returns:
            Cozum bilgisi.
        """
        esc = self._pending.get(action_id)
        if not esc:
            return {"error": "escalation_not_found"}

        esc["status"] = "resolved"
        esc["decision"] = decision
        esc["response"] = response or {}
        esc["resolved_at"] = time.time()

        del self._pending[action_id]
        self._stats["resolved"] += 1

        return {
            "action_id": action_id,
            "decision": decision,
            "resolved": True,
        }

    def check_timeouts(
        self,
    ) -> list[dict[str, Any]]:
        """Zaman asimlarini kontrol eder.

        Returns:
            Zaman asimli eskalasyonlar.
        """
        now = time.time()
        timed_out = []

        for aid, esc in list(
            self._pending.items(),
        ):
            if now >= esc["timeout_at"]:
                domain = esc.get("domain", "")
                default = self._default_actions.get(
                    domain, "reject",
                )

                esc["status"] = "timed_out"
                esc["default_action"] = default
                del self._pending[aid]
                self._stats["timed_out"] += 1

                timed_out.append({
                    "action_id": aid,
                    "default_action": default,
                    "status": "timed_out",
                })

        return timed_out

    def get_pending(
        self,
        target: str | None = None,
    ) -> list[dict[str, Any]]:
        """Bekleyen eskalasyonlari getirir.

        Args:
            target: Hedef filtresi.

        Returns:
            Eskalasyon listesi.
        """
        pending = list(self._pending.values())
        if target:
            pending = [
                e for e in pending
                if e["target"] == target
            ]
        return pending

    def get_route(
        self,
        domain: str,
    ) -> dict[str, Any] | None:
        """Eskalasyon yolunu getirir.

        Args:
            domain: Alan.

        Returns:
            Yol bilgisi veya None.
        """
        return self._routes.get(domain)

    @property
    def route_count(self) -> int:
        """Yol sayisi."""
        return len(self._routes)

    @property
    def pending_count(self) -> int:
        """Bekleyen sayisi."""
        return len(self._pending)

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayisi."""
        return len(self._escalations)
