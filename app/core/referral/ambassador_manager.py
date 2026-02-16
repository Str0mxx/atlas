"""ATLAS Elçi Yöneticisi.

Elçi alımı, performans takibi,
seviye yönetimi, iletişim ve tanınma.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AmbassadorManager:
    """Elçi yöneticisi.

    Marka elçilerini yönetir, performans
    takip eder ve seviye belirler.

    Attributes:
        _ambassadors: Elçi kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._ambassadors: dict[
            str, dict
        ] = {}
        self._stats = {
            "ambassadors_recruited": 0,
            "recognitions_given": 0,
        }
        logger.info(
            "AmbassadorManager baslatildi",
        )

    @property
    def ambassador_count(self) -> int:
        """Alınan elçi sayısı."""
        return self._stats[
            "ambassadors_recruited"
        ]

    @property
    def recognition_count(self) -> int:
        """Verilen tanınma sayısı."""
        return self._stats[
            "recognitions_given"
        ]

    def recruit(
        self,
        name: str,
        email: str = "",
        channel: str = "organic",
    ) -> dict[str, Any]:
        """Elçi alır.

        Args:
            name: Elçi adı.
            email: E-posta.
            channel: Edinme kanalı.

        Returns:
            Alım bilgisi.
        """
        aid = (
            f"amb_{len(self._ambassadors)}"
        )
        self._ambassadors[aid] = {
            "name": name,
            "email": email,
            "channel": channel,
            "tier": "bronze",
            "referrals": 0,
            "earnings": 0.0,
        }
        self._stats[
            "ambassadors_recruited"
        ] += 1

        logger.info(
            "Elci alindi: %s",
            name,
        )

        return {
            "ambassador_id": aid,
            "name": name,
            "tier": "bronze",
            "recruited": True,
        }

    def track_performance(
        self,
        ambassador_id: str,
        referrals: int = 0,
        conversions: int = 0,
        revenue: float = 0.0,
    ) -> dict[str, Any]:
        """Performans takibi yapar.

        Args:
            ambassador_id: Elçi kimliği.
            referrals: Referans sayısı.
            conversions: Dönüşüm sayısı.
            revenue: Gelir.

        Returns:
            Performans bilgisi.
        """
        conv_rate = (
            conversions / referrals
            if referrals > 0
            else 0.0
        )

        if ambassador_id in (
            self._ambassadors
        ):
            self._ambassadors[
                ambassador_id
            ]["referrals"] = referrals
            self._ambassadors[
                ambassador_id
            ]["earnings"] = revenue

        return {
            "ambassador_id": ambassador_id,
            "referrals": referrals,
            "conversions": conversions,
            "conversion_rate": round(
                conv_rate, 2,
            ),
            "revenue": revenue,
            "tracked": True,
        }

    def update_tier(
        self,
        ambassador_id: str,
        referral_count: int = 0,
    ) -> dict[str, Any]:
        """Seviye günceller.

        Args:
            ambassador_id: Elçi kimliği.
            referral_count: Referans sayısı.

        Returns:
            Seviye bilgisi.
        """
        if referral_count >= 50:
            tier = "diamond"
        elif referral_count >= 20:
            tier = "platinum"
        elif referral_count >= 10:
            tier = "gold"
        elif referral_count >= 5:
            tier = "silver"
        else:
            tier = "bronze"

        if ambassador_id in (
            self._ambassadors
        ):
            self._ambassadors[
                ambassador_id
            ]["tier"] = tier

        return {
            "ambassador_id": ambassador_id,
            "tier": tier,
            "referral_count": referral_count,
            "updated": True,
        }

    def send_communication(
        self,
        ambassador_id: str,
        message_type: str = "update",
        channel: str = "email",
    ) -> dict[str, Any]:
        """İletişim gönderir.

        Args:
            ambassador_id: Elçi kimliği.
            message_type: Mesaj tipi.
            channel: Kanal.

        Returns:
            İletişim bilgisi.
        """
        return {
            "ambassador_id": ambassador_id,
            "message_type": message_type,
            "channel": channel,
            "sent": True,
        }

    def give_recognition(
        self,
        ambassador_id: str,
        recognition_type: str = "badge",
        reason: str = "",
    ) -> dict[str, Any]:
        """Tanınma verir.

        Args:
            ambassador_id: Elçi kimliği.
            recognition_type: Tanınma tipi.
            reason: Neden.

        Returns:
            Tanınma bilgisi.
        """
        self._stats[
            "recognitions_given"
        ] += 1

        return {
            "ambassador_id": ambassador_id,
            "recognition_type": (
                recognition_type
            ),
            "reason": reason,
            "given": True,
        }
