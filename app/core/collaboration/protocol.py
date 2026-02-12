"""ATLAS Agent mesajlasma protokolu.

Agentlar arasi asenkron mesaj gecisi, publish/subscribe
ve istek-yanit kaliplari.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from app.models.collaboration import (
    AgentMessage,
    MessagePriority,
    MessageType,
    Subscription,
)

logger = logging.getLogger(__name__)

# Oncelik sirasi (dusuk sayi = yuksek oncelik)
_PRIORITY_ORDER: dict[MessagePriority, int] = {
    MessagePriority.URGENT: 0,
    MessagePriority.HIGH: 1,
    MessagePriority.NORMAL: 2,
    MessagePriority.LOW: 3,
}

# Mesaj isleyici tipi
MessageHandler = Callable[[AgentMessage], Coroutine[Any, Any, None]]


class MessageBus:
    """Merkezi mesaj otobüsü.

    Agentlar arasi asenkron mesaj gecisi, publish/subscribe
    ve istek-yanit deseni saglar.

    Attributes:
        _inboxes: Agent posta kutulari (agent_adi -> PriorityQueue).
        _subscriptions: Konu abonelikleri (konu -> [agent_adi]).
        _handlers: Mesaj isleyicileri (agent_adi -> handler).
        _message_log: Mesaj gecmisi.
    """

    def __init__(self, max_queue_size: int = 1000) -> None:
        self._inboxes: dict[str, asyncio.PriorityQueue[tuple[int, str, AgentMessage]]] = {}
        self._subscriptions: dict[str, list[str]] = defaultdict(list)
        self._handlers: dict[str, MessageHandler] = {}
        self._message_log: list[AgentMessage] = []
        self._max_queue_size = max_queue_size
        self._pending_responses: dict[str, asyncio.Future[AgentMessage]] = {}

    def register_agent(self, agent_name: str) -> None:
        """Agent'i mesaj otobusune kayit eder.

        Args:
            agent_name: Kaydedilecek agent adi.
        """
        if agent_name not in self._inboxes:
            self._inboxes[agent_name] = asyncio.PriorityQueue(
                maxsize=self._max_queue_size,
            )
            logger.debug("Agent mesaj otobusune kaydedildi: %s", agent_name)

    def unregister_agent(self, agent_name: str) -> None:
        """Agent'i mesaj otobusundan cikarir.

        Args:
            agent_name: Cikarilacak agent adi.
        """
        self._inboxes.pop(agent_name, None)
        self._handlers.pop(agent_name, None)
        # Aboneliklerden cikar
        for topic_subs in self._subscriptions.values():
            if agent_name in topic_subs:
                topic_subs.remove(agent_name)

    def set_handler(self, agent_name: str, handler: MessageHandler) -> None:
        """Agent mesaj isleyicisi ayarlar.

        Args:
            agent_name: Agent adi.
            handler: Asenkron mesaj isleyici fonksiyonu.
        """
        self._handlers[agent_name] = handler

    async def send(self, message: AgentMessage) -> bool:
        """Mesaj gonderir.

        Args:
            message: Gonderilecek mesaj.

        Returns:
            Mesaj basariyla kuyruga eklendi mi.
        """
        self._message_log.append(message)

        if message.receiver is None:
            # Broadcast: tum kayitli agentlara gonder
            return await self._broadcast(message)

        inbox = self._inboxes.get(message.receiver)
        if inbox is None:
            logger.warning("Alici bulunamadi: %s", message.receiver)
            return False

        priority = _PRIORITY_ORDER.get(message.priority, 2)
        try:
            inbox.put_nowait((priority, message.id, message))
        except asyncio.QueueFull:
            logger.warning("Kuyruk dolu: %s", message.receiver)
            return False

        # Yanit bekleniyor mu kontrol et
        if message.correlation_id and message.correlation_id in self._pending_responses:
            future = self._pending_responses.pop(message.correlation_id)
            if not future.done():
                future.set_result(message)

        logger.debug(
            "Mesaj gonderildi: %s -> %s (tip=%s)",
            message.sender,
            message.receiver,
            message.message_type.value,
        )
        return True

    async def _broadcast(self, message: AgentMessage) -> bool:
        """Mesaji tum agentlara gonderir.

        Args:
            message: Broadcast mesaji.

        Returns:
            En az bir agent'a ulasti mi.
        """
        sent = False
        for agent_name, inbox in self._inboxes.items():
            if agent_name == message.sender:
                continue
            priority = _PRIORITY_ORDER.get(message.priority, 2)
            try:
                inbox.put_nowait((priority, message.id, message))
                sent = True
            except asyncio.QueueFull:
                logger.warning("Broadcast: kuyruk dolu (%s)", agent_name)
        return sent

    async def receive(self, agent_name: str, timeout: float | None = None) -> AgentMessage | None:
        """Mesaj alir (bloklayici).

        Args:
            agent_name: Alici agent adi.
            timeout: Bekleme suresi (saniye, None = sinirsiz).

        Returns:
            Alinan mesaj veya None (timeout).
        """
        inbox = self._inboxes.get(agent_name)
        if inbox is None:
            return None

        try:
            if timeout is not None:
                _, _, message = await asyncio.wait_for(
                    inbox.get(), timeout=timeout,
                )
            else:
                _, _, message = await inbox.get()

            # TTL kontrolu
            if message.ttl > 0:
                elapsed = (datetime.now(timezone.utc) - message.timestamp).total_seconds()
                if elapsed > message.ttl:
                    logger.debug("Mesaj suresi dolmus: %s", message.id)
                    return None

            return message
        except asyncio.TimeoutError:
            return None

    async def receive_nowait(self, agent_name: str) -> AgentMessage | None:
        """Mesaj alir (bloklayici degil).

        Args:
            agent_name: Alici agent adi.

        Returns:
            Alinan mesaj veya None.
        """
        inbox = self._inboxes.get(agent_name)
        if inbox is None or inbox.empty():
            return None

        try:
            _, _, message = inbox.get_nowait()
            return message
        except asyncio.QueueEmpty:
            return None

    async def request(
        self,
        sender: str,
        receiver: str,
        content: dict[str, Any],
        timeout: float = 30.0,
    ) -> AgentMessage | None:
        """Istek-yanit kalibinda mesaj gonderir.

        Args:
            sender: Gonderen agent adi.
            receiver: Alici agent adi.
            content: Mesaj icerigi.
            timeout: Yanit bekleme suresi (saniye).

        Returns:
            Yanit mesaji veya None (timeout).
        """
        msg = AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.REQUEST,
            content=content,
        )

        # Yanit icin future olustur
        loop = asyncio.get_event_loop()
        future: asyncio.Future[AgentMessage] = loop.create_future()
        self._pending_responses[msg.id] = future

        await self.send(msg)

        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            self._pending_responses.pop(msg.id, None)
            return None

    def subscribe(self, agent_name: str, topic: str) -> Subscription:
        """Konuya abone olur.

        Args:
            agent_name: Abone olacak agent adi.
            topic: Abone olunacak konu.

        Returns:
            Abonelik kaydi.
        """
        subs = self._subscriptions[topic]
        if agent_name not in subs:
            subs.append(agent_name)

        logger.debug("Abonelik: %s -> %s", agent_name, topic)
        return Subscription(agent_name=agent_name, topic=topic)

    def unsubscribe(self, agent_name: str, topic: str) -> bool:
        """Aboneligi iptal eder.

        Args:
            agent_name: Agent adi.
            topic: Konu.

        Returns:
            Iptal basarili mi.
        """
        subs = self._subscriptions.get(topic, [])
        if agent_name in subs:
            subs.remove(agent_name)
            return True
        return False

    async def publish(self, sender: str, topic: str, content: dict[str, Any]) -> int:
        """Konuya mesaj yayinlar.

        Args:
            sender: Gonderen agent adi.
            topic: Konu.
            content: Mesaj icerigi.

        Returns:
            Mesaj ulasan abone sayisi.
        """
        subscribers = self._subscriptions.get(topic, [])
        count = 0
        for agent_name in subscribers:
            if agent_name == sender:
                continue
            msg = AgentMessage(
                sender=sender,
                receiver=agent_name,
                message_type=MessageType.INFORM,
                topic=topic,
                content=content,
            )
            if await self.send(msg):
                count += 1

        logger.debug("Publish: %s -> %s (%d abone)", sender, topic, count)
        return count

    def get_queue_size(self, agent_name: str) -> int:
        """Agent kuyruk boyutunu dondurur.

        Args:
            agent_name: Agent adi.

        Returns:
            Kuyruk boyutu.
        """
        inbox = self._inboxes.get(agent_name)
        if inbox is None:
            return 0
        return inbox.qsize()

    def get_message_log(self, limit: int = 100) -> list[AgentMessage]:
        """Mesaj gecmisini dondurur.

        Args:
            limit: Maksimum kayit sayisi.

        Returns:
            Mesaj listesi.
        """
        return list(self._message_log[-limit:])

    def get_subscribers(self, topic: str) -> list[str]:
        """Konu abonelerini dondurur.

        Args:
            topic: Konu.

        Returns:
            Abone agent adi listesi.
        """
        return list(self._subscriptions.get(topic, []))
