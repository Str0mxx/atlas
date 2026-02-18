"""
Fine-tune model degerlendirici modulu.

Kalite degerlendirme, benchmark testi,
karsilastirma analizi, regresyon tespiti,
gecme/kalma kriterleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FTModelEvaluator:
    """Fine-tune model degerlendirici.

    Attributes:
        _evaluations: Degerlendirmeler.
        _benchmarks: Benchmark'lar.
        _stats: Istatistikler.
    """

    METRICS: list[str] = [
        "accuracy",
        "perplexity",
        "bleu",
        "rouge",
        "f1",
        "latency",
    ]

    def __init__(
        self,
        pass_threshold: float = 0.7,
        regression_tolerance: float = 0.05,
    ) -> None:
        """Degerlendiriciyi baslatir.

        Args:
            pass_threshold: Gecme esigi.
            regression_tolerance: Regresyon toleransi.
        """
        self._pass_threshold = (
            pass_threshold
        )
        self._regression_tolerance = (
            regression_tolerance
        )
        self._evaluations: dict[
            str, dict
        ] = {}
        self._benchmarks: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "evaluations_done": 0,
            "benchmarks_run": 0,
            "models_passed": 0,
            "models_failed": 0,
            "regressions_detected": 0,
        }
        logger.info(
            "FTModelEvaluator baslatildi"
        )

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return len(self._evaluations)

    def evaluate_model(
        self,
        model_id: str = "",
        test_dataset: list[dict]
        | None = None,
        metrics: list[str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Model degerlendirir.

        Args:
            model_id: Model ID.
            test_dataset: Test verisi.
            metrics: Metrik listesi.
            description: Aciklama.

        Returns:
            Degerlendirme bilgisi.
        """
        try:
            eid = f"eval_{uuid4()!s:.8}"
            items = test_dataset or []
            metric_list = (
                metrics or ["accuracy", "f1"]
            )

            # Metrik hesaplama
            results: dict[str, float] = {}
            for m in metric_list:
                if m == "accuracy":
                    correct = sum(
                        1
                        for t in items
                        if t.get("predicted")
                        == t.get("expected")
                    )
                    results[m] = (
                        correct / len(items)
                        if items
                        else 0.0
                    )
                elif m == "perplexity":
                    scores = [
                        t.get("score", 10.0)
                        for t in items
                    ]
                    results[m] = (
                        sum(scores)
                        / len(scores)
                        if scores
                        else 10.0
                    )
                elif m in (
                    "bleu",
                    "rouge",
                    "f1",
                ):
                    scores = [
                        t.get(m, 0.5)
                        for t in items
                    ]
                    results[m] = (
                        sum(scores)
                        / len(scores)
                        if scores
                        else 0.0
                    )
                elif m == "latency":
                    lats = [
                        t.get(
                            "latency_ms", 100
                        )
                        for t in items
                    ]
                    results[m] = (
                        sum(lats)
                        / len(lats)
                        if lats
                        else 100.0
                    )

            # Gecme/kalma
            quality_metrics = {
                k: v
                for k, v in results.items()
                if k != "latency"
                and k != "perplexity"
            }
            avg_quality = (
                sum(quality_metrics.values())
                / len(quality_metrics)
                if quality_metrics
                else 0.0
            )
            passed = (
                avg_quality
                >= self._pass_threshold
            )

            self._evaluations[eid] = {
                "eval_id": eid,
                "model_id": model_id,
                "test_size": len(items),
                "metrics": results,
                "avg_quality": round(
                    avg_quality, 4
                ),
                "passed": passed,
                "description": description,
                "evaluated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "evaluations_done"
            ] += 1
            if passed:
                self._stats[
                    "models_passed"
                ] += 1
            else:
                self._stats[
                    "models_failed"
                ] += 1

            return {
                "eval_id": eid,
                "model_id": model_id,
                "metrics": {
                    k: round(v, 4)
                    for k, v in (
                        results.items()
                    )
                },
                "avg_quality": round(
                    avg_quality, 4
                ),
                "passed": passed,
                "evaluated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "evaluated": False,
                "error": str(e),
            }

    def run_benchmark(
        self,
        model_id: str = "",
        benchmark_name: str = "",
        test_cases: list[dict]
        | None = None,
    ) -> dict[str, Any]:
        """Benchmark calistirir.

        Args:
            model_id: Model ID.
            benchmark_name: Benchmark adi.
            test_cases: Test vakalari.

        Returns:
            Benchmark bilgisi.
        """
        try:
            bid = f"bench_{uuid4()!s:.8}"
            cases = test_cases or []

            scores: list[float] = []
            latencies: list[float] = []
            for tc in cases:
                scores.append(
                    tc.get("score", 0.5)
                )
                latencies.append(
                    tc.get(
                        "latency_ms", 100
                    )
                )

            avg_score = (
                sum(scores) / len(scores)
                if scores
                else 0.0
            )
            avg_lat = (
                sum(latencies)
                / len(latencies)
                if latencies
                else 0.0
            )

            self._benchmarks[bid] = {
                "benchmark_id": bid,
                "model_id": model_id,
                "name": benchmark_name,
                "test_count": len(cases),
                "avg_score": round(
                    avg_score, 4
                ),
                "avg_latency": round(
                    avg_lat, 2
                ),
                "scores": scores,
                "run_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "benchmarks_run"
            ] += 1

            return {
                "benchmark_id": bid,
                "model_id": model_id,
                "name": benchmark_name,
                "avg_score": round(
                    avg_score, 4
                ),
                "avg_latency": round(
                    avg_lat, 2
                ),
                "test_count": len(cases),
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def compare_models(
        self,
        model_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Modelleri karsilastirir.

        Args:
            model_ids: Model ID listesi.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            ids = model_ids or []
            comparisons: list[dict] = []

            for mid in ids:
                evals = [
                    e
                    for e in (
                        self._evaluations
                        .values()
                    )
                    if e["model_id"] == mid
                ]
                if evals:
                    latest = evals[-1]
                    comparisons.append({
                        "model_id": mid,
                        "avg_quality": (
                            latest[
                                "avg_quality"
                            ]
                        ),
                        "passed": (
                            latest["passed"]
                        ),
                        "metrics": (
                            latest["metrics"]
                        ),
                    })

            # En iyi model
            best = None
            if comparisons:
                best = max(
                    comparisons,
                    key=lambda x: x[
                        "avg_quality"
                    ],
                )["model_id"]

            return {
                "models": comparisons,
                "best_model": best,
                "total_compared": len(
                    comparisons
                ),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def detect_regression(
        self,
        model_id: str = "",
        baseline_eval_id: str = "",
        new_eval_id: str = "",
    ) -> dict[str, Any]:
        """Regresyon tespit eder.

        Args:
            model_id: Model ID.
            baseline_eval_id: Temel eval ID.
            new_eval_id: Yeni eval ID.

        Returns:
            Regresyon bilgisi.
        """
        try:
            baseline = (
                self._evaluations.get(
                    baseline_eval_id
                )
            )
            new = self._evaluations.get(
                new_eval_id
            )

            if not baseline or not new:
                return {
                    "detected": False,
                    "error": (
                        "Degerlendirme "
                        "bulunamadi"
                    ),
                }

            regressions: list[dict] = []
            for metric in (
                baseline["metrics"]
            ):
                if metric not in (
                    new["metrics"]
                ):
                    continue

                base_val = baseline[
                    "metrics"
                ][metric]
                new_val = new["metrics"][
                    metric
                ]

                # Perplexity icin dusuk iyi
                if metric == "perplexity":
                    diff = (
                        new_val - base_val
                    )
                    regressed = diff > (
                        base_val
                        * self
                        ._regression_tolerance
                    )
                else:
                    diff = (
                        base_val - new_val
                    )
                    regressed = diff > (
                        base_val
                        * self
                        ._regression_tolerance
                    )

                if regressed:
                    regressions.append({
                        "metric": metric,
                        "baseline": round(
                            base_val, 4
                        ),
                        "current": round(
                            new_val, 4
                        ),
                        "diff": round(
                            abs(diff), 4
                        ),
                    })

            if regressions:
                self._stats[
                    "regressions_detected"
                ] += 1

            return {
                "model_id": model_id,
                "regressions": regressions,
                "regression_found": (
                    len(regressions) > 0
                ),
                "total_regressions": len(
                    regressions
                ),
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def get_eval_info(
        self,
        eval_id: str = "",
    ) -> dict[str, Any]:
        """Degerlendirme bilgisi getirir."""
        try:
            ev = self._evaluations.get(
                eval_id
            )
            if not ev:
                return {
                    "retrieved": False,
                    "error": (
                        "Degerlendirme "
                        "bulunamadi"
                    ),
                }
            return {
                **{
                    k: v
                    for k, v in ev.items()
                    if k != "description"
                },
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_evaluations": len(
                    self._evaluations
                ),
                "total_benchmarks": len(
                    self._benchmarks
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
