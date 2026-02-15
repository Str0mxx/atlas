"""ATLAS Deney Takibi modulu.

A/B deneyleri, hipotez testi,
istatistiksel anlamlilik, kazanan secimi, dagitim karari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ClosedLoopExperimentTracker:
    """Deney takipcisi.

    Kapali dongu deneylerini yonetir.

    Attributes:
        _experiments: Deney kayitlari.
        _results: Sonuc kayitlari.
    """

    def __init__(
        self,
        default_duration_hours: int = 24,
        significance_threshold: float = 0.05,
    ) -> None:
        """Deney takipcisini baslatir.

        Args:
            default_duration_hours: Varsayilan sure (saat).
            significance_threshold: Anlamlilik esigi.
        """
        self._experiments: dict[
            str, dict[str, Any]
        ] = {}
        self._results: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._default_duration = (
            default_duration_hours
        )
        self._significance_threshold = (
            significance_threshold
        )
        self._stats = {
            "created": 0,
            "completed": 0,
            "winners": 0,
        }

        logger.info(
            "ClosedLoopExperimentTracker baslatildi",
        )

    def create_experiment(
        self,
        experiment_id: str,
        hypothesis: str,
        variants: list[str],
        duration_hours: int | None = None,
    ) -> dict[str, Any]:
        """Deney olusturur.

        Args:
            experiment_id: Deney ID.
            hypothesis: Hipotez.
            variants: Varyantlar.
            duration_hours: Sure (saat).

        Returns:
            Deney bilgisi.
        """
        duration = (
            duration_hours or self._default_duration
        )

        experiment = {
            "experiment_id": experiment_id,
            "hypothesis": hypothesis,
            "variants": variants,
            "status": "running",
            "duration_hours": duration,
            "created_at": time.time(),
            "ends_at": (
                time.time() + duration * 3600
            ),
            "winner": None,
        }

        self._experiments[experiment_id] = experiment
        self._results[experiment_id] = []
        self._stats["created"] += 1

        return {
            "experiment_id": experiment_id,
            "status": "running",
            "variants": variants,
            "duration_hours": duration,
        }

    def record_result(
        self,
        experiment_id: str,
        variant: str,
        success: bool,
        value: float = 0.0,
    ) -> dict[str, Any]:
        """Deney sonucu kaydeder.

        Args:
            experiment_id: Deney ID.
            variant: Varyant.
            success: Basarili mi.
            value: Deger.

        Returns:
            Kayit bilgisi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        if exp["status"] != "running":
            return {"error": "experiment_not_running"}

        result = {
            "variant": variant,
            "success": success,
            "value": value,
            "timestamp": time.time(),
        }

        self._results[experiment_id].append(result)

        return {
            "experiment_id": experiment_id,
            "variant": variant,
            "recorded": True,
            "total_results": len(
                self._results[experiment_id],
            ),
        }

    def analyze_experiment(
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

        # Varyant bazli istatistikler
        variant_stats: dict[
            str, dict[str, Any]
        ] = {}
        for v in exp["variants"]:
            v_results = [
                r for r in results
                if r["variant"] == v
            ]
            total = len(v_results)
            successes = sum(
                1 for r in v_results if r["success"]
            )
            values = [
                r["value"] for r in v_results
            ]

            variant_stats[v] = {
                "total": total,
                "successes": successes,
                "success_rate": (
                    round(successes / total, 3)
                    if total > 0
                    else 0.0
                ),
                "avg_value": (
                    round(
                        sum(values) / len(values), 3,
                    )
                    if values
                    else 0.0
                ),
            }

        # Anlamlilik testi (basit)
        significance = self._check_significance(
            variant_stats,
        )

        return {
            "experiment_id": experiment_id,
            "variant_stats": variant_stats,
            "significant": significance[
                "significant"
            ],
            "p_value": significance["p_value"],
            "total_samples": len(results),
        }

    def select_winner(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Kazanan secer.

        Args:
            experiment_id: Deney ID.

        Returns:
            Kazanan bilgisi.
        """
        analysis = self.analyze_experiment(
            experiment_id,
        )
        if "error" in analysis:
            return analysis

        exp = self._experiments[experiment_id]
        stats = analysis["variant_stats"]

        if not stats:
            return {"error": "no_variant_data"}

        # En yuksek basari oranli varyant
        best_variant = max(
            stats.items(),
            key=lambda x: x[1]["success_rate"],
        )

        winner = best_variant[0]
        winner_stats = best_variant[1]

        exp["winner"] = winner
        exp["status"] = "completed"
        exp["completed_at"] = time.time()

        self._stats["completed"] += 1
        self._stats["winners"] += 1

        return {
            "experiment_id": experiment_id,
            "winner": winner,
            "success_rate": winner_stats[
                "success_rate"
            ],
            "significant": analysis["significant"],
            "status": "completed",
        }

    def get_rollout_decision(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Dagitim karari verir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Dagitim karari.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        if not exp.get("winner"):
            analysis = self.analyze_experiment(
                experiment_id,
            )
            if not analysis.get("significant"):
                return {
                    "experiment_id": experiment_id,
                    "decision": "continue",
                    "reason": "not_significant",
                }

            self.select_winner(experiment_id)
            exp = self._experiments[experiment_id]

        return {
            "experiment_id": experiment_id,
            "decision": "rollout",
            "winner": exp["winner"],
            "recommendation": (
                f"Deploy variant '{exp['winner']}'"
            ),
        }

    def pause_experiment(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Deneyi duraklatir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Duraklama bilgisi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        exp["status"] = "paused"

        return {
            "experiment_id": experiment_id,
            "status": "paused",
        }

    def resume_experiment(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Deneyi devam ettirir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Devam bilgisi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp:
            return {"error": "experiment_not_found"}

        exp["status"] = "running"

        return {
            "experiment_id": experiment_id,
            "status": "running",
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

    def list_experiments(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Deneyleri listeler.

        Args:
            status: Durum filtresi.

        Returns:
            Deney listesi.
        """
        exps = list(self._experiments.values())
        if status:
            exps = [
                e for e in exps
                if e["status"] == status
            ]
        return exps

    def _check_significance(
        self,
        variant_stats: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Istatistiksel anlamlilik kontrol eder.

        Args:
            variant_stats: Varyant istatistikleri.

        Returns:
            Anlamlilik bilgisi.
        """
        if len(variant_stats) < 2:
            return {
                "significant": False,
                "p_value": 1.0,
            }

        rates = [
            s["success_rate"]
            for s in variant_stats.values()
        ]
        totals = [
            s["total"]
            for s in variant_stats.values()
        ]

        # Minimum ornek boyutu
        if any(t < 10 for t in totals):
            return {
                "significant": False,
                "p_value": 1.0,
                "reason": "insufficient_samples",
            }

        # Basit fark esik kontrolu
        max_rate = max(rates)
        min_rate = min(rates)
        diff = max_rate - min_rate

        # Buyuk ornekleme = daha guclu sinyal
        avg_total = sum(totals) / len(totals)
        sample_factor = min(1.0, avg_total / 100.0)

        simulated_p = max(
            0.001,
            (1.0 - diff) * (1.0 - sample_factor),
        )

        return {
            "significant": (
                simulated_p
                < self._significance_threshold
            ),
            "p_value": round(simulated_p, 4),
            "effect_size": round(diff, 3),
        }

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
