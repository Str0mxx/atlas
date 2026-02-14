"""ATLAS Ag Yoneticisi modulu.

Bant genisligi izleme, baglanti havuzu,
trafik sekillendirme, oncelik kuyruklama
ve zaman asimi yonetimi.
"""

import logging
from typing import Any

from app.models.resource import ResourceStatus

logger = logging.getLogger(__name__)


class NetworkManager:
    """Ag yoneticisi.

    Ag kaynaklarini izler ve yonetir.

    Attributes:
        _connections: Baglanti havuzu.
        _bandwidth_history: Bant genisligi gecmisi.
        _traffic_rules: Trafik kurallari.
        _timeouts: Zaman asimi ayarlari.
    """

    def __init__(
        self,
        max_connections: int = 100,
        bandwidth_limit_mbps: float = 1000.0,
    ) -> None:
        """Ag yoneticisini baslatir.

        Args:
            max_connections: Maks baglanti.
            bandwidth_limit_mbps: Bant genisligi limiti (Mbps).
        """
        self._connections: dict[str, dict[str, Any]] = {}
        self._bandwidth_history: list[float] = []
        self._traffic_rules: list[dict[str, Any]] = []
        self._timeouts: dict[str, float] = {"default": 30.0}
        self._max_connections = max(1, max_connections)
        self._bandwidth_limit = max(1.0, bandwidth_limit_mbps)
        self._current_bandwidth = 0.0
        self._priority_queue: list[dict[str, Any]] = []

        logger.info(
            "NetworkManager baslatildi (max_conn=%d, bw=%.0f Mbps)",
            self._max_connections, self._bandwidth_limit,
        )

    def record_bandwidth(
        self,
        mbps: float,
    ) -> ResourceStatus:
        """Bant genisligi kaydeder.

        Args:
            mbps: Mevcut bant genisligi (Mbps).

        Returns:
            Kaynak durumu.
        """
        self._current_bandwidth = max(0.0, mbps)
        self._bandwidth_history.append(self._current_bandwidth)
        ratio = self._current_bandwidth / self._bandwidth_limit
        if ratio >= 0.95:
            return ResourceStatus.CRITICAL
        if ratio >= 0.8:
            return ResourceStatus.WARNING
        return ResourceStatus.NORMAL

    def create_connection(
        self,
        name: str,
        target: str,
        priority: int = 5,
    ) -> dict[str, Any] | None:
        """Baglanti olusturur.

        Args:
            name: Baglanti adi.
            target: Hedef adres.
            priority: Oncelik (1-10).

        Returns:
            Baglanti bilgisi veya None.
        """
        if len(self._connections) >= self._max_connections:
            return None

        conn = {
            "name": name,
            "target": target,
            "priority": max(1, min(10, priority)),
            "active": True,
            "bytes_sent": 0,
            "bytes_received": 0,
        }
        self._connections[name] = conn
        return conn

    def close_connection(self, name: str) -> bool:
        """Baglanti kapatir.

        Args:
            name: Baglanti adi.

        Returns:
            Basarili ise True.
        """
        conn = self._connections.get(name)
        if not conn:
            return False
        conn["active"] = False
        del self._connections[name]
        return True

    def add_traffic_rule(
        self,
        name: str,
        target_pattern: str,
        max_mbps: float,
        priority: int = 5,
    ) -> dict[str, Any]:
        """Trafik kurali ekler.

        Args:
            name: Kural adi.
            target_pattern: Hedef deseni.
            max_mbps: Maks bant genisligi.
            priority: Oncelik.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "target_pattern": target_pattern,
            "max_mbps": max_mbps,
            "priority": priority,
            "enabled": True,
        }
        self._traffic_rules.append(rule)
        return rule

    def set_timeout(
        self,
        name: str,
        seconds: float,
    ) -> None:
        """Zaman asimi ayarlar.

        Args:
            name: Hedef/servis adi.
            seconds: Zaman asimi (saniye).
        """
        self._timeouts[name] = max(0.1, seconds)

    def get_timeout(self, name: str) -> float:
        """Zaman asimi getirir.

        Args:
            name: Hedef/servis adi.

        Returns:
            Zaman asimi (saniye).
        """
        return self._timeouts.get(
            name, self._timeouts.get("default", 30.0),
        )

    def enqueue_priority(
        self,
        request_id: str,
        priority: int,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Oncelikli kuyruga ekler.

        Args:
            request_id: Istek ID.
            priority: Oncelik (yuksek=once).
            data: Istek verisi.

        Returns:
            Kuyruk konumu.
        """
        entry = {
            "request_id": request_id,
            "priority": priority,
            "data": data or {},
        }
        self._priority_queue.append(entry)
        self._priority_queue.sort(
            key=lambda x: x["priority"], reverse=True,
        )
        pos = next(
            i for i, e in enumerate(self._priority_queue)
            if e["request_id"] == request_id
        )
        return pos

    def dequeue_priority(self) -> dict[str, Any] | None:
        """Kuyruktan cikarir.

        Returns:
            En oncelikli istek veya None.
        """
        if not self._priority_queue:
            return None
        return self._priority_queue.pop(0)

    def get_avg_bandwidth(self, window: int = 10) -> float:
        """Ortalama bant genisligi.

        Args:
            window: Pencere boyutu.

        Returns:
            Ortalama (Mbps).
        """
        recent = self._bandwidth_history[-window:]
        if not recent:
            return 0.0
        return sum(recent) / len(recent)

    @property
    def connection_count(self) -> int:
        """Baglanti sayisi."""
        return len(self._connections)

    @property
    def current_bandwidth(self) -> float:
        """Mevcut bant genisligi (Mbps)."""
        return self._current_bandwidth

    @property
    def rule_count(self) -> int:
        """Trafik kurali sayisi."""
        return len(self._traffic_rules)

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._priority_queue)
