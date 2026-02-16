"""ATLAS Kalite İyileştirici modülü.

Kalite puanlama, iyileştirme önerileri,
otomatik geliştirme, A/B karşılaştırma,
en iyi uygulama öğrenme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class QualityImprover:
    """Kalite iyileştirici.

    Görev çıktı kalitesini ölçer ve iyileştirir.

    Attributes:
        _scores: Kalite puanları.
        _best_practices: En iyi uygulamalar.
    """

    QUALITY_CRITERIA = {
        "completeness": 0.25,
        "accuracy": 0.25,
        "clarity": 0.20,
        "timeliness": 0.15,
        "relevance": 0.15,
    }

    def __init__(self) -> None:
        """İyileştiriciyi başlatır."""
        self._scores: list[
            dict[str, Any]
        ] = []
        self._best_practices: list[
            dict[str, Any]
        ] = []
        self._ab_tests: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "scores_given": 0,
            "improvements_suggested": 0,
            "ab_tests_run": 0,
            "practices_learned": 0,
        }

        logger.info(
            "QualityImprover baslatildi",
        )

    def score_quality(
        self,
        task_id: str,
        criteria_scores: dict[str, float],
    ) -> dict[str, Any]:
        """Kalite puanlar.

        Args:
            task_id: Görev ID.
            criteria_scores: Kriter puanları.

        Returns:
            Puanlama bilgisi.
        """
        self._counter += 1
        sid = f"qs_{self._counter}"

        weighted_sum = 0.0
        total_weight = 0.0

        for criterion, weight in (
            self.QUALITY_CRITERIA.items()
        ):
            score = criteria_scores.get(
                criterion, 0.0,
            )
            weighted_sum += (
                score * weight
            )
            total_weight += weight

        overall = round(
            weighted_sum
            / max(total_weight, 0.01),
            2,
        )

        level = (
            "excellent" if overall >= 4.0
            else "good" if overall >= 3.0
            else "average" if overall >= 2.0
            else "poor"
        )

        record = {
            "score_id": sid,
            "task_id": task_id,
            "criteria": criteria_scores,
            "overall": overall,
            "level": level,
            "timestamp": time.time(),
        }
        self._scores.append(record)
        self._stats["scores_given"] += 1

        return {
            "score_id": sid,
            "task_id": task_id,
            "overall": overall,
            "level": level,
            "scored": True,
        }

    def suggest_improvements(
        self,
        task_id: str,
        criteria_scores: dict[str, float],
    ) -> dict[str, Any]:
        """İyileştirme önerir.

        Args:
            task_id: Görev ID.
            criteria_scores: Kriter puanları.

        Returns:
            Öneri bilgisi.
        """
        suggestions = []
        for criterion, weight in (
            self.QUALITY_CRITERIA.items()
        ):
            score = criteria_scores.get(
                criterion, 0.0,
            )
            if score < 3.0:
                suggestions.append({
                    "criterion": criterion,
                    "current_score": score,
                    "target_score": 4.0,
                    "weight": weight,
                    "suggestion": (
                        f"Improve {criterion} "
                        f"from {score} to 4.0"
                    ),
                    "impact": round(
                        (4.0 - score) * weight,
                        2,
                    ),
                })

        suggestions.sort(
            key=lambda x: x["impact"],
            reverse=True,
        )
        self._stats[
            "improvements_suggested"
        ] += len(suggestions)

        return {
            "task_id": task_id,
            "suggestions": suggestions,
            "count": len(suggestions),
        }

    def auto_enhance(
        self,
        content: str,
        enhancements: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Otomatik geliştirme yapar.

        Args:
            content: İçerik.
            enhancements: Geliştirmeler.

        Returns:
            Geliştirme bilgisi.
        """
        enhanced = content
        applied = []

        rules = enhancements or [
            "add_structure",
            "improve_clarity",
        ]

        for rule in rules:
            if rule == "add_structure":
                if not enhanced.startswith(
                    "#"
                ):
                    lines = enhanced.split(
                        "\n",
                    )
                    if lines:
                        enhanced = (
                            f"# {lines[0]}\n"
                            + "\n".join(
                                lines[1:],
                            )
                        )
                        applied.append(
                            "add_structure",
                        )
            elif rule == "improve_clarity":
                if len(enhanced) > 500:
                    enhanced = (
                        enhanced[:500]
                        + "\n\n[Summary "
                        "truncated for "
                        "clarity]"
                    )
                    applied.append(
                        "improve_clarity",
                    )

        return {
            "original_length": len(content),
            "enhanced_length": len(enhanced),
            "enhanced_content": enhanced,
            "enhancements_applied": applied,
            "enhanced": len(applied) > 0,
        }

    def run_ab_test(
        self,
        variant_a: dict[str, Any],
        variant_b: dict[str, Any],
        metric: str = "overall",
    ) -> dict[str, Any]:
        """A/B testi çalıştırır.

        Args:
            variant_a: A varyantı.
            variant_b: B varyantı.
            metric: Karşılaştırma metriği.

        Returns:
            Test bilgisi.
        """
        self._counter += 1
        tid = f"ab_{self._counter}"

        score_a = variant_a.get(metric, 0)
        score_b = variant_b.get(metric, 0)

        winner = (
            "A" if score_a > score_b
            else "B" if score_b > score_a
            else "tie"
        )

        test = {
            "test_id": tid,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "metric": metric,
            "score_a": score_a,
            "score_b": score_b,
            "winner": winner,
            "improvement": round(
                abs(score_a - score_b), 2,
            ),
            "timestamp": time.time(),
        }
        self._ab_tests.append(test)
        self._stats["ab_tests_run"] += 1

        return {
            "test_id": tid,
            "winner": winner,
            "score_a": score_a,
            "score_b": score_b,
            "improvement": test[
                "improvement"
            ],
        }

    def learn_best_practice(
        self,
        practice: str,
        category: str = "general",
        effectiveness: float = 1.0,
    ) -> dict[str, Any]:
        """En iyi uygulamayı öğrenir.

        Args:
            practice: Uygulama.
            category: Kategori.
            effectiveness: Etkinlik.

        Returns:
            Öğrenme bilgisi.
        """
        self._counter += 1
        bid = f"bp_{self._counter}"

        bp = {
            "practice_id": bid,
            "practice": practice,
            "category": category,
            "effectiveness": effectiveness,
            "learned_at": time.time(),
        }
        self._best_practices.append(bp)
        self._stats[
            "practices_learned"
        ] += 1

        return {
            "practice_id": bid,
            "practice": practice,
            "learned": True,
        }

    def get_quality_trend(
        self,
    ) -> dict[str, Any]:
        """Kalite trendini döndürür."""
        if not self._scores:
            return {
                "trend": "no_data",
                "avg": 0.0,
            }

        scores = [
            s["overall"]
            for s in self._scores
        ]
        avg = sum(scores) / len(scores)

        if len(scores) >= 5:
            recent = scores[-5:]
            older = scores[-10:-5]
            if older:
                r_avg = sum(recent) / len(
                    recent,
                )
                o_avg = sum(older) / len(
                    older,
                )
                trend = (
                    "improving"
                    if r_avg > o_avg
                    else "declining"
                    if r_avg < o_avg
                    else "stable"
                )
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "avg": round(avg, 2),
            "count": len(scores),
        }

    @property
    def score_count(self) -> int:
        """Puan sayısı."""
        return self._stats["scores_given"]

    @property
    def practice_count(self) -> int:
        """Uygulama sayısı."""
        return len(self._best_practices)
