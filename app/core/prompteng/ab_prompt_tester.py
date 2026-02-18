"""
Prompt A/B test modulu.

A/B test olusturma, istatistiksel analiz,
kazanan belirleme, otomatik terfi,
ogrenme cikarimi.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ABPromptTester:
    """Prompt A/B test yoneticisi.

    Attributes:
        _tests: A/B testleri.
        _results: Test sonuclari.
        _learnings: Ogrenimler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """A/B test yoneticisini baslatir."""
        self._tests: dict[str, dict] = {}
        self._results: dict[
            str, list[dict]
        ] = {}
        self._learnings: list[dict] = []
        self._stats: dict[str, int] = {
            "tests_created": 0,
            "results_recorded": 0,
            "winners_detected": 0,
            "promotions_done": 0,
        }
        logger.info(
            "ABPromptTester baslatildi"
        )

    @property
    def test_count(self) -> int:
        """Test sayisi."""
        return len(self._tests)

    def create_test(
        self,
        name: str = "",
        prompt_a: str = "",
        prompt_b: str = "",
        metric: str = "quality",
        sample_size: int = 100,
        confidence_level: float = 0.95,
        description: str = "",
    ) -> dict[str, Any]:
        """A/B test olusturur.

        Args:
            name: Test adi.
            prompt_a: A varyanti.
            prompt_b: B varyanti.
            metric: Olcum metrigi.
            sample_size: Orneklem buyuklugu.
            confidence_level: Guven duzeyi.
            description: Aciklama.

        Returns:
            Test bilgisi.
        """
        try:
            tid = f"ab_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()

            self._tests[tid] = {
                "test_id": tid,
                "name": name,
                "prompt_a": prompt_a,
                "prompt_b": prompt_b,
                "metric": metric,
                "sample_size": sample_size,
                "confidence_level": (
                    confidence_level
                ),
                "description": description,
                "status": "running",
                "winner": None,
                "created_at": now,
            }

            self._results[tid] = []
            self._stats[
                "tests_created"
            ] += 1

            return {
                "test_id": tid,
                "name": name,
                "status": "running",
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def record_result(
        self,
        test_id: str = "",
        variant: str = "a",
        score: float = 0.0,
        latency_ms: float = 0.0,
        success: bool = True,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Sonuc kaydeder.

        Args:
            test_id: Test ID.
            variant: Varyant (a/b).
            score: Puan.
            latency_ms: Gecikme ms.
            success: Basarili mi.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            test = self._tests.get(test_id)
            if not test:
                return {
                    "recorded": False,
                    "error": (
                        "Test bulunamadi"
                    ),
                }

            if test["status"] != "running":
                return {
                    "recorded": False,
                    "error": (
                        "Test tamamlanmis"
                    ),
                }

            if variant not in ("a", "b"):
                return {
                    "recorded": False,
                    "error": (
                        "Gecersiz varyant"
                    ),
                }

            self._results[test_id].append({
                "variant": variant,
                "score": score,
                "latency_ms": latency_ms,
                "success": success,
                "metadata": metadata or {},
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            self._stats[
                "results_recorded"
            ] += 1

            # Otomatik tamamlama
            results = self._results[test_id]
            count_a = sum(
                1
                for r in results
                if r["variant"] == "a"
            )
            count_b = sum(
                1
                for r in results
                if r["variant"] == "b"
            )
            total = count_a + count_b
            if total >= test["sample_size"]:
                self._detect_winner(test_id)

            return {
                "test_id": test_id,
                "variant": variant,
                "total_results": len(results),
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def _detect_winner(
        self,
        test_id: str,
    ) -> None:
        """Kazanani belirler."""
        test = self._tests.get(test_id)
        if not test:
            return

        results = self._results.get(
            test_id, []
        )

        scores_a = [
            r["score"]
            for r in results
            if r["variant"] == "a"
        ]
        scores_b = [
            r["score"]
            for r in results
            if r["variant"] == "b"
        ]

        if not scores_a or not scores_b:
            return

        avg_a = sum(scores_a) / len(scores_a)
        avg_b = sum(scores_b) / len(scores_b)

        # Basit t-test yaklasimi
        significant = self._is_significant(
            scores_a,
            scores_b,
            test["confidence_level"],
        )

        if significant:
            winner = (
                "a" if avg_a > avg_b else "b"
            )
            test["winner"] = winner
            test["status"] = "completed"
            self._stats[
                "winners_detected"
            ] += 1
        else:
            test["status"] = "completed"
            test["winner"] = "inconclusive"

    def _is_significant(
        self,
        scores_a: list[float],
        scores_b: list[float],
        confidence: float,
    ) -> bool:
        """Istatistiksel anlamlilik."""
        if (
            len(scores_a) < 2
            or len(scores_b) < 2
        ):
            return False

        avg_a = sum(scores_a) / len(scores_a)
        avg_b = sum(scores_b) / len(scores_b)

        var_a = sum(
            (x - avg_a) ** 2
            for x in scores_a
        ) / (len(scores_a) - 1)
        var_b = sum(
            (x - avg_b) ** 2
            for x in scores_b
        ) / (len(scores_b) - 1)

        se = math.sqrt(
            var_a / len(scores_a)
            + var_b / len(scores_b)
        )

        if se == 0:
            return avg_a != avg_b

        t_stat = abs(avg_a - avg_b) / se

        # Yaklasik z-degeri
        z_map = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }
        z_critical = z_map.get(
            confidence, 1.96
        )

        return t_stat > z_critical

    def get_test_results(
        self,
        test_id: str = "",
    ) -> dict[str, Any]:
        """Test sonuclarini getirir.

        Args:
            test_id: Test ID.

        Returns:
            Sonuc bilgisi.
        """
        try:
            test = self._tests.get(test_id)
            if not test:
                return {
                    "retrieved": False,
                    "error": (
                        "Test bulunamadi"
                    ),
                }

            results = self._results.get(
                test_id, []
            )

            scores_a = [
                r["score"]
                for r in results
                if r["variant"] == "a"
            ]
            scores_b = [
                r["score"]
                for r in results
                if r["variant"] == "b"
            ]

            avg_a = (
                sum(scores_a) / len(scores_a)
                if scores_a
                else 0.0
            )
            avg_b = (
                sum(scores_b) / len(scores_b)
                if scores_b
                else 0.0
            )

            return {
                "test_id": test_id,
                "status": test["status"],
                "winner": test["winner"],
                "variant_a": {
                    "count": len(scores_a),
                    "avg_score": round(
                        avg_a, 4
                    ),
                },
                "variant_b": {
                    "count": len(scores_b),
                    "avg_score": round(
                        avg_b, 4
                    ),
                },
                "total_results": len(
                    results
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def promote_winner(
        self,
        test_id: str = "",
    ) -> dict[str, Any]:
        """Kazanani terfi ettirir.

        Args:
            test_id: Test ID.

        Returns:
            Terfi bilgisi.
        """
        try:
            test = self._tests.get(test_id)
            if not test:
                return {
                    "promoted": False,
                    "error": (
                        "Test bulunamadi"
                    ),
                }

            if (
                test["status"] != "completed"
                or test["winner"]
                in (None, "inconclusive")
            ):
                return {
                    "promoted": False,
                    "error": (
                        "Kazanan yok"
                    ),
                }

            winner = test["winner"]
            prompt_key = (
                f"prompt_{winner}"
            )
            winning_prompt = test[prompt_key]

            test["status"] = "promoted"
            self._stats[
                "promotions_done"
            ] += 1

            return {
                "test_id": test_id,
                "winner": winner,
                "winning_prompt": (
                    winning_prompt
                ),
                "promoted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "promoted": False,
                "error": str(e),
            }

    def extract_learning(
        self,
        test_id: str = "",
    ) -> dict[str, Any]:
        """Test ogrenimini cikarir.

        Args:
            test_id: Test ID.

        Returns:
            Ogrenim bilgisi.
        """
        try:
            test = self._tests.get(test_id)
            if not test:
                return {
                    "extracted": False,
                    "error": (
                        "Test bulunamadi"
                    ),
                }

            results = self._results.get(
                test_id, []
            )
            scores_a = [
                r["score"]
                for r in results
                if r["variant"] == "a"
            ]
            scores_b = [
                r["score"]
                for r in results
                if r["variant"] == "b"
            ]

            avg_a = (
                sum(scores_a) / len(scores_a)
                if scores_a
                else 0.0
            )
            avg_b = (
                sum(scores_b) / len(scores_b)
                if scores_b
                else 0.0
            )

            diff = abs(avg_a - avg_b)
            improvement = (
                diff / max(avg_a, avg_b, 0.01)
            )

            learning = {
                "test_id": test_id,
                "test_name": test["name"],
                "metric": test["metric"],
                "winner": test["winner"],
                "score_diff": round(diff, 4),
                "improvement_pct": round(
                    improvement * 100, 2
                ),
                "sample_count": len(results),
                "extracted_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._learnings.append(learning)

            return {
                **learning,
                "extracted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "extracted": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            running = sum(
                1
                for t in self._tests.values()
                if t["status"] == "running"
            )
            completed = sum(
                1
                for t in self._tests.values()
                if t["status"]
                in ("completed", "promoted")
            )

            return {
                "total_tests": len(
                    self._tests
                ),
                "running_tests": running,
                "completed_tests": completed,
                "total_learnings": len(
                    self._learnings
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
