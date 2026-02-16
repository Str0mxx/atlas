"""ATLAS Referans Ödül Hesaplayıcı.

Ödül hesaplama, çok seviyeli ödüller,
limitler, para birimi ve vergi.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReferralRewardCalculator:
    """Referans ödül hesaplayıcısı.

    Referans ödüllerini hesaplar,
    limitleri uygular ve vergiyi hesaplar.

    Attributes:
        _rewards: Ödül kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._rewards: dict[str, dict] = {}
        self._stats = {
            "rewards_calculated": 0,
            "total_paid": 0.0,
        }
        logger.info(
            "ReferralRewardCalculator "
            "baslatildi",
        )

    @property
    def reward_count(self) -> int:
        """Hesaplanan ödül sayısı."""
        return self._stats[
            "rewards_calculated"
        ]

    @property
    def total_paid(self) -> float:
        """Toplam ödenen miktar."""
        return self._stats["total_paid"]

    def calculate_reward(
        self,
        referrer_id: str,
        base_amount: float = 10.0,
        multiplier: float = 1.0,
    ) -> dict[str, Any]:
        """Ödül hesaplar.

        Args:
            referrer_id: Referansçı kimliği.
            base_amount: Temel miktar.
            multiplier: Çarpan.

        Returns:
            Ödül bilgisi.
        """
        amount = round(
            base_amount * multiplier, 2,
        )

        rid = (
            f"rwd_{len(self._rewards)}"
        )
        self._rewards[rid] = {
            "referrer_id": referrer_id,
            "amount": amount,
        }
        self._stats[
            "rewards_calculated"
        ] += 1
        self._stats["total_paid"] += amount

        return {
            "reward_id": rid,
            "referrer_id": referrer_id,
            "amount": amount,
            "calculated": True,
        }

    def calculate_tiered(
        self,
        referrer_id: str,
        referral_count: int = 0,
        tier_rates: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Çok seviyeli ödül hesaplar.

        Args:
            referrer_id: Referansçı kimliği.
            referral_count: Referans sayısı.
            tier_rates: Seviye oranları.

        Returns:
            Ödül bilgisi.
        """
        if tier_rates is None:
            tier_rates = [
                {"min": 0, "rate": 10.0},
                {"min": 5, "rate": 15.0},
                {"min": 20, "rate": 20.0},
                {"min": 50, "rate": 30.0},
            ]

        rate = tier_rates[0]["rate"]
        for tier in tier_rates:
            if referral_count >= tier["min"]:
                rate = tier["rate"]

        return {
            "referrer_id": referrer_id,
            "referral_count": referral_count,
            "reward_rate": rate,
            "calculated": True,
        }

    def apply_cap(
        self,
        referrer_id: str,
        amount: float = 0.0,
        daily_cap: float = 100.0,
        monthly_cap: float = 1000.0,
        current_daily: float = 0.0,
        current_monthly: float = 0.0,
    ) -> dict[str, Any]:
        """Limit uygular.

        Args:
            referrer_id: Referansçı kimliği.
            amount: Talep edilen miktar.
            daily_cap: Günlük limit.
            monthly_cap: Aylık limit.
            current_daily: Bugünkü toplam.
            current_monthly: Bu ayki toplam.

        Returns:
            Limit bilgisi.
        """
        daily_remaining = max(
            daily_cap - current_daily, 0,
        )
        monthly_remaining = max(
            monthly_cap - current_monthly, 0,
        )
        approved = min(
            amount,
            daily_remaining,
            monthly_remaining,
        )

        return {
            "referrer_id": referrer_id,
            "requested": amount,
            "approved": round(approved, 2),
            "daily_remaining": round(
                daily_remaining, 2,
            ),
            "capped": approved < amount,
        }

    def convert_currency(
        self,
        amount: float = 0.0,
        from_currency: str = "USD",
        to_currency: str = "TRY",
        rate: float = 30.0,
    ) -> dict[str, Any]:
        """Para birimi dönüştürür.

        Args:
            amount: Miktar.
            from_currency: Kaynak para birimi.
            to_currency: Hedef para birimi.
            rate: Döviz kuru.

        Returns:
            Dönüşüm bilgisi.
        """
        converted = round(
            amount * rate, 2,
        )

        return {
            "original_amount": amount,
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "converted_amount": converted,
            "converted": True,
        }

    def estimate_tax(
        self,
        amount: float = 0.0,
        tax_rate: float = 0.2,
    ) -> dict[str, Any]:
        """Vergi tahmini yapar.

        Args:
            amount: Miktar.
            tax_rate: Vergi oranı.

        Returns:
            Vergi bilgisi.
        """
        tax = round(amount * tax_rate, 2)
        net = round(amount - tax, 2)

        return {
            "gross_amount": amount,
            "tax_rate": tax_rate,
            "tax_amount": tax,
            "net_amount": net,
            "estimated": True,
        }
