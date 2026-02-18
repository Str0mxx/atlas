"""
Fine-tune performans benchmark modulu.

Benchmark suitleri, metrik hesaplama,
baseline karsilastirma, rapor uretimi,
trend analizi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FTPerformanceBenchmarker:
    """Fine-tune performans benchmarker.

    Attributes:
        _suites: Benchmark suitleri.
        _results: Sonuclar.
        _baselines: Baseline'lar.
        _stats: Istatistikler.
    """

    METRIC_TYPES: list[str] = [
        "accuracy",
        "latency",
        "throughput",
        "cost",
        "quality",
        "consistency",
    ]

    def __init__(self) -> None:
        """Benchmarker'i baslatir."""
        self._suites: dict[
            str, dict
        ] = {}
        self._results: dict[
            str, dict
        ] = {}
        self._baselines: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "suites_created": 0,
            "benchmarks_run": 0,
            "baselines_set": 0,
            "reports_generated": 0,
        }
        logger.info(
            "FTPerformanceBenchmarker "
            "baslatildi"
        )

    @property
    def suite_count(self) -> int:
        """Suite sayisi."""
        return len(self._suites)

    def create_suite(
        self,
        name: str = "",
        metrics: list[str] | None = None,
        test_cases: list[dict]
        | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Benchmark suite olusturur.

        Args:
            name: Suite adi.
            metrics: Metrik listesi.
            test_cases: Test vakalari.
            description: Aciklama.

        Returns:
            Suite bilgisi.
        """
        try:
            sid = f"bsuite_{uuid4()!s:.8}"

            self._suites[sid] = {
                "suite_id": sid,
                "name": name,
                "metrics": (
                    metrics
                    or [
                        "accuracy",
                        "latency",
                    ]
                ),
                "test_cases": (
                    test_cases or []
                ),
                "description": description,
                "run_count": 0,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "suites_created"
            ] += 1

            return {
                "suite_id": sid,
                "name": name,
                "test_count": len(
                    test_cases or []
                ),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def run_benchmark(
        self,
        suite_id: str = "",
        model_id: str = "",
        results: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Benchmark calistirir.

        Args:
            suite_id: Suite ID.
            model_id: Model ID.
            results: Test sonuclari.

        Returns:
            Benchmark bilgisi.
        """
        try:
            suite = self._suites.get(
                suite_id
            )
            if not suite:
                return {
                    "completed": False,
                    "error": (
                        "Suite bulunamadi"
                    ),
                }

            rid = f"brun_{uuid4()!s:.8}"
            items = results or []

            # Metrik hesaplama
            metric_results: dict[
                str, float
            ] = {}
            for m in suite["metrics"]:
                vals = [
                    r.get(m, 0.0)
                    for r in items
                    if m in r
                ]
                if vals:
                    metric_results[m] = (
                        round(
                            sum(vals)
                            / len(vals),
                            4,
                        )
                    )
                else:
                    metric_results[m] = 0.0

            self._results[rid] = {
                "run_id": rid,
                "suite_id": suite_id,
                "model_id": model_id,
                "metrics": metric_results,
                "test_count": len(items),
                "raw_results": items,
                "run_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            suite["run_count"] += 1
            self._stats[
                "benchmarks_run"
            ] += 1

            return {
                "run_id": rid,
                "suite_id": suite_id,
                "model_id": model_id,
                "metrics": metric_results,
                "test_count": len(items),
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def set_baseline(
        self,
        suite_id: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        """Baseline ayarlar.

        Args:
            suite_id: Suite ID.
            run_id: Run ID.

        Returns:
            Baseline bilgisi.
        """
        try:
            run = self._results.get(run_id)
            if not run:
                return {
                    "set": False,
                    "error": (
                        "Sonuc bulunamadi"
                    ),
                }

            self._baselines[suite_id] = {
                "suite_id": suite_id,
                "run_id": run_id,
                "metrics": run["metrics"],
                "model_id": run["model_id"],
                "set_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "baselines_set"
            ] += 1

            return {
                "suite_id": suite_id,
                "run_id": run_id,
                "metrics": run["metrics"],
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def compare_to_baseline(
        self,
        suite_id: str = "",
        run_id: str = "",
    ) -> dict[str, Any]:
        """Baseline ile karsilastirir.

        Args:
            suite_id: Suite ID.
            run_id: Run ID.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            baseline = (
                self._baselines.get(
                    suite_id
                )
            )
            if not baseline:
                return {
                    "compared": False,
                    "error": (
                        "Baseline bulunamadi"
                    ),
                }

            run = self._results.get(run_id)
            if not run:
                return {
                    "compared": False,
                    "error": (
                        "Sonuc bulunamadi"
                    ),
                }

            diffs: dict[str, dict] = {}
            improved = 0
            regressed = 0

            for metric in (
                baseline["metrics"]
            ):
                base_val = baseline[
                    "metrics"
                ][metric]
                run_val = run["metrics"].get(
                    metric, 0.0
                )

                diff = run_val - base_val
                pct = (
                    (diff / base_val * 100)
                    if base_val != 0
                    else 0.0
                )

                # Latency/cost icin dusuk iyi
                if metric in (
                    "latency",
                    "cost",
                ):
                    is_better = diff < 0
                else:
                    is_better = diff > 0

                if is_better:
                    improved += 1
                elif abs(pct) > 1:
                    regressed += 1

                diffs[metric] = {
                    "baseline": round(
                        base_val, 4
                    ),
                    "current": round(
                        run_val, 4
                    ),
                    "diff": round(diff, 4),
                    "pct_change": round(
                        pct, 2
                    ),
                    "better": is_better,
                }

            return {
                "suite_id": suite_id,
                "baseline_run": (
                    baseline["run_id"]
                ),
                "current_run": run_id,
                "diffs": diffs,
                "improved_count": improved,
                "regressed_count": (
                    regressed
                ),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def generate_report(
        self,
        suite_id: str = "",
    ) -> dict[str, Any]:
        """Benchmark raporu uretir.

        Args:
            suite_id: Suite ID.

        Returns:
            Rapor bilgisi.
        """
        try:
            suite = self._suites.get(
                suite_id
            )
            if not suite:
                return {
                    "generated": False,
                    "error": (
                        "Suite bulunamadi"
                    ),
                }

            runs = [
                r
                for r in (
                    self._results.values()
                )
                if r["suite_id"] == suite_id
            ]

            # Metrik trendi
            trends: dict[
                str, list[float]
            ] = {}
            for r in runs:
                for m, v in r[
                    "metrics"
                ].items():
                    if m not in trends:
                        trends[m] = []
                    trends[m].append(v)

            # Trend yonu
            trend_dir: dict[
                str, str
            ] = {}
            for m, vals in trends.items():
                if len(vals) < 2:
                    trend_dir[m] = "stable"
                else:
                    first = sum(
                        vals[
                            : len(vals) // 2
                        ]
                    ) / max(
                        1, len(vals) // 2
                    )
                    second = sum(
                        vals[
                            len(vals) // 2 :
                        ]
                    ) / max(
                        1,
                        len(vals)
                        - len(vals) // 2,
                    )
                    if second > first * 1.05:
                        trend_dir[m] = (
                            "improving"
                        )
                    elif (
                        second < first * 0.95
                    ):
                        trend_dir[m] = (
                            "declining"
                        )
                    else:
                        trend_dir[m] = (
                            "stable"
                        )

            self._stats[
                "reports_generated"
            ] += 1

            return {
                "suite_id": suite_id,
                "suite_name": suite["name"],
                "total_runs": len(runs),
                "trends": {
                    m: {
                        "values": [
                            round(v, 4)
                            for v in vals
                        ],
                        "direction": (
                            trend_dir[m]
                        ),
                    }
                    for m, vals in (
                        trends.items()
                    )
                },
                "has_baseline": (
                    suite_id
                    in self._baselines
                ),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def analyze_trends(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Model trend analizi yapar.

        Args:
            model_id: Model ID.

        Returns:
            Trend bilgisi.
        """
        try:
            runs = [
                r
                for r in (
                    self._results.values()
                )
                if r["model_id"] == model_id
            ]

            if not runs:
                return {
                    "analyzed": True,
                    "model_id": model_id,
                    "runs": 0,
                    "trends": {},
                }

            metrics: dict[
                str, list[float]
            ] = {}
            for r in runs:
                for m, v in r[
                    "metrics"
                ].items():
                    if m not in metrics:
                        metrics[m] = []
                    metrics[m].append(v)

            return {
                "model_id": model_id,
                "runs": len(runs),
                "metrics": {
                    m: {
                        "min": round(
                            min(vals), 4
                        ),
                        "max": round(
                            max(vals), 4
                        ),
                        "avg": round(
                            sum(vals)
                            / len(vals),
                            4,
                        ),
                        "latest": round(
                            vals[-1], 4
                        ),
                    }
                    for m, vals in (
                        metrics.items()
                    )
                },
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_suites": len(
                    self._suites
                ),
                "total_results": len(
                    self._results
                ),
                "total_baselines": len(
                    self._baselines
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
