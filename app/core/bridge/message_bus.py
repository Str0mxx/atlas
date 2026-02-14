"""ATLAS Mesaj Yolu modulu.

Pub/sub mesajlasma, istek/yanit, yayin,
oncelikli kuyruk ve olum mektubu isleme.
"""

import logging
from typing import Any, Callable

from app.models.bridge import BusMessage, MessagePriority, MessageState

logger = logging.getLogger(__name__)


class MessageBus:
    """Mesaj yolu.

    Sistemler arasi mesajlasmayi yonetir,
    pub/sub ve istek/yanit kaliplarini destekler.

    Attributes:
        _subscribers: Konu -> abone listesi.
        _messages: Tum mesajlar.
        _dead_letters: Olum mektuplari.
        _max_queue_size: Maks kuyruk boyutu.
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        """Mesaj yolunu baslatir.

        Args:
            max_queue_size: Maks kuyruk boyutu.
        """
        self._subscribers: dict[str, list[Callable]] = {}
        self._messages: list[BusMessage] = []
        self._dead_letters: list[BusMessage] = []
        self._responses: dict[str, Any] = {}
        self._max_queue_size = max_queue_size

        logger.info("MessageBus baslatildi (queue=%d)", max_queue_size)

    def subscribe(
        self,
        topic: str,
        handler: Callable,
    ) -> None:
        """Konuya abone olur.

        Args:
            topic: Konu.
            handler: Isleyici fonksiyon.
        """
        self._subscribers.setdefault(topic, []).append(handler)

    def unsubscribe(
        self,
        topic: str,
        handler: Callable,
    ) -> bool:
        """Aboneligi iptal eder.

        Args:
            topic: Konu.
            handler: Isleyici.

        Returns:
            Basarili ise True.
        """
        handlers = self._subscribers.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)
            return True
        return False

    def publish(
        self,
        topic: str,
        payload: dict[str, Any],
        source: str = "",
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> BusMessage:
        """Mesaj yayinlar.

        Args:
            topic: Konu.
            payload: Icerik.
            source: Kaynak sistem.
            priority: Oncelik.

        Returns:
            BusMessage nesnesi.
        """
        message = BusMessage(
            topic=topic,
            source=source,
            payload=payload,
            priority=priority,
        )
        self._messages.append(message)

        # Abonelere ilet
        handlers = self._subscribers.get(topic, [])
        delivered = False
        for handler in handlers:
            try:
                handler(message)
                delivered = True
            except Exception as e:
                logger.error("Mesaj isleme hatasi: %s", e)

        if delivered:
            message.state = MessageState.DELIVERED
        elif not handlers:
            message.state = MessageState.DELIVERED  # Abone yok, sorun degil
        else:
            message.state = MessageState.FAILED
            self._dead_letters.append(message)

        return message

    def send(
        self,
        target: str,
        payload: dict[str, Any],
        source: str = "",
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> BusMessage:
        """Hedefli mesaj gonderir.

        Args:
            target: Hedef sistem.
            payload: Icerik.
            source: Kaynak.
            priority: Oncelik.

        Returns:
            BusMessage nesnesi.
        """
        message = BusMessage(
            topic=f"direct:{target}",
            source=source,
            target=target,
            payload=payload,
            priority=priority,
        )
        self._messages.append(message)

        handlers = self._subscribers.get(f"direct:{target}", [])
        if handlers:
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:
                    logger.error("Direkt mesaj hatasi: %s", e)
            message.state = MessageState.DELIVERED
        else:
            message.state = MessageState.FAILED
            self._dead_letters.append(message)

        return message

    def broadcast(
        self,
        payload: dict[str, Any],
        source: str = "",
    ) -> list[BusMessage]:
        """Tum konulara yayin yapar.

        Args:
            payload: Icerik.
            source: Kaynak.

        Returns:
            Mesaj listesi.
        """
        messages = []
        for topic in list(self._subscribers.keys()):
            msg = self.publish(topic, payload, source, MessagePriority.HIGH)
            messages.append(msg)
        return messages

    def request(
        self,
        target: str,
        payload: dict[str, Any],
        source: str = "",
    ) -> str:
        """Istek gonderir (yanit bekler).

        Args:
            target: Hedef.
            payload: Icerik.
            source: Kaynak.

        Returns:
            Mesaj ID (yanit anahtari).
        """
        message = self.send(target, payload, source, MessagePriority.HIGH)
        return message.message_id

    def respond(
        self,
        message_id: str,
        response: Any,
    ) -> None:
        """Istege yanit verir.

        Args:
            message_id: Istek mesaj ID.
            response: Yanit.
        """
        self._responses[message_id] = response

    def get_response(self, message_id: str) -> Any:
        """Yaniti getirir.

        Args:
            message_id: Mesaj ID.

        Returns:
            Yanit veya None.
        """
        return self._responses.get(message_id)

    def get_dead_letters(self) -> list[BusMessage]:
        """Olum mektuplarini getirir.

        Returns:
            Mesaj listesi.
        """
        return list(self._dead_letters)

    def retry_dead_letters(self) -> int:
        """Olum mektuplarini yeniden dener.

        Returns:
            Basarili yeniden deneme sayisi.
        """
        retried = 0
        remaining = []

        for msg in self._dead_letters:
            handlers = self._subscribers.get(msg.topic, [])
            if handlers:
                for handler in handlers:
                    try:
                        handler(msg)
                        msg.state = MessageState.DELIVERED
                        retried += 1
                    except Exception:
                        remaining.append(msg)
            else:
                msg.state = MessageState.DEAD
                remaining.append(msg)

        self._dead_letters = remaining
        return retried

    def get_messages(
        self,
        topic: str = "",
        source: str = "",
        limit: int = 0,
    ) -> list[BusMessage]:
        """Mesajlari getirir.

        Args:
            topic: Konu filtresi.
            source: Kaynak filtresi.
            limit: Maks kayit.

        Returns:
            Mesaj listesi.
        """
        msgs = list(self._messages)
        if topic:
            msgs = [m for m in msgs if m.topic == topic]
        if source:
            msgs = [m for m in msgs if m.source == source]
        if limit > 0:
            msgs = msgs[-limit:]
        return msgs

    @property
    def total_messages(self) -> int:
        """Toplam mesaj sayisi."""
        return len(self._messages)

    @property
    def pending_count(self) -> int:
        """Bekleyen mesaj sayisi."""
        return sum(
            1 for m in self._messages
            if m.state == MessageState.PENDING
        )

    @property
    def dead_letter_count(self) -> int:
        """Olum mektubu sayisi."""
        return len(self._dead_letters)

    @property
    def subscriber_count(self) -> int:
        """Toplam abone sayisi."""
        return sum(len(h) for h in self._subscribers.values())
