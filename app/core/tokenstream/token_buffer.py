"""Token buffer yonetimi.

Token birikimi, flush kontrolu, kelime/cumle
siniri ve goruntuleme optimizasyonu saglar.
"""

import logging
import time
from typing import Any

from app.models.streaming_models import (
    BufferState,
    FlushReason,
)

logger = logging.getLogger(__name__)

# Cumle sonu isaretleri
_SENTENCE_ENDINGS = {".","!","?","。","！","？","…"}

# Kelime ayiricilar
_WORD_SEPARATORS = {" ", "\t", "\n", "\r"}


class TokenBuffer:
    """Token buffer yonetimi.

    Token biriktirme, kelime/cumle sinirinda
    flush ve goruntuleme optimizasyonu saglar.

    Attributes:
        _buffer: Mevcut buffer icerigi.
        _max_size: Maksimum buffer boyutu.
        _flush_interval_ms: Flush araligi (ms).
        _last_flush_time: Son flush zamani.
        _flush_count: Toplam flush sayisi.
        _total_tokens: Toplam token sayisi.
        _total_bytes: Toplam bayt.
        _pending: Bekleyen token listesi.
    """

    def __init__(
        self,
        max_size: int = 64,
        flush_interval_ms: int = 50,
    ) -> None:
        """TokenBuffer baslatir.

        Args:
            max_size: Maksimum buffer boyutu (karakter).
            flush_interval_ms: Otomatik flush araligi (ms).
        """
        self._buffer: str = ""
        self._max_size = max_size
        self._flush_interval_ms = flush_interval_ms
        self._last_flush_time: float = time.time()
        self._flush_count: int = 0
        self._total_tokens: int = 0
        self._total_bytes: int = 0
        self._pending: list[str] = []
        self._last_flush_reason: str = ""

        logger.info(
            "TokenBuffer baslatildi: max_size=%d, interval=%dms",
            max_size, flush_interval_ms,
        )

    def add(self, token: str) -> str | None:
        """Token ekler, gerekirse flush yapar.

        Args:
            token: Eklenecek token.

        Returns:
            Flush edilen icerik veya None.
        """
        if not token:
            return None

        self._buffer += token
        self._total_tokens += 1
        self._total_bytes += len(token.encode("utf-8"))
        self._pending.append(token)

        # Buffer dolu mu?
        if len(self._buffer) >= self._max_size:
            return self._flush(FlushReason.BUFFER_FULL)

        # Cumle siniri?
        if self._is_sentence_boundary(token):
            return self._flush(FlushReason.SENTENCE_BOUNDARY)

        # Zaman asimi?
        elapsed = (time.time() - self._last_flush_time) * 1000
        if elapsed >= self._flush_interval_ms and len(self._buffer) > 0:
            return self._flush(FlushReason.INTERVAL)

        return None

    def add_batch(self, tokens: list[str]) -> list[str]:
        """Toplu token ekler.

        Args:
            tokens: Token listesi.

        Returns:
            Flush edilen icerikler.
        """
        results: list[str] = []
        for token in tokens:
            flushed = self.add(token)
            if flushed is not None:
                results.append(flushed)
        return results

    def flush(self) -> str:
        """Buffer'i zorla bosaltir.

        Returns:
            Buffer icerigi.
        """
        return self._flush(FlushReason.FORCED)

    def flush_complete(self) -> str:
        """Tamamlama flush'i yapar.

        Returns:
            Kalan icerik.
        """
        return self._flush(FlushReason.COMPLETION)

    def _flush(self, reason: FlushReason) -> str:
        """Dahili flush islemi.

        Args:
            reason: Flush nedeni.

        Returns:
            Flush edilen icerik.
        """
        content = self._buffer
        self._buffer = ""
        self._pending.clear()
        self._flush_count += 1
        self._last_flush_time = time.time()
        self._last_flush_reason = reason.value

        if content:
            logger.debug(
                "Buffer flush: reason=%s, len=%d",
                reason.value, len(content),
            )

        return content

    def _is_sentence_boundary(self, token: str) -> bool:
        """Cumle siniri kontrolu.

        Args:
            token: Kontrol edilecek token.

        Returns:
            Cumle siniri ise True.
        """
        stripped = token.rstrip()
        if not stripped:
            return False
        return stripped[-1] in _SENTENCE_ENDINGS

    def _is_word_boundary(self, token: str) -> bool:
        """Kelime siniri kontrolu.

        Args:
            token: Kontrol edilecek token.

        Returns:
            Kelime siniri ise True.
        """
        if not token:
            return False
        return token[-1] in _WORD_SEPARATORS or token[0] in _WORD_SEPARATORS

    def flush_at_word_boundary(self) -> str | None:
        """Kelime sinirinda flush yapar.

        Returns:
            Flush edilen icerik veya None.
        """
        if not self._buffer:
            return None

        # Son boslugu bul
        last_space = -1
        for i in range(len(self._buffer) - 1, -1, -1):
            if self._buffer[i] in _WORD_SEPARATORS:
                last_space = i
                break

        if last_space < 0:
            return None

        content = self._buffer[:last_space + 1]
        self._buffer = self._buffer[last_space + 1:]
        self._flush_count += 1
        self._last_flush_time = time.time()
        self._last_flush_reason = FlushReason.WORD_BOUNDARY.value
        self._pending.clear()

        return content

    def flush_at_sentence_boundary(self) -> str | None:
        """Cumle sinirinda flush yapar.

        Returns:
            Flush edilen icerik veya None.
        """
        if not self._buffer:
            return None

        # Son cumle sonu isaretini bul
        last_end = -1
        for i in range(len(self._buffer) - 1, -1, -1):
            if self._buffer[i] in _SENTENCE_ENDINGS:
                last_end = i
                break

        if last_end < 0:
            return None

        content = self._buffer[:last_end + 1]
        self._buffer = self._buffer[last_end + 1:]
        self._flush_count += 1
        self._last_flush_time = time.time()
        self._last_flush_reason = FlushReason.SENTENCE_BOUNDARY.value
        self._pending.clear()

        return content

    def peek(self) -> str:
        """Buffer icerigine bakar (bosaltmaz).

        Returns:
            Mevcut buffer icerigi.
        """
        return self._buffer

    def clear(self) -> None:
        """Buffer'i temizler."""
        self._buffer = ""
        self._pending.clear()

    @property
    def size(self) -> int:
        """Mevcut buffer boyutu."""
        return len(self._buffer)

    @property
    def is_empty(self) -> bool:
        """Buffer bos mu?"""
        return len(self._buffer) == 0

    @property
    def is_full(self) -> bool:
        """Buffer dolu mu?"""
        return len(self._buffer) >= self._max_size

    def should_flush(self) -> bool:
        """Flush gerekli mi?

        Returns:
            Flush gerekli ise True.
        """
        if not self._buffer:
            return False

        if len(self._buffer) >= self._max_size:
            return True

        elapsed = (time.time() - self._last_flush_time) * 1000
        if elapsed >= self._flush_interval_ms:
            return True

        return False

    def get_state(self) -> BufferState:
        """Buffer durumunu dondurur.

        Returns:
            Buffer durumu.
        """
        return BufferState(
            content=self._buffer,
            token_count=self._total_tokens,
            byte_size=self._total_bytes,
            flush_count=self._flush_count,
            last_flush_reason=self._last_flush_reason,
            pending_tokens=len(self._pending),
        )

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "buffer_size": len(self._buffer),
            "max_size": self._max_size,
            "flush_interval_ms": self._flush_interval_ms,
            "total_tokens": self._total_tokens,
            "total_bytes": self._total_bytes,
            "flush_count": self._flush_count,
            "last_flush_reason": self._last_flush_reason,
            "pending_tokens": len(self._pending),
        }
