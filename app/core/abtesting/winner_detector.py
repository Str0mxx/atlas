"""ATLAS Kazanan Tespitçisi modülü.

Kazanan belirleme, erken durdurma,
çoklu metrik değerlendirme,
koruma kontrolü, öneri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WinnerDetector:
    """Kazanan tespitçisi.

    Deney kazananını tespit eder.

    Attributes:
        _results: Sonuç kayıtları.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._results: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "detections": 0,
            "early_stops": 0,
        }

        logger.info(
            "WinnerDetector baslatildi",
        )

    def determine_winner(
        self,
        experiment_id: str,
        variant_results: list[
            dict[str, Any]
        ],
        primary_metric: str = "conversion",
    ) -> dict[str, Any]:
        """Kazanan belirler.

        Args:
            experiment_id: Deney kimliği.
            variant_results: Varyant sonuçları.
            primary_metric: Birincil metrik.

        Returns:
            Belirleme bilgisi.
        """
        if not variant_results:
            return {
                "experiment_id": experiment_id,
                "winner": None,
                "determined": False,
            }

        best = max(
            variant_results,
            key=lambda v: v.get(
                primary_metric, 0,
            ),
        )

        significant = best.get(
            "significant", False,
        )

        self._results[
            experiment_id
        ] = {
            "winner": best.get("name", ""),
            "metric": primary_metric,
            "value": best.get(
                primary_metric, 0,
            ),
            "significant": significant,
            "timestamp": time.time(),
        }

        self._stats["detections"] += 1

        return {
            "experiment_id": experiment_id,
            "winner": best.get("name", ""),
            "value": best.get(
                primary_metric, 0,
            ),
            "significant": significant,
            "determined": True,
        }

    def check_early_stop(
        self,
        experiment_id: str,
        current_p_value: float = 0.05,
        threshold: float = 0.01,
        min_samples: int = 100,
        current_samples: int = 0,
    ) -> dict[str, Any]:
        """Erken durdurma kontrolü yapar.

        Args:
            experiment_id: Deney kimliği.
            current_p_value: Güncel p-değeri.
            threshold: Eşik.
            min_samples: Minimum örneklem.
            current_samples: Güncel örneklem.

        Returns:
            Kontrol bilgisi.
        """
        enough_samples = (
            current_samples >= min_samples
        )
        very_significant = (
            current_p_value < threshold
        )
        should_stop = (
            enough_samples
            and very_significant
        )

        if should_stop:
            self._stats[
                "early_stops"
            ] += 1

        return {
            "experiment_id": experiment_id,
            "should_stop": should_stop,
            "reason": (
                "Highly significant result"
                if should_stop
                else "Continue testing"
            ),
            "p_value": current_p_value,
            "samples": current_samples,
            "checked": True,
        }

    def evaluate_multi_metric(
        self,
        experiment_id: str,
        metrics: dict[str, dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Çoklu metrik değerlendirir.

        Args:
            experiment_id: Deney kimliği.
            metrics: Metrik sonuçları.

        Returns:
            Değerlendirme bilgisi.
        """
        metrics = metrics or {}

        wins = 0
        losses = 0
        neutral = 0

        for name, result in (
            metrics.items()
        ):
            lift = result.get("lift", 0)
            sig = result.get(
                "significant", False,
            )
            if sig and lift > 0:
                wins += 1
            elif sig and lift < 0:
                losses += 1
            else:
                neutral += 1

        overall = (
            "winner"
            if wins > 0 and losses == 0
            else "loser"
            if losses > 0 and wins == 0
            else "mixed"
            if wins > 0 and losses > 0
            else "inconclusive"
        )

        return {
            "experiment_id": experiment_id,
            "wins": wins,
            "losses": losses,
            "neutral": neutral,
            "overall": overall,
            "evaluated": True,
        }

    def check_guardrails(
        self,
        experiment_id: str,
        guardrail_metrics: dict[
            str, dict[str, Any]
        ]
        | None = None,
    ) -> dict[str, Any]:
        """Koruma kontrolü yapar.

        Args:
            experiment_id: Deney kimliği.
            guardrail_metrics: Koruma metrikleri.

        Returns:
            Kontrol bilgisi.
        """
        guardrail_metrics = (
            guardrail_metrics or {}
        )

        violations = []
        for name, metric in (
            guardrail_metrics.items()
        ):
            threshold = metric.get(
                "threshold", 0,
            )
            current = metric.get(
                "current", 0,
            )
            direction = metric.get(
                "direction", "above",
            )

            violated = (
                (
                    direction == "below"
                    and current < threshold
                )
                or (
                    direction == "above"
                    and current > threshold
                )
            )

            if violated:
                violations.append({
                    "metric": name,
                    "threshold": threshold,
                    "current": current,
                })

        return {
            "experiment_id": experiment_id,
            "violations": violations,
            "violation_count": len(
                violations,
            ),
            "safe": len(violations) == 0,
            "checked": True,
        }

    def recommend(
        self,
        experiment_id: str,
        winner: str = "",
        significant: bool = False,
        guardrails_safe: bool = True,
    ) -> dict[str, Any]:
        """Öneri verir.

        Args:
            experiment_id: Deney kimliği.
            winner: Kazanan.
            significant: Anlamlı mı.
            guardrails_safe: Koruma güvenli mi.

        Returns:
            Öneri bilgisi.
        """
        if (
            significant
            and guardrails_safe
            and winner
        ):
            action = "rollout"
            reason = (
                f"Deploy {winner}: "
                f"significant & safe"
            )
        elif not significant:
            action = "continue"
            reason = "Not yet significant"
        elif not guardrails_safe:
            action = "investigate"
            reason = "Guardrail violations"
        else:
            action = "review"
            reason = "Manual review needed"

        return {
            "experiment_id": experiment_id,
            "action": action,
            "reason": reason,
            "winner": winner,
            "recommended": True,
        }

    @property
    def detection_count(self) -> int:
        """Tespit sayısı."""
        return self._stats["detections"]

    @property
    def early_stop_count(self) -> int:
        """Erken durdurma sayısı."""
        return self._stats[
            "early_stops"
        ]
