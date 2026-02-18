"""
API Anahtar Dogrulayici modulu.

Anahtar format kontrolu, saglayici dogrulama,
izin testi, kota kontrolu, hata yonetimi.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class APIKeyValidator:
    """API anahtari dogrulayici.

    Attributes:
        _results: Dogrulama sonuclari.
        _stats: Istatistikler.
    """

    # Provider formatları (regex)
    PROVIDER_FORMATS: dict[str, str] = {
        "anthropic": r"^sk-ant-[a-zA-Z0-9\-_]{20,}$",
        "openai": r"^sk-[a-zA-Z0-9]{32,}$",
        "google": r"^AIza[a-zA-Z0-9\-_]{35,}$",
        "telegram": r"^\d{8,12}:[a-zA-Z0-9\-_]{35}$",
        "discord": r"^[a-zA-Z0-9]{24}\.[a-zA-Z0-9\-_]{6}\.[a-zA-Z0-9\-_]{27,}$",
        "slack": r"^xox[bpoa]-[a-zA-Z0-9\-]+$",
        "generic": r"^[a-zA-Z0-9\-_\.]{8,}$",
    }

    SUPPORTED_PROVIDERS: list[str] = [
        "anthropic",
        "openai",
        "google",
        "telegram",
        "discord",
        "slack",
        "generic",
    ]

    def __init__(self) -> None:
        """Dogrulayiciyi baslatir."""
        self._results: list[dict] = []
        self._stats: dict[str, int] = {
            "validations_run": 0,
            "format_checks": 0,
            "provider_checks": 0,
            "permission_tests": 0,
            "quota_checks": 0,
        }
        logger.info("APIKeyValidator baslatildi")

    def validate_format(
        self,
        key: str = "",
        provider: str = "generic",
    ) -> dict[str, Any]:
        """Anahtar formatini dogrular.

        Args:
            key: API anahtari.
            provider: Saglayici adi.

        Returns:
            Format dogrulama sonucu.
        """
        try:
            self._stats["format_checks"] += 1
            pattern = self.PROVIDER_FORMATS.get(
                provider,
                self.PROVIDER_FORMATS["generic"],
            )
            if not key:
                return {
                    "valid": False,
                    "format": "empty",
                    "provider": provider,
                    "error": "bos_anahtar",
                }
            match = bool(re.match(pattern, key))
            fmt = f"{provider}_format"
            return {
                "valid": match,
                "format": fmt,
                "provider": provider,
                "key_length": len(key),
            }
        except Exception as e:
            logger.error("Format kontrolu hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def validate_provider(
        self,
        key: str = "",
        provider: str = "generic",
    ) -> dict[str, Any]:
        """Saglayici dogrulama yapar.

        Args:
            key: API anahtari.
            provider: Saglayici adi.

        Returns:
            Saglayici dogrulama sonucu.
        """
        try:
            self._stats["provider_checks"] += 1

            if provider not in self.SUPPORTED_PROVIDERS:
                return {
                    "valid": False,
                    "provider": provider,
                    "error": "desteklenmeyen_saglayici",
                }

            # Format kontrolunu cagir
            fmt = self.validate_format(key, provider)
            if not fmt.get("valid"):
                return {
                    "valid": False,
                    "provider": provider,
                    "reason": "format_hatasi",
                }

            # Simüle: key bos degilse gecerli kabul et
            valid = bool(key and len(key) >= 8)
            return {
                "valid": valid,
                "provider": provider,
                "supported": True,
            }
        except Exception as e:
            logger.error("Saglayici dogrulama hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def test_permission(
        self,
        key: str = "",
        provider: str = "generic",
        permission: str = "read",
    ) -> dict[str, Any]:
        """Izin testi yapar.

        Args:
            key: API anahtari.
            provider: Saglayici adi.
            permission: Test edilecek izin.

        Returns:
            Izin testi sonucu.
        """
        try:
            self._stats["permission_tests"] += 1

            if not key:
                return {
                    "passed": False,
                    "permission": permission,
                    "error": "bos_anahtar",
                }

            # Simüle: format gecerliyse izin var kabul et
            fmt = self.validate_format(key, provider)
            passed = fmt.get("valid", False)

            return {
                "passed": passed,
                "permission": permission,
                "provider": provider,
            }
        except Exception as e:
            logger.error("Izin testi hatasi: %s", e)
            return {"passed": False, "error": str(e)}

    def check_quota(
        self,
        key: str = "",
        provider: str = "generic",
    ) -> dict[str, Any]:
        """Kota kontrolu yapar.

        Args:
            key: API anahtari.
            provider: Saglayici adi.

        Returns:
            Kota bilgisi.
        """
        try:
            self._stats["quota_checks"] += 1

            if not key:
                return {
                    "checked": False,
                    "error": "bos_anahtar",
                }

            # Simüle kota degerleri
            quota_map = {
                "anthropic": 100000,
                "openai": 90000,
                "google": 50000,
                "generic": 10000,
            }
            quota_remaining = quota_map.get(provider, 10000)

            return {
                "checked": True,
                "provider": provider,
                "quota_remaining": quota_remaining,
                "quota_unit": "tokens",
                "has_quota": quota_remaining > 0,
            }
        except Exception as e:
            logger.error("Kota kontrolu hatasi: %s", e)
            return {"checked": False, "error": str(e)}

    def validate_all(
        self,
        key: str = "",
        provider: str = "generic",
    ) -> dict[str, Any]:
        """Tum dogrulamalari calistirir.

        Args:
            key: API anahtari.
            provider: Saglayici adi.

        Returns:
            Toplu dogrulama sonucu.
        """
        try:
            self._stats["validations_run"] += 1

            checks: dict[str, Any] = {}

            fmt = self.validate_format(key, provider)
            checks["format"] = fmt.get("valid", False)

            prov = self.validate_provider(key, provider)
            checks["provider"] = prov.get("valid", False)

            perm = self.test_permission(key, provider)
            checks["permission"] = perm.get("passed", False)

            quota = self.check_quota(key, provider)
            checks["quota"] = quota.get("has_quota", False)

            all_valid = all(checks.values())

            result = {
                "valid": all_valid,
                "provider": provider,
                "checks": checks,
                "passed_count": sum(1 for v in checks.values() if v),
                "total_checks": len(checks),
            }
            self._results.append(result)
            return result

        except Exception as e:
            logger.error("Toplu dogrulama hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def get_supported_providers(self) -> list[str]:
        """Desteklenen saglayicilari dondurur.

        Returns:
            Saglayici listesi.
        """
        return list(self.SUPPORTED_PROVIDERS)

    def mask_key(self, key: str = "") -> str:
        """Anahtari maskeler (log icin).

        Args:
            key: API anahtari.

        Returns:
            Maskelenmis anahtar.
        """
        if not key or len(key) < 8:
            return "***"
        return key[:4] + "****" + key[-4:]

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "supported_providers": len(self.SUPPORTED_PROVIDERS),
                "validations_run": self._stats["validations_run"],
                "results_count": len(self._results),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
