"""ATLAS MQTT Köprüsü modülü.

MQTT bağlantı, konu yönetimi,
mesaj yayınlama, abonelik,
QoS yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MQTTBridge:
    """MQTT köprüsü.

    MQTT protokolü üzerinden iletişim sağlar.

    Attributes:
        _subscriptions: Abonelik kayıtları.
        _messages: Mesaj kayıtları.
    """

    def __init__(self) -> None:
        """Köprüyü başlatır."""
        self._connected = False
        self._broker = ""
        self._subscriptions: dict[
            str, dict[str, Any]
        ] = {}
        self._messages: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "messages_published": 0,
            "messages_received": 0,
        }

        logger.info(
            "MQTTBridge baslatildi",
        )

    def connect(
        self,
        broker: str = "localhost",
        port: int = 1883,
        client_id: str = "atlas",
    ) -> dict[str, Any]:
        """MQTT bağlantısı kurar.

        Args:
            broker: Broker adresi.
            port: Port.
            client_id: İstemci kimliği.

        Returns:
            Bağlantı bilgisi.
        """
        self._connected = True
        self._broker = broker

        return {
            "broker": broker,
            "port": port,
            "client_id": client_id,
            "connected": True,
        }

    def manage_topic(
        self,
        topic: str,
        action: str = "create",
        retain: bool = False,
    ) -> dict[str, Any]:
        """Konu yönetimi yapar.

        Args:
            topic: Konu adı.
            action: Aksiyon (create/delete).
            retain: Tutma.

        Returns:
            Yönetim bilgisi.
        """
        if action == "create":
            self._subscriptions[topic] = {
                "topic": topic,
                "retain": retain,
                "created_at": time.time(),
            }
        elif action == "delete":
            self._subscriptions.pop(
                topic, None,
            )

        return {
            "topic": topic,
            "action": action,
            "managed": True,
        }

    def publish(
        self,
        topic: str,
        payload: str = "",
        qos: int = 0,
        retain: bool = False,
    ) -> dict[str, Any]:
        """Mesaj yayınlar.

        Args:
            topic: Konu.
            payload: Yük.
            qos: QoS seviyesi.
            retain: Tutma.

        Returns:
            Yayın bilgisi.
        """
        self._counter += 1
        mid = f"msg_{self._counter}"

        self._messages.append({
            "message_id": mid,
            "topic": topic,
            "payload": payload,
            "qos": qos,
            "retain": retain,
            "direction": "outgoing",
            "timestamp": time.time(),
        })

        self._stats[
            "messages_published"
        ] += 1

        return {
            "message_id": mid,
            "topic": topic,
            "qos": qos,
            "published": True,
        }

    def subscribe(
        self,
        topic: str,
        qos: int = 0,
        callback: str = "",
    ) -> dict[str, Any]:
        """Konuya abone olur.

        Args:
            topic: Konu.
            qos: QoS seviyesi.
            callback: Geri çağrı.

        Returns:
            Abonelik bilgisi.
        """
        self._subscriptions[topic] = {
            "topic": topic,
            "qos": qos,
            "callback": callback,
            "subscribed_at": time.time(),
        }

        return {
            "topic": topic,
            "qos": qos,
            "subscribed": True,
        }

    def set_qos(
        self,
        topic: str,
        qos: int = 1,
    ) -> dict[str, Any]:
        """QoS seviyesi belirler.

        Args:
            topic: Konu.
            qos: QoS seviyesi (0-2).

        Returns:
            QoS bilgisi.
        """
        qos = max(0, min(2, qos))

        sub = self._subscriptions.get(
            topic,
        )
        if sub:
            sub["qos"] = qos

        return {
            "topic": topic,
            "qos": qos,
            "set": True,
        }

    @property
    def published_count(self) -> int:
        """Yayın sayısı."""
        return self._stats[
            "messages_published"
        ]

    @property
    def is_connected(self) -> bool:
        """Bağlantı durumu."""
        return self._connected
