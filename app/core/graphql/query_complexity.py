"""ATLAS Sorgu Karmasikligi modulu.

Karmasiklik hesabi, derinlik siniri,
maliyet analizi, hiz siniri
ve reddetme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QueryComplexity:
    """Sorgu karmasikligi analizcisi.

    Sorgu maliyetini ve karmasikligini olcer.

    Attributes:
        _field_costs: Alan maliyetleri.
        _limits: Sinirlar.
    """

    def __init__(
        self,
        max_depth: int = 10,
        max_complexity: int = 1000,
    ) -> None:
        """Analizcisi baslatir.

        Args:
            max_depth: Maks derinlik.
            max_complexity: Maks karmasiklik.
        """
        self._max_depth = max_depth
        self._max_complexity = max_complexity
        self._field_costs: dict[
            str, int
        ] = {}
        self._type_costs: dict[
            str, int
        ] = {}
        self._rate_limits: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "analyzed": 0,
            "rejected": 0,
            "rate_limited": 0,
        }

        logger.info(
            "QueryComplexity baslatildi: "
            "max_depth=%d, max_complexity=%d",
            max_depth, max_complexity,
        )

    def set_field_cost(
        self,
        field: str,
        cost: int,
    ) -> None:
        """Alan maliyeti ayarlar.

        Args:
            field: Alan adi.
            cost: Maliyet.
        """
        self._field_costs[field] = cost

    def set_type_cost(
        self,
        type_name: str,
        cost: int,
    ) -> None:
        """Tip maliyeti ayarlar.

        Args:
            type_name: Tip adi.
            cost: Maliyet.
        """
        self._type_costs[type_name] = cost

    def analyze(
        self,
        fields: list[str],
        depth: int,
        multipliers: dict[str, int]
            | None = None,
    ) -> dict[str, Any]:
        """Sorgu karmasikligini analiz eder.

        Args:
            fields: Sorgu alanlari.
            depth: Derinlik.
            multipliers: Carpanlar.

        Returns:
            Analiz sonucu.
        """
        self._stats["analyzed"] += 1

        # Maliyet hesapla
        total_cost = 0
        field_breakdown: dict[str, int] = {}

        for field in fields:
            base_cost = self._field_costs.get(
                field, 1,
            )
            mult = 1
            if multipliers:
                mult = multipliers.get(field, 1)
            cost = base_cost * mult
            field_breakdown[field] = cost
            total_cost += cost

        # Derinlik carpani
        depth_factor = max(1, depth)
        total_cost *= depth_factor

        # Seviye
        if total_cost > self._max_complexity:
            level = "blocked"
        elif total_cost > self._max_complexity * 0.8:
            level = "critical"
        elif total_cost > self._max_complexity * 0.5:
            level = "high"
        elif total_cost > self._max_complexity * 0.2:
            level = "medium"
        else:
            level = "low"

        allowed = (
            total_cost <= self._max_complexity
            and depth <= self._max_depth
        )

        if not allowed:
            self._stats["rejected"] += 1

        result = {
            "complexity": total_cost,
            "depth": depth,
            "max_complexity": self._max_complexity,
            "max_depth": self._max_depth,
            "level": level,
            "allowed": allowed,
            "field_costs": field_breakdown,
            "depth_exceeded": (
                depth > self._max_depth
            ),
            "complexity_exceeded": (
                total_cost > self._max_complexity
            ),
        }

        self._history.append({
            **result,
            "timestamp": time.time(),
        })

        return result

    def set_rate_limit(
        self,
        client_id: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> dict[str, Any]:
        """Hiz siniri ayarlar.

        Args:
            client_id: Istemci ID.
            max_requests: Maks istek.
            window_seconds: Pencere suresi.

        Returns:
            Limit bilgisi.
        """
        self._rate_limits[client_id] = {
            "max_requests": max_requests,
            "window": window_seconds,
            "current": 0,
            "last_reset": time.time(),
        }

        return {
            "client_id": client_id,
            "max_requests": max_requests,
        }

    def check_rate_limit(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """Hiz sinirini kontrol eder.

        Args:
            client_id: Istemci ID.

        Returns:
            Kontrol sonucu.
        """
        limit = self._rate_limits.get(client_id)
        if not limit:
            return {"allowed": True, "limited": False}

        now = time.time()
        if now - limit["last_reset"] >= limit[
            "window"
        ]:
            limit["current"] = 0
            limit["last_reset"] = now

        limit["current"] += 1
        allowed = (
            limit["current"]
            <= limit["max_requests"]
        )

        if not allowed:
            self._stats["rate_limited"] += 1

        return {
            "allowed": allowed,
            "limited": not allowed,
            "current": limit["current"],
            "max": limit["max_requests"],
            "remaining": max(
                0,
                limit["max_requests"]
                - limit["current"],
            ),
        }

    def get_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Analiz gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        return self._history[-limit:]

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def max_depth(self) -> int:
        """Maks derinlik."""
        return self._max_depth

    @property
    def max_complexity(self) -> int:
        """Maks karmasiklik."""
        return self._max_complexity

    @property
    def analyzed_count(self) -> int:
        """Analiz sayisi."""
        return self._stats["analyzed"]

    @property
    def rejected_count(self) -> int:
        """Reddedilen sayisi."""
        return self._stats["rejected"]

    @property
    def field_cost_count(self) -> int:
        """Alan maliyet sayisi."""
        return len(self._field_costs)

    @property
    def rate_limit_count(self) -> int:
        """Hiz siniri sayisi."""
        return len(self._rate_limits)
