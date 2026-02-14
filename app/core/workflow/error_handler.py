"""ATLAS Is Akisi Hata Yoneticisi modulu.

Hata yakalama, yeniden deneme
mantigi, yedek aksiyonlar,
telafi ve bildirim.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class WorkflowErrorHandler:
    """Is akisi hata yoneticisi.

    Hatalari yakalar, yeniden dener
    ve yedek aksiyonlar calistirir.

    Attributes:
        _handlers: Hata isleyicileri.
        _retry_policies: Yeniden deneme politikalari.
        _errors: Hata gecmisi.
    """

    def __init__(
        self,
        max_retries: int = 3,
    ) -> None:
        """Hata yoneticisini baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._handlers: dict[
            str, Callable[[Exception], Any]
        ] = {}
        self._fallbacks: dict[
            str, Callable[[], Any]
        ] = {}
        self._retry_policies: dict[
            str, dict[str, Any]
        ] = {}
        self._errors: list[dict[str, Any]] = []
        self._compensations: dict[
            str, Callable[[], Any]
        ] = {}
        self._max_retries = max_retries

        logger.info(
            "WorkflowErrorHandler baslatildi",
        )

    def register_handler(
        self,
        error_type: str,
        handler: Callable[[Exception], Any],
    ) -> None:
        """Hata isleyici kaydeder.

        Args:
            error_type: Hata turu.
            handler: Isleyici fonksiyon.
        """
        self._handlers[error_type] = handler

    def register_fallback(
        self,
        action_name: str,
        fallback: Callable[[], Any],
    ) -> None:
        """Yedek aksiyon kaydeder.

        Args:
            action_name: Aksiyon adi.
            fallback: Yedek fonksiyon.
        """
        self._fallbacks[action_name] = fallback

    def register_compensation(
        self,
        step_name: str,
        compensation: Callable[[], Any],
    ) -> None:
        """Telafi aksiyonu kaydeder.

        Args:
            step_name: Adim adi.
            compensation: Telafi fonksiyonu.
        """
        self._compensations[step_name] = compensation

    def set_retry_policy(
        self,
        action_name: str,
        max_retries: int = 0,
        delay_seconds: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> dict[str, Any]:
        """Yeniden deneme politikasi ayarlar.

        Args:
            action_name: Aksiyon adi.
            max_retries: Maks deneme.
            delay_seconds: Bekleme suresi.
            backoff_factor: Artis katsayisi.

        Returns:
            Politika bilgisi.
        """
        retries = max_retries or self._max_retries
        policy = {
            "action": action_name,
            "max_retries": retries,
            "delay": delay_seconds,
            "backoff": backoff_factor,
        }
        self._retry_policies[action_name] = policy
        return policy

    def execute_with_retry(
        self,
        action_name: str,
        action: Callable[[], Any],
    ) -> dict[str, Any]:
        """Yeniden denemeli calistirir.

        Args:
            action_name: Aksiyon adi.
            action: Aksiyon fonksiyonu.

        Returns:
            Calistirma sonucu.
        """
        policy = self._retry_policies.get(
            action_name,
            {
                "max_retries": self._max_retries,
                "delay": 0,
                "backoff": 1.0,
            },
        )

        max_tries = policy["max_retries"]
        attempt = 0
        last_error = ""

        while attempt <= max_tries:
            try:
                result = action()
                return {
                    "success": True,
                    "action": action_name,
                    "result": result,
                    "attempts": attempt + 1,
                }
            except Exception as e:
                last_error = str(e)
                attempt += 1
                self._errors.append({
                    "action": action_name,
                    "error": last_error,
                    "attempt": attempt,
                    "at": time.time(),
                })

        # Yedek aksiyon dene
        fallback = self._fallbacks.get(action_name)
        if fallback:
            try:
                result = fallback()
                return {
                    "success": True,
                    "action": action_name,
                    "result": result,
                    "fallback": True,
                    "attempts": attempt,
                }
            except Exception as e:
                last_error = f"fallback: {e}"

        return {
            "success": False,
            "action": action_name,
            "error": last_error,
            "attempts": attempt,
        }

    def handle_error(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Hata isler.

        Args:
            error: Hata.
            context: Baglam.

        Returns:
            Islem sonucu.
        """
        error_type = type(error).__name__
        handler = self._handlers.get(error_type)

        self._errors.append({
            "type": error_type,
            "message": str(error),
            "context": context or {},
            "handled": handler is not None,
            "at": time.time(),
        })

        if handler:
            result = handler(error)
            return {
                "handled": True,
                "type": error_type,
                "result": result,
            }

        return {
            "handled": False,
            "type": error_type,
            "message": str(error),
        }

    def compensate(
        self,
        steps: list[str],
    ) -> list[dict[str, Any]]:
        """Telafi aksiyonlarini calistirir.

        Args:
            steps: Telafi edilecek adimlar.

        Returns:
            Telafi sonuclari.
        """
        results: list[dict[str, Any]] = []
        for step in reversed(steps):
            comp = self._compensations.get(step)
            if comp:
                try:
                    comp()
                    results.append({
                        "step": step,
                        "compensated": True,
                    })
                except Exception as e:
                    results.append({
                        "step": step,
                        "compensated": False,
                        "error": str(e),
                    })
        return results

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return len(self._errors)

    @property
    def handler_count(self) -> int:
        """Isleyici sayisi."""
        return len(self._handlers)

    @property
    def fallback_count(self) -> int:
        """Yedek sayisi."""
        return len(self._fallbacks)

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._retry_policies)

    @property
    def compensation_count(self) -> int:
        """Telafi sayisi."""
        return len(self._compensations)
