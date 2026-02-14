"""ATLAS Entegrasyon Hata Yoneticisi modulu.

Hata siniflandirma, yeniden deneme
stratejileri, yedek yanitlar, raporlama
ve kurtarma aksiyonlari.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.integration import ErrorCategory, IntegrationError

logger = logging.getLogger(__name__)


class IntegrationErrorHandler:
    """Entegrasyon hata yoneticisi.

    Dis servis hatalarini siniflandirir,
    yeniden dener ve kurtarma saglar.

    Attributes:
        _errors: Hata kayitlari.
        _retry_policies: Yeniden deneme politikalari.
        _fallbacks: Yedek yanitlar.
        _recovery_actions: Kurtarma aksiyonlari.
        _max_retries: Maks yeniden deneme.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Hata yoneticisini baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._errors: list[IntegrationError] = []
        self._retry_policies: dict[str, dict[str, Any]] = {}
        self._fallbacks: dict[str, dict[str, Any]] = {}
        self._recovery_actions: list[dict[str, Any]] = []
        self._max_retries = max(1, max_retries)

        logger.info(
            "IntegrationErrorHandler baslatildi (max_retries=%d)",
            self._max_retries,
        )

    def handle_error(
        self,
        service: str,
        message: str,
        status_code: int = 0,
        category: ErrorCategory | None = None,
    ) -> dict[str, Any]:
        """Hata isler.

        Args:
            service: Servis adi.
            message: Hata mesaji.
            status_code: HTTP durum kodu.
            category: Hata kategorisi.

        Returns:
            Isleme sonucu.
        """
        if category is None:
            category = self._categorize_error(
                status_code, message,
            )

        retryable = category in (
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.SERVER,
        )

        error = IntegrationError(
            service=service,
            category=category,
            message=message,
            status_code=status_code,
            retryable=retryable,
        )
        self._errors.append(error)

        result: dict[str, Any] = {
            "error_id": error.error_id,
            "category": category.value,
            "retryable": retryable,
        }

        # Yedek yanit kontrol
        fallback = self._fallbacks.get(service)
        if fallback:
            result["fallback"] = fallback.get("response", {})
            result["used_fallback"] = True

        # Kurtarma aksiyonu
        recovery = self._get_recovery_action(category)
        if recovery:
            result["recovery_action"] = recovery
            self._recovery_actions.append({
                "error_id": error.error_id,
                "action": recovery,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        logger.warning(
            "Entegrasyon hatasi: %s - %s (%s)",
            service, message, category.value,
        )
        return result

    def set_retry_policy(
        self,
        service: str,
        max_retries: int | None = None,
        backoff: str = "exponential",
        retry_on: list[str] | None = None,
    ) -> dict[str, Any]:
        """Yeniden deneme politikasi ayarlar.

        Args:
            service: Servis adi.
            max_retries: Maks deneme.
            backoff: Backoff stratejisi.
            retry_on: Hangi kategorilerde dene.

        Returns:
            Politika bilgisi.
        """
        policy = {
            "service": service,
            "max_retries": max_retries or self._max_retries,
            "backoff": backoff,
            "retry_on": retry_on or [
                "network", "timeout", "server",
            ],
        }
        self._retry_policies[service] = policy
        return policy

    def should_retry(
        self,
        service: str,
        attempt: int,
        category: ErrorCategory,
    ) -> dict[str, Any]:
        """Yeniden denenmeli mi kontrol eder.

        Args:
            service: Servis adi.
            attempt: Deneme sayisi.
            category: Hata kategorisi.

        Returns:
            Karar sonucu.
        """
        policy = self._retry_policies.get(service, {})
        max_r = policy.get("max_retries", self._max_retries)
        retry_on = policy.get("retry_on", [
            "network", "timeout", "server",
        ])

        if attempt >= max_r:
            return {"retry": False, "reason": "max_retries_reached"}

        if category.value not in retry_on:
            return {"retry": False, "reason": "category_not_retryable"}

        backoff = policy.get("backoff", "exponential")
        if backoff == "exponential":
            wait = min(2 ** attempt, 300)
        elif backoff == "linear":
            wait = min(attempt * 5, 300)
        else:
            wait = 10

        return {
            "retry": True,
            "attempt": attempt + 1,
            "wait_seconds": wait,
            "backoff": backoff,
        }

    def set_fallback(
        self,
        service: str,
        response: dict[str, Any],
        description: str = "",
    ) -> dict[str, Any]:
        """Yedek yanit ayarlar.

        Args:
            service: Servis adi.
            response: Yedek yanit verisi.
            description: Aciklama.

        Returns:
            Yedek bilgisi.
        """
        fallback = {
            "service": service,
            "response": response,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._fallbacks[service] = fallback
        return fallback

    def get_error_report(
        self,
        service: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Hata raporu getirir.

        Args:
            service: Servis filtresi.
            limit: Maks kayit.

        Returns:
            Hata raporu.
        """
        errors = self._errors
        if service:
            errors = [
                e for e in errors
                if e.service == service
            ]

        recent = errors[-limit:]

        # Kategori dagilimi
        categories: dict[str, int] = {}
        for err in errors:
            cat = err.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_errors": len(errors),
            "recent_errors": [
                {
                    "error_id": e.error_id,
                    "service": e.service,
                    "category": e.category.value,
                    "message": e.message,
                    "retryable": e.retryable,
                }
                for e in recent
            ],
            "category_distribution": categories,
        }

    def get_errors_by_service(
        self,
        service: str,
    ) -> list[dict[str, Any]]:
        """Servise gore hatalari getirir.

        Args:
            service: Servis adi.

        Returns:
            Hata listesi.
        """
        return [
            {
                "error_id": e.error_id,
                "category": e.category.value,
                "message": e.message,
                "status_code": e.status_code,
            }
            for e in self._errors
            if e.service == service
        ]

    def clear_errors(
        self,
        service: str = "",
    ) -> int:
        """Hatalari temizler.

        Args:
            service: Servis filtresi.

        Returns:
            Temizlenen sayisi.
        """
        if service:
            before = len(self._errors)
            self._errors = [
                e for e in self._errors
                if e.service != service
            ]
            return before - len(self._errors)

        count = len(self._errors)
        self._errors.clear()
        return count

    def _categorize_error(
        self,
        status_code: int,
        message: str,
    ) -> ErrorCategory:
        """Hatayi siniflandirir.

        Args:
            status_code: HTTP durum kodu.
            message: Hata mesaji.

        Returns:
            Hata kategorisi.
        """
        msg_lower = message.lower()

        if "timeout" in msg_lower:
            return ErrorCategory.TIMEOUT
        if "rate limit" in msg_lower or status_code == 429:
            return ErrorCategory.RATE_LIMIT
        if "auth" in msg_lower or status_code in (401, 403):
            return ErrorCategory.AUTH
        if "connection" in msg_lower or "network" in msg_lower:
            return ErrorCategory.NETWORK
        if 500 <= status_code < 600:
            return ErrorCategory.SERVER
        if 400 <= status_code < 500:
            return ErrorCategory.CLIENT

        return ErrorCategory.NETWORK

    def _get_recovery_action(
        self,
        category: ErrorCategory,
    ) -> str:
        """Kurtarma aksiyonu belirler.

        Args:
            category: Hata kategorisi.

        Returns:
            Aksiyon aciklamasi.
        """
        actions = {
            ErrorCategory.NETWORK: "Baglanti yeniden dene",
            ErrorCategory.AUTH: "Kimlik bilgilerini yenile",
            ErrorCategory.RATE_LIMIT: "Bekle ve yeniden dene",
            ErrorCategory.TIMEOUT: "Zaman asimi artir",
            ErrorCategory.SERVER: "Yedek servisi kullan",
            ErrorCategory.CLIENT: "Istegi duzelt",
            ErrorCategory.DATA: "Veriyi dogrula",
        }
        return actions.get(category, "")

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return len(self._errors)

    @property
    def recovery_count(self) -> int:
        """Kurtarma sayisi."""
        return len(self._recovery_actions)

    @property
    def fallback_count(self) -> int:
        """Yedek yanit sayisi."""
        return len(self._fallbacks)
