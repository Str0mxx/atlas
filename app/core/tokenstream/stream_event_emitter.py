"""Akim olay yayicisi.

Olay yayini, abone yonetimi, geri basinc,
hata olaylari ve tamamlama olaylari saglar.
"""

import logging
import time
from typing import Any, Callable

from app.models.streaming_models import (
    StreamEvent,
    StreamEventType,
)

logger = logging.getLogger(__name__)

# Abone tipi
SubscriberFn = Callable[[StreamEvent], None]


class StreamEventEmitter:
    """Akim olay yayicisi.

    Pub/sub olay yayini, geri basinc kontrolu
    ve hata yonetimi saglar.

    Attributes:
        _subscribers: Olay tipi bazli abone listesi.
        _global_subscribers: Tum olaylar icin aboneler.
        _event_count: Toplam olay sayisi.
        _error_count: Hata sayisi.
        _backpressure_threshold: Geri basinc esigi.
        _queue: Olay kuyrugu.
        _paused: Duraklatildi mi.
        _sequence: Sira numarasi.
    """

    def __init__(
        self,
        backpressure_threshold: int = 100,
    ) -> None:
        """StreamEventEmitter baslatir.

        Args:
            backpressure_threshold: Geri basinc esigi.
        """
        self._subscribers: dict[StreamEventType, list[SubscriberFn]] = {}
        self._global_subscribers: list[SubscriberFn] = []
        self._event_count: int = 0
        self._error_count: int = 0
        self._backpressure_threshold = backpressure_threshold
        self._queue: list[StreamEvent] = []
        self._paused: bool = False
        self._sequence: int = 0
        self._stream_id: str = ""

        logger.info(
            "StreamEventEmitter baslatildi: backpressure=%d",
            backpressure_threshold,
        )

    def set_stream_id(self, stream_id: str) -> None:
        """Akim ID'sini ayarlar.

        Args:
            stream_id: Akim ID'si.
        """
        self._stream_id = stream_id

    def subscribe(
        self,
        event_type: StreamEventType,
        callback: SubscriberFn,
    ) -> str:
        """Belirli olay tipine abone olur.

        Args:
            event_type: Olay tipi.
            callback: Geri cagirim fonksiyonu.

        Returns:
            Abonelik ID'si.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(callback)
        sub_id = f"sub_{event_type.value}_{len(self._subscribers[event_type])}"

        logger.debug("Abone eklendi: %s -> %s", event_type.value, sub_id)
        return sub_id

    def subscribe_all(self, callback: SubscriberFn) -> str:
        """Tum olaylara abone olur.

        Args:
            callback: Geri cagirim fonksiyonu.

        Returns:
            Abonelik ID'si.
        """
        self._global_subscribers.append(callback)
        sub_id = f"sub_all_{len(self._global_subscribers)}"
        logger.debug("Global abone eklendi: %s", sub_id)
        return sub_id

    def unsubscribe(
        self,
        event_type: StreamEventType,
        callback: SubscriberFn,
    ) -> bool:
        """Aboneligi iptal eder.

        Args:
            event_type: Olay tipi.
            callback: Geri cagirim fonksiyonu.

        Returns:
            Basarili ise True.
        """
        subs = self._subscribers.get(event_type, [])
        if callback in subs:
            subs.remove(callback)
            return True
        return False

    def unsubscribe_all(self, callback: SubscriberFn) -> bool:
        """Global aboneligi iptal eder.

        Args:
            callback: Geri cagirim fonksiyonu.

        Returns:
            Basarili ise True.
        """
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)
            return True
        return False

    def emit(
        self,
        event_type: StreamEventType,
        data: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> StreamEvent:
        """Olay yayinlar.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.
            metadata: Ek bilgiler.

        Returns:
            Yayinlanan olay.
        """
        self._sequence += 1

        event = StreamEvent(
            event_type=event_type,
            data=data,
            metadata=metadata or {},
            stream_id=self._stream_id,
            sequence=self._sequence,
        )

        # Geri basinc kontrolu
        if self._paused:
            self._queue.append(event)
            if len(self._queue) > self._backpressure_threshold:
                logger.warning(
                    "Geri basinc esigi asildi: kuyruk=%d",
                    len(self._queue),
                )
            return event

        self._deliver(event)
        return event

    def emit_token(self, token: str) -> StreamEvent:
        """Token olayi yayinlar.

        Args:
            token: Token icerigi.

        Returns:
            Yayinlanan olay.
        """
        return self.emit(StreamEventType.TOKEN, data=token)

    def emit_start(self, metadata: dict[str, Any] | None = None) -> StreamEvent:
        """Baslangic olayi yayinlar.

        Args:
            metadata: Ek bilgiler.

        Returns:
            Yayinlanan olay.
        """
        return self.emit(StreamEventType.START, metadata=metadata)

    def emit_end(self, metadata: dict[str, Any] | None = None) -> StreamEvent:
        """Bitis olayi yayinlar.

        Args:
            metadata: Ek bilgiler.

        Returns:
            Yayinlanan olay.
        """
        return self.emit(StreamEventType.END, metadata=metadata)

    def emit_error(
        self, error_msg: str, metadata: dict[str, Any] | None = None
    ) -> StreamEvent:
        """Hata olayi yayinlar.

        Args:
            error_msg: Hata mesaji.
            metadata: Ek bilgiler.

        Returns:
            Yayinlanan olay.
        """
        self._error_count += 1
        return self.emit(StreamEventType.ERROR, data=error_msg, metadata=metadata)

    def emit_flush(self, content: str) -> StreamEvent:
        """Flush olayi yayinlar.

        Args:
            content: Flush edilen icerik.

        Returns:
            Yayinlanan olay.
        """
        return self.emit(StreamEventType.FLUSH, data=content)

    def _deliver(self, event: StreamEvent) -> None:
        """Olayi abonelere iletir.

        Args:
            event: Iletilecek olay.
        """
        self._event_count += 1

        # Tip bazli aboneler
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    "Abone hatasi (%s): %s",
                    event.event_type.value, e,
                )
                self._error_count += 1

        # Global aboneler
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error("Global abone hatasi: %s", e)
                self._error_count += 1

    def pause(self) -> None:
        """Olay yayinini duraklatir."""
        self._paused = True
        self.emit(StreamEventType.PAUSE)
        logger.info("Olay yayini duraklatildi")

    def resume(self) -> int:
        """Olay yayinini devam ettirir.

        Returns:
            Islenen kuyruk olay sayisi.
        """
        self._paused = False
        processed = 0

        while self._queue:
            event = self._queue.pop(0)
            self._deliver(event)
            processed += 1

        self.emit(StreamEventType.RESUME)
        logger.info("Olay yayini devam etti: %d olay islendi", processed)
        return processed

    def clear_queue(self) -> int:
        """Olay kuyruğunu temizler.

        Returns:
            Temizlenen olay sayisi.
        """
        count = len(self._queue)
        self._queue.clear()
        return count

    @property
    def subscriber_count(self) -> int:
        """Toplam abone sayisi."""
        total = len(self._global_subscribers)
        for subs in self._subscribers.values():
            total += len(subs)
        return total

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def is_paused(self) -> bool:
        """Duraklatilmis mi?"""
        return self._paused

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "stream_id": self._stream_id,
            "event_count": self._event_count,
            "error_count": self._error_count,
            "subscriber_count": self.subscriber_count,
            "queue_size": len(self._queue),
            "is_paused": self._paused,
            "sequence": self._sequence,
            "backpressure_threshold": self._backpressure_threshold,
        }
