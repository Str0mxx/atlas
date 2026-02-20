"""
Agent Bridge modulu.

Yerel makine agent baglantisi, kimlik dogrulama,
heartbeat ve yeniden baglanti yonetimi.
"""

import hashlib
import logging
import secrets
import time
from typing import Any

logger = logging.getLogger(__name__)


class AgentBridge:
    """Yerel makine agent koprusu.

    Attributes:
        _host: Bagli host.
        _port: Bagli port.
        _connected: Baglanti durumu.
        _auth_token: Kimlik dogrulama tokeni.
        _last_heartbeat: Son heartbeat zamani.
        _reconnect_attempts: Yeniden baglanti sayisi.
        _channel_id: Guvenli kanal ID.
        _stats: Istatistikler.
    """

    MAX_RECONNECT = 5
    HEARTBEAT_INTERVAL = 30.0

    def __init__(self) -> None:
        """Kopruyu baslatir."""
        self._host: str = ""
        self._port: int = 0
        self._connected: bool = False
        self._auth_token: str = ""
        self._last_heartbeat: float = 0.0
        self._reconnect_attempts: int = 0
        self._channel_id: str = ""
        self._pending_messages: list[dict] = []
        self._stats: dict[str, int] = {
            "connections": 0,
            "heartbeats": 0,
            "reconnects": 0,
            "auth_failures": 0,
            "messages_sent": 0,
        }
        logger.info("AgentBridge baslatildi")

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def reconnect_count(self) -> int:
        return self._stats["reconnects"]

    def establish(self, host: str = "localhost", port: int = 8765, auth_token: str = "") -> dict[str, Any]:
        """Baglanti kurar."""
        try:
            if not host:
                return {"established": False, "error": "host_gerekli"}
            if not (1 <= port <= 65535):
                return {"established": False, "error": "gecersiz_port"}
            self._host = host
            self._port = port
            self._auth_token = auth_token
            self._channel_id = secrets.token_hex(16)
            self._connected = True
            self._reconnect_attempts = 0
            self._last_heartbeat = time.time()
            self._stats["connections"] += 1
            return {"established": True, "host": host, "port": port, "channel_id": self._channel_id}
        except Exception as e:
            logger.error("Baglanti hatasi: %s", e)
            return {"established": False, "error": str(e)}

    def authenticate(self, token: str = "") -> dict[str, Any]:
        """Kimlik dogrulama yapar."""
        try:
            if not token:
                return {"authenticated": False, "error": "token_gerekli"}
            if not self._connected:
                return {"authenticated": False, "error": "baglanti_yok"}
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expected_hash = hashlib.sha256(self._auth_token.encode()).hexdigest()
            if not self._auth_token or token_hash == expected_hash:
                return {"authenticated": True, "channel_id": self._channel_id}
            self._stats["auth_failures"] += 1
            return {"authenticated": False, "reason": "gecersiz_token"}
        except Exception as e:
            logger.error("Auth hatasi: %s", e)
            return {"authenticated": False, "error": str(e)}

    def send_heartbeat(self) -> dict[str, Any]:
        """Heartbeat gonderir."""
        try:
            if not self._connected:
                return {"sent": False, "error": "baglanti_yok"}
            now = time.time()
            self._last_heartbeat = now
            self._stats["heartbeats"] += 1
            return {"sent": True, "timestamp": now, "channel_id": self._channel_id, "latency_ms": 0}
        except Exception as e:
            logger.error("Heartbeat hatasi: %s", e)
            return {"sent": False, "error": str(e)}

    def check_heartbeat(self) -> dict[str, Any]:
        """Heartbeat sagligini kontrol eder."""
        try:
            if not self._connected:
                return {"healthy": False, "reason": "baglanti_yok"}
            elapsed = time.time() - self._last_heartbeat
            healthy = elapsed < self.HEARTBEAT_INTERVAL * 2
            return {"healthy": healthy, "last_heartbeat": self._last_heartbeat, "elapsed_seconds": round(elapsed, 2), "threshold_seconds": self.HEARTBEAT_INTERVAL * 2}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    def disconnect(self) -> dict[str, Any]:
        """Baglantiyi kapatir."""
        try:
            if not self._connected:
                return {"disconnected": True, "reason": "zaten_kapali"}
            self._connected = False
            self._channel_id = ""
            self._pending_messages.clear()
            return {"disconnected": True, "host": self._host, "port": self._port}
        except Exception as e:
            return {"disconnected": False, "error": str(e)}

    def reconnect(self) -> dict[str, Any]:
        """Yeniden baglanti dener."""
        try:
            if self._reconnect_attempts >= self.MAX_RECONNECT:
                return {"reconnected": False, "reason": "maksimum_deneme_asildi", "attempts": self._reconnect_attempts}
            self._reconnect_attempts += 1
            self._stats["reconnects"] += 1
            if self._host:
                self._connected = True
                self._channel_id = secrets.token_hex(16)
                self._last_heartbeat = time.time()
                return {"reconnected": True, "attempt": self._reconnect_attempts, "channel_id": self._channel_id}
            return {"reconnected": False, "reason": "host_bilgisi_yok"}
        except Exception as e:
            return {"reconnected": False, "error": str(e)}

    def send_message(self, message_type: str = "", payload: dict | None = None) -> dict[str, Any]:
        """Guvenli kanaldan mesaj gonderir."""
        try:
            if not self._connected:
                return {"sent": False, "error": "baglanti_yok"}
            if not message_type:
                return {"sent": False, "error": "mesaj_tipi_gerekli"}
            self._pending_messages.append({"type": message_type, "payload": payload or {}, "timestamp": time.time()})
            self._stats["messages_sent"] += 1
            return {"sent": True, "message_type": message_type, "channel_id": self._channel_id}
        except Exception as e:
            return {"sent": False, "error": str(e)}

    def get_status(self) -> dict[str, Any]:
        """Baglanti durumunu dondurur."""
        try:
            return {
                "retrieved": True,
                "connected": self._connected,
                "host": self._host,
                "port": self._port,
                "channel_id": self._channel_id,
                "last_heartbeat": self._last_heartbeat,
                "reconnect_attempts": self._reconnect_attempts,
                "pending_messages": len(self._pending_messages),
            }
        except Exception as e:
            return {"retrieved": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur."""
        try:
            return {
                "retrieved": True,
                "connected": self._connected,
                "host": self._host,
                "port": self._port,
                "reconnect_attempts": self._reconnect_attempts,
                "stats": dict(self._stats),
            }
        except Exception as e:
            return {"retrieved": False, "error": str(e)}
