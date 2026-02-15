"""ATLAS Veri On Isleyici modulu.

Feature scaling, normalization,
eksik deger yonetimi, kodlama
ve ozellik secimi.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Veri on isleyici.

    Veriyi model egitimi icin hazirlar.

    Attributes:
        _scalers: Olcekleyiciler.
        _encoders: Kodlayicilar.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """On isleyiciyi baslatir."""
        self._scalers: dict[
            str, dict[str, Any]
        ] = {}
        self._encoders: dict[
            str, dict[str, Any]
        ] = {}
        self._imputers: dict[
            str, dict[str, Any]
        ] = {}
        self._feature_stats: dict[
            str, dict[str, Any]
        ] = {}
        self._selected_features: list[str] = []
        self._history: list[
            dict[str, Any]
        ] = []

        logger.info(
            "DataPreprocessor baslatildi",
        )

    def fit_scaler(
        self,
        feature: str,
        values: list[float],
        method: str = "standard",
    ) -> dict[str, Any]:
        """Olcekleyici egitir.

        Args:
            feature: Ozellik adi.
            values: Degerler.
            method: Yontem.

        Returns:
            Olcekleyici bilgisi.
        """
        if not values:
            return {"feature": feature, "error": "empty"}

        stats: dict[str, Any] = {
            "method": method,
            "count": len(values),
        }

        if method == "standard":
            mean = sum(values) / len(values)
            variance = sum(
                (v - mean) ** 2 for v in values
            ) / len(values)
            std = math.sqrt(variance) if variance > 0 else 1.0
            stats["mean"] = mean
            stats["std"] = std
        elif method == "minmax":
            mn, mx = min(values), max(values)
            stats["min"] = mn
            stats["max"] = mx
        elif method == "robust":
            sorted_v = sorted(values)
            n = len(sorted_v)
            q1 = sorted_v[n // 4]
            q3 = sorted_v[3 * n // 4]
            median = sorted_v[n // 2]
            iqr = q3 - q1 if q3 != q1 else 1.0
            stats["median"] = median
            stats["iqr"] = iqr
        elif method == "maxabs":
            ma = max(abs(v) for v in values)
            stats["max_abs"] = ma if ma > 0 else 1.0
        elif method == "log":
            stats["offset"] = abs(min(values)) + 1 if min(values) <= 0 else 0

        self._scalers[feature] = stats
        self._feature_stats[feature] = {
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "count": len(values),
        }

        return {
            "feature": feature,
            "method": method,
            "samples": len(values),
        }

    def transform(
        self,
        feature: str,
        values: list[float],
    ) -> list[float]:
        """Degerleri donusturur.

        Args:
            feature: Ozellik adi.
            values: Degerler.

        Returns:
            Donusturulmus degerler.
        """
        scaler = self._scalers.get(feature)
        if not scaler:
            return list(values)

        method = scaler["method"]

        if method == "standard":
            mean = scaler["mean"]
            std = scaler["std"]
            return [
                (v - mean) / std for v in values
            ]
        elif method == "minmax":
            mn = scaler["min"]
            mx = scaler["max"]
            rng = mx - mn if mx != mn else 1.0
            return [
                (v - mn) / rng for v in values
            ]
        elif method == "robust":
            median = scaler["median"]
            iqr = scaler["iqr"]
            return [
                (v - median) / iqr for v in values
            ]
        elif method == "maxabs":
            ma = scaler["max_abs"]
            return [v / ma for v in values]
        elif method == "log":
            offset = scaler["offset"]
            return [
                math.log(v + offset + 1)
                for v in values
            ]

        return list(values)

    def handle_missing(
        self,
        feature: str,
        values: list[float | None],
        strategy: str = "mean",
    ) -> list[float]:
        """Eksik degerleri yonetir.

        Args:
            feature: Ozellik adi.
            values: Degerler (None olabilir).
            strategy: Strateji (mean/median/zero/drop).

        Returns:
            Doldurulmus degerler.
        """
        valid = [
            v for v in values if v is not None
        ]

        if not valid:
            return [0.0] * len(values)

        if strategy == "mean":
            fill = sum(valid) / len(valid)
        elif strategy == "median":
            s = sorted(valid)
            fill = s[len(s) // 2]
        elif strategy == "zero":
            fill = 0.0
        elif strategy == "drop":
            return valid
        else:
            fill = 0.0

        self._imputers[feature] = {
            "strategy": strategy,
            "fill_value": fill,
            "missing_count": len(values) - len(valid),
        }

        return [
            v if v is not None else fill
            for v in values
        ]

    def encode_categorical(
        self,
        feature: str,
        values: list[str],
        method: str = "label",
    ) -> list[int | list[int]]:
        """Kategorik verileri kodlar.

        Args:
            feature: Ozellik adi.
            values: Kategorik degerler.
            method: Kodlama yontemi.

        Returns:
            Kodlanmis degerler.
        """
        unique = sorted(set(values))
        mapping = {
            v: i for i, v in enumerate(unique)
        }

        self._encoders[feature] = {
            "method": method,
            "mapping": mapping,
            "categories": unique,
        }

        if method == "label":
            return [mapping[v] for v in values]
        elif method == "onehot":
            result: list[int | list[int]] = []
            for v in values:
                vec = [0] * len(unique)
                vec[mapping[v]] = 1
                result.append(vec)
            return result

        return [mapping.get(v, -1) for v in values]

    def select_features(
        self,
        features: dict[str, list[float]],
        target: list[float],
        top_k: int = 5,
    ) -> list[str]:
        """Ozellik secer.

        Args:
            features: Ozellik-deger eslemesi.
            target: Hedef degisken.
            top_k: Secilecek ozellik sayisi.

        Returns:
            Secilen ozellikler.
        """
        scores: dict[str, float] = {}

        for fname, fvalues in features.items():
            if len(fvalues) != len(target):
                continue
            # Basit korelasyon skoru
            n = len(fvalues)
            if n == 0:
                continue
            mean_f = sum(fvalues) / n
            mean_t = sum(target) / n
            cov = sum(
                (f - mean_f) * (t - mean_t)
                for f, t in zip(fvalues, target)
            ) / n
            std_f = math.sqrt(
                sum((f - mean_f) ** 2 for f in fvalues) / n
            )
            std_t = math.sqrt(
                sum((t - mean_t) ** 2 for t in target) / n
            )
            denom = std_f * std_t
            corr = abs(cov / denom) if denom > 0 else 0.0
            scores[fname] = corr

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        self._selected_features = [
            f for f, _ in ranked[:top_k]
        ]

        self._history.append({
            "action": "feature_selection",
            "selected": list(self._selected_features),
            "scores": scores,
            "timestamp": time.time(),
        })

        return list(self._selected_features)

    def get_stats(
        self,
        feature: str,
    ) -> dict[str, Any] | None:
        """Ozellik istatistiklerini getirir.

        Args:
            feature: Ozellik adi.

        Returns:
            Istatistikler veya None.
        """
        return self._feature_stats.get(feature)

    @property
    def scaler_count(self) -> int:
        """Olcekleyici sayisi."""
        return len(self._scalers)

    @property
    def encoder_count(self) -> int:
        """Kodlayici sayisi."""
        return len(self._encoders)

    @property
    def selected_features(self) -> list[str]:
        """Secilen ozellikler."""
        return list(self._selected_features)

    @property
    def history_count(self) -> int:
        """Islem gecmisi sayisi."""
        return len(self._history)
