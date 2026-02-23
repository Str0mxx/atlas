"""Hata yonetimi iyilestirmeleri.

Billing hata zenginlestirme, sikistirma
yeniden deneme, TTS hata yuzeylenme
ve failover siniflandirma.
"""

import logging
import time
from typing import Any, Callable

from app.models.performance_models import (
    ErrorClassification,
    EnhancedError,
)

logger = logging.getLogger(__name__)


class ErrorEnhancer:
    """Hata yonetimi iyilestirmeleri.

    Attributes:
        _retry_count: Yeniden deneme sayaci.
        _max_retries: Maksimum yeniden deneme.
        _deferred_snapshots: Ertelenmis snapshot'lar.
    """

    def __init__(
        self,
        max_retries: int = 3,
    ) -> None:
        """ErrorEnhancer baslatir."""
        self._retry_count = 0
        self._max_retries = max_retries
        self._deferred_snapshots: list[
            dict[str, Any]
        ] = []

    def billing_error_with_model(
        self,
        error: str,
        model: str,
    ) -> str:
        """Billing hatasina model adini ekler.

        Args:
            error: Orijinal hata mesaji.
            model: Aktif model adi.

        Returns:
            Zenginlestirilmis hata mesaji.
        """
        if model:
            return f"{error} [model: {model}]"
        return error

    def compaction_retry(
        self,
        func: Callable[..., Any],
        context: dict[str, Any],
        max_retries: int = 0,
    ) -> Any:
        """Context overflow icin coklu yeniden deneme.

        Args:
            func: Calistirilacak fonksiyon.
            context: Baglam bilgisi.
            max_retries: Maks yeniden deneme.

        Returns:
            Fonksiyon sonucu.

        Raises:
            Exception: Tum denemeler basarisiz.
        """
        retries = max_retries or self._max_retries
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                result = func(**context)
                self._retry_count = attempt
                return result
            except Exception as e:
                last_error = e
                self._retry_count = attempt + 1
                logger.warning(
                    "Sikistirma denemesi %d/%d "
                    "basarisiz: %s",
                    attempt + 1,
                    retries,
                    e,
                )

                scale = 0.5 ** (attempt + 1)
                if "budget" in context:
                    context["budget"] = int(
                        context["budget"] * scale
                    )

        if last_error:
            raise last_error
        return None

    @staticmethod
    def surface_tts_errors(
        errors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Tum TTS saglayici hatalarini yuzeye cikarir.

        Hatalari yutmaz, hepsini dondurur.

        Args:
            errors: Hata listesi.

        Returns:
            Zenginlestirilmis hata listesi.
        """
        surfaced: list[dict[str, Any]] = []
        for err in errors:
            entry = dict(err)
            entry.setdefault(
                "surfaced", True,
            )
            entry.setdefault(
                "timestamp", time.time(),
            )
            surfaced.append(entry)
        return surfaced

    def defer_transient_snapshot(
        self,
        error: dict[str, Any],
    ) -> None:
        """Gecici hata snapshot'ini erteler.

        Toplu islem icin biriktirir.

        Args:
            error: Hata bilgisi.
        """
        entry = dict(error)
        entry["deferred_at"] = time.time()
        self._deferred_snapshots.append(entry)

    def get_deferred_snapshots(
        self,
    ) -> list[dict[str, Any]]:
        """Ertelenmis snapshot'lari dondurur.

        Returns:
            Ertelenmis snapshot listesi.
        """
        result = list(self._deferred_snapshots)
        self._deferred_snapshots.clear()
        return result

    @staticmethod
    def classify_abort_as_timeout(
        error_type: str,
    ) -> str:
        """Abort'u timeout olarak siniflandirir.

        Failover zincir tetiklemesi icin.

        Args:
            error_type: Hata tipi.

        Returns:
            Siniflandirilmis hata tipi.
        """
        if error_type in ("abort", "aborted"):
            return ErrorClassification.TIMEOUT
        return error_type

    def create_enhanced_error(
        self,
        error: str,
        model: str = "",
        provider: str = "",
    ) -> EnhancedError:
        """Zenginlestirilmis hata olusturur.

        Args:
            error: Hata mesaji.
            model: Model adi.
            provider: Saglayici adi.

        Returns:
            Zenginlestirilmis hata.
        """
        classification = (
            ErrorClassification.TRANSIENT
        )
        retryable = True

        err_lower = error.lower()
        if "billing" in err_lower or (
            "quota" in err_lower
        ):
            classification = (
                ErrorClassification.BILLING
            )
            retryable = False
        elif "timeout" in err_lower:
            classification = (
                ErrorClassification.TIMEOUT
            )
        elif "context" in err_lower and (
            "overflow" in err_lower
        ):
            classification = (
                ErrorClassification.CONTEXT_OVERFLOW
            )

        return EnhancedError(
            original_error=error,
            classification=classification,
            model=model,
            provider=provider,
            retryable=retryable,
            retry_count=self._retry_count,
            max_retries=self._max_retries,
        )
