"""ATLAS Olay Yonlendirici modulu.

Olay tipi yonlendirme, coklu abone, olay filtreleme,
olay donusturme ve tekrar oynatma.
"""

import logging
from typing import Any, Callable

from app.models.bridge import BridgeEvent, EventType

logger = logging.getLogger(__name__)


class EventRouter:
    """Olay yonlendirici.

    Olaylari tipine gore yonlendirir, filtreler,
    donusturur ve tekrar oynatir.

    Attributes:
        _handlers: Olay tipi -> isleyici listesi.
        _filters: Olay filtreleri.
        _transformers: Olay donusturuculeri.
        _event_log: Olay gecmisi.
    """

    def __init__(self, retention: int = 1000) -> None:
        """Olay yonlendiriciyi baslatir.

        Args:
            retention: Gecmis tutma limiti.
        """
        self._handlers: dict[str, list[Callable]] = {}
        self._filters: dict[str, Callable] = {}
        self._transformers: dict[str, Callable] = {}
        self._event_log: list[BridgeEvent] = []
        self._retention = retention

        logger.info("EventRouter baslatildi (retention=%d)", retention)

    def register_handler(
        self,
        event_type: str,
        handler: Callable,
    ) -> None:
        """Olay isleyici kaydeder.

        Args:
            event_type: Olay tipi.
            handler: Isleyici.
        """
        self._handlers.setdefault(event_type, []).append(handler)

    def unregister_handler(
        self,
        event_type: str,
        handler: Callable,
    ) -> bool:
        """Isleyici kaydini siler.

        Args:
            event_type: Olay tipi.
            handler: Isleyici.

        Returns:
            Basarili ise True.
        """
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def add_filter(
        self,
        name: str,
        filter_fn: Callable,
    ) -> None:
        """Olay filtresi ekler.

        Args:
            name: Filtre adi.
            filter_fn: Filtre fonksiyonu (event -> bool).
        """
        self._filters[name] = filter_fn

    def remove_filter(self, name: str) -> bool:
        """Filtreyi kaldirir.

        Args:
            name: Filtre adi.

        Returns:
            Basarili ise True.
        """
        return self._filters.pop(name, None) is not None

    def add_transformer(
        self,
        event_type: str,
        transformer: Callable,
    ) -> None:
        """Olay donusturucu ekler.

        Args:
            event_type: Olay tipi.
            transformer: Donusturucu (event -> event).
        """
        self._transformers[event_type] = transformer

    def emit(
        self,
        event_type: str,
        source: str,
        data: dict[str, Any] | None = None,
    ) -> BridgeEvent:
        """Olay yayar.

        Args:
            event_type: Olay tipi.
            source: Kaynak.
            data: Veri.

        Returns:
            BridgeEvent nesnesi.
        """
        try:
            etype = EventType(event_type)
        except ValueError:
            etype = EventType.SYSTEM

        event = BridgeEvent(
            event_type=etype,
            source=source,
            data=data or {},
        )

        # Filtreleri uygula
        for filter_fn in self._filters.values():
            if not filter_fn(event):
                self._log_event(event)
                return event

        # Donusturu uygula
        transformer = self._transformers.get(event_type)
        if transformer:
            try:
                event = transformer(event)
            except Exception as e:
                logger.error("Olay donusturme hatasi: %s", e)

        # Isleyicilere yonlendir
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Olay isleme hatasi: %s", e)

        # Gecmise kaydet
        self._log_event(event)

        return event

    def replay(
        self,
        event_type: str = "",
        source: str = "",
        limit: int = 0,
    ) -> list[BridgeEvent]:
        """Olaylari tekrar oynatir.

        Args:
            event_type: Tip filtresi.
            source: Kaynak filtresi.
            limit: Maks olay.

        Returns:
            Tekrar oynanan olaylar.
        """
        events = list(self._event_log)
        if event_type:
            events = [
                e for e in events
                if e.event_type.value == event_type
            ]
        if source:
            events = [e for e in events if e.source == source]
        if limit > 0:
            events = events[-limit:]

        # Isleyicilere tekrar gonder
        for event in events:
            handlers = self._handlers.get(event.event_type.value, [])
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error("Tekrar oynatma hatasi: %s", e)

        return events

    def get_events(
        self,
        event_type: str = "",
        source: str = "",
        limit: int = 0,
    ) -> list[BridgeEvent]:
        """Olaylari getirir.

        Args:
            event_type: Tip filtresi.
            source: Kaynak filtresi.
            limit: Maks olay.

        Returns:
            Olay listesi.
        """
        events = list(self._event_log)
        if event_type:
            events = [
                e for e in events
                if e.event_type.value == event_type
            ]
        if source:
            events = [e for e in events if e.source == source]
        if limit > 0:
            events = events[-limit:]
        return events

    def _log_event(self, event: BridgeEvent) -> None:
        """Olayi gecmise kaydeder."""
        self._event_log.append(event)
        if len(self._event_log) > self._retention:
            self._event_log = self._event_log[-self._retention:]

    @property
    def total_events(self) -> int:
        """Toplam olay sayisi."""
        return len(self._event_log)

    @property
    def handler_count(self) -> int:
        """Toplam isleyici sayisi."""
        return sum(len(h) for h in self._handlers.values())

    @property
    def filter_count(self) -> int:
        """Filtre sayisi."""
        return len(self._filters)
