"""ATLAS Ozellik Muhendisi modulu.

Ozellik cikarma, donusum,
polinom, etkilesim ve
zaman temelli ozellikler.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Ozellik muhendisi.

    Veri ozelliklerini uretir ve donusturur.

    Attributes:
        _transformations: Donusumler.
        _generated: Uretilen ozellikler.
    """

    def __init__(self) -> None:
        """Muhendisi baslatir."""
        self._transformations: dict[
            str, dict[str, Any]
        ] = {}
        self._generated_features: dict[
            str, list[float]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "FeatureEngineer baslatildi",
        )

    def extract_statistical(
        self,
        name: str,
        values: list[float],
    ) -> dict[str, float]:
        """Istatistiksel ozellikler cikarir.

        Args:
            name: Ozellik adi.
            values: Degerler.

        Returns:
            Istatistik ozellikleri.
        """
        if not values:
            return {}

        n = len(values)
        mean = sum(values) / n
        sorted_v = sorted(values)
        median = sorted_v[n // 2]
        variance = sum(
            (v - mean) ** 2 for v in values
        ) / n
        std = math.sqrt(variance)

        features = {
            f"{name}_mean": mean,
            f"{name}_median": median,
            f"{name}_std": std,
            f"{name}_min": min(values),
            f"{name}_max": max(values),
            f"{name}_range": max(values) - min(values),
        }

        for k, v in features.items():
            self._generated_features[k] = [v]

        self._history.append({
            "action": "extract_statistical",
            "source": name,
            "features": len(features),
            "timestamp": time.time(),
        })

        return features

    def polynomial_features(
        self,
        name: str,
        values: list[float],
        degree: int = 2,
    ) -> dict[str, list[float]]:
        """Polinom ozellikler uretir.

        Args:
            name: Ozellik adi.
            values: Degerler.
            degree: Derece.

        Returns:
            Polinom ozellikleri.
        """
        result: dict[str, list[float]] = {}

        for d in range(2, degree + 1):
            key = f"{name}_pow{d}"
            result[key] = [v ** d for v in values]
            self._generated_features[key] = (
                result[key]
            )

        self._transformations[name] = {
            "type": "polynomial",
            "degree": degree,
        }

        self._history.append({
            "action": "polynomial_features",
            "source": name,
            "degree": degree,
            "timestamp": time.time(),
        })

        return result

    def interaction_features(
        self,
        name_a: str,
        values_a: list[float],
        name_b: str,
        values_b: list[float],
    ) -> dict[str, list[float]]:
        """Etkilesim ozellikleri uretir.

        Args:
            name_a: Birinci ozellik adi.
            values_a: Birinci degerler.
            name_b: Ikinci ozellik adi.
            values_b: Ikinci degerler.

        Returns:
            Etkilesim ozellikleri.
        """
        n = min(len(values_a), len(values_b))
        result: dict[str, list[float]] = {}

        # Carpim
        mul_key = f"{name_a}_x_{name_b}"
        result[mul_key] = [
            values_a[i] * values_b[i]
            for i in range(n)
        ]

        # Toplam
        add_key = f"{name_a}_plus_{name_b}"
        result[add_key] = [
            values_a[i] + values_b[i]
            for i in range(n)
        ]

        # Oran
        ratio_key = f"{name_a}_div_{name_b}"
        result[ratio_key] = [
            (
                values_a[i] / values_b[i]
                if values_b[i] != 0
                else 0.0
            )
            for i in range(n)
        ]

        for k, v in result.items():
            self._generated_features[k] = v

        self._history.append({
            "action": "interaction_features",
            "sources": [name_a, name_b],
            "features": len(result),
            "timestamp": time.time(),
        })

        return result

    def time_features(
        self,
        name: str,
        timestamps: list[float],
    ) -> dict[str, list[float]]:
        """Zaman temelli ozellikler uretir.

        Args:
            name: Ozellik adi.
            timestamps: Unix zaman damgalari.

        Returns:
            Zaman ozellikleri.
        """
        if not timestamps:
            return {}

        result: dict[str, list[float]] = {}

        # Farklar (delta)
        deltas = [0.0]
        for i in range(1, len(timestamps)):
            deltas.append(
                timestamps[i] - timestamps[i - 1],
            )
        result[f"{name}_delta"] = deltas

        # Hareketli ortalama (window=3)
        window = min(3, len(timestamps))
        moving_avg: list[float] = []
        for i in range(len(timestamps)):
            start = max(0, i - window + 1)
            chunk = timestamps[start:i + 1]
            moving_avg.append(
                sum(chunk) / len(chunk),
            )
        result[f"{name}_ma"] = moving_avg

        # Kumulatif toplam
        cumsum: list[float] = []
        total = 0.0
        for v in timestamps:
            total += v
            cumsum.append(total)
        result[f"{name}_cumsum"] = cumsum

        for k, v in result.items():
            self._generated_features[k] = v

        self._history.append({
            "action": "time_features",
            "source": name,
            "features": len(result),
            "timestamp": time.time(),
        })

        return result

    def apply_transform(
        self,
        name: str,
        values: list[float],
        transform: str = "log",
    ) -> list[float]:
        """Donusum uygular.

        Args:
            name: Ozellik adi.
            values: Degerler.
            transform: Donusum tipi.

        Returns:
            Donusturulmus degerler.
        """
        if transform == "log":
            offset = (
                abs(min(values)) + 1
                if values and min(values) <= 0
                else 0
            )
            result = [
                math.log(v + offset + 1)
                for v in values
            ]
        elif transform == "sqrt":
            result = [
                math.sqrt(abs(v)) for v in values
            ]
        elif transform == "square":
            result = [v ** 2 for v in values]
        elif transform == "reciprocal":
            result = [
                1 / v if v != 0 else 0.0
                for v in values
            ]
        elif transform == "abs":
            result = [abs(v) for v in values]
        else:
            result = list(values)

        key = f"{name}_{transform}"
        self._generated_features[key] = result
        self._transformations[name] = {
            "type": transform,
        }

        return result

    def get_generated(self) -> dict[
        str, list[float]
    ]:
        """Uretilen ozellikleri getirir.

        Returns:
            Ozellik-deger eslesmesi.
        """
        return dict(self._generated_features)

    def get_feature(
        self,
        name: str,
    ) -> list[float] | None:
        """Ozellik degerlerini getirir.

        Args:
            name: Ozellik adi.

        Returns:
            Degerler veya None.
        """
        return self._generated_features.get(name)

    @property
    def feature_count(self) -> int:
        """Uretilen ozellik sayisi."""
        return len(self._generated_features)

    @property
    def transformation_count(self) -> int:
        """Donusum sayisi."""
        return len(self._transformations)

    @property
    def history_count(self) -> int:
        """Islem gecmisi sayisi."""
        return len(self._history)
