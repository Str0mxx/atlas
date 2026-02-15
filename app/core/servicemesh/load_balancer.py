"""ATLAS Mesh Yuk Dengeleyici modulu.

Round robin, en az baglanti,
agirlikli yonlendirme, saglik-duyarli
yonlendirme ve yapiskan oturumlar.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MeshLoadBalancer:
    """Mesh yuk dengeleyici.

    Trafigi ornekler arasinda dagitir.

    Attributes:
        _algorithm: Dengeleme algoritmasi.
        _connections: Baglanti sayilari.
    """

    def __init__(
        self,
        algorithm: str = "round_robin",
    ) -> None:
        """Yuk dengeleyiciyi baslatir.

        Args:
            algorithm: Algoritma.
        """
        self._algorithm = algorithm
        self._rr_index: dict[str, int] = {}
        self._connections: dict[str, int] = {}
        self._weights: dict[str, float] = {}
        self._health: dict[str, bool] = {}
        self._sticky: dict[str, str] = {}
        self._stats: dict[str, int] = {}

        logger.info(
            "MeshLoadBalancer baslatildi: %s",
            algorithm,
        )

    def select(
        self,
        service: str,
        instances: list[dict[str, Any]],
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Ornek secer.

        Args:
            service: Servis adi.
            instances: Mevcut ornekler.
            session_id: Oturum ID (sticky icin).

        Returns:
            Secilen ornek veya None.
        """
        if not instances:
            return None

        # Sticky session kontrolu
        if session_id and session_id in self._sticky:
            sticky_id = self._sticky[session_id]
            for inst in instances:
                if inst.get("instance_id") == sticky_id:
                    self._record_selection(
                        inst["instance_id"],
                    )
                    return inst

        # Saglik filtresi
        healthy = self._filter_healthy(instances)
        if not healthy:
            healthy = instances

        selected = None
        if self._algorithm == "round_robin":
            selected = self._round_robin(
                service, healthy,
            )
        elif self._algorithm == "least_connections":
            selected = self._least_connections(
                healthy,
            )
        elif self._algorithm == "weighted":
            selected = self._weighted(healthy)
        elif self._algorithm == "health_aware":
            selected = self._health_aware(healthy)
        else:
            selected = healthy[0]

        if selected:
            iid = selected.get("instance_id", "")
            self._record_selection(iid)
            if session_id:
                self._sticky[session_id] = iid

        return selected

    def _round_robin(
        self,
        service: str,
        instances: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Round robin secimi.

        Args:
            service: Servis adi.
            instances: Ornekler.

        Returns:
            Secilen ornek.
        """
        idx = self._rr_index.get(service, 0)
        selected = instances[idx % len(instances)]
        self._rr_index[service] = idx + 1
        return selected

    def _least_connections(
        self,
        instances: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """En az baglanti secimi.

        Args:
            instances: Ornekler.

        Returns:
            Secilen ornek.
        """
        min_conn = float("inf")
        best = instances[0]
        for inst in instances:
            iid = inst.get("instance_id", "")
            conn = self._connections.get(iid, 0)
            if conn < min_conn:
                min_conn = conn
                best = inst
        return best

    def _weighted(
        self,
        instances: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Agirlikli secim.

        Args:
            instances: Ornekler.

        Returns:
            Secilen ornek.
        """
        max_weight = 0.0
        best = instances[0]
        for inst in instances:
            iid = inst.get("instance_id", "")
            w = self._weights.get(iid, 1.0)
            if w > max_weight:
                max_weight = w
                best = inst
        return best

    def _health_aware(
        self,
        instances: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Saglik-duyarli secim.

        Args:
            instances: Ornekler.

        Returns:
            Secilen ornek.
        """
        healthy = [
            i for i in instances
            if self._health.get(
                i.get("instance_id", ""), True,
            )
        ]
        if not healthy:
            healthy = instances
        # Saglikli ornekler arasinda en az baglanti
        return self._least_connections(healthy)

    def _filter_healthy(
        self,
        instances: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sagliklilari filtreler.

        Args:
            instances: Ornekler.

        Returns:
            Sagliklı ornekler.
        """
        return [
            i for i in instances
            if i.get("status") == "active"
        ]

    def _record_selection(
        self,
        instance_id: str,
    ) -> None:
        """Secim kaydeder.

        Args:
            instance_id: Ornek ID.
        """
        self._stats[instance_id] = (
            self._stats.get(instance_id, 0) + 1
        )

    def set_weight(
        self,
        instance_id: str,
        weight: float,
    ) -> None:
        """Agirlik ayarlar.

        Args:
            instance_id: Ornek ID.
            weight: Agirlik.
        """
        self._weights[instance_id] = max(
            0.0, weight,
        )

    def set_health(
        self,
        instance_id: str,
        healthy: bool,
    ) -> None:
        """Saglik durumu ayarlar.

        Args:
            instance_id: Ornek ID.
            healthy: Sagliklı mi.
        """
        self._health[instance_id] = healthy

    def add_connection(
        self,
        instance_id: str,
    ) -> int:
        """Baglanti ekler.

        Args:
            instance_id: Ornek ID.

        Returns:
            Yeni baglanti sayisi.
        """
        self._connections[instance_id] = (
            self._connections.get(instance_id, 0)
            + 1
        )
        return self._connections[instance_id]

    def remove_connection(
        self,
        instance_id: str,
    ) -> int:
        """Baglanti azaltir.

        Args:
            instance_id: Ornek ID.

        Returns:
            Yeni baglanti sayisi.
        """
        current = self._connections.get(
            instance_id, 0,
        )
        self._connections[instance_id] = max(
            0, current - 1,
        )
        return self._connections[instance_id]

    def clear_sticky(
        self,
        session_id: str | None = None,
    ) -> int:
        """Sticky oturumlari temizler.

        Args:
            session_id: Spesifik oturum (None=tumu).

        Returns:
            Temizlenen sayi.
        """
        if session_id:
            if session_id in self._sticky:
                del self._sticky[session_id]
                return 1
            return 0
        count = len(self._sticky)
        self._sticky.clear()
        return count

    def get_stats(self) -> dict[str, int]:
        """Secim istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def algorithm(self) -> str:
        """Algoritma."""
        return self._algorithm

    @property
    def sticky_count(self) -> int:
        """Sticky oturum sayisi."""
        return len(self._sticky)

    @property
    def total_connections(self) -> int:
        """Toplam baglanti sayisi."""
        return sum(self._connections.values())
