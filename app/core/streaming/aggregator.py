"""ATLAS Akis Toplayici modulu.

Sum/avg/min/max, sayac,
yuzdelikler, ozel toplamalar
ve artimsal guncellemeler.
"""

import logging
import math
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StreamAggregator:
    """Akis toplayici.

    Akis verilerini toplar ve ozetler.

    Attributes:
        _aggregations: Toplamalar.
        _custom_fns: Ozel fonksiyonlar.
    """

    def __init__(self) -> None:
        """Toplayiciyi baslatir."""
        self._aggregations: dict[
            str, dict[str, Any]
        ] = {}
        self._custom_fns: dict[
            str, Callable[[list[Any]], Any]
        ] = {}
        self._distinct_sets: dict[
            str, set[Any]
        ] = {}

        logger.info(
            "StreamAggregator baslatildi",
        )

    def create(
        self,
        name: str,
        agg_type: str = "sum",
    ) -> dict[str, Any]:
        """Toplama olusturur.

        Args:
            name: Toplama adi.
            agg_type: Tip (sum/avg/min/max/count).

        Returns:
            Olusturma bilgisi.
        """
        self._aggregations[name] = {
            "type": agg_type,
            "value": 0.0,
            "count": 0,
            "values": [],
            "sum": 0.0,
            "min": float("inf"),
            "max": float("-inf"),
            "created_at": time.time(),
        }

        return {"name": name, "type": agg_type}

    def update(
        self,
        name: str,
        value: float,
    ) -> dict[str, Any]:
        """Toplamaya deger ekler.

        Args:
            name: Toplama adi.
            value: Deger.

        Returns:
            Guncelleme sonucu.
        """
        agg = self._aggregations.get(name)
        if not agg:
            return {"error": "not_found"}

        agg["count"] += 1
        agg["sum"] += value
        agg["values"].append(value)
        agg["min"] = min(agg["min"], value)
        agg["max"] = max(agg["max"], value)

        # Tip bazli deger
        if agg["type"] == "sum":
            agg["value"] = agg["sum"]
        elif agg["type"] == "avg":
            agg["value"] = (
                agg["sum"] / agg["count"]
            )
        elif agg["type"] == "min":
            agg["value"] = agg["min"]
        elif agg["type"] == "max":
            agg["value"] = agg["max"]
        elif agg["type"] == "count":
            agg["value"] = agg["count"]

        return {
            "name": name,
            "value": agg["value"],
            "count": agg["count"],
        }

    def update_batch(
        self,
        name: str,
        values: list[float],
    ) -> dict[str, Any]:
        """Toplu guncelleme yapar.

        Args:
            name: Toplama adi.
            values: Degerler.

        Returns:
            Guncelleme sonucu.
        """
        result: dict[str, Any] = {}
        for v in values:
            result = self.update(name, v)
        return result

    def get_value(
        self,
        name: str,
    ) -> float | None:
        """Toplama degerini getirir.

        Args:
            name: Toplama adi.

        Returns:
            Deger veya None.
        """
        agg = self._aggregations.get(name)
        if not agg:
            return None
        return agg["value"]

    def get_summary(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Ozet getirir.

        Args:
            name: Toplama adi.

        Returns:
            Ozet bilgisi veya None.
        """
        agg = self._aggregations.get(name)
        if not agg:
            return None

        return {
            "name": name,
            "type": agg["type"],
            "value": agg["value"],
            "count": agg["count"],
            "sum": agg["sum"],
            "min": (
                agg["min"]
                if agg["min"] != float("inf")
                else None
            ),
            "max": (
                agg["max"]
                if agg["max"] != float("-inf")
                else None
            ),
            "avg": (
                agg["sum"] / agg["count"]
                if agg["count"] > 0 else 0.0
            ),
        }

    def percentile(
        self,
        name: str,
        p: float,
    ) -> float | None:
        """Yuzdelik hesaplar.

        Args:
            name: Toplama adi.
            p: Yuzdelik (0-100).

        Returns:
            Yuzdelik degeri veya None.
        """
        agg = self._aggregations.get(name)
        if not agg or not agg["values"]:
            return None

        sorted_vals = sorted(agg["values"])
        n = len(sorted_vals)
        idx = (p / 100) * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        frac = idx - lower

        return (
            sorted_vals[lower] * (1 - frac)
            + sorted_vals[upper] * frac
        )

    def count_distinct(
        self,
        name: str,
        value: Any,
    ) -> int:
        """Benzersiz deger sayar.

        Args:
            name: Sayac adi.
            value: Deger.

        Returns:
            Benzersiz sayi.
        """
        if name not in self._distinct_sets:
            self._distinct_sets[name] = set()
        self._distinct_sets[name].add(value)
        return len(self._distinct_sets[name])

    def get_distinct_count(
        self,
        name: str,
    ) -> int:
        """Benzersiz sayiyi getirir.

        Args:
            name: Sayac adi.

        Returns:
            Benzersiz sayi.
        """
        return len(
            self._distinct_sets.get(name, set()),
        )

    def register_custom(
        self,
        name: str,
        fn: Callable[[list[Any]], Any],
    ) -> dict[str, Any]:
        """Ozel toplama kaydeder.

        Args:
            name: Toplama adi.
            fn: Toplama fonksiyonu.

        Returns:
            Kayit bilgisi.
        """
        self._custom_fns[name] = fn
        self.create(name, "custom")
        return {"name": name, "type": "custom"}

    def apply_custom(
        self,
        name: str,
    ) -> Any:
        """Ozel toplamayi uygular.

        Args:
            name: Toplama adi.

        Returns:
            Sonuc.
        """
        fn = self._custom_fns.get(name)
        agg = self._aggregations.get(name)
        if not fn or not agg:
            return None

        result = fn(agg["values"])
        agg["value"] = result
        return result

    def reset(self, name: str) -> bool:
        """Toplamayi sifirlar.

        Args:
            name: Toplama adi.

        Returns:
            Basarili mi.
        """
        agg = self._aggregations.get(name)
        if not agg:
            return False

        agg["value"] = 0.0
        agg["count"] = 0
        agg["values"] = []
        agg["sum"] = 0.0
        agg["min"] = float("inf")
        agg["max"] = float("-inf")
        return True

    @property
    def aggregation_count(self) -> int:
        """Toplama sayisi."""
        return len(self._aggregations)

    @property
    def distinct_count(self) -> int:
        """Benzersiz sayac sayisi."""
        return len(self._distinct_sets)

    @property
    def custom_count(self) -> int:
        """Ozel toplama sayisi."""
        return len(self._custom_fns)
