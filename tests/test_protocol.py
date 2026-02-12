"""MessageBus testleri.

Mesaj gonderme/alma, broadcast, pub/sub,
istek-yanit ve oncelik testleri.
"""

import asyncio

from app.core.collaboration.protocol import MessageBus
from app.models.collaboration import (
    AgentMessage,
    MessagePriority,
    MessageType,
)


# === Yardimci fonksiyonlar ===


def _make_bus() -> MessageBus:
    bus = MessageBus()
    bus.register_agent("agent_a")
    bus.register_agent("agent_b")
    bus.register_agent("agent_c")
    return bus


def _msg(
    sender: str = "agent_a",
    receiver: str = "agent_b",
    content: dict | None = None,
    msg_type: MessageType = MessageType.INFORM,
    priority: MessagePriority = MessagePriority.NORMAL,
) -> AgentMessage:
    return AgentMessage(
        sender=sender,
        receiver=receiver,
        message_type=msg_type,
        priority=priority,
        content=content or {},
    )


# === Init Testleri ===


class TestMessageBusInit:
    def test_default(self) -> None:
        bus = MessageBus()
        assert bus.get_queue_size("nope") == 0

    def test_register(self) -> None:
        bus = MessageBus()
        bus.register_agent("agent_a")
        assert bus.get_queue_size("agent_a") == 0

    def test_unregister(self) -> None:
        bus = MessageBus()
        bus.register_agent("agent_a")
        bus.unregister_agent("agent_a")
        assert bus.get_queue_size("agent_a") == 0


# === send/receive Testleri ===


class TestMessageBusSendReceive:
    async def test_send_and_receive(self) -> None:
        bus = _make_bus()
        msg = _msg()
        result = await bus.send(msg)
        assert result is True
        assert bus.get_queue_size("agent_b") == 1
        received = await bus.receive("agent_b", timeout=1.0)
        assert received is not None
        assert received.id == msg.id
        assert received.sender == "agent_a"

    async def test_send_to_unknown(self) -> None:
        bus = _make_bus()
        msg = _msg(receiver="nonexistent")
        result = await bus.send(msg)
        assert result is False

    async def test_receive_empty(self) -> None:
        bus = _make_bus()
        result = await bus.receive("agent_a", timeout=0.01)
        assert result is None

    async def test_receive_nowait_empty(self) -> None:
        bus = _make_bus()
        result = await bus.receive_nowait("agent_a")
        assert result is None

    async def test_receive_nowait(self) -> None:
        bus = _make_bus()
        await bus.send(_msg())
        result = await bus.receive_nowait("agent_b")
        assert result is not None

    async def test_receive_unregistered(self) -> None:
        bus = _make_bus()
        result = await bus.receive("nope", timeout=0.01)
        assert result is None

    async def test_receive_nowait_unregistered(self) -> None:
        bus = _make_bus()
        result = await bus.receive_nowait("nope")
        assert result is None


# === Priority Testleri ===


class TestMessageBusPriority:
    async def test_urgent_first(self) -> None:
        bus = _make_bus()
        low = _msg(content={"p": "low"}, priority=MessagePriority.LOW)
        urgent = _msg(content={"p": "urgent"}, priority=MessagePriority.URGENT)
        await bus.send(low)
        await bus.send(urgent)
        first = await bus.receive("agent_b", timeout=1.0)
        assert first is not None
        assert first.content["p"] == "urgent"

    async def test_high_before_normal(self) -> None:
        bus = _make_bus()
        normal = _msg(content={"p": "normal"}, priority=MessagePriority.NORMAL)
        high = _msg(content={"p": "high"}, priority=MessagePriority.HIGH)
        await bus.send(normal)
        await bus.send(high)
        first = await bus.receive("agent_b", timeout=1.0)
        assert first is not None
        assert first.content["p"] == "high"


# === Broadcast Testleri ===


class TestMessageBusBroadcast:
    async def test_broadcast(self) -> None:
        bus = _make_bus()
        msg = AgentMessage(
            sender="agent_a",
            receiver=None,
            message_type=MessageType.BROADCAST,
            content={"alert": True},
        )
        result = await bus.send(msg)
        assert result is True
        # agent_b ve agent_c almali, agent_a almamali
        assert bus.get_queue_size("agent_b") == 1
        assert bus.get_queue_size("agent_c") == 1
        assert bus.get_queue_size("agent_a") == 0

    async def test_broadcast_empty(self) -> None:
        bus = MessageBus()
        bus.register_agent("alone")
        msg = AgentMessage(sender="alone", receiver=None)
        result = await bus.send(msg)
        assert result is False  # Kendinden baskasi yok


# === Pub/Sub Testleri ===


class TestMessageBusPubSub:
    async def test_subscribe_and_publish(self) -> None:
        bus = _make_bus()
        bus.subscribe("agent_b", "server_events")
        bus.subscribe("agent_c", "server_events")
        count = await bus.publish("agent_a", "server_events", {"cpu": 90})
        assert count == 2
        msg_b = await bus.receive_nowait("agent_b")
        assert msg_b is not None
        assert msg_b.topic == "server_events"
        assert msg_b.content == {"cpu": 90}

    async def test_publish_no_subscribers(self) -> None:
        bus = _make_bus()
        count = await bus.publish("agent_a", "empty_topic", {})
        assert count == 0

    async def test_unsubscribe(self) -> None:
        bus = _make_bus()
        bus.subscribe("agent_b", "topic")
        assert bus.unsubscribe("agent_b", "topic") is True
        count = await bus.publish("agent_a", "topic", {})
        assert count == 0

    async def test_unsubscribe_not_subscribed(self) -> None:
        bus = _make_bus()
        assert bus.unsubscribe("agent_b", "topic") is False

    def test_get_subscribers(self) -> None:
        bus = _make_bus()
        bus.subscribe("agent_b", "events")
        bus.subscribe("agent_c", "events")
        subs = bus.get_subscribers("events")
        assert "agent_b" in subs
        assert "agent_c" in subs

    async def test_publisher_not_self_receive(self) -> None:
        bus = _make_bus()
        bus.subscribe("agent_a", "topic")
        bus.subscribe("agent_b", "topic")
        count = await bus.publish("agent_a", "topic", {"data": 1})
        assert count == 1  # Sadece agent_b
        assert bus.get_queue_size("agent_a") == 0


# === Request/Response Testleri ===


class TestMessageBusRequestResponse:
    async def test_request_timeout(self) -> None:
        bus = _make_bus()
        result = await bus.request("agent_a", "agent_b", {"q": "status"}, timeout=0.05)
        assert result is None

    async def test_request_with_response(self) -> None:
        bus = _make_bus()

        async def responder() -> None:
            msg = await bus.receive("agent_b", timeout=1.0)
            if msg:
                response = AgentMessage(
                    sender="agent_b",
                    receiver="agent_a",
                    message_type=MessageType.RESPONSE,
                    correlation_id=msg.id,
                    content={"status": "ok"},
                )
                await bus.send(response)

        task = asyncio.create_task(responder())
        result = await bus.request("agent_a", "agent_b", {"q": "status"}, timeout=2.0)
        await task
        assert result is not None
        assert result.content["status"] == "ok"


# === TTL Testleri ===


class TestMessageBusTTL:
    async def test_expired_message(self) -> None:
        bus = _make_bus()
        from datetime import datetime, timedelta, timezone
        msg = AgentMessage(
            sender="agent_a",
            receiver="agent_b",
            content={"old": True},
            ttl=1,
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=5),
        )
        await bus.send(msg)
        received = await bus.receive("agent_b", timeout=0.1)
        assert received is None  # Suresi dolmus


# === Message Log Testleri ===


class TestMessageBusLog:
    async def test_log(self) -> None:
        bus = _make_bus()
        await bus.send(_msg())
        await bus.send(_msg(sender="agent_b", receiver="agent_a"))
        log = bus.get_message_log()
        assert len(log) == 2

    async def test_log_limit(self) -> None:
        bus = _make_bus()
        for _ in range(5):
            await bus.send(_msg())
        log = bus.get_message_log(limit=3)
        assert len(log) == 3
