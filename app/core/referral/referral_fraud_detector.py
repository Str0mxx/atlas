"""ATLAS Referans Dolandırıcılık Tespiti.

Kendi kendine referans, sahte hesap,
desen analizi, hız kontrolleri ve kara liste.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ReferralFraudDetector:
    """Referans dolandırıcılık tespitçisi.

    Referans dolandırıcılıklarını tespit eder,
    şüpheli davranışları analiz eder.

    Attributes:
        _blacklist: Kara liste.
        _detections: Tespit kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._blacklist: set[str] = set()
        self._detections: dict[
            str, dict
        ] = {}
        self._stats = {
            "checks_performed": 0,
            "frauds_detected": 0,
        }
        logger.info(
            "ReferralFraudDetector "
            "baslatildi",
        )

    @property
    def check_count(self) -> int:
        """Yapılan kontrol sayısı."""
        return self._stats[
            "checks_performed"
        ]

    @property
    def fraud_count(self) -> int:
        """Tespit edilen dolandırıcılık."""
        return self._stats[
            "frauds_detected"
        ]

    def detect_self_referral(
        self,
        referrer_id: str,
        referred_id: str,
        referrer_ip: str = "",
        referred_ip: str = "",
    ) -> dict[str, Any]:
        """Kendi kendine referans tespiti.

        Args:
            referrer_id: Referansçı kimliği.
            referred_id: Davet edilen kimliği.
            referrer_ip: Referansçı IP.
            referred_ip: Davet edilen IP.

        Returns:
            Tespit bilgisi.
        """
        self._stats[
            "checks_performed"
        ] += 1

        is_self = (
            referrer_id == referred_id
        )
        same_ip = (
            referrer_ip == referred_ip
            and referrer_ip != ""
        )
        fraud = is_self or same_ip

        if fraud:
            self._stats[
                "frauds_detected"
            ] += 1

        risk = (
            "high" if fraud else "clean"
        )

        return {
            "referrer_id": referrer_id,
            "referred_id": referred_id,
            "is_self_referral": is_self,
            "same_ip": same_ip,
            "risk": risk,
            "detected": True,
        }

    def detect_fake_account(
        self,
        account_id: str,
        account_age_hours: int = 0,
        profile_complete: bool = True,
        email_verified: bool = True,
    ) -> dict[str, Any]:
        """Sahte hesap tespiti.

        Args:
            account_id: Hesap kimliği.
            account_age_hours: Hesap yaşı (saat).
            profile_complete: Profil tamamlanmış.
            email_verified: E-posta doğrulanmış.

        Returns:
            Tespit bilgisi.
        """
        self._stats[
            "checks_performed"
        ] += 1

        signals = 0
        if account_age_hours < 1:
            signals += 2
        elif account_age_hours < 24:
            signals += 1
        if not profile_complete:
            signals += 1
        if not email_verified:
            signals += 2

        if signals >= 3:
            risk = "high"
        elif signals >= 2:
            risk = "medium"
        elif signals >= 1:
            risk = "low"
        else:
            risk = "clean"

        if risk == "high":
            self._stats[
                "frauds_detected"
            ] += 1

        return {
            "account_id": account_id,
            "risk": risk,
            "signal_count": signals,
            "detected": True,
        }

    def analyze_pattern(
        self,
        referrer_id: str,
        referral_times: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Desen analizi yapar.

        Args:
            referrer_id: Referansçı kimliği.
            referral_times: Referans zamanları
                (saat cinsinden aralıklar).

        Returns:
            Analiz bilgisi.
        """
        if referral_times is None:
            referral_times = []

        self._stats[
            "checks_performed"
        ] += 1

        suspicious = False
        if len(referral_times) >= 3:
            avg_interval = (
                sum(referral_times)
                / len(referral_times)
            )
            if avg_interval < 0.1:
                suspicious = True

        if suspicious:
            self._stats[
                "frauds_detected"
            ] += 1

        return {
            "referrer_id": referrer_id,
            "referral_count": len(
                referral_times,
            ),
            "suspicious": suspicious,
            "analyzed": True,
        }

    def check_velocity(
        self,
        referrer_id: str,
        referrals_last_hour: int = 0,
        referrals_last_day: int = 0,
        hourly_limit: int = 5,
        daily_limit: int = 20,
    ) -> dict[str, Any]:
        """Hız kontrolü yapar.

        Args:
            referrer_id: Referansçı kimliği.
            referrals_last_hour: Son 1 saat.
            referrals_last_day: Son 1 gün.
            hourly_limit: Saatlik limit.
            daily_limit: Günlük limit.

        Returns:
            Kontrol bilgisi.
        """
        self._stats[
            "checks_performed"
        ] += 1

        hourly_exceeded = (
            referrals_last_hour
            >= hourly_limit
        )
        daily_exceeded = (
            referrals_last_day
            >= daily_limit
        )
        violation = (
            hourly_exceeded or daily_exceeded
        )

        if violation:
            self._stats[
                "frauds_detected"
            ] += 1

        return {
            "referrer_id": referrer_id,
            "hourly_exceeded": hourly_exceeded,
            "daily_exceeded": daily_exceeded,
            "violation": violation,
            "checked": True,
        }

    def blacklist(
        self,
        entity_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Kara listeye ekler.

        Args:
            entity_id: Varlık kimliği.
            reason: Neden.

        Returns:
            Kara liste bilgisi.
        """
        self._blacklist.add(entity_id)

        return {
            "entity_id": entity_id,
            "reason": reason,
            "blacklist_size": len(
                self._blacklist,
            ),
            "blacklisted": True,
        }
