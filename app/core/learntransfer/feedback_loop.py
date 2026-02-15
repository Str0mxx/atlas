"""ATLAS Transfer Geri Bildirim Dongusu modulu.

Etkinlik olcumu, transfer iyilestirme,
basarisizliktan ogrenme, esleme iyilestirme, optimizasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TransferFeedbackLoop:
    """Transfer geri bildirim dongusu.

    Transferlerden ogrenip iyilestirme yapar.

    Attributes:
        _feedback: Geri bildirim kayitlari.
        _patterns: Ogrenen kaliplar.
    """

    def __init__(self) -> None:
        """Geri bildirim dongusunu baslatir."""
        self._feedback: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._improvements: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "feedback_collected": 0,
            "improvements": 0,
        }

        logger.info(
            "TransferFeedbackLoop "
            "baslatildi",
        )

    def collect_feedback(
        self,
        transfer_id: str,
        feedback_type: str,
        score: float,
        details: str = "",
    ) -> dict[str, Any]:
        """Geri bildirim toplar.

        Args:
            transfer_id: Transfer ID.
            feedback_type: Geri bildirim tipi.
            score: Skor (0-1).
            details: Detaylar.

        Returns:
            Toplama bilgisi.
        """
        fb = {
            "transfer_id": transfer_id,
            "feedback_type": feedback_type,
            "score": score,
            "details": details,
            "collected_at": time.time(),
        }

        if transfer_id not in self._feedback:
            self._feedback[transfer_id] = []
        self._feedback[transfer_id].append(fb)
        self._stats["feedback_collected"] += 1

        return {
            "transfer_id": transfer_id,
            "feedback_type": feedback_type,
            "score": score,
            "collected": True,
        }

    def measure_effectiveness(
        self,
        transfer_id: str,
    ) -> dict[str, Any]:
        """Etkinlik olcer.

        Args:
            transfer_id: Transfer ID.

        Returns:
            Etkinlik bilgisi.
        """
        fbs = self._feedback.get(
            transfer_id, [],
        )
        if not fbs:
            return {
                "transfer_id": transfer_id,
                "effectiveness": 0.0,
                "feedback_count": 0,
            }

        scores = [f["score"] for f in fbs]
        avg = round(
            sum(scores) / len(scores), 3,
        )

        positive = sum(
            1 for s in scores if s >= 0.6
        )
        negative = sum(
            1 for s in scores if s < 0.4
        )

        return {
            "transfer_id": transfer_id,
            "effectiveness": avg,
            "feedback_count": len(fbs),
            "positive_count": positive,
            "negative_count": negative,
        }

    def learn_from_failure(
        self,
        transfer_id: str,
        failure_reason: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Basarisizliktan ogrenir.

        Args:
            transfer_id: Transfer ID.
            failure_reason: Basarisizlik nedeni.
            context: Baglam.

        Returns:
            Ogrenme bilgisi.
        """
        pattern_key = failure_reason

        if pattern_key in self._patterns:
            self._patterns[pattern_key][
                "occurrences"
            ] += 1
        else:
            self._patterns[pattern_key] = {
                "reason": failure_reason,
                "occurrences": 1,
                "context_samples": [],
                "learned_at": time.time(),
            }

        if context:
            samples = self._patterns[
                pattern_key
            ]["context_samples"]
            if len(samples) < 5:
                samples.append(context)

        return {
            "transfer_id": transfer_id,
            "pattern": pattern_key,
            "occurrences": self._patterns[
                pattern_key
            ]["occurrences"],
            "learned": True,
        }

    def refine_transfer(
        self,
        transfer_id: str,
        adjustment: dict[str, Any],
    ) -> dict[str, Any]:
        """Transferi iyilestirir.

        Args:
            transfer_id: Transfer ID.
            adjustment: Ayarlama.

        Returns:
            Iyilestirme bilgisi.
        """
        improvement = {
            "transfer_id": transfer_id,
            "adjustment": adjustment,
            "refined_at": time.time(),
        }
        self._improvements.append(improvement)
        self._stats["improvements"] += 1

        return {
            "transfer_id": transfer_id,
            "refined": True,
            "adjustment_keys": list(
                adjustment.keys(),
            ),
        }

    def optimize_matching(
        self,
    ) -> dict[str, Any]:
        """Esleme optimizasyonu yapar.

        Returns:
            Optimizasyon sonucu.
        """
        # Basarisizlik kaliplarini analiz et
        recurring = [
            {
                "reason": p["reason"],
                "occurrences": p[
                    "occurrences"
                ],
            }
            for p in self._patterns.values()
            if p["occurrences"] >= 2
        ]

        recommendations = []
        for r in recurring:
            recommendations.append({
                "avoid": r["reason"],
                "frequency": r["occurrences"],
                "action": (
                    "Add to exclusion list"
                ),
            })

        return {
            "recurring_failures": len(
                recurring,
            ),
            "recommendations": recommendations,
            "total_patterns": len(
                self._patterns,
            ),
        }

    def get_feedback(
        self,
        transfer_id: str,
    ) -> list[dict[str, Any]]:
        """Geri bildirim getirir.

        Args:
            transfer_id: Transfer ID.

        Returns:
            Geri bildirim listesi.
        """
        return list(
            self._feedback.get(
                transfer_id, [],
            ),
        )

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayisi."""
        return self._stats[
            "feedback_collected"
        ]

    @property
    def improvement_count(self) -> int:
        """Iyilestirme sayisi."""
        return self._stats["improvements"]

    @property
    def pattern_count(self) -> int:
        """Kalip sayisi."""
        return len(self._patterns)
