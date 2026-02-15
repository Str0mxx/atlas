"""ATLAS KPI Tanimlayici modulu.

Sistem KPI, agent KPI, ozel metrikler,
hedef belirleme, esik tanimlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KPIDefiner:
    """KPI tanimlayici.

    KPI tanimlarini yonetir.

    Attributes:
        _kpis: KPI tanimlari.
        _categories: Kategori gruplari.
    """

    def __init__(self) -> None:
        """KPI tanimlayiciyi baslatir."""
        self._kpis: dict[
            str, dict[str, Any]
        ] = {}
        self._categories: dict[
            str, list[str]
        ] = {}
        self._stats = {
            "defined": 0,
            "targets_set": 0,
        }

        logger.info(
            "KPIDefiner baslatildi",
        )

    def define_kpi(
        self,
        kpi_id: str,
        name: str,
        category: str = "custom",
        unit: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """KPI tanimlar.

        Args:
            kpi_id: KPI ID.
            name: KPI adi.
            category: Kategori.
            unit: Birim.
            description: Aciklama.

        Returns:
            Tanim bilgisi.
        """
        kpi = {
            "kpi_id": kpi_id,
            "name": name,
            "category": category,
            "unit": unit,
            "description": description,
            "target": None,
            "threshold": None,
            "created_at": time.time(),
        }

        self._kpis[kpi_id] = kpi

        if category not in self._categories:
            self._categories[category] = []
        if kpi_id not in self._categories[category]:
            self._categories[category].append(
                kpi_id,
            )

        self._stats["defined"] += 1

        return {
            "kpi_id": kpi_id,
            "name": name,
            "category": category,
            "defined": True,
        }

    def set_target(
        self,
        kpi_id: str,
        target: float,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        """Hedef belirler.

        Args:
            kpi_id: KPI ID.
            target: Hedef deger.
            threshold: Esik deger.

        Returns:
            Hedef bilgisi.
        """
        kpi = self._kpis.get(kpi_id)
        if not kpi:
            return {"error": "kpi_not_found"}

        kpi["target"] = target
        if threshold is not None:
            kpi["threshold"] = threshold
        else:
            kpi["threshold"] = target * 0.8

        self._stats["targets_set"] += 1

        return {
            "kpi_id": kpi_id,
            "target": target,
            "threshold": kpi["threshold"],
            "set": True,
        }

    def define_system_kpis(
        self,
    ) -> list[dict[str, Any]]:
        """Sistem KPI'larini tanimlar.

        Returns:
            Tanimlanan KPI listesi.
        """
        system_kpis = [
            ("sys_uptime", "System Uptime", "%"),
            ("sys_latency", "Response Latency", "ms"),
            ("sys_throughput", "Throughput", "req/s"),
            ("sys_error_rate", "Error Rate", "%"),
            ("sys_memory", "Memory Usage", "%"),
        ]

        results = []
        for kpi_id, name, unit in system_kpis:
            r = self.define_kpi(
                kpi_id, name,
                category="system", unit=unit,
            )
            results.append(r)

        return results

    def define_agent_kpis(
        self,
    ) -> list[dict[str, Any]]:
        """Agent KPI'larini tanimlar.

        Returns:
            Tanimlanan KPI listesi.
        """
        agent_kpis = [
            ("agent_success", "Task Success Rate", "%"),
            ("agent_speed", "Avg Completion Time", "s"),
            ("agent_accuracy", "Decision Accuracy", "%"),
            ("agent_utilization", "Agent Utilization", "%"),
        ]

        results = []
        for kpi_id, name, unit in agent_kpis:
            r = self.define_kpi(
                kpi_id, name,
                category="agent", unit=unit,
            )
            results.append(r)

        return results

    def get_kpi(
        self,
        kpi_id: str,
    ) -> dict[str, Any] | None:
        """KPI getirir.

        Args:
            kpi_id: KPI ID.

        Returns:
            KPI verisi veya None.
        """
        kpi = self._kpis.get(kpi_id)
        if kpi:
            return dict(kpi)
        return None

    def get_by_category(
        self,
        category: str,
    ) -> list[dict[str, Any]]:
        """Kategoriye gore KPI'lari getirir.

        Args:
            category: Kategori.

        Returns:
            KPI listesi.
        """
        kpi_ids = self._categories.get(
            category, [],
        )
        return [
            dict(self._kpis[kid])
            for kid in kpi_ids
            if kid in self._kpis
        ]

    def list_kpis(
        self,
    ) -> list[dict[str, Any]]:
        """Tum KPI'lari listeler.

        Returns:
            KPI listesi.
        """
        return [
            dict(kpi)
            for kpi in self._kpis.values()
        ]

    def remove_kpi(
        self,
        kpi_id: str,
    ) -> dict[str, Any]:
        """KPI kaldirir.

        Args:
            kpi_id: KPI ID.

        Returns:
            Kaldirma bilgisi.
        """
        if kpi_id not in self._kpis:
            return {"error": "kpi_not_found"}

        kpi = self._kpis.pop(kpi_id)
        cat = kpi.get("category", "")
        if cat in self._categories:
            self._categories[cat] = [
                k for k in self._categories[cat]
                if k != kpi_id
            ]

        return {
            "kpi_id": kpi_id,
            "removed": True,
        }

    @property
    def kpi_count(self) -> int:
        """KPI sayisi."""
        return len(self._kpis)

    @property
    def category_count(self) -> int:
        """Kategori sayisi."""
        return len(self._categories)
