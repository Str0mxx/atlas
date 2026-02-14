"""ATLAS Dagitik Onbellek modulu.

Redis entegrasyonu, cluster destegi,
replikasyon, bolumleme ve
failover.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DistributedCache:
    """Dagitik onbellek.

    Redis-benzeri dagitik onbellek
    simulasyonu saglar.

    Attributes:
        _shards: Bolum depolari.
        _replicas: Replika sayisi.
    """

    def __init__(
        self,
        num_shards: int = 4,
        replicas: int = 1,
    ) -> None:
        """Dagitik onbellegi baslatir.

        Args:
            num_shards: Bolum sayisi.
            replicas: Replika sayisi.
        """
        self._num_shards = num_shards
        self._replicas = replicas
        self._shards: list[
            dict[str, dict[str, Any]]
        ] = [
            {} for _ in range(num_shards)
        ]
        self._hits = 0
        self._misses = 0
        self._nodes: dict[
            str, dict[str, Any]
        ] = {
            "primary": {
                "status": "active",
                "role": "primary",
            },
        }

        logger.info(
            "DistributedCache baslatildi",
        )

    def _get_shard(self, key: str) -> int:
        """Anahtar icin bolum belirler.

        Args:
            key: Anahtar.

        Returns:
            Bolum indeksi.
        """
        return hash(key) % self._num_shards

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Deger getirir.

        Args:
            key: Anahtar.
            default: Varsayilan.

        Returns:
            Deger veya varsayilan.
        """
        shard_idx = self._get_shard(key)
        shard = self._shards[shard_idx]
        entry = shard.get(key)

        if not entry:
            self._misses += 1
            return default

        # TTL kontrolu
        if entry.get("expires_at", 0) > 0:
            if time.time() > entry["expires_at"]:
                del shard[key]
                self._misses += 1
                return default

        entry["hits"] = entry.get("hits", 0) + 1
        self._hits += 1
        return entry["value"]

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 0,
    ) -> None:
        """Deger yazar.

        Args:
            key: Anahtar.
            value: Deger.
            ttl: Yasam suresi.
        """
        shard_idx = self._get_shard(key)
        entry = {
            "value": value,
            "hits": 0,
            "set_at": time.time(),
            "expires_at": (
                time.time() + ttl if ttl > 0
                else 0
            ),
        }
        self._shards[shard_idx][key] = entry

    def delete(self, key: str) -> bool:
        """Siler.

        Args:
            key: Anahtar.

        Returns:
            Basarili ise True.
        """
        shard_idx = self._get_shard(key)
        shard = self._shards[shard_idx]
        if key in shard:
            del shard[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Var mi kontrol eder.

        Args:
            key: Anahtar.

        Returns:
            Varsa True.
        """
        shard_idx = self._get_shard(key)
        entry = self._shards[shard_idx].get(key)
        if not entry:
            return False
        if entry.get("expires_at", 0) > 0:
            if time.time() > entry["expires_at"]:
                del self._shards[shard_idx][key]
                return False
        return True

    def flush(self) -> int:
        """Tum veriyi siler.

        Returns:
            Silinen girdi sayisi.
        """
        total = sum(
            len(s) for s in self._shards
        )
        for shard in self._shards:
            shard.clear()
        return total

    def add_node(
        self,
        node_id: str,
        role: str = "replica",
    ) -> dict[str, Any]:
        """Dugum ekler.

        Args:
            node_id: Dugum ID.
            role: Rol.

        Returns:
            Dugum bilgisi.
        """
        node = {
            "status": "active",
            "role": role,
        }
        self._nodes[node_id] = node
        return node

    def remove_node(
        self,
        node_id: str,
    ) -> bool:
        """Dugum kaldirir.

        Args:
            node_id: Dugum ID.

        Returns:
            Basarili ise True.
        """
        if node_id == "primary":
            return False
        if node_id in self._nodes:
            del self._nodes[node_id]
            return True
        return False

    def failover(
        self,
        failed_node: str,
    ) -> dict[str, Any]:
        """Failover yapar.

        Args:
            failed_node: Basan dugum.

        Returns:
            Failover sonucu.
        """
        node = self._nodes.get(failed_node)
        if not node:
            return {
                "success": False,
                "reason": "node_not_found",
            }

        node["status"] = "failed"

        # Replika varsa terfi ettir
        for nid, n in self._nodes.items():
            if (
                n["role"] == "replica"
                and n["status"] == "active"
            ):
                if failed_node == "primary":
                    n["role"] = "primary"
                return {
                    "success": True,
                    "promoted": nid,
                }

        return {
            "success": True,
            "promoted": None,
        }

    def get_shard_stats(
        self,
    ) -> list[dict[str, Any]]:
        """Bolum istatistikleri getirir.

        Returns:
            Bolum istatistikleri.
        """
        return [
            {
                "shard": i,
                "entries": len(shard),
            }
            for i, shard in enumerate(
                self._shards,
            )
        ]

    def get_stats(self) -> dict[str, Any]:
        """Istatistik getirir.

        Returns:
            Istatistik.
        """
        total = self._hits + self._misses
        total_entries = sum(
            len(s) for s in self._shards
        )
        return {
            "total_entries": total_entries,
            "shards": self._num_shards,
            "nodes": len(self._nodes),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(
                self._hits / max(1, total), 3,
            ),
        }

    @property
    def total_entries(self) -> int:
        """Toplam girdi sayisi."""
        return sum(
            len(s) for s in self._shards
        )

    @property
    def node_count(self) -> int:
        """Dugum sayisi."""
        return len(self._nodes)

    @property
    def shard_count(self) -> int:
        """Bolum sayisi."""
        return self._num_shards
