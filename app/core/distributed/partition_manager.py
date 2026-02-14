"""ATLAS Bolum Yoneticisi modulu.

Veri bolumleme, shard yonetimi,
yeniden dengeleme, consistent hashing
ve bolum kurtarma.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PartitionManager:
    """Bolum yoneticisi.

    Veri bolumleme ve shard yonetimi.

    Attributes:
        _partitions: Bolum tanimlari.
        _ring: Consistent hash halkasi.
    """

    def __init__(
        self,
        num_partitions: int = 16,
        virtual_nodes: int = 3,
    ) -> None:
        """Bolum yoneticisini baslatir.

        Args:
            num_partitions: Bolum sayisi.
            virtual_nodes: Sanal dugum sayisi.
        """
        self._partitions: dict[
            str, dict[str, Any]
        ] = {}
        self._ring: list[
            tuple[int, str]
        ] = []
        self._nodes: dict[
            str, dict[str, Any]
        ] = {}
        self._data_map: dict[
            str, str
        ] = {}
        self._num_partitions = num_partitions
        self._virtual_nodes = virtual_nodes
        self._rebalance_log: list[
            dict[str, Any]
        ] = []

        logger.info(
            "PartitionManager baslatildi",
        )

    def add_node(
        self,
        node_id: str,
        capacity: int = 100,
    ) -> dict[str, Any]:
        """Dugum ekler.

        Args:
            node_id: Dugum ID.
            capacity: Kapasite.

        Returns:
            Dugum bilgisi.
        """
        node = {
            "node_id": node_id,
            "capacity": capacity,
            "partition_count": 0,
            "status": "active",
        }
        self._nodes[node_id] = node

        # Hash halkasina ekle
        for i in range(self._virtual_nodes):
            key = f"{node_id}:{i}"
            h = self._hash(key)
            self._ring.append((h, node_id))

        self._ring.sort(key=lambda x: x[0])
        return node

    def remove_node(
        self,
        node_id: str,
    ) -> bool:
        """Dugumu kaldirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Basarili mi.
        """
        if node_id not in self._nodes:
            return False

        del self._nodes[node_id]
        self._ring = [
            (h, n) for h, n in self._ring
            if n != node_id
        ]

        # Bolumlerini temizle
        to_remove = [
            pid for pid, p in
            self._partitions.items()
            if p["node_id"] == node_id
        ]
        for pid in to_remove:
            del self._partitions[pid]

        return True

    def create_partition(
        self,
        partition_id: str,
        node_id: str = "",
        strategy: str = "hash",
    ) -> dict[str, Any]:
        """Bolum olusturur.

        Args:
            partition_id: Bolum ID.
            node_id: Dugum ID.
            strategy: Strateji.

        Returns:
            Bolum bilgisi.
        """
        if not node_id:
            node_id = self._get_least_loaded()

        partition = {
            "partition_id": partition_id,
            "node_id": node_id,
            "strategy": strategy,
            "item_count": 0,
            "status": "active",
            "created_at": time.time(),
        }
        self._partitions[partition_id] = partition

        if node_id in self._nodes:
            self._nodes[node_id][
                "partition_count"
            ] += 1

        return partition

    def assign_key(
        self,
        key: str,
    ) -> dict[str, Any]:
        """Anahtari bolume atar.

        Args:
            key: Anahtar.

        Returns:
            Atama bilgisi.
        """
        if not self._ring:
            return {
                "key": key,
                "assigned": False,
                "reason": "no_nodes",
            }

        h = self._hash(key)
        # Saat yonunde ilk dugumu bul
        node_id = self._ring[0][1]
        for ring_hash, nid in self._ring:
            if ring_hash >= h:
                node_id = nid
                break

        self._data_map[key] = node_id
        return {
            "key": key,
            "assigned": True,
            "node_id": node_id,
        }

    def lookup_key(
        self,
        key: str,
    ) -> str | None:
        """Anahtar arar.

        Args:
            key: Anahtar.

        Returns:
            Dugum ID veya None.
        """
        return self._data_map.get(key)

    def rebalance(self) -> dict[str, Any]:
        """Yeniden dengeler.

        Returns:
            Dengeleme sonucu.
        """
        if not self._nodes:
            return {
                "moved": 0,
                "reason": "no_nodes",
            }

        moved = 0
        # Her anahtari yeniden ata
        for key in list(self._data_map.keys()):
            old_node = self._data_map[key]
            result = self.assign_key(key)
            new_node = result.get("node_id")
            if new_node and new_node != old_node:
                moved += 1

        record = {
            "moved": moved,
            "total_keys": len(self._data_map),
            "timestamp": time.time(),
        }
        self._rebalance_log.append(record)
        return record

    def recover_partition(
        self,
        partition_id: str,
        new_node_id: str,
    ) -> dict[str, Any]:
        """Bolumu kurtarir.

        Args:
            partition_id: Bolum ID.
            new_node_id: Yeni dugum ID.

        Returns:
            Kurtarma sonucu.
        """
        partition = self._partitions.get(
            partition_id,
        )
        if not partition:
            return {
                "status": "error",
                "reason": "partition_not_found",
            }

        old_node = partition["node_id"]
        partition["node_id"] = new_node_id
        partition["status"] = "active"

        if new_node_id in self._nodes:
            self._nodes[new_node_id][
                "partition_count"
            ] += 1

        return {
            "partition_id": partition_id,
            "old_node": old_node,
            "new_node": new_node_id,
            "status": "recovered",
        }

    def get_partition_map(
        self,
    ) -> dict[str, str]:
        """Bolum haritasini getirir.

        Returns:
            Bolum -> Dugum eslesmesi.
        """
        return {
            pid: p["node_id"]
            for pid, p in self._partitions.items()
        }

    def _hash(self, key: str) -> int:
        """Consistent hash uretir.

        Args:
            key: Anahtar.

        Returns:
            Hash degeri.
        """
        h = hashlib.md5(
            key.encode(),
        ).hexdigest()
        return int(h[:8], 16)

    def _get_least_loaded(self) -> str:
        """En az yuklu dugumu bulur.

        Returns:
            Dugum ID.
        """
        if not self._nodes:
            return ""
        return min(
            self._nodes,
            key=lambda n: self._nodes[n][
                "partition_count"
            ],
        )

    @property
    def partition_count(self) -> int:
        """Bolum sayisi."""
        return len(self._partitions)

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def key_count(self) -> int:
        """Anahtar sayisi."""
        return len(self._data_map)

    @property
    def rebalance_count(self) -> int:
        """Dengeleme sayisi."""
        return len(self._rebalance_log)
