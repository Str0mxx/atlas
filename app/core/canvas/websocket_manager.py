"""WebSocket baglanti yonetimi modulu.

Istemci baglantilari, oturum bazli yayın ve
saglik kontrolu islevleri saglar.
"""

import logging
import time
from typing import Any, Optional

from app.models.canvas_models import WebSocketClient

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket baglanti yoneticisi.

    Istemci kaydi, mesaj gonderimi ve
    oturum bazli yayın islevleri saglar.
    """

    def __init__(self) -> None:
        """WebSocket yoneticisini baslatir."""
        self._clients: dict[str, WebSocketClient] = {}
        self._session_clients: dict[str, list[str]] = {}
        self._messages: list[dict] = []
        self._history: list[dict] = []

    def _record_history(self, action: str, **kwargs) -> None:
        """Gecmis kaydina olay ekler."""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs,
        })

    def connect(self, client_id: str, session_id: str) -> WebSocketClient:
        """Istemciyi kaydeder.

        Args:
            client_id: Istemci kimligi
            session_id: Oturum kimligi

        Returns:
            Kaydedilen istemci
        """
        client = WebSocketClient(
            client_id=client_id,
            session_id=session_id,
            connected_at=time.time(),
            is_alive=True,
        )
        self._clients[client_id] = client
        if session_id not in self._session_clients:
            self._session_clients[session_id] = []
        self._session_clients[session_id].append(client_id)
        self._record_history("connect", client_id=client_id, session_id=session_id)
        logger.info(f"Istemci baglandi: {client_id} -> {session_id}")
        return client

    def disconnect(self, client_id: str) -> bool:
        """Istemciyi kaldirir.

        Args:
            client_id: Kaldirilacak istemci kimligi

        Returns:
            Basarili ise True
        """
        client = self._clients.get(client_id)
        if not client:
            return False
        client.is_alive = False
        # Oturum listesinden kaldir
        session_id = client.session_id
        if session_id in self._session_clients:
            self._session_clients[session_id] = [
                c for c in self._session_clients[session_id] if c != client_id
            ]
        del self._clients[client_id]
        self._record_history("disconnect", client_id=client_id)
        logger.info(f"Istemci ayrildi: {client_id}")
        return True

    def broadcast(self, session_id: str, message: dict) -> int:
        """Oturumdaki tum istemcilere mesaj gonderir.

        Args:
            session_id: Hedef oturum kimligi
            message: Gonderilecek mesaj

        Returns:
            Mesaj gonderilen istemci sayisi
        """
        client_ids = self._session_clients.get(session_id, [])
        sent = 0
        for cid in client_ids:
            client = self._clients.get(cid)
            if client and client.is_alive:
                self._messages.append({
                    "client_id": cid,
                    "session_id": session_id,
                    "message": message,
                    "timestamp": time.time(),
                })
                sent += 1
        self._record_history("broadcast", session_id=session_id, sent=sent)
        return sent

    def send(self, client_id: str, message: dict) -> bool:
        """Belirli istemciye mesaj gonderir.

        Args:
            client_id: Hedef istemci kimligi
            message: Gonderilecek mesaj

        Returns:
            Basarili ise True
        """
        client = self._clients.get(client_id)
        if not client or not client.is_alive:
            return False
        self._messages.append({
            "client_id": client_id,
            "session_id": client.session_id,
            "message": message,
            "timestamp": time.time(),
        })
        self._record_history("send", client_id=client_id)
        return True

    def get_clients(self, session_id: str) -> list[WebSocketClient]:
        """Oturumdaki istemcileri listeler.

        Args:
            session_id: Oturum kimligi

        Returns:
            Istemci listesi
        """
        client_ids = self._session_clients.get(session_id, [])
        return [
            self._clients[cid]
            for cid in client_ids
            if cid in self._clients and self._clients[cid].is_alive
        ]

    def ping_all(self) -> dict[str, bool]:
        """Tum istemcilere saglik kontrolu yapar.

        Returns:
            Istemci kimligi -> canli durumu eslesmesi
        """
        results = {}
        for cid, client in self._clients.items():
            results[cid] = client.is_alive
        self._record_history("ping_all", total=len(results))
        return results

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        alive = sum(1 for c in self._clients.values() if c.is_alive)
        return {
            "total_clients": len(self._clients),
            "alive_clients": alive,
            "total_sessions": len(self._session_clients),
            "total_messages": len(self._messages),
            "history_count": len(self._history),
        }
