"""
WebSocket sunucu modulu.

Baglanti yonetimi, mesaj yonlendirme,
heartbeat, yeniden baglanti, yayinlama.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CoreWebSocketServer:
    """Cekirdek WebSocket sunucu.

    Attributes:
        _connections: Baglantilar.
        _rooms: Odalar.
        _handlers: Mesaj isleyiciler.
        _stats: Istatistikler.
    """

    CONNECTION_STATES: list[str] = [
        "connecting",
        "connected",
        "disconnecting",
        "disconnected",
        "error",
    ]

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        heartbeat_interval: int = 30,
        max_connections: int = 500,
    ) -> None:
        """Sunucuyu baslatir.

        Args:
            host: Dinleme adresi.
            port: Port numarasi.
            heartbeat_interval: Kalp atisi (sn).
            max_connections: Max baglanti.
        """
        self._host = host
        self._port = port
        self._heartbeat_interval = (
            heartbeat_interval
        )
        self._max_connections = (
            max_connections
        )
        self._connections: dict[
            str, dict
        ] = {}
        self._rooms: dict[
            str, set[str]
        ] = {}
        self._handlers: dict[
            str, list
        ] = {}
        self._message_log: list[
            dict
        ] = []
        self._running = False
        self._stats: dict[str, int] = {
            "connections_total": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "broadcasts": 0,
            "disconnections": 0,
            "reconnections": 0,
        }
        logger.info(
            "CoreWebSocketServer "
            f"baslatildi: {host}:{port}"
        )

    @property
    def connection_count(self) -> int:
        """Baglanti sayisi."""
        return len(self._connections)

    @property
    def is_running(self) -> bool:
        """Calisiyor mu."""
        return self._running

    def start(self) -> dict[str, Any]:
        """Sunucuyu baslatir.

        Returns:
            Baslatma bilgisi.
        """
        try:
            self._running = True
            return {
                "host": self._host,
                "port": self._port,
                "started": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "started": False,
                "error": str(e),
            }

    def stop(self) -> dict[str, Any]:
        """Sunucuyu durdurur.

        Returns:
            Durdurma bilgisi.
        """
        try:
            self._running = False
            count = len(self._connections)
            self._connections.clear()
            self._rooms.clear()
            return {
                "closed_connections": (
                    count
                ),
                "stopped": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "stopped": False,
                "error": str(e),
            }

    def connect(
        self,
        client_id: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Baglanti olusturur.

        Args:
            client_id: Istemci ID.
            metadata: Ek veri.

        Returns:
            Baglanti bilgisi.
        """
        try:
            if (
                len(self._connections)
                >= self._max_connections
            ):
                return {
                    "connected": False,
                    "error": (
                        "Max baglanti siniri"
                    ),
                }

            cid = client_id or (
                f"ws_{uuid4()!s:.8}"
            )

            # Yeniden baglanti kontrolu
            is_reconnect = (
                cid in self._connections
            )
            if is_reconnect:
                self._stats[
                    "reconnections"
                ] += 1

            conn = {
                "connection_id": cid,
                "state": "connected",
                "metadata": (
                    metadata or {}
                ),
                "connected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "last_heartbeat": (
                    time.time()
                ),
                "messages_sent": 0,
                "messages_received": 0,
            }

            self._connections[cid] = conn
            self._stats[
                "connections_total"
            ] += 1

            return {
                "connection_id": cid,
                "reconnected": (
                    is_reconnect
                ),
                "connected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "connected": False,
                "error": str(e),
            }

    def disconnect(
        self, connection_id: str = ""
    ) -> dict[str, Any]:
        """Baglantiyi kapatir.

        Args:
            connection_id: Baglanti ID.

        Returns:
            Kapatma bilgisi.
        """
        try:
            conn = self._connections.pop(
                connection_id, None
            )
            if not conn:
                return {
                    "disconnected": False,
                    "error": (
                        "Baglanti bulunamadi"
                    ),
                }

            # Odalardan cikar
            for room_id in list(
                self._rooms.keys()
            ):
                self._rooms[
                    room_id
                ].discard(connection_id)

            self._stats[
                "disconnections"
            ] += 1

            return {
                "connection_id": (
                    connection_id
                ),
                "disconnected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "disconnected": False,
                "error": str(e),
            }

    def send(
        self,
        connection_id: str = "",
        message_type: str = "",
        data: Any = None,
    ) -> dict[str, Any]:
        """Mesaj gonderir.

        Args:
            connection_id: Baglanti ID.
            message_type: Mesaj tipi.
            data: Mesaj verisi.

        Returns:
            Gonderim bilgisi.
        """
        try:
            conn = self._connections.get(
                connection_id
            )
            if not conn:
                return {
                    "sent": False,
                    "error": (
                        "Baglanti bulunamadi"
                    ),
                }

            mid = f"msg_{uuid4()!s:.8}"
            msg = {
                "message_id": mid,
                "type": message_type,
                "data": data,
                "to": connection_id,
                "sent_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._message_log.append(msg)
            conn["messages_sent"] += 1
            self._stats[
                "messages_sent"
            ] += 1

            return {
                "message_id": mid,
                "sent": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "sent": False,
                "error": str(e),
            }

    def receive(
        self,
        connection_id: str = "",
        message_type: str = "",
        data: Any = None,
    ) -> dict[str, Any]:
        """Mesaj alir ve isler.

        Args:
            connection_id: Baglanti ID.
            message_type: Mesaj tipi.
            data: Mesaj verisi.

        Returns:
            Isleme bilgisi.
        """
        try:
            conn = self._connections.get(
                connection_id
            )
            if not conn:
                return {
                    "received": False,
                    "error": (
                        "Baglanti bulunamadi"
                    ),
                }

            conn[
                "messages_received"
            ] += 1
            conn["last_heartbeat"] = (
                time.time()
            )
            self._stats[
                "messages_received"
            ] += 1

            # Handler'lari calistir
            handlers = (
                self._handlers.get(
                    message_type, []
                )
            )
            results: list[Any] = []
            for h in handlers:
                try:
                    r = h(
                        connection_id, data
                    )
                    results.append(r)
                except Exception as he:
                    logger.error(
                        f"Handler hatasi: {he}"
                    )

            return {
                "connection_id": (
                    connection_id
                ),
                "handlers_called": len(
                    handlers
                ),
                "received": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "received": False,
                "error": str(e),
            }

    def on_message(
        self,
        message_type: str = "",
        handler: Any = None,
    ) -> dict[str, Any]:
        """Mesaj isleyici kaydeder.

        Args:
            message_type: Mesaj tipi.
            handler: Isleyici.

        Returns:
            Kayit bilgisi.
        """
        try:
            self._handlers.setdefault(
                message_type, []
            )
            if handler:
                self._handlers[
                    message_type
                ].append(handler)
            return {
                "message_type": (
                    message_type
                ),
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def broadcast(
        self,
        message_type: str = "",
        data: Any = None,
        exclude: list[str] | None = None,
    ) -> dict[str, Any]:
        """Tum istemcilere yayinlar.

        Args:
            message_type: Mesaj tipi.
            data: Mesaj verisi.
            exclude: Haric tutulanlar.

        Returns:
            Yayin bilgisi.
        """
        try:
            excluded = set(exclude or [])
            sent = 0
            for cid in self._connections:
                if cid not in excluded:
                    self.send(
                        cid,
                        message_type,
                        data,
                    )
                    sent += 1

            self._stats[
                "broadcasts"
            ] += 1

            return {
                "sent_to": sent,
                "broadcast": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "broadcast": False,
                "error": str(e),
            }

    def join_room(
        self,
        connection_id: str = "",
        room_id: str = "",
    ) -> dict[str, Any]:
        """Odaya katilir.

        Args:
            connection_id: Baglanti ID.
            room_id: Oda ID.

        Returns:
            Katilim bilgisi.
        """
        try:
            if (
                connection_id
                not in self._connections
            ):
                return {
                    "joined": False,
                    "error": (
                        "Baglanti bulunamadi"
                    ),
                }

            self._rooms.setdefault(
                room_id, set()
            )
            self._rooms[room_id].add(
                connection_id
            )

            return {
                "room_id": room_id,
                "members": len(
                    self._rooms[room_id]
                ),
                "joined": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "joined": False,
                "error": str(e),
            }

    def leave_room(
        self,
        connection_id: str = "",
        room_id: str = "",
    ) -> dict[str, Any]:
        """Odadan ayrilir.

        Args:
            connection_id: Baglanti ID.
            room_id: Oda ID.

        Returns:
            Ayrilma bilgisi.
        """
        try:
            room = self._rooms.get(
                room_id
            )
            if not room:
                return {
                    "left": False,
                    "error": (
                        "Oda bulunamadi"
                    ),
                }

            room.discard(connection_id)
            return {
                "room_id": room_id,
                "left": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "left": False,
                "error": str(e),
            }

    def room_broadcast(
        self,
        room_id: str = "",
        message_type: str = "",
        data: Any = None,
        exclude: list[str] | None = None,
    ) -> dict[str, Any]:
        """Odaya yayinlar.

        Args:
            room_id: Oda ID.
            message_type: Mesaj tipi.
            data: Mesaj verisi.
            exclude: Haric tutulanlar.

        Returns:
            Yayin bilgisi.
        """
        try:
            room = self._rooms.get(
                room_id
            )
            if not room:
                return {
                    "broadcast": False,
                    "error": (
                        "Oda bulunamadi"
                    ),
                }

            excluded = set(exclude or [])
            sent = 0
            for cid in room:
                if cid not in excluded:
                    self.send(
                        cid,
                        message_type,
                        data,
                    )
                    sent += 1

            return {
                "room_id": room_id,
                "sent_to": sent,
                "broadcast": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "broadcast": False,
                "error": str(e),
            }

    def heartbeat(
        self, connection_id: str = ""
    ) -> dict[str, Any]:
        """Kalp atisi gunceller.

        Args:
            connection_id: Baglanti ID.

        Returns:
            Heartbeat bilgisi.
        """
        try:
            conn = self._connections.get(
                connection_id
            )
            if not conn:
                return {
                    "alive": False,
                    "error": (
                        "Baglanti bulunamadi"
                    ),
                }

            conn["last_heartbeat"] = (
                time.time()
            )

            return {
                "connection_id": (
                    connection_id
                ),
                "alive": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "alive": False,
                "error": str(e),
            }

    def check_stale(
        self,
    ) -> dict[str, Any]:
        """Eski baglantilarini kontrol eder.

        Returns:
            Kontrol bilgisi.
        """
        try:
            now = time.time()
            threshold = (
                self._heartbeat_interval * 3
            )
            stale: list[str] = []

            for cid, conn in list(
                self._connections.items()
            ):
                elapsed = (
                    now
                    - conn[
                        "last_heartbeat"
                    ]
                )
                if elapsed > threshold:
                    stale.append(cid)

            for cid in stale:
                self.disconnect(cid)

            return {
                "stale_count": len(stale),
                "remaining": len(
                    self._connections
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "running": self._running,
                "host": self._host,
                "port": self._port,
                "connections": len(
                    self._connections
                ),
                "rooms": len(
                    self._rooms
                ),
                "handlers": len(
                    self._handlers
                ),
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
