"""ATLAS Toplu Islemci modulu.

Istek toparlama, toplu islemler,
gecikme, kisitlama ve
kuyruk yonetimi.
"""

import logging
import time
from typing import Any, Callable

from app.models.caching import (
    BatchRecord,
    BatchStatus,
)

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Toplu islemci.

    Istekleri toparlar ve toplu
    olarak isler.

    Attributes:
        _queue: Islem kuyrugu.
        _batches: Toplu islem kayitlari.
    """

    def __init__(
        self,
        batch_size: int = 50,
        flush_interval: float = 5.0,
        max_queue: int = 1000,
    ) -> None:
        """Toplu islemciyi baslatir.

        Args:
            batch_size: Toplu boyut.
            flush_interval: Bosaltma araligi.
            max_queue: Maks kuyruk.
        """
        self._queue: list[dict[str, Any]] = []
        self._batches: dict[
            str, BatchRecord
        ] = {}
        self._processors: dict[
            str, Callable[[list[Any]], Any]
        ] = {}
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_queue = max_queue
        self._last_flush = time.time()
        self._total_processed = 0
        self._total_failed = 0
        self._throttle_rate = 0.0
        self._debounce_timers: dict[
            str, float
        ] = {}

        logger.info(
            "BatchProcessor baslatildi",
        )

    def enqueue(
        self,
        item: dict[str, Any],
        processor_name: str = "default",
    ) -> bool:
        """Kuyruga ekler.

        Args:
            item: Islem ogesi.
            processor_name: Islemci adi.

        Returns:
            Basarili ise True.
        """
        if len(self._queue) >= self._max_queue:
            return False

        item["_processor"] = processor_name
        item["_enqueued_at"] = time.time()
        self._queue.append(item)

        # Toplu boyuta ulasildiysa isle
        if len(self._queue) >= self._batch_size:
            self.flush()

        return True

    def register_processor(
        self,
        name: str,
        processor: Callable[[list[Any]], Any],
    ) -> None:
        """Islemci kaydeder.

        Args:
            name: Islemci adi.
            processor: Islem fonksiyonu.
        """
        self._processors[name] = processor

    def flush(self) -> dict[str, Any]:
        """Kuyrugu bosaltir ve isler.

        Returns:
            Islem sonucu.
        """
        if not self._queue:
            return {
                "processed": 0,
                "failed": 0,
            }

        batch = BatchRecord(
            total_items=len(self._queue),
            status=BatchStatus.PROCESSING,
        )
        self._batches[batch.batch_id] = batch

        # Islemciye gore grupla
        groups: dict[
            str, list[dict[str, Any]]
        ] = {}
        for item in self._queue:
            pname = item.pop("_processor", "default")
            item.pop("_enqueued_at", None)
            if pname not in groups:
                groups[pname] = []
            groups[pname].append(item)

        start = time.time()
        processed = 0
        failed = 0

        for pname, items in groups.items():
            processor = self._processors.get(pname)
            if processor:
                try:
                    processor(items)
                    processed += len(items)
                except Exception:
                    failed += len(items)
            else:
                processed += len(items)

        batch.processed_items = processed
        batch.failed_items = failed
        batch.duration = time.time() - start
        batch.status = (
            BatchStatus.COMPLETED
            if failed == 0
            else BatchStatus.FAILED
        )

        self._total_processed += processed
        self._total_failed += failed
        self._queue.clear()
        self._last_flush = time.time()

        return {
            "batch_id": batch.batch_id,
            "processed": processed,
            "failed": failed,
            "duration": batch.duration,
        }

    def debounce(
        self,
        key: str,
        delay: float = 1.0,
    ) -> bool:
        """Gecikme uygular.

        Args:
            key: Islem anahtari.
            delay: Gecikme suresi.

        Returns:
            Islenmeli ise True.
        """
        now = time.time()
        last = self._debounce_timers.get(key, 0)

        if now - last < delay:
            return False

        self._debounce_timers[key] = now
        return True

    def throttle(
        self,
        key: str,
        max_per_second: float = 10.0,
    ) -> bool:
        """Kisitlama uygular.

        Args:
            key: Islem anahtari.
            max_per_second: Saniyede maks.

        Returns:
            Izin verildiyse True.
        """
        now = time.time()
        last = self._debounce_timers.get(key, 0)
        min_interval = 1.0 / max_per_second

        if now - last < min_interval:
            return False

        self._debounce_timers[key] = now
        return True

    def get_queue_size(self) -> int:
        """Kuyruk boyutu.

        Returns:
            Kuyruk boyutu.
        """
        return len(self._queue)

    def get_batch(
        self,
        batch_id: str,
    ) -> BatchRecord | None:
        """Toplu islem getirir.

        Args:
            batch_id: Toplu islem ID.

        Returns:
            Toplu islem veya None.
        """
        return self._batches.get(batch_id)

    def get_stats(self) -> dict[str, Any]:
        """Istatistik getirir.

        Returns:
            Istatistik.
        """
        return {
            "queue_size": len(self._queue),
            "total_batches": len(self._batches),
            "total_processed": (
                self._total_processed
            ),
            "total_failed": self._total_failed,
            "batch_size": self._batch_size,
        }

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def batch_count(self) -> int:
        """Toplu islem sayisi."""
        return len(self._batches)

    @property
    def total_processed(self) -> int:
        """Toplam islenen."""
        return self._total_processed

    @property
    def total_failed(self) -> int:
        """Toplam basarisiz."""
        return self._total_failed
