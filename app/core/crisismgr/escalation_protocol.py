"""ATLAS Eskalasyon Protokolü modülü.

Eskalasyon seviyeleri, iletişim zincirleri,
yanıt süreleri, otomatik eskalasyon,
geçersiz kılma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EscalationProtocol:
    """Eskalasyon protokolü.

    Kriz eskalasyonunu yönetir.

    Attributes:
        _chains: İletişim zincirleri.
        _escalations: Eskalasyon kayıtları.
    """

    def __init__(self) -> None:
        """Protokolü başlatır."""
        self._chains: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._escalations: dict[
            str, dict[str, Any]
        ] = {}
        self._response_times: dict[
            str, float
        ] = {
            "tier1": 300,
            "tier2": 600,
            "tier3": 1800,
            "executive": 3600,
        }
        self._counter = 0
        self._stats = {
            "escalations_triggered": 0,
            "overrides": 0,
        }

        logger.info(
            "EscalationProtocol "
            "baslatildi",
        )

    def define_levels(
        self,
        crisis_id: str,
        levels: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Eskalasyon seviyeleri tanımlar.

        Args:
            crisis_id: Kriz kimliği.
            levels: Seviyeler.

        Returns:
            Tanımlama bilgisi.
        """
        levels = levels or [
            {
                "tier": "tier1",
                "role": "on_call",
            },
            {
                "tier": "tier2",
                "role": "team_lead",
            },
            {
                "tier": "tier3",
                "role": "director",
            },
            {
                "tier": "executive",
                "role": "ceo",
            },
        ]

        self._chains[crisis_id] = levels

        return {
            "crisis_id": crisis_id,
            "level_count": len(levels),
            "defined": True,
        }

    def set_contact_chain(
        self,
        crisis_id: str,
        contacts: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """İletişim zinciri ayarlar.

        Args:
            crisis_id: Kriz kimliği.
            contacts: İletişim listesi.

        Returns:
            Ayarlama bilgisi.
        """
        contacts = contacts or []

        self._chains[crisis_id] = contacts

        return {
            "crisis_id": crisis_id,
            "contact_count": len(contacts),
            "set_ok": True,
        }

    def get_response_time(
        self,
        tier: str,
    ) -> dict[str, Any]:
        """Yanıt süresi döndürür.

        Args:
            tier: Katman.

        Returns:
            Süre bilgisi.
        """
        seconds = self._response_times.get(
            tier, 600,
        )

        return {
            "tier": tier,
            "max_response_seconds": seconds,
            "max_response_minutes": round(
                seconds / 60, 1,
            ),
            "retrieved": True,
        }

    def auto_escalate(
        self,
        crisis_id: str,
        current_tier: str = "tier1",
        elapsed_seconds: float = 0,
    ) -> dict[str, Any]:
        """Otomatik eskalasyon yapar.

        Args:
            crisis_id: Kriz kimliği.
            current_tier: Güncel katman.
            elapsed_seconds: Geçen süre.

        Returns:
            Eskalasyon bilgisi.
        """
        max_time = (
            self._response_times.get(
                current_tier, 600,
            )
        )

        tier_order = [
            "tier1", "tier2",
            "tier3", "executive",
        ]

        should_escalate = (
            elapsed_seconds > max_time
        )

        if should_escalate:
            idx = tier_order.index(
                current_tier,
            ) if current_tier in (
                tier_order
            ) else 0
            next_tier = (
                tier_order[idx + 1]
                if idx + 1 < len(tier_order)
                else current_tier
            )

            self._counter += 1
            eid = f"esc_{self._counter}"

            self._escalations[
                crisis_id
            ] = {
                "escalation_id": eid,
                "from_tier": current_tier,
                "to_tier": next_tier,
                "timestamp": time.time(),
            }

            self._stats[
                "escalations_triggered"
            ] += 1

            return {
                "crisis_id": crisis_id,
                "escalated": True,
                "from_tier": current_tier,
                "to_tier": next_tier,
            }

        return {
            "crisis_id": crisis_id,
            "escalated": False,
            "current_tier": current_tier,
            "time_remaining": round(
                max_time - elapsed_seconds,
            ),
        }

    def override(
        self,
        crisis_id: str,
        target_tier: str = "executive",
        reason: str = "",
        authorized_by: str = "",
    ) -> dict[str, Any]:
        """Geçersiz kılma yapar.

        Args:
            crisis_id: Kriz kimliği.
            target_tier: Hedef katman.
            reason: Sebep.
            authorized_by: Yetkilendiren.

        Returns:
            Geçersiz kılma bilgisi.
        """
        self._counter += 1
        eid = f"esc_{self._counter}"

        self._escalations[crisis_id] = {
            "escalation_id": eid,
            "to_tier": target_tier,
            "override": True,
            "reason": reason,
            "authorized_by": authorized_by,
            "timestamp": time.time(),
        }

        self._stats["overrides"] += 1
        self._stats[
            "escalations_triggered"
        ] += 1

        return {
            "crisis_id": crisis_id,
            "target_tier": target_tier,
            "overridden": True,
        }

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayısı."""
        return self._stats[
            "escalations_triggered"
        ]

    @property
    def override_count(self) -> int:
        """Geçersiz kılma sayısı."""
        return self._stats["overrides"]
