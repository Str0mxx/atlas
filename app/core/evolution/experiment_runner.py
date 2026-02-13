"""ATLAS Deney Yoneticisi modulu.

Sandbox test, A/B karsilastirma, performans benchmark,
istatistiksel dogrulama ve kademeli yayilim.
"""

import logging
import math
import time
from typing import Any

from app.models.evolution import (
    CodeChange,
    ExperimentResult,
    ExperimentStatus,
)

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Deney yonetim sistemi.

    Kod degisikliklerini sandbox'ta test eder,
    A/B karsilastirma yapar ve istatistiksel dogrulama saglar.

    Attributes:
        _experiments: Deney sonuclari.
        _benchmarks: Benchmark kayitlari.
    """

    def __init__(self, confidence_threshold: float = 0.95) -> None:
        """Deney yoneticisini baslatir.

        Args:
            confidence_threshold: Guven esigi.
        """
        self._experiments: list[ExperimentResult] = []
        self._benchmarks: dict[str, list[float]] = {}
        self._confidence_threshold = confidence_threshold

        logger.info("ExperimentRunner baslatildi (confidence=%.2f)", confidence_threshold)

    def run_sandbox_test(self, change: CodeChange, test_data: dict[str, Any] | None = None) -> ExperimentResult:
        """Sandbox'ta test calistirir.

        Args:
            change: Test edilecek degisiklik.
            test_data: Test verileri.

        Returns:
            ExperimentResult nesnesi.
        """
        start = time.monotonic()

        try:
            # Syntax kontrolu (diff icindeki + satirlari)
            code_lines = [
                line[1:] for line in change.diff.split("\n")
                if line.startswith("+") and not line.startswith("+++")
            ]
            code = "\n".join(code_lines)

            if code.strip():
                compile(code, f"<sandbox_{change.file_path}>", "exec")

            elapsed = (time.monotonic() - start) * 1000

            result = ExperimentResult(
                experiment_name=f"sandbox_{change.id[:8]}",
                status=ExperimentStatus.PASSED,
                baseline_score=1.0,
                variant_score=1.0,
                improvement_pct=0.0,
                sample_size=1,
                confidence=1.0,
                details={"execution_ms": elapsed, "test_data": test_data or {}},
            )

        except SyntaxError as e:
            elapsed = (time.monotonic() - start) * 1000
            result = ExperimentResult(
                experiment_name=f"sandbox_{change.id[:8]}",
                status=ExperimentStatus.FAILED,
                details={"error": str(e), "execution_ms": elapsed},
            )

        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            result = ExperimentResult(
                experiment_name=f"sandbox_{change.id[:8]}",
                status=ExperimentStatus.FAILED,
                details={"error": str(e), "execution_ms": elapsed},
            )

        self._experiments.append(result)
        return result

    def run_ab_comparison(
        self,
        baseline_scores: list[float],
        variant_scores: list[float],
        experiment_name: str = "ab_test",
    ) -> ExperimentResult:
        """A/B karsilastirma yapar.

        Args:
            baseline_scores: Mevcut sistem puanlari.
            variant_scores: Yeni degisiklik puanlari.
            experiment_name: Deney adi.

        Returns:
            ExperimentResult nesnesi.
        """
        if not baseline_scores or not variant_scores:
            result = ExperimentResult(
                experiment_name=experiment_name,
                status=ExperimentStatus.INCONCLUSIVE,
                details={"reason": "Yetersiz veri"},
            )
            self._experiments.append(result)
            return result

        baseline_avg = sum(baseline_scores) / len(baseline_scores)
        variant_avg = sum(variant_scores) / len(variant_scores)

        improvement = ((variant_avg - baseline_avg) / baseline_avg * 100) if baseline_avg > 0 else 0.0
        confidence = self._calculate_confidence(baseline_scores, variant_scores)

        sample_size = len(baseline_scores) + len(variant_scores)

        if confidence >= self._confidence_threshold:
            status = ExperimentStatus.PASSED if improvement > 0 else ExperimentStatus.FAILED
        else:
            status = ExperimentStatus.INCONCLUSIVE

        result = ExperimentResult(
            experiment_name=experiment_name,
            status=status,
            baseline_score=baseline_avg,
            variant_score=variant_avg,
            improvement_pct=improvement,
            sample_size=sample_size,
            confidence=confidence,
        )

        self._experiments.append(result)
        return result

    def run_benchmark(self, name: str, scores: list[float]) -> ExperimentResult:
        """Performans benchmark calistirir.

        Args:
            name: Benchmark adi.
            scores: Performans puanlari.

        Returns:
            ExperimentResult nesnesi.
        """
        if not scores:
            result = ExperimentResult(
                experiment_name=f"bench_{name}",
                status=ExperimentStatus.INCONCLUSIVE,
            )
            self._experiments.append(result)
            return result

        avg_score = sum(scores) / len(scores)

        # Onceki benchmark ile karsilastir
        prev_scores = self._benchmarks.get(name, [])
        self._benchmarks[name] = scores

        if prev_scores:
            prev_avg = sum(prev_scores) / len(prev_scores)
            improvement = ((avg_score - prev_avg) / prev_avg * 100) if prev_avg > 0 else 0.0
            status = ExperimentStatus.PASSED if improvement >= 0 else ExperimentStatus.FAILED
        else:
            improvement = 0.0
            status = ExperimentStatus.PASSED

        result = ExperimentResult(
            experiment_name=f"bench_{name}",
            status=status,
            baseline_score=sum(prev_scores) / len(prev_scores) if prev_scores else avg_score,
            variant_score=avg_score,
            improvement_pct=improvement,
            sample_size=len(scores),
            confidence=0.95 if len(scores) >= 10 else len(scores) / 10.0,
        )

        self._experiments.append(result)
        return result

    def validate_statistically(self, scores_a: list[float], scores_b: list[float]) -> dict[str, Any]:
        """Istatistiksel dogrulama yapar.

        Args:
            scores_a: A grubu puanlari.
            scores_b: B grubu puanlari.

        Returns:
            Dogrulama sonucu.
        """
        if not scores_a or not scores_b:
            return {"valid": False, "reason": "Yetersiz veri"}

        mean_a = sum(scores_a) / len(scores_a)
        mean_b = sum(scores_b) / len(scores_b)

        var_a = sum((x - mean_a) ** 2 for x in scores_a) / max(len(scores_a) - 1, 1)
        var_b = sum((x - mean_b) ** 2 for x in scores_b) / max(len(scores_b) - 1, 1)

        se = math.sqrt(var_a / len(scores_a) + var_b / len(scores_b)) if (var_a + var_b) > 0 else 0.001

        t_stat = (mean_b - mean_a) / se
        # Basit p-deger tahmini
        p_value = max(0.01, 1.0 - min(abs(t_stat) / 3.0, 0.99))

        return {
            "valid": True,
            "mean_a": mean_a,
            "mean_b": mean_b,
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < (1 - self._confidence_threshold),
        }

    def plan_gradual_rollout(self, total_users: int, phases: int = 4) -> list[dict[str, Any]]:
        """Kademeli yayilim plani olusturur.

        Args:
            total_users: Toplam kullanici sayisi.
            phases: Asamali sayisi.

        Returns:
            Asama listesi.
        """
        rollout: list[dict[str, Any]] = []
        cumulative = 0

        for i in range(phases):
            pct = (2 ** i) / (2 ** phases - 1) * 100
            users = int(total_users * pct / 100)
            cumulative += users

            rollout.append({
                "phase": i + 1,
                "percentage": round(pct, 1),
                "users": min(users, total_users),
                "cumulative": min(cumulative, total_users),
            })

        return rollout

    def _calculate_confidence(self, scores_a: list[float], scores_b: list[float]) -> float:
        """Guven duzeyini hesaplar."""
        n = len(scores_a) + len(scores_b)
        if n < 4:
            return 0.5

        mean_a = sum(scores_a) / len(scores_a)
        mean_b = sum(scores_b) / len(scores_b)

        var_a = sum((x - mean_a) ** 2 for x in scores_a) / max(len(scores_a) - 1, 1)
        var_b = sum((x - mean_b) ** 2 for x in scores_b) / max(len(scores_b) - 1, 1)

        pooled_se = math.sqrt(var_a / len(scores_a) + var_b / len(scores_b)) if (var_a + var_b) > 0 else 0.001

        t_stat = abs(mean_b - mean_a) / pooled_se
        # Basit guven tahmini
        confidence = min(t_stat / 3.0, 1.0)
        return round(confidence, 3)

    def get_experiment(self, name: str) -> ExperimentResult | None:
        """Deney sonucu getirir.

        Args:
            name: Deney adi.

        Returns:
            ExperimentResult veya None.
        """
        for exp in reversed(self._experiments):
            if exp.experiment_name == name:
                return exp
        return None

    @property
    def experiment_count(self) -> int:
        """Deney sayisi."""
        return len(self._experiments)

    @property
    def pass_count(self) -> int:
        """Gecen deney sayisi."""
        return sum(1 for e in self._experiments if e.status == ExperimentStatus.PASSED)

    @property
    def fail_count(self) -> int:
        """Basarisiz deney sayisi."""
        return sum(1 for e in self._experiments if e.status == ExperimentStatus.FAILED)

    @property
    def experiments(self) -> list[ExperimentResult]:
        """Tum deneyler."""
        return list(self._experiments)
