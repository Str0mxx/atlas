"""ATLAS Yeniden Deneme Politikasi modulu.

Deneme stratejileri, geri cekilme
algoritmalari, deneme butceleri,
idempotency ve devre entegrasyonu.
"""

import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Yeniden deneme politikasi.

    Basarisiz istekleri yeniden dener.

    Attributes:
        _policies: Politika tanimlari.
        _budgets: Deneme butceleri.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        strategy: str = "exponential",
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        """Deneme politikasini baslatir.

        Args:
            max_attempts: Maks deneme.
            strategy: Strateji.
            base_delay: Temel gecikme (sn).
            max_delay: Maks gecikme (sn).
        """
        self._max_attempts = max_attempts
        self._strategy = strategy
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._policies: dict[
            str, dict[str, Any]
        ] = {}
        self._budgets: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._idempotency_keys: set[str] = set()

        logger.info(
            "RetryPolicy baslatildi: "
            "max=%d, strategy=%s",
            max_attempts, strategy,
        )

    def should_retry(
        self,
        service: str,
        attempt: int,
        error: str = "",
    ) -> dict[str, Any]:
        """Yeniden denenmeli mi.

        Args:
            service: Servis adi.
            attempt: Mevcut deneme.
            error: Hata mesaji.

        Returns:
            Karar bilgisi.
        """
        policy = self._policies.get(service)
        max_att = (
            policy["max_attempts"]
            if policy else self._max_attempts
        )
        strategy = (
            policy["strategy"]
            if policy else self._strategy
        )

        # Butce kontrolu
        budget = self._budgets.get(service)
        if budget:
            if budget["remaining"] <= 0:
                return {
                    "retry": False,
                    "reason": "budget_exhausted",
                }
            budget["remaining"] -= 1

        if attempt >= max_att:
            return {
                "retry": False,
                "reason": "max_attempts",
            }

        delay = self._calculate_delay(
            attempt, strategy,
        )

        record = {
            "service": service,
            "attempt": attempt,
            "delay": delay,
            "error": error,
            "timestamp": time.time(),
        }
        self._history.append(record)

        return {
            "retry": True,
            "delay": delay,
            "attempt": attempt + 1,
            "max_attempts": max_att,
        }

    def _calculate_delay(
        self,
        attempt: int,
        strategy: str,
    ) -> float:
        """Gecikme hesaplar.

        Args:
            attempt: Deneme numarasi.
            strategy: Strateji.

        Returns:
            Gecikme (sn).
        """
        if strategy == "fixed":
            delay = self._base_delay
        elif strategy == "exponential":
            delay = self._base_delay * (
                2 ** attempt
            )
        elif strategy == "linear":
            delay = self._base_delay * (
                attempt + 1
            )
        elif strategy == "jitter":
            base = self._base_delay * (
                2 ** attempt
            )
            delay = base * random.uniform(0.5, 1.5)
        elif strategy == "fibonacci":
            delay = self._base_delay * self._fib(
                attempt + 1,
            )
        else:
            delay = self._base_delay

        return min(delay, self._max_delay)

    def _fib(self, n: int) -> int:
        """Fibonacci sayisi.

        Args:
            n: Sira.

        Returns:
            Fibonacci degeri.
        """
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    def set_policy(
        self,
        service: str,
        max_attempts: int | None = None,
        strategy: str | None = None,
    ) -> dict[str, Any]:
        """Servis politikasi ayarlar.

        Args:
            service: Servis adi.
            max_attempts: Maks deneme.
            strategy: Strateji.

        Returns:
            Politika bilgisi.
        """
        self._policies[service] = {
            "max_attempts": (
                max_attempts or self._max_attempts
            ),
            "strategy": (
                strategy or self._strategy
            ),
        }
        return self._policies[service]

    def set_budget(
        self,
        service: str,
        max_retries: int,
        window_seconds: int = 60,
    ) -> None:
        """Deneme butcesi ayarlar.

        Args:
            service: Servis adi.
            max_retries: Maks yeniden deneme.
            window_seconds: Pencere suresi.
        """
        self._budgets[service] = {
            "max_retries": max_retries,
            "remaining": max_retries,
            "window": window_seconds,
            "reset_at": (
                time.time() + window_seconds
            ),
        }

    def reset_budget(
        self,
        service: str,
    ) -> bool:
        """Butceyi sifirlar.

        Args:
            service: Servis adi.

        Returns:
            Basarili mi.
        """
        budget = self._budgets.get(service)
        if budget:
            budget["remaining"] = (
                budget["max_retries"]
            )
            budget["reset_at"] = (
                time.time() + budget["window"]
            )
            return True
        return False

    def mark_idempotent(
        self,
        key: str,
    ) -> bool:
        """Idempotent istek isaretler.

        Args:
            key: Idempotency anahtari.

        Returns:
            Yeni mi (True) yoksa tekrar mi (False).
        """
        if key in self._idempotency_keys:
            return False
        self._idempotency_keys.add(key)
        return True

    def is_idempotent(
        self,
        key: str,
    ) -> bool:
        """Idempotent mi kontrol eder.

        Args:
            key: Anahtar.

        Returns:
            Daha once islendi mi.
        """
        return key in self._idempotency_keys

    def get_history(
        self,
        service: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Deneme gecmisi getirir.

        Args:
            service: Filtre.
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        history = self._history
        if service:
            history = [
                h for h in history
                if h["service"] == service
            ]
        return history[-limit:]

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)

    @property
    def retry_count(self) -> int:
        """Toplam deneme sayisi."""
        return len(self._history)

    @property
    def idempotent_count(self) -> int:
        """Idempotent anahtar sayisi."""
        return len(self._idempotency_keys)
