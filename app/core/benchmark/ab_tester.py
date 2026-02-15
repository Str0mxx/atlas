"""ATLAS A/B Test Motoru modulu.

Deney kurulumu, trafik bolumleme,
istatistiksel analiz, kazanan belirleme, dagitim onerisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ABTester:
    """A/B test motoru.

    Benchmark A/B testleri yonetir.

    Attributes:
        _experiments: Deney kayitlari.
        _results: Sonuc kayitlari.
    """

    def __init__(
        self,
        min_samples: int = 30,
        significance_level: float = 0.05,
    ) -> None:
        """A/B test motorunu baslatir.

        Args:
            min_samples: Minimum ornek sayisi.
            significance_level: Anlamlilik seviyesi.
        """
        self._experiments: dict[
            str, dict[str, Any]
        ] = {}
        self._results: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._min_samples = min_samples
        self._significance_level = (
            significance_level
        )
        self._stats = {
            "created": 0,
            "completed": 0,
        }

        logger.info(
            "ABTester baslatildi",
        )

    def create_experiment(
        self,
        experiment_id: str,
        name: str,
        variants: list[str],
        kpi_id: str = "",
        traffic_split: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Deney olusturur.

        Args:
            experiment_id: Deney ID.
            name: Deney adi.
            variants: Varyantlar.
            kpi_id: Olculecek KPI.
            traffic_split: Trafik dagilimi.

        Returns:
            Deney bilgisi.
        """
        split = traffic_split
        if not split:
            share = round(1.0 / len(variants), 2)
            split = {v: share for v in variants}

        self._experiments[experiment_id] = {
            "experiment_id": experiment_id,
            "name": name,
            "variants": variants,
            "kpi_id": kpi_id,
            "traffic_split": split,
            "status": "running",
            "winner": None,
            "created_at": time.time(),
        }
        self._results[experiment_id] = []
        self._stats["created"] += 1

        return {
            "experiment_id": experiment_id,
            "status": "running",
            "variants": variants,
        }

    def record_observation(
        self,
        experiment_id: str,
        variant: str,
        value: float,
        success: bool = True,
    ) -> dict[str, Any]:
        """Gozlem kaydeder.

        Args:
            experiment_id: Deney ID.
            variant: Varyant.
            value: Deger.
            success: Basarili mi.

        Returns:
            Kayit bilgisi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        if exp["status"] != "running":
            return {"error": "experiment_not_running"}

        self._results[experiment_id].append({
            "variant": variant,
            "value": value,
            "success": success,
            "timestamp": time.time(),
        })

        return {
            "experiment_id": experiment_id,
            "variant": variant,
            "recorded": True,
        }

    def analyze(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Deney analiz eder.

        Args:
            experiment_id: Deney ID.

        Returns:
            Analiz sonucu.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        results = self._results.get(
            experiment_id, [],
        )

        variant_stats: dict[
            str, dict[str, Any]
        ] = {}
        for v in exp["variants"]:
            v_results = [
                r for r in results
                if r["variant"] == v
            ]
            values = [r["value"] for r in v_results]
            successes = sum(
                1 for r in v_results if r["success"]
            )
            total = len(v_results)

            variant_stats[v] = {
                "count": total,
                "success_rate": (
                    round(successes / total, 4)
                    if total > 0
                    else 0.0
                ),
                "avg_value": (
                    round(
                        sum(values) / len(values), 4,
                    )
                    if values
                    else 0.0
                ),
            }

        significant = self._check_significance(
            variant_stats,
        )

        return {
            "experiment_id": experiment_id,
            "variant_stats": variant_stats,
            "significant": significant,
            "total_observations": len(results),
            "sufficient_data": all(
                s["count"] >= self._min_samples
                for s in variant_stats.values()
            ),
        }

    def determine_winner(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Kazanan belirler.

        Args:
            experiment_id: Deney ID.

        Returns:
            Kazanan bilgisi.
        """
        analysis = self.analyze(experiment_id)
        if "error" in analysis:
            return analysis

        stats = analysis["variant_stats"]
        if not stats:
            return {"error": "no_data"}

        best = max(
            stats.items(),
            key=lambda x: x[1]["success_rate"],
        )
        winner = best[0]

        exp = self._experiments[experiment_id]
        exp["winner"] = winner
        exp["status"] = "completed"
        self._stats["completed"] += 1

        return {
            "experiment_id": experiment_id,
            "winner": winner,
            "success_rate": best[1]["success_rate"],
            "significant": analysis["significant"],
        }

    def get_rollout_recommendation(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Dagitim onerisi verir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Dagitim onerisi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        if exp.get("winner"):
            return {
                "experiment_id": experiment_id,
                "recommendation": "rollout",
                "variant": exp["winner"],
            }

        analysis = self.analyze(experiment_id)
        if not analysis.get("sufficient_data"):
            return {
                "experiment_id": experiment_id,
                "recommendation": "continue",
                "reason": "insufficient_data",
            }

        if not analysis.get("significant"):
            return {
                "experiment_id": experiment_id,
                "recommendation": "continue",
                "reason": "not_significant",
            }

        result = self.determine_winner(
            experiment_id,
        )
        return {
            "experiment_id": experiment_id,
            "recommendation": "rollout",
            "variant": result.get("winner"),
        }

    def get_experiment(
        self,
        experiment_id: str,
    ) -> dict[str, Any] | None:
        """Deneyi getirir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Deney verisi veya None.
        """
        exp = self._experiments.get(experiment_id)
        if exp:
            return dict(exp)
        return None

    def _check_significance(
        self,
        variant_stats: dict[str, dict[str, Any]],
    ) -> bool:
        """Anlamlilik kontrol eder.

        Args:
            variant_stats: Varyant istatistikleri.

        Returns:
            Anlamli mi.
        """
        if len(variant_stats) < 2:
            return False

        counts = [
            s["count"] for s in variant_stats.values()
        ]
        if any(c < self._min_samples for c in counts):
            return False

        rates = [
            s["success_rate"]
            for s in variant_stats.values()
        ]
        diff = max(rates) - min(rates)

        avg_count = sum(counts) / len(counts)
        factor = min(1.0, avg_count / 100.0)

        return diff * factor > 0.1

    @property
    def experiment_count(self) -> int:
        """Deney sayisi."""
        return len(self._experiments)

    @property
    def active_count(self) -> int:
        """Aktif deney sayisi."""
        return sum(
            1
            for e in self._experiments.values()
            if e["status"] == "running"
        )
