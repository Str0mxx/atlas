"""Akim hata yoneticisi.

Hata tespiti, yeniden deneme, kismi kurtarma,
yedek ve kullanici bildirimi saglar.
"""

import logging
import time
from typing import Any, Callable

from app.models.streaming_models import (
    StreamError,
    StreamErrorType,
)

logger = logging.getLogger(__name__)

# Yeniden denenebilir hata tipleri
_RETRYABLE_ERRORS = {
    StreamErrorType.CONNECTION,
    StreamErrorType.TIMEOUT,
    StreamErrorType.RATE_LIMIT,
    StreamErrorType.SERVER,
}


class StreamErrorHandler:
    """Akim hata yoneticisi.

    Hata siniflandirma, yeniden deneme stratejisi,
    kismi kurtarma ve bildirim saglar.

    Attributes:
        _max_retries: Maksimum yeniden deneme.
        _retry_delay_ms: Yeniden deneme gecikmesi.
        _errors: Hata gecmisi.
        _retry_count: Toplam yeniden deneme.
        _recovery_count: Kurtarma sayisi.
        _callbacks: Hata geri cagirimlari.
        _partial_content: Kismi icerik.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay_ms: int = 1000,
    ) -> None:
        """StreamErrorHandler baslatir.

        Args:
            max_retries: Maksimum yeniden deneme.
            retry_delay_ms: Yeniden deneme gecikmesi (ms).
        """
        self._max_retries = max_retries
        self._retry_delay_ms = retry_delay_ms
        self._errors: list[StreamError] = []
        self._retry_count: int = 0
        self._recovery_count: int = 0
        self._callbacks: list[Callable[[StreamError], None]] = []
        self._partial_content: str = ""
        self._consecutive_errors: int = 0
        self._last_error_time: float = 0.0

        logger.info(
            "StreamErrorHandler baslatildi: max_retries=%d, delay=%dms",
            max_retries, retry_delay_ms,
        )

    def handle_error(
        self,
        error: Exception | str,
        provider: str = "",
        partial_content: str = "",
    ) -> StreamError:
        """Hatayi isler.

        Args:
            error: Hata nesnesi veya mesaj.
            provider: Saglayici adi.
            partial_content: Kismi icerik.

        Returns:
            Islenmis hata.
        """
        error_msg = str(error)
        error_type = self._classify_error(error_msg)
        retryable = error_type in _RETRYABLE_ERRORS

        # Yeniden deneme gecikmesi (ustsel geri cekilme)
        retry_after = 0
        if retryable:
            retry_after = self._calculate_retry_delay()

        stream_error = StreamError(
            error_type=error_type,
            message=error_msg,
            retryable=retryable,
            retry_after_ms=retry_after,
            partial_content=partial_content,
            provider=provider,
        )

        self._errors.append(stream_error)
        self._consecutive_errors += 1
        self._last_error_time = time.time()

        if partial_content:
            self._partial_content = partial_content

        # Geri cagirimlari calistir
        for cb in self._callbacks:
            try:
                cb(stream_error)
            except Exception as e:
                logger.error("Hata callback hatasi: %s", e)

        logger.warning(
            "Akim hatasi: type=%s, provider=%s, retryable=%s",
            error_type.value, provider, retryable,
        )

        return stream_error

    def _classify_error(self, error_msg: str) -> StreamErrorType:
        """Hatayi siniflandirir.

        Args:
            error_msg: Hata mesaji.

        Returns:
            Hata tipi.
        """
        msg = error_msg.lower()

        if any(k in msg for k in ("connection", "connect", "refused", "reset")):
            return StreamErrorType.CONNECTION

        if any(k in msg for k in ("timeout", "timed out", "deadline")):
            return StreamErrorType.TIMEOUT

        if any(k in msg for k in ("rate limit", "429", "too many", "throttle")):
            return StreamErrorType.RATE_LIMIT

        if any(k in msg for k in ("auth", "401", "403", "unauthorized", "forbidden")):
            return StreamErrorType.AUTH

        if any(k in msg for k in ("500", "502", "503", "504", "server error", "internal")):
            return StreamErrorType.SERVER

        if any(k in msg for k in ("parse", "json", "decode", "invalid format")):
            return StreamErrorType.PARSE

        if any(k in msg for k in ("incomplete", "truncated", "partial")):
            return StreamErrorType.INCOMPLETE

        if any(k in msg for k in ("cancel", "abort", "stopped")):
            return StreamErrorType.CANCELLED

        return StreamErrorType.UNKNOWN

    def _calculate_retry_delay(self) -> int:
        """Ustsel geri cekilme ile gecikme hesaplar.

        Returns:
            Gecikme (ms).
        """
        # 2^n * base_delay, max 30 saniye
        delay = self._retry_delay_ms * (2 ** self._consecutive_errors)
        return min(delay, 30000)

    def should_retry(self, error: StreamError) -> bool:
        """Yeniden denenmeli mi?

        Args:
            error: Hata nesnesi.

        Returns:
            Yeniden denenmeli ise True.
        """
        if not error.retryable:
            return False

        if self._retry_count >= self._max_retries:
            return False

        if self._consecutive_errors > self._max_retries * 2:
            return False

        return True

    def record_retry(self) -> None:
        """Yeniden deneme kaydeder."""
        self._retry_count += 1
        logger.info(
            "Yeniden deneme: %d/%d",
            self._retry_count, self._max_retries,
        )

    def record_recovery(self) -> None:
        """Kurtarma kaydeder."""
        self._recovery_count += 1
        self._consecutive_errors = 0
        logger.info("Akim kurtarildi")

    def get_partial_content(self) -> str:
        """Kismi icerigi dondurur.

        Returns:
            Kismi icerik.
        """
        return self._partial_content

    def save_partial_content(self, content: str) -> None:
        """Kismi icerigi kaydeder.

        Args:
            content: Icerik.
        """
        self._partial_content = content

    def clear_partial_content(self) -> None:
        """Kismi icerigi temizler."""
        self._partial_content = ""

    def on_error(self, callback: Callable[[StreamError], None]) -> None:
        """Hata geri cagirim ekler.

        Args:
            callback: Geri cagirim fonksiyonu.
        """
        self._callbacks.append(callback)

    def get_last_error(self) -> StreamError | None:
        """Son hatayi dondurur.

        Returns:
            Son hata veya None.
        """
        return self._errors[-1] if self._errors else None

    def get_errors_by_type(
        self, error_type: StreamErrorType
    ) -> list[StreamError]:
        """Tipe gore hatalari filtreler.

        Args:
            error_type: Hata tipi.

        Returns:
            Filtrelenmis hata listesi.
        """
        return [e for e in self._errors if e.error_type == error_type]

    def reset(self) -> None:
        """Hata sayaclarini sifirlar."""
        self._retry_count = 0
        self._consecutive_errors = 0
        self._partial_content = ""

    def get_error_rate(self) -> float:
        """Hata oranini hesaplar.

        Returns:
            Hata orani (0.0-1.0).
        """
        if not self._errors:
            return 0.0
        retryable = sum(1 for e in self._errors if e.retryable)
        return retryable / len(self._errors)

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        error_types: dict[str, int] = {}
        for e in self._errors:
            t = e.error_type.value
            error_types[t] = error_types.get(t, 0) + 1

        return {
            "total_errors": len(self._errors),
            "retry_count": self._retry_count,
            "recovery_count": self._recovery_count,
            "consecutive_errors": self._consecutive_errors,
            "max_retries": self._max_retries,
            "error_types": error_types,
            "has_partial_content": bool(self._partial_content),
            "callbacks_registered": len(self._callbacks),
        }
