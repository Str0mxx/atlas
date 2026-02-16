"""
Değer önerisi test edici modülü.

Değer önermelerini test eder, geri bildirim
toplar, rakiplerle karşılaştırır ve
iyileştirme önerileri sunar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ValuePropositionTester:
    """Değer önerisi test edici.

    Değer önermelerini analiz eder,
    müşteri geri bildirimi toplar,
    rakip karşılaştırması yapar ve
    iterasyon önerileri sunar.

    Attributes:
        _tests: Test kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Test ediciyi başlatır."""
        self._tests: list[dict] = []
        self._stats: dict[str, int] = {
            "tests_run": 0,
        }
        logger.info(
            "ValuePropositionTester "
            "baslatildi"
        )

    @property
    def test_count(self) -> int:
        """Çalıştırılan test sayısı."""
        return self._stats["tests_run"]

    def test_value_prop(
        self,
        proposition: str = "",
        target_segment: str = "general",
    ) -> dict[str, Any]:
        """Değer önerisi testi yapar.

        Args:
            proposition: Değer önerisi.
            target_segment: Hedef segment.

        Returns:
            Test sonucu.
        """
        try:
            issues: list[str] = []

            if len(proposition) < 10:
                issues.append("too_vague")

            low = proposition.lower()
            if (
                "unique" not in low
                and "better" not in low
            ):
                issues.append(
                    "weak_differentiation"
                )

            score = max(
                100 - len(issues) * 30, 0
            )

            if score >= 70:
                grade = "strong"
            elif score >= 40:
                grade = "moderate"
            else:
                grade = "weak"

            self._stats["tests_run"] += 1

            result = {
                "proposition": proposition,
                "target_segment": (
                    target_segment
                ),
                "issues": issues,
                "issue_count": len(issues),
                "score": score,
                "grade": grade,
                "tested": True,
            }

            logger.info(
                f"Value prop test: "
                f"score={score}, "
                f"grade={grade}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Value prop test "
                f"hatasi: {e}"
            )
            return {
                "proposition": proposition,
                "target_segment": (
                    target_segment
                ),
                "issues": [],
                "issue_count": 0,
                "score": 0,
                "grade": "unknown",
                "tested": False,
                "error": str(e),
            }

    def collect_feedback(
        self,
        responses: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Müşteri geri bildirimi toplar.

        Args:
            responses: Yanıt listesi.

        Returns:
            Geri bildirim özeti.
        """
        try:
            if responses is None:
                responses = []

            positive = sum(
                1
                for r in responses
                if r.get("sentiment")
                == "positive"
            )
            negative = sum(
                1
                for r in responses
                if r.get("sentiment")
                == "negative"
            )
            neutral = (
                len(responses)
                - positive
                - negative
            )
            satisfaction = round(
                (
                    positive
                    / max(len(responses), 1)
                )
                * 100,
                1,
            )

            self._stats["tests_run"] += 1

            result = {
                "total_responses": len(
                    responses
                ),
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "satisfaction_rate": (
                    satisfaction
                ),
                "collected": True,
            }

            logger.info(
                f"Feedback toplandi: "
                f"{len(responses)} yanit, "
                f"memnuniyet={satisfaction}%"
            )

            return result

        except Exception as e:
            logger.error(
                f"Feedback toplama "
                f"hatasi: {e}"
            )
            return {
                "total_responses": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "satisfaction_rate": 0.0,
                "collected": False,
                "error": str(e),
            }

    def compare_competitors(
        self,
        our_score: float = 0.0,
        competitor_scores: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Rakiplerle karşılaştırır.

        Args:
            our_score: Bizim skor.
            competitor_scores: Rakip skorları.

        Returns:
            Karşılaştırma sonucu.
        """
        try:
            if competitor_scores is None:
                competitor_scores = []

            if competitor_scores:
                avg_comp = round(
                    sum(competitor_scores)
                    / len(competitor_scores),
                    2,
                )
            else:
                avg_comp = 0.0

            advantage = round(
                our_score - avg_comp, 2
            )

            if advantage > 10:
                position = "superior"
            elif advantage < -10:
                position = "inferior"
            else:
                position = "comparable"

            self._stats["tests_run"] += 1

            result = {
                "our_score": our_score,
                "avg_competitor": avg_comp,
                "advantage": advantage,
                "position": position,
                "compared": True,
            }

            logger.info(
                f"Rakip karsilastirma: "
                f"avantaj={advantage}, "
                f"pozisyon={position}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Rakip karsilastirma "
                f"hatasi: {e}"
            )
            return {
                "our_score": our_score,
                "avg_competitor": 0.0,
                "advantage": 0.0,
                "position": "unknown",
                "compared": False,
                "error": str(e),
            }

    def calculate_fit(
        self,
        needs_met: int = 0,
        total_needs: int = 1,
    ) -> dict[str, Any]:
        """Uyum skoru hesaplar.

        Args:
            needs_met: Karşılanan ihtiyaç.
            total_needs: Toplam ihtiyaç.

        Returns:
            Uyum sonucu.
        """
        try:
            fit_score = round(
                (
                    needs_met
                    / max(total_needs, 1)
                )
                * 100,
                1,
            )

            if fit_score >= 80:
                fit_level = "excellent"
            elif fit_score >= 60:
                fit_level = "good"
            elif fit_score >= 40:
                fit_level = "partial"
            else:
                fit_level = "poor"

            self._stats["tests_run"] += 1

            result = {
                "needs_met": needs_met,
                "total_needs": total_needs,
                "fit_score": fit_score,
                "fit_level": fit_level,
                "calculated": True,
            }

            logger.info(
                f"Uyum hesaplandi: "
                f"skor={fit_score}, "
                f"seviye={fit_level}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Uyum hesaplama "
                f"hatasi: {e}"
            )
            return {
                "needs_met": needs_met,
                "total_needs": total_needs,
                "fit_score": 0.0,
                "fit_level": "unknown",
                "calculated": False,
                "error": str(e),
            }

    def suggest_iteration(
        self,
        score: float = 50.0,
        feedback_sentiment: str = "neutral",
    ) -> dict[str, Any]:
        """İterasyon önerileri sunar.

        Args:
            score: Mevcut skor.
            feedback_sentiment: Duygu durumu.

        Returns:
            İterasyon önerileri.
        """
        try:
            suggestions: list[str] = []

            if score < 40:
                suggestions.append(
                    "major_pivot_needed"
                )
            if score < 70:
                suggestions.append(
                    "refine_messaging"
                )
            if feedback_sentiment == "negative":
                suggestions.append(
                    "address_pain_points"
                )
            if feedback_sentiment == "neutral":
                suggestions.append(
                    "increase_differentiation"
                )
            if not suggestions:
                suggestions.append(
                    "maintain_and_optimize"
                )

            if score < 40:
                priority = "high"
            elif score < 70:
                priority = "medium"
            else:
                priority = "low"

            self._stats["tests_run"] += 1

            result = {
                "suggestions": suggestions,
                "suggestion_count": len(
                    suggestions
                ),
                "priority": priority,
                "iterated": True,
            }

            logger.info(
                f"Iterasyon onerisi: "
                f"{len(suggestions)} oneri, "
                f"oncelik={priority}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Iterasyon onerisi "
                f"hatasi: {e}"
            )
            return {
                "suggestions": [],
                "suggestion_count": 0,
                "priority": "unknown",
                "iterated": False,
                "error": str(e),
            }
