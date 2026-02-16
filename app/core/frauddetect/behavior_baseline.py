"""ATLAS Davranış Temeli modülü.

Normal davranış öğrenme, profil oluşturma,
sapma ölçümü, adaptif temel,
mevsimsel ayarlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BehaviorBaseline:
    """Davranış temeli.

    Normal davranış kalıplarını öğrenir.

    Attributes:
        _profiles: Profil kayıtları.
        _observations: Gözlem kayıtları.
    """

    def __init__(self) -> None:
        """Temeli başlatır."""
        self._profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._observations: dict[
            str, list[dict[str, float]]
        ] = {}
        self._counter = 0
        self._stats = {
            "profiles_built": 0,
            "deviations_measured": 0,
        }

        logger.info(
            "BehaviorBaseline baslatildi",
        )

    def learn_normal(
        self,
        entity: str,
        metrics: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Normal davranış öğrenir.

        Args:
            entity: Varlık.
            metrics: Metrikler.

        Returns:
            Öğrenme bilgisi.
        """
        metrics = metrics or {}
        if entity not in self._observations:
            self._observations[entity] = []
        self._observations[entity].append(
            metrics,
        )

        return {
            "entity": entity,
            "metrics": len(metrics),
            "observations": len(
                self._observations[entity],
            ),
            "learned": True,
        }

    def build_profile(
        self,
        entity: str,
    ) -> dict[str, Any]:
        """Profil oluşturur.

        Args:
            entity: Varlık.

        Returns:
            Profil bilgisi.
        """
        obs = self._observations.get(
            entity, [],
        )
        if len(obs) < 3:
            return {
                "entity": entity,
                "built": False,
                "reason": "Insufficient data",
            }

        # Her metrik için ortalama hesapla
        all_keys: set[str] = set()
        for o in obs:
            all_keys.update(o.keys())

        averages: dict[str, float] = {}
        for key in all_keys:
            vals = [
                o[key] for o in obs
                if key in o
            ]
            if vals:
                averages[key] = round(
                    sum(vals) / len(vals), 2,
                )

        self._profiles[entity] = {
            "entity": entity,
            "averages": averages,
            "observation_count": len(obs),
            "timestamp": time.time(),
        }
        self._stats[
            "profiles_built"
        ] += 1

        return {
            "entity": entity,
            "metrics": len(averages),
            "observations": len(obs),
            "built": True,
        }

    def measure_deviation(
        self,
        entity: str,
        current: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Sapma ölçer.

        Args:
            entity: Varlık.
            current: Mevcut metrikler.

        Returns:
            Sapma bilgisi.
        """
        profile = self._profiles.get(
            entity,
        )
        if not profile:
            return {
                "entity": entity,
                "measured": False,
            }

        current = current or {}
        avgs = profile["averages"]
        deviations = {}

        for key, val in current.items():
            baseline = avgs.get(key, 0)
            if baseline > 0:
                dev = round(
                    abs(val - baseline)
                    / baseline * 100,
                    1,
                )
                deviations[key] = dev

        max_dev = (
            max(deviations.values())
            if deviations
            else 0.0
        )
        is_anomalous = max_dev > 50

        self._stats[
            "deviations_measured"
        ] += 1

        return {
            "entity": entity,
            "deviations": deviations,
            "max_deviation": max_dev,
            "is_anomalous": is_anomalous,
            "measured": True,
        }

    def adapt_baseline(
        self,
        entity: str,
        new_metrics: dict[str, float]
        | None = None,
        weight: float = 0.1,
    ) -> dict[str, Any]:
        """Temel değeri adapte eder.

        Args:
            entity: Varlık.
            new_metrics: Yeni metrikler.
            weight: Ağırlık.

        Returns:
            Adaptasyon bilgisi.
        """
        profile = self._profiles.get(
            entity,
        )
        if not profile:
            return {
                "entity": entity,
                "adapted": False,
            }

        new_metrics = new_metrics or {}
        avgs = profile["averages"]
        updated = 0

        for key, val in (
            new_metrics.items()
        ):
            if key in avgs:
                avgs[key] = round(
                    avgs[key] * (1 - weight)
                    + val * weight,
                    2,
                )
                updated += 1

        return {
            "entity": entity,
            "metrics_updated": updated,
            "weight": weight,
            "adapted": updated > 0,
        }

    def adjust_seasonal(
        self,
        entity: str,
        season: str = "normal",
        factor: float = 1.0,
    ) -> dict[str, Any]:
        """Mevsimsel ayarlama yapar.

        Args:
            entity: Varlık.
            season: Mevsim.
            factor: Faktör.

        Returns:
            Ayarlama bilgisi.
        """
        profile = self._profiles.get(
            entity,
        )
        if not profile:
            return {
                "entity": entity,
                "adjusted": False,
            }

        avgs = profile["averages"]
        adjusted = 0
        for key in avgs:
            avgs[key] = round(
                avgs[key] * factor, 2,
            )
            adjusted += 1

        return {
            "entity": entity,
            "season": season,
            "factor": factor,
            "metrics_adjusted": adjusted,
            "adjusted": adjusted > 0,
        }

    @property
    def profile_count(self) -> int:
        """Profil sayısı."""
        return self._stats[
            "profiles_built"
        ]

    @property
    def deviation_count(self) -> int:
        """Sapma sayısı."""
        return self._stats[
            "deviations_measured"
        ]
