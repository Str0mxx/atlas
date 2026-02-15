"""ATLAS Transfer Takipcisi modulu.

Transfer takibi, basari olcumu,
etki analizi, atfetme, gecmis.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TransferTracker:
    """Transfer takipcisi.

    Transfer islemlerini izler.

    Attributes:
        _transfers: Transfer kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Transfer takipcisini baslatir."""
        self._transfers: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "tracked": 0,
            "successful": 0,
            "failed": 0,
        }

        logger.info(
            "TransferTracker baslatildi",
        )

    def track_transfer(
        self,
        source_system: str,
        target_system: str,
        knowledge_id: str,
    ) -> dict[str, Any]:
        """Transfer kaydeder.

        Args:
            source_system: Kaynak sistem.
            target_system: Hedef sistem.
            knowledge_id: Bilgi ID.

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        tid = f"tr_{self._counter}"

        transfer = {
            "transfer_id": tid,
            "source_system": source_system,
            "target_system": target_system,
            "knowledge_id": knowledge_id,
            "status": "in_progress",
            "outcome": None,
            "impact_score": None,
            "started_at": time.time(),
            "completed_at": None,
        }

        self._transfers[tid] = transfer
        self._stats["tracked"] += 1

        return {
            "transfer_id": tid,
            "tracked": True,
        }

    def record_outcome(
        self,
        transfer_id: str,
        success: bool,
        impact_score: float = 0.0,
        details: str = "",
    ) -> dict[str, Any]:
        """Sonuc kaydeder.

        Args:
            transfer_id: Transfer ID.
            success: Basarili mi.
            impact_score: Etki skoru.
            details: Detaylar.

        Returns:
            Kayit bilgisi.
        """
        t = self._transfers.get(transfer_id)
        if not t:
            return {
                "error": (
                    "transfer_not_found"
                ),
            }

        t["status"] = (
            "completed" if success
            else "failed"
        )
        t["outcome"] = (
            "success" if success else "failure"
        )
        t["impact_score"] = impact_score
        t["details"] = details
        t["completed_at"] = time.time()

        if success:
            self._stats["successful"] += 1
        else:
            self._stats["failed"] += 1

        return {
            "transfer_id": transfer_id,
            "outcome": t["outcome"],
            "recorded": True,
        }

    def measure_success(
        self,
        transfer_id: str,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Basari olcer.

        Args:
            transfer_id: Transfer ID.
            metrics: Metrikler.

        Returns:
            Olcum bilgisi.
        """
        t = self._transfers.get(transfer_id)
        if not t:
            return {
                "error": (
                    "transfer_not_found"
                ),
            }

        # Metrik ortalamasindan basari skoru
        values = list(metrics.values())
        avg = (
            sum(values) / len(values)
            if values else 0.0
        )

        t["success_metrics"] = metrics
        t["success_score"] = round(avg, 3)

        return {
            "transfer_id": transfer_id,
            "success_score": round(avg, 3),
            "metrics": metrics,
        }

    def analyze_impact(
        self,
        transfer_id: str,
    ) -> dict[str, Any]:
        """Etki analizi yapar.

        Args:
            transfer_id: Transfer ID.

        Returns:
            Etki bilgisi.
        """
        t = self._transfers.get(transfer_id)
        if not t:
            return {
                "error": (
                    "transfer_not_found"
                ),
            }

        impact = t.get("impact_score", 0.0)
        if impact is None:
            impact = 0.0

        # Etki seviyesi
        if impact >= 0.7:
            level = "high"
        elif impact >= 0.4:
            level = "medium"
        else:
            level = "low"

        duration = None
        if t["completed_at"] and t["started_at"]:
            duration = round(
                t["completed_at"]
                - t["started_at"], 2,
            )

        return {
            "transfer_id": transfer_id,
            "impact_score": impact,
            "impact_level": level,
            "duration_seconds": duration,
            "outcome": t.get("outcome"),
        }

    def get_history(
        self,
        system_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Gecmis getirir.

        Args:
            system_id: Sistem filtresi.

        Returns:
            Transfer listesi.
        """
        results = []
        for t in self._transfers.values():
            if system_id and (
                t["source_system"] != system_id
                and t["target_system"]
                != system_id
            ):
                continue

            results.append({
                "transfer_id": t[
                    "transfer_id"
                ],
                "source": t["source_system"],
                "target": t["target_system"],
                "status": t["status"],
                "outcome": t["outcome"],
            })

        return results

    def get_attribution(
        self,
        target_system: str,
    ) -> dict[str, Any]:
        """Atfetme bilgisi getirir.

        Args:
            target_system: Hedef sistem.

        Returns:
            Atfetme bilgisi.
        """
        sources: dict[str, int] = {}
        for t in self._transfers.values():
            if (
                t["target_system"]
                == target_system
                and t["outcome"] == "success"
            ):
                src = t["source_system"]
                sources[src] = (
                    sources.get(src, 0) + 1
                )

        return {
            "target_system": target_system,
            "sources": sources,
            "total_transfers": sum(
                sources.values(),
            ),
        }

    def get_transfer(
        self,
        transfer_id: str,
    ) -> dict[str, Any]:
        """Transfer getirir.

        Args:
            transfer_id: Transfer ID.

        Returns:
            Transfer bilgisi.
        """
        t = self._transfers.get(transfer_id)
        if not t:
            return {
                "error": (
                    "transfer_not_found"
                ),
            }
        return dict(t)

    @property
    def transfer_count(self) -> int:
        """Transfer sayisi."""
        return self._stats["tracked"]

    @property
    def success_rate(self) -> float:
        """Basari orani."""
        completed = (
            self._stats["successful"]
            + self._stats["failed"]
        )
        if completed == 0:
            return 0.0
        return round(
            self._stats["successful"]
            / completed * 100, 1,
        )
