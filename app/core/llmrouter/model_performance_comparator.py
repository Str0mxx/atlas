"""
Model performans karsilastirici modulu.

Kalite puanlama, A/B test,
benchmark sonuclari, gorev bazli
karsilastirma, oneri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ModelPerformanceComparator:
    """Model performans karsilastirici.

    Attributes:
        _evaluations: Degerlendirmeler.
        _ab_tests: A/B testler.
        _benchmarks: Benchmark kayitlari.
        _stats: Istatistikler.
    """

    QUALITY_DIMENSIONS: list[str] = [
        "accuracy",
        "relevance",
        "coherence",
        "completeness",
        "creativity",
        "safety",
        "instruction_following",
    ]

    def __init__(self) -> None:
        """Karsilastiriciyi baslatir."""
        self._evaluations: list[
            dict
        ] = []
        self._ab_tests: dict[
            str, dict
        ] = {}
        self._benchmarks: dict[
            str, dict
        ] = {}
        self._model_scores: dict[
            str, list[float]
        ] = {}
        self._stats: dict[str, int] = {
            "evaluations_done": 0,
            "ab_tests_created": 0,
            "ab_tests_completed": 0,
            "benchmarks_run": 0,
            "recommendations_made": 0,
        }
        logger.info(
            "ModelPerformanceComparator "
            "baslatildi"
        )

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return len(self._evaluations)

    def evaluate_response(
        self,
        model_id: str = "",
        task_id: str = "",
        task_domain: str = "",
        scores: dict[str, float]
        | None = None,
        overall_score: float = 0.0,
        feedback: str = "",
    ) -> dict[str, Any]:
        """Yaniti degerlendirir.

        Args:
            model_id: Model ID.
            task_id: Gorev ID.
            task_domain: Alan.
            scores: Boyut puanlari.
            overall_score: Genel puan.
            feedback: Geri bildirim.

        Returns:
            Degerlendirme bilgisi.
        """
        try:
            eid = f"ev_{uuid4()!s:.8}"
            dim_scores = scores or {}

            # Boyut puanlarini dogrula
            for k, v in (
                dim_scores.items()
            ):
                dim_scores[k] = max(
                    0.0, min(1.0, v)
                )

            # Genel puan
            if (
                not overall_score
                and dim_scores
            ):
                overall_score = round(
                    sum(
                        dim_scores.values()
                    )
                    / len(dim_scores),
                    4,
                )

            overall_score = max(
                0.0, min(1.0, overall_score)
            )

            record = {
                "eval_id": eid,
                "model_id": model_id,
                "task_id": task_id,
                "task_domain": task_domain,
                "scores": dim_scores,
                "overall_score": (
                    overall_score
                ),
                "feedback": feedback,
                "evaluated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._evaluations.append(record)

            if model_id not in (
                self._model_scores
            ):
                self._model_scores[
                    model_id
                ] = []
            self._model_scores[
                model_id
            ].append(overall_score)

            self._stats[
                "evaluations_done"
            ] += 1

            return {
                "eval_id": eid,
                "overall_score": (
                    overall_score
                ),
                "evaluated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "evaluated": False,
                "error": str(e),
            }

    def create_ab_test(
        self,
        name: str = "",
        model_a: str = "",
        model_b: str = "",
        task_domain: str = "",
        sample_size: int = 100,
        description: str = "",
    ) -> dict[str, Any]:
        """A/B test olusturur.

        Args:
            name: Test adi.
            model_a: Model A.
            model_b: Model B.
            task_domain: Alan.
            sample_size: Ornek boyutu.
            description: Aciklama.

        Returns:
            Test bilgisi.
        """
        try:
            tid = f"ab_{uuid4()!s:.8}"

            self._ab_tests[tid] = {
                "test_id": tid,
                "name": name,
                "model_a": model_a,
                "model_b": model_b,
                "task_domain": task_domain,
                "sample_size": sample_size,
                "description": description,
                "status": "active",
                "results_a": [],
                "results_b": [],
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "ab_tests_created"
            ] += 1

            return {
                "test_id": tid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def record_ab_result(
        self,
        test_id: str = "",
        variant: str = "a",
        score: float = 0.0,
        latency_ms: float = 0.0,
    ) -> dict[str, Any]:
        """A/B test sonucu kaydeder.

        Args:
            test_id: Test ID.
            variant: Varyant (a/b).
            score: Puan.
            latency_ms: Gecikme.

        Returns:
            Kayit bilgisi.
        """
        try:
            test = self._ab_tests.get(
                test_id
            )
            if not test:
                return {
                    "recorded": False,
                    "error": (
                        "Test bulunamadi"
                    ),
                }

            if variant not in ("a", "b"):
                return {
                    "recorded": False,
                    "error": (
                        "Gecersiz varyant"
                    ),
                }

            key = f"results_{variant}"
            test[key].append({
                "score": max(
                    0.0, min(1.0, score)
                ),
                "latency_ms": latency_ms,
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            # Tamamlanma kontrolu
            total = len(
                test["results_a"]
            ) + len(test["results_b"])
            if total >= (
                test["sample_size"]
            ):
                test["status"] = "completed"
                self._stats[
                    "ab_tests_completed"
                ] += 1

            return {
                "test_id": test_id,
                "variant": variant,
                "total_results": total,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_ab_winner(
        self,
        test_id: str = "",
    ) -> dict[str, Any]:
        """A/B test kazanani bulur.

        Args:
            test_id: Test ID.

        Returns:
            Kazanan bilgisi.
        """
        try:
            test = self._ab_tests.get(
                test_id
            )
            if not test:
                return {
                    "determined": False,
                    "error": (
                        "Test bulunamadi"
                    ),
                }

            ra = test["results_a"]
            rb = test["results_b"]

            if not ra or not rb:
                return {
                    "determined": False,
                    "error": (
                        "Yeterli veri yok"
                    ),
                }

            avg_a = round(
                sum(r["score"] for r in ra)
                / len(ra),
                4,
            )
            avg_b = round(
                sum(r["score"] for r in rb)
                / len(rb),
                4,
            )

            lat_a = round(
                sum(
                    r["latency_ms"]
                    for r in ra
                )
                / len(ra),
                2,
            )
            lat_b = round(
                sum(
                    r["latency_ms"]
                    for r in rb
                )
                / len(rb),
                2,
            )

            winner = (
                "a" if avg_a >= avg_b
                else "b"
            )
            winner_model = (
                test["model_a"]
                if winner == "a"
                else test["model_b"]
            )

            return {
                "test_id": test_id,
                "winner": winner,
                "winner_model": (
                    winner_model
                ),
                "model_a_score": avg_a,
                "model_b_score": avg_b,
                "model_a_latency": lat_a,
                "model_b_latency": lat_b,
                "determined": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "determined": False,
                "error": str(e),
            }

    def run_benchmark(
        self,
        name: str = "",
        model_ids: (
            list[str] | None
        ) = None,
        task_domain: str = "",
        test_cases: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Benchmark calistirir.

        Args:
            name: Benchmark adi.
            model_ids: Modeller.
            task_domain: Alan.
            test_cases: Test vakalari.

        Returns:
            Benchmark sonucu.
        """
        try:
            bid = f"bm_{uuid4()!s:.8}"
            models = model_ids or []
            cases = test_cases or []

            results = {}
            for m in models:
                scores = (
                    self._model_scores
                    .get(m, [])
                )
                avg = (
                    round(
                        sum(scores)
                        / len(scores),
                        4,
                    )
                    if scores
                    else 0.5
                )
                results[m] = {
                    "model_id": m,
                    "avg_score": avg,
                    "sample_count": (
                        len(scores)
                    ),
                }

            ranking = sorted(
                results.values(),
                key=lambda x: x[
                    "avg_score"
                ],
                reverse=True,
            )

            self._benchmarks[bid] = {
                "benchmark_id": bid,
                "name": name,
                "task_domain": task_domain,
                "results": results,
                "ranking": [
                    r["model_id"]
                    for r in ranking
                ],
                "test_case_count": (
                    len(cases)
                ),
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
                "ranking": [
                    r["model_id"]
                    for r in ranking
                ],
                "results": results,
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def recommend_model(
        self,
        task_domain: str = "",
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        """Model onerir.

        Args:
            task_domain: Alan.
            min_score: Min puan.

        Returns:
            Oneri bilgisi.
        """
        try:
            # Alan bazli filtre
            domain_evals: dict[
                str, list[float]
            ] = {}

            for ev in self._evaluations:
                if (
                    task_domain
                    and ev["task_domain"]
                    != task_domain
                ):
                    continue
                m = ev["model_id"]
                if m not in domain_evals:
                    domain_evals[m] = []
                domain_evals[m].append(
                    ev["overall_score"]
                )

            # Puan yoksa genel
            if not domain_evals:
                domain_evals = {
                    m: list(scores)
                    for m, scores in (
                        self._model_scores
                        .items()
                    )
                }

            candidates = []
            for m, scores in (
                domain_evals.items()
            ):
                if not scores:
                    continue
                avg = round(
                    sum(scores)
                    / len(scores),
                    4,
                )
                if (
                    min_score > 0
                    and avg < min_score
                ):
                    continue
                candidates.append({
                    "model_id": m,
                    "avg_score": avg,
                    "eval_count": (
                        len(scores)
                    ),
                })

            candidates.sort(
                key=lambda x: x[
                    "avg_score"
                ],
                reverse=True,
            )

            self._stats[
                "recommendations_made"
            ] += 1

            return {
                "recommended": (
                    candidates[0][
                        "model_id"
                    ]
                    if candidates
                    else None
                ),
                "candidates": candidates,
                "task_domain": task_domain,
                "found": bool(candidates),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
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
                "total_ab_tests": len(
                    self._ab_tests
                ),
                "total_benchmarks": len(
                    self._benchmarks
                ),
                "models_scored": len(
                    self._model_scores
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
