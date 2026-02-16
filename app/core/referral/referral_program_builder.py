"""ATLAS Referans Program Oluşturucu.

Program tasarımı, ödül yapısı,
kural motoru, seviye sistemi ve A/B varyantları.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReferralProgramBuilder:
    """Referans program oluşturucu.

    Referans programlarını tasarlar,
    kuralları belirler ve varyantlar oluşturur.

    Attributes:
        _programs: Program kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._programs: dict[str, dict] = {}
        self._stats = {
            "programs_created": 0,
            "variants_created": 0,
        }
        logger.info(
            "ReferralProgramBuilder "
            "baslatildi",
        )

    @property
    def program_count(self) -> int:
        """Oluşturulan program sayısı."""
        return self._stats[
            "programs_created"
        ]

    @property
    def variant_count(self) -> int:
        """Oluşturulan varyant sayısı."""
        return self._stats[
            "variants_created"
        ]

    def design_program(
        self,
        name: str,
        reward_type: str = "credit",
        reward_amount: float = 10.0,
    ) -> dict[str, Any]:
        """Program tasarlar.

        Args:
            name: Program adı.
            reward_type: Ödül tipi.
            reward_amount: Ödül miktarı.

        Returns:
            Program bilgisi.
        """
        pid = (
            f"prog_{len(self._programs)}"
        )
        self._programs[pid] = {
            "name": name,
            "reward_type": reward_type,
            "reward_amount": reward_amount,
            "rules": [],
            "tiers": [],
        }
        self._stats[
            "programs_created"
        ] += 1

        logger.info(
            "Program tasarlandi: %s",
            name,
        )

        return {
            "program_id": pid,
            "name": name,
            "reward_type": reward_type,
            "reward_amount": reward_amount,
            "designed": True,
        }

    def set_reward_structure(
        self,
        program_id: str,
        referrer_reward: float = 10.0,
        referee_reward: float = 5.0,
        double_sided: bool = True,
    ) -> dict[str, Any]:
        """Ödül yapısı belirler.

        Args:
            program_id: Program kimliği.
            referrer_reward: Referansçı ödülü.
            referee_reward: Davet edilen ödülü.
            double_sided: Çift taraflı mı.

        Returns:
            Yapı bilgisi.
        """
        if program_id in self._programs:
            self._programs[program_id][
                "referrer_reward"
            ] = referrer_reward
            self._programs[program_id][
                "referee_reward"
            ] = referee_reward

        return {
            "program_id": program_id,
            "referrer_reward": referrer_reward,
            "referee_reward": referee_reward,
            "double_sided": double_sided,
            "configured": True,
        }

    def add_rule(
        self,
        program_id: str,
        rule_name: str,
        condition: str = "",
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            program_id: Program kimliği.
            rule_name: Kural adı.
            condition: Koşul.

        Returns:
            Kural bilgisi.
        """
        if program_id in self._programs:
            self._programs[program_id][
                "rules"
            ].append({
                "name": rule_name,
                "condition": condition,
            })

        rule_count = len(
            self._programs.get(
                program_id, {},
            ).get("rules", []),
        )

        return {
            "program_id": program_id,
            "rule_name": rule_name,
            "rule_count": rule_count,
            "added": True,
        }

    def configure_tiers(
        self,
        program_id: str,
        tiers: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Seviye sistemi yapılandırır.

        Args:
            program_id: Program kimliği.
            tiers: Seviye listesi.

        Returns:
            Yapılandırma bilgisi.
        """
        if tiers is None:
            tiers = [
                {"name": "bronze", "min": 0},
                {"name": "silver", "min": 5},
                {"name": "gold", "min": 20},
                {"name": "platinum", "min": 50},
            ]

        if program_id in self._programs:
            self._programs[program_id][
                "tiers"
            ] = tiers

        return {
            "program_id": program_id,
            "tier_count": len(tiers),
            "configured": True,
        }

    def create_variant(
        self,
        program_id: str,
        variant_name: str,
        changes: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """A/B varyantı oluşturur.

        Args:
            program_id: Program kimliği.
            variant_name: Varyant adı.
            changes: Değişiklikler.

        Returns:
            Varyant bilgisi.
        """
        if changes is None:
            changes = {}

        self._stats[
            "variants_created"
        ] += 1

        return {
            "program_id": program_id,
            "variant_name": variant_name,
            "change_count": len(changes),
            "created": True,
        }
