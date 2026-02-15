"""ATLAS Span Toplayici modulu.

Span toplama, tamponlama,
toplu disa aktarma, filtreleme
ve zenginlestirme.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class SpanCollector:
    """Span toplayici.

    Span verilerini toplar ve isler.

    Attributes:
        _buffer: Span tamponu.
        _exported: Disa aktarilmis spanlar.
    """

    def __init__(
        self,
        buffer_size: int = 100,
        flush_interval: float = 10.0,
    ) -> None:
        """Span toplayiciyi baslatir.

        Args:
            buffer_size: Tampon boyutu.
            flush_interval: Bosaltma araligi (sn).
        """
        self._buffer: list[dict[str, Any]] = []
        self._exported: list[
            list[dict[str, Any]]
        ] = []
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._filters: list[
            Callable[..., bool]
        ] = []
        self._enrichers: list[
            Callable[..., dict[str, Any]]
        ] = []
        self._last_flush = time.time()
        self._total_collected = 0
        self._total_filtered = 0

        logger.info(
            "SpanCollector baslatildi: "
            "buffer=%d",
            buffer_size,
        )

    def collect(
        self,
        span: dict[str, Any],
    ) -> bool:
        """Span toplar.

        Args:
            span: Span verisi.

        Returns:
            Kabul edildi mi.
        """
        # Filtreleme
        for f in self._filters:
            try:
                if not f(span):
                    self._total_filtered += 1
                    return False
            except Exception:
                pass

        # Zenginlestirme
        enriched = dict(span)
        for e in self._enrichers:
            try:
                extra = e(enriched)
                if extra:
                    enriched.update(extra)
            except Exception:
                pass

        enriched["collected_at"] = time.time()
        self._buffer.append(enriched)
        self._total_collected += 1

        # Tampon dolu mu?
        if len(self._buffer) >= self._buffer_size:
            self.flush()

        return True

    def collect_batch(
        self,
        spans: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplu span toplar.

        Args:
            spans: Span listesi.

        Returns:
            Toplama sonucu.
        """
        accepted = 0
        rejected = 0
        for span in spans:
            if self.collect(span):
                accepted += 1
            else:
                rejected += 1

        return {
            "accepted": accepted,
            "rejected": rejected,
            "total": len(spans),
        }

    def flush(self) -> dict[str, Any]:
        """Tamponu bosaltir.

        Returns:
            Bosaltma sonucu.
        """
        if not self._buffer:
            return {"flushed": 0}

        batch = list(self._buffer)
        self._exported.append(batch)
        count = len(batch)
        self._buffer.clear()
        self._last_flush = time.time()

        return {
            "flushed": count,
            "batch_index": len(self._exported) - 1,
        }

    def add_filter(
        self,
        filter_fn: Callable[..., bool],
    ) -> None:
        """Filtre ekler.

        Args:
            filter_fn: Filtre fonksiyonu.
        """
        self._filters.append(filter_fn)

    def remove_filters(self) -> int:
        """Tum filtreleri kaldirir.

        Returns:
            Kaldirilan sayi.
        """
        count = len(self._filters)
        self._filters.clear()
        return count

    def add_enricher(
        self,
        enricher_fn: Callable[..., dict[str, Any]],
    ) -> None:
        """Zenginlestirici ekler.

        Args:
            enricher_fn: Zenginlestirici fonksiyonu.
        """
        self._enrichers.append(enricher_fn)

    def get_buffer(self) -> list[dict[str, Any]]:
        """Mevcut tamponu getirir.

        Returns:
            Tampondaki spanlar.
        """
        return list(self._buffer)

    def get_exported_batch(
        self,
        index: int,
    ) -> list[dict[str, Any]] | None:
        """Disa aktarilmis batch'i getirir.

        Args:
            index: Batch indeksi.

        Returns:
            Span listesi veya None.
        """
        if 0 <= index < len(self._exported):
            return list(self._exported[index])
        return None

    def should_flush(self) -> bool:
        """Bosaltma gerekli mi.

        Returns:
            Gerekli mi.
        """
        if len(self._buffer) >= self._buffer_size:
            return True
        elapsed = time.time() - self._last_flush
        return elapsed >= self._flush_interval

    @property
    def buffer_count(self) -> int:
        """Tampondaki span sayisi."""
        return len(self._buffer)

    @property
    def export_count(self) -> int:
        """Disa aktarma sayisi."""
        return len(self._exported)

    @property
    def total_collected(self) -> int:
        """Toplam toplanan span."""
        return self._total_collected

    @property
    def total_filtered(self) -> int:
        """Toplam filtrelenen span."""
        return self._total_filtered
