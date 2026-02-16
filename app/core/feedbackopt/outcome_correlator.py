"""ATLAS Sonuç İlişkilendirici modülü.

Eylem-sonuç bağlama, korelasyon analizi,
nedensel çıkarım, kalıp tespiti,
atfetme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OutcomeCorrelator:
    """Sonuç ilişkilendirici.

    Eylemler ve sonuçlar arası ilişki kurar.

    Attributes:
        _actions: Eylem kayıtları.
        _outcomes: Sonuç kayıtları.
    """

    def __init__(self) -> None:
        """İlişkilendiriciyi başlatır."""
        self._actions: list[
            dict[str, Any]
        ] = []
        self._outcomes: list[
            dict[str, Any]
        ] = []
        self._correlations: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "correlations_found": 0,
            "patterns_detected": 0,
        }

        logger.info(
            "OutcomeCorrelator baslatildi",
        )

    def link_action_outcome(
        self,
        action_id: str,
        action_type: str,
        outcome_value: float,
        outcome_type: str = "score",
    ) -> dict[str, Any]:
        """Eylem-sonuç bağlar.

        Args:
            action_id: Eylem ID.
            action_type: Eylem tipi.
            outcome_value: Sonuç değeri.
            outcome_type: Sonuç tipi.

        Returns:
            Bağlama bilgisi.
        """
        self._counter += 1
        lid = f"link_{self._counter}"

        entry = {
            "link_id": lid,
            "action_id": action_id,
            "action_type": action_type,
            "outcome_value": outcome_value,
            "outcome_type": outcome_type,
            "timestamp": time.time(),
        }
        self._actions.append(entry)

        return {
            "link_id": lid,
            "action_type": action_type,
            "outcome_value": outcome_value,
            "linked": True,
        }

    def analyze_correlation(
        self,
        action_type: str,
    ) -> dict[str, Any]:
        """Korelasyon analizi yapar.

        Args:
            action_type: Eylem tipi.

        Returns:
            Korelasyon bilgisi.
        """
        related = [
            a for a in self._actions
            if a["action_type"] == action_type
        ]

        if len(related) < 2:
            return {
                "action_type": action_type,
                "analyzed": False,
                "reason": "Insufficient data",
            }

        values = [
            a["outcome_value"]
            for a in related
        ]
        avg = round(
            sum(values) / len(values), 2,
        )
        variance = round(
            sum(
                (v - avg) ** 2
                for v in values
            ) / len(values),
            2,
        )

        # Tutarlılık -> güçlü korelasyon
        consistency = round(
            1.0 - min(
                variance / (avg ** 2 + 1),
                1.0,
            ),
            2,
        )

        strength = (
            "strong" if consistency >= 0.8
            else "moderate"
            if consistency >= 0.5
            else "weak"
            if consistency >= 0.2
            else "none"
        )

        self._stats[
            "correlations_found"
        ] += 1

        return {
            "action_type": action_type,
            "avg_outcome": avg,
            "variance": variance,
            "consistency": consistency,
            "strength": strength,
            "sample_size": len(related),
            "analyzed": True,
        }

    def infer_causality(
        self,
        action_type: str,
        baseline: float = 0.0,
    ) -> dict[str, Any]:
        """Nedensel çıkarım yapar.

        Args:
            action_type: Eylem tipi.
            baseline: Temel değer.

        Returns:
            Çıkarım bilgisi.
        """
        related = [
            a for a in self._actions
            if a["action_type"] == action_type
        ]

        if len(related) < 3:
            return {
                "action_type": action_type,
                "inferred": False,
            }

        values = [
            a["outcome_value"]
            for a in related
        ]
        avg = sum(values) / len(values)
        lift = round(
            avg - baseline, 2,
        ) if baseline else round(avg, 2)

        confidence = min(
            round(
                len(related) / 10, 2,
            ),
            0.95,
        )

        likely_causal = (
            abs(lift) > 5
            and confidence >= 0.3
        )

        return {
            "action_type": action_type,
            "avg_outcome": round(avg, 2),
            "baseline": baseline,
            "lift": lift,
            "confidence": confidence,
            "likely_causal": likely_causal,
            "inferred": True,
        }

    def detect_pattern(
        self,
        min_occurrences: int = 3,
    ) -> dict[str, Any]:
        """Kalıp tespit eder.

        Args:
            min_occurrences: Min tekrar.

        Returns:
            Kalıp bilgisi.
        """
        type_counts: dict[str, list[float]] = {}
        for a in self._actions:
            at = a["action_type"]
            if at not in type_counts:
                type_counts[at] = []
            type_counts[at].append(
                a["outcome_value"],
            )

        patterns = []
        for at, vals in type_counts.items():
            if len(vals) >= min_occurrences:
                avg = round(
                    sum(vals) / len(vals), 2,
                )
                patterns.append({
                    "action_type": at,
                    "avg_outcome": avg,
                    "count": len(vals),
                })

        self._stats[
            "patterns_detected"
        ] += len(patterns)

        return {
            "patterns": patterns,
            "pattern_count": len(patterns),
            "detected": len(patterns) > 0,
        }

    def attribute_outcome(
        self,
        outcome_value: float,
        action_types: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Sonucu eylemlere atfeder.

        Args:
            outcome_value: Sonuç değeri.
            action_types: Eylem tipleri.

        Returns:
            Atfetme bilgisi.
        """
        action_types = action_types or []
        attributions = []

        for at in action_types:
            related = [
                a for a in self._actions
                if a["action_type"] == at
            ]
            if related:
                avg = sum(
                    a["outcome_value"]
                    for a in related
                ) / len(related)
                weight = round(
                    min(avg / (
                        outcome_value + 1
                    ), 1.0),
                    2,
                )
                attributions.append({
                    "action_type": at,
                    "weight": weight,
                })

        # Normalize
        total_w = sum(
            a["weight"]
            for a in attributions
        )
        if total_w > 0:
            for a in attributions:
                a["weight"] = round(
                    a["weight"] / total_w, 2,
                )

        return {
            "outcome_value": outcome_value,
            "attributions": attributions,
            "attribution_count": len(
                attributions,
            ),
            "attributed": len(
                attributions,
            ) > 0,
        }

    @property
    def correlation_count(self) -> int:
        """Korelasyon sayısı."""
        return self._stats[
            "correlations_found"
        ]

    @property
    def pattern_count(self) -> int:
        """Kalıp sayısı."""
        return self._stats[
            "patterns_detected"
        ]
