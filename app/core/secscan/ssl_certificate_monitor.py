"""
SSL sertifika izleyici modulu.

Sertifika takibi, sure uyarilari,
zincir dogrulama, sifreleme gucu,
otomatik yenileme.
"""

import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SSLCertificateMonitor:
    """SSL sertifika izleyici.

    Attributes:
        _certificates: Sertifika kayitlari.
        _checks: Kontrol kayitlari.
        _renewals: Yenileme kayitlari.
        _stats: Istatistikler.
    """

    STRONG_CIPHERS: list[str] = [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
    ]

    WEAK_CIPHERS: list[str] = [
        "RC4",
        "DES",
        "3DES",
        "MD5",
        "NULL",
        "EXPORT",
    ]

    def __init__(self) -> None:
        """Izleyiciyi baslatir."""
        self._certificates: list[dict] = []
        self._checks: list[dict] = []
        self._renewals: list[dict] = []
        self._stats: dict[str, int] = {
            "certs_tracked": 0,
            "checks_done": 0,
            "renewals_done": 0,
        }
        logger.info(
            "SSLCertificateMonitor baslatildi"
        )

    @property
    def cert_count(self) -> int:
        """Sertifika sayisi."""
        return len(self._certificates)

    def add_certificate(
        self,
        domain: str = "",
        issuer: str = "",
        expires_at: str = "",
        cipher_suite: str = "",
        key_size: int = 2048,
    ) -> dict[str, Any]:
        """Sertifika ekler.

        Args:
            domain: Alan adi.
            issuer: Veren kurum.
            expires_at: Bitis tarihi (ISO).
            cipher_suite: Sifreleme paketi.
            key_size: Anahtar boyutu.

        Returns:
            Ekleme bilgisi.
        """
        try:
            cid = f"sc_{uuid4()!s:.8}"
            cert = {
                "cert_id": cid,
                "domain": domain,
                "issuer": issuer,
                "expires_at": expires_at,
                "cipher_suite": cipher_suite,
                "key_size": key_size,
                "auto_renew": False,
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._certificates.append(cert)
            self._stats["certs_tracked"] += 1

            return {
                "cert_id": cid,
                "domain": domain,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def check_expiration(
        self,
        domain: str = "",
        warn_days: int = 30,
    ) -> dict[str, Any]:
        """Sure kontrol eder.

        Args:
            domain: Alan adi.
            warn_days: Uyari gunu.

        Returns:
            Kontrol bilgisi.
        """
        try:
            for cert in self._certificates:
                if cert["domain"] == domain:
                    exp = datetime.fromisoformat(
                        cert["expires_at"]
                    )
                    now = datetime.now(
                        timezone.utc
                    )
                    days_left = (
                        exp - now
                    ).days

                    expiring = (
                        days_left <= warn_days
                    )
                    expired = days_left <= 0

                    check = {
                        "domain": domain,
                        "days_left": days_left,
                        "expiring": expiring,
                        "expired": expired,
                        "timestamp": now.isoformat(),
                    }
                    self._checks.append(check)
                    self._stats[
                        "checks_done"
                    ] += 1

                    return {
                        "domain": domain,
                        "days_left": days_left,
                        "expiring": expiring,
                        "expired": expired,
                        "checked": True,
                    }

            return {
                "checked": False,
                "error": "Sertifika bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def validate_chain(
        self,
        domain: str = "",
        chain: list[str] | None = None,
    ) -> dict[str, Any]:
        """Zincir dogrular.

        Args:
            domain: Alan adi.
            chain: Sertifika zinciri.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            cert_chain = chain or []
            valid = len(cert_chain) >= 2
            issues: list[str] = []

            if len(cert_chain) == 0:
                issues.append(
                    "Zincir bos"
                )
            elif len(cert_chain) == 1:
                issues.append(
                    "Ara sertifika eksik"
                )

            return {
                "domain": domain,
                "chain_length": len(
                    cert_chain
                ),
                "valid": valid,
                "issues": issues,
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "validated": False,
                "error": str(e),
            }

    def check_cipher_strength(
        self,
        domain: str = "",
    ) -> dict[str, Any]:
        """Sifreleme gucu kontrol eder.

        Args:
            domain: Alan adi.

        Returns:
            Guc bilgisi.
        """
        try:
            for cert in self._certificates:
                if cert["domain"] == domain:
                    cipher = cert[
                        "cipher_suite"
                    ]
                    key_size = cert["key_size"]

                    strong = (
                        cipher
                        in self.STRONG_CIPHERS
                    )
                    weak = any(
                        w in cipher.upper()
                        for w in self.WEAK_CIPHERS
                    )
                    key_ok = key_size >= 2048

                    issues: list[str] = []
                    if weak:
                        issues.append(
                            "Zayif sifreleme"
                        )
                    if not key_ok:
                        issues.append(
                            "Kucuk anahtar"
                        )

                    grade = "A"
                    if weak or not key_ok:
                        grade = "F"
                    elif not strong:
                        grade = "B"

                    return {
                        "domain": domain,
                        "cipher": cipher,
                        "key_size": key_size,
                        "strong": strong,
                        "weak": weak,
                        "grade": grade,
                        "issues": issues,
                        "checked": True,
                    }

            return {
                "checked": False,
                "error": "Sertifika bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def enable_auto_renewal(
        self,
        domain: str = "",
    ) -> dict[str, Any]:
        """Otomatik yenileme aktifler.

        Args:
            domain: Alan adi.

        Returns:
            Aktivasyon bilgisi.
        """
        try:
            for cert in self._certificates:
                if cert["domain"] == domain:
                    cert["auto_renew"] = True
                    return {
                        "domain": domain,
                        "auto_renew": True,
                        "enabled": True,
                    }

            return {
                "enabled": False,
                "error": "Sertifika bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "enabled": False,
                "error": str(e),
            }

    def renew_certificate(
        self,
        domain: str = "",
        new_expires: str = "",
    ) -> dict[str, Any]:
        """Sertifika yeniler.

        Args:
            domain: Alan adi.
            new_expires: Yeni bitis tarihi.

        Returns:
            Yenileme bilgisi.
        """
        try:
            for cert in self._certificates:
                if cert["domain"] == domain:
                    old_exp = cert[
                        "expires_at"
                    ]
                    if not new_expires:
                        new_exp = (
                            datetime.now(
                                timezone.utc
                            )
                            + timedelta(days=365)
                        )
                        new_expires = (
                            new_exp.isoformat()
                        )

                    cert[
                        "expires_at"
                    ] = new_expires

                    renewal = {
                        "domain": domain,
                        "old_expires": old_exp,
                        "new_expires": (
                            new_expires
                        ),
                        "renewed_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }
                    self._renewals.append(
                        renewal
                    )
                    self._stats[
                        "renewals_done"
                    ] += 1

                    return {
                        "domain": domain,
                        "new_expires": (
                            new_expires
                        ),
                        "renewed": True,
                    }

            return {
                "renewed": False,
                "error": "Sertifika bulunamadi",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "renewed": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            now = datetime.now(timezone.utc)
            expiring = 0
            expired = 0
            for cert in self._certificates:
                try:
                    exp = datetime.fromisoformat(
                        cert["expires_at"]
                    )
                    days = (exp - now).days
                    if days <= 0:
                        expired += 1
                    elif days <= 30:
                        expiring += 1
                except (ValueError, KeyError):
                    pass

            return {
                "total_certs": len(
                    self._certificates
                ),
                "expiring_soon": expiring,
                "expired": expired,
                "renewals": len(
                    self._renewals
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
