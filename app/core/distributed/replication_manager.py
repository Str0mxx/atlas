"""ATLAS Replikasyon Yoneticisi modulu.

Veri replikasyonu, senkron/asenkron
modlar, catisma cozumu, tutarlilik
seviyeleri ve gecikme izleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReplicationManager:
    """Replikasyon yoneticisi.

    Veri replikasyonunu yonetir.

    Attributes:
        _replicas: Replika tanimlari.
        _data: Replike edilen veri.
    """

    def __init__(
        self,
        replication_factor: int = 3,
    ) -> None:
        """Replikasyon yoneticisini baslatir.

        Args:
            replication_factor: Replika sayisi.
        """
        self._replicas: dict[
            str, dict[str, Any]
        ] = {}
        self._data: dict[
            str, dict[str, Any]
        ] = {}
        self._replication_factor = replication_factor
        self._conflicts: list[
            dict[str, Any]
        ] = []
        self._lag_history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "ReplicationManager baslatildi",
        )

    def add_replica(
        self,
        replica_id: str,
        node_id: str,
        mode: str = "async",
        role: str = "follower",
    ) -> dict[str, Any]:
        """Replika ekler.

        Args:
            replica_id: Replika ID.
            node_id: Dugum ID.
            mode: Replikasyon modu.
            role: Rol (leader/follower).

        Returns:
            Replika bilgisi.
        """
        replica = {
            "replica_id": replica_id,
            "node_id": node_id,
            "mode": mode,
            "role": role,
            "status": "active",
            "lag_ms": 0.0,
            "synced_version": 0,
            "created_at": time.time(),
        }
        self._replicas[replica_id] = replica
        return replica

    def remove_replica(
        self,
        replica_id: str,
    ) -> bool:
        """Replikayi kaldirir.

        Args:
            replica_id: Replika ID.

        Returns:
            Basarili mi.
        """
        if replica_id in self._replicas:
            del self._replicas[replica_id]
            return True
        return False

    def replicate(
        self,
        key: str,
        value: Any,
        version: int = 1,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Veri replike eder.

        Args:
            key: Anahtar.
            value: Deger.
            version: Surum.
            mode: Mod.

        Returns:
            Replikasyon sonucu.
        """
        entry = {
            "key": key,
            "value": value,
            "version": version,
            "timestamp": time.time(),
        }
        self._data[key] = entry

        synced = 0
        failed = 0
        active_replicas = [
            r for r in self._replicas.values()
            if r["status"] == "active"
        ]

        for replica in active_replicas:
            rep_mode = mode or replica["mode"]
            if rep_mode == "sync":
                replica["synced_version"] = version
                replica["lag_ms"] = 0.0
                synced += 1
            elif rep_mode == "async":
                replica["synced_version"] = (
                    version - 1 if version > 1
                    else version
                )
                replica["lag_ms"] = 10.0
                synced += 1
            else:
                synced += 1

        return {
            "key": key,
            "version": version,
            "synced": synced,
            "failed": failed,
            "total_replicas": len(
                active_replicas,
            ),
        }

    def read(
        self,
        key: str,
        consistency: str = "eventual",
    ) -> dict[str, Any]:
        """Veri okur.

        Args:
            key: Anahtar.
            consistency: Tutarlilik seviyesi.

        Returns:
            Okuma sonucu.
        """
        entry = self._data.get(key)
        if not entry:
            return {
                "key": key,
                "found": False,
            }

        if consistency == "strong":
            # Tum replikalarin senkron olmasi
            all_synced = all(
                r["synced_version"]
                >= entry["version"]
                for r in self._replicas.values()
                if r["status"] == "active"
            )
            if not all_synced:
                return {
                    "key": key,
                    "found": True,
                    "consistent": False,
                    "reason": "replicas_behind",
                }

        return {
            "key": key,
            "found": True,
            "consistent": True,
            "value": entry["value"],
            "version": entry["version"],
        }

    def check_lag(self) -> dict[str, Any]:
        """Gecikme kontrol eder.

        Returns:
            Gecikme bilgisi.
        """
        lags = []
        for r in self._replicas.values():
            if r["status"] == "active":
                lags.append({
                    "replica_id": r["replica_id"],
                    "lag_ms": r["lag_ms"],
                    "mode": r["mode"],
                })

        avg_lag = (
            sum(l["lag_ms"] for l in lags)
            / len(lags) if lags else 0.0
        )
        max_lag = (
            max(l["lag_ms"] for l in lags)
            if lags else 0.0
        )

        result = {
            "replicas": len(lags),
            "avg_lag_ms": round(avg_lag, 2),
            "max_lag_ms": round(max_lag, 2),
            "lags": lags,
        }
        self._lag_history.append(result)
        return result

    def detect_conflict(
        self,
        key: str,
        value_a: Any,
        value_b: Any,
        version_a: int = 1,
        version_b: int = 1,
    ) -> dict[str, Any]:
        """Catisma tespit eder.

        Args:
            key: Anahtar.
            value_a: Deger A.
            value_b: Deger B.
            version_a: Surum A.
            version_b: Surum B.

        Returns:
            Tespit sonucu.
        """
        has_conflict = (
            value_a != value_b
            and version_a == version_b
        )

        conflict = {
            "key": key,
            "conflict": has_conflict,
            "value_a": value_a,
            "value_b": value_b,
            "version_a": version_a,
            "version_b": version_b,
            "timestamp": time.time(),
        }
        if has_conflict:
            self._conflicts.append(conflict)

        return conflict

    def resolve_conflict(
        self,
        key: str,
        strategy: str = "last_write_wins",
    ) -> dict[str, Any]:
        """Catisma cozer.

        Args:
            key: Anahtar.
            strategy: Cozum stratejisi.

        Returns:
            Cozum sonucu.
        """
        matching = [
            c for c in self._conflicts
            if c["key"] == key
        ]
        if not matching:
            return {
                "key": key,
                "resolved": False,
                "reason": "no_conflict",
            }

        conflict = matching[-1]
        if strategy == "last_write_wins":
            winner = conflict["value_b"]
        elif strategy == "first_write_wins":
            winner = conflict["value_a"]
        elif strategy == "higher_version":
            winner = (
                conflict["value_a"]
                if conflict["version_a"]
                > conflict["version_b"]
                else conflict["value_b"]
            )
        else:
            winner = conflict["value_b"]

        self._conflicts = [
            c for c in self._conflicts
            if c["key"] != key
        ]

        return {
            "key": key,
            "resolved": True,
            "strategy": strategy,
            "winner": winner,
        }

    def promote_replica(
        self,
        replica_id: str,
    ) -> dict[str, Any]:
        """Replikayi lider yapar.

        Args:
            replica_id: Replika ID.

        Returns:
            Sonuc bilgisi.
        """
        replica = self._replicas.get(replica_id)
        if not replica:
            return {
                "status": "error",
                "reason": "replica_not_found",
            }

        # Mevcut lideri follower yap
        for r in self._replicas.values():
            if r["role"] == "leader":
                r["role"] = "follower"

        replica["role"] = "leader"
        return {
            "replica_id": replica_id,
            "role": "leader",
            "status": "promoted",
        }

    @property
    def replica_count(self) -> int:
        """Replika sayisi."""
        return len(self._replicas)

    @property
    def data_count(self) -> int:
        """Veri sayisi."""
        return len(self._data)

    @property
    def conflict_count(self) -> int:
        """Catisma sayisi."""
        return len(self._conflicts)

    @property
    def leader(self) -> str | None:
        """Mevcut lider."""
        for r in self._replicas.values():
            if r["role"] == "leader":
                return r["replica_id"]
        return None
