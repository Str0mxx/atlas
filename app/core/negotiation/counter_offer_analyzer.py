"""ATLAS Karşı Teklif Analizcisi modülü.

Teklif ayrıştırma, değer değerlendirme,
fark analizi, niyet tespiti,
yanıt önerisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CounterOfferAnalyzer:
    """Karşı teklif analizcisi.

    Karşı teklifleri analiz eder.

    Attributes:
        _analyses: Analiz kayıtları.
        _history: Teklif geçmişi.
    """

    def __init__(self) -> None:
        """Analizcisini başlatır."""
        self._analyses: list[
            dict[str, Any]
        ] = []
        self._history: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "offers_analyzed": 0,
            "gaps_calculated": 0,
            "intents_detected": 0,
        }

        logger.info(
            "CounterOfferAnalyzer "
            "baslatildi",
        )

    def parse_offer(
        self,
        amount: float,
        terms: dict[str, Any] | None = None,
        party: str = "",
        context: str = "",
    ) -> dict[str, Any]:
        """Teklifi ayrıştırır.

        Args:
            amount: Teklif tutarı.
            terms: Koşullar.
            party: Taraf.
            context: Bağlam.

        Returns:
            Ayrıştırma bilgisi.
        """
        self._counter += 1
        pid = f"parse_{self._counter}"

        parsed = {
            "parse_id": pid,
            "amount": amount,
            "terms": terms or {},
            "party": party,
            "context": context,
            "components": {
                "base_amount": amount,
                "term_count": len(
                    terms or {},
                ),
                "has_conditions": bool(
                    terms,
                ),
            },
            "timestamp": time.time(),
        }
        self._history.append(parsed)

        return {
            "parse_id": pid,
            "amount": amount,
            "components": parsed[
                "components"
            ],
            "parsed": True,
        }

    def assess_value(
        self,
        offer_amount: float,
        our_target: float,
        our_minimum: float,
        market_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Değer değerlendirir.

        Args:
            offer_amount: Teklif tutarı.
            our_target: Hedefimiz.
            our_minimum: Minimumumuz.
            market_rate: Piyasa oranı.

        Returns:
            Değerlendirme bilgisi.
        """
        self._counter += 1
        aid = f"assess_{self._counter}"

        # Hedefle karşılaştır
        target_gap = round(
            our_target - offer_amount, 2,
        )
        target_ratio = round(
            offer_amount
            / max(our_target, 0.01)
            * 100, 1,
        )

        # Kabul edilebilirlik
        acceptable = (
            offer_amount >= our_minimum
        )

        # Piyasa karşılaştırması
        market_compare = ""
        if market_rate > 0:
            if offer_amount > market_rate * 1.1:
                market_compare = "above_market"
            elif (
                offer_amount < market_rate * 0.9
            ):
                market_compare = "below_market"
            else:
                market_compare = "at_market"

        quality = (
            "excellent"
            if target_ratio >= 100
            else "good"
            if target_ratio >= 90
            else "fair"
            if target_ratio >= 75
            else "poor"
        )

        self._stats[
            "offers_analyzed"
        ] += 1

        return {
            "assess_id": aid,
            "offer_amount": offer_amount,
            "target_gap": target_gap,
            "target_ratio": target_ratio,
            "acceptable": acceptable,
            "quality": quality,
            "market_compare": market_compare,
        }

    def analyze_gap(
        self,
        our_position: float,
        their_position: float,
    ) -> dict[str, Any]:
        """Fark analizi yapar.

        Args:
            our_position: Bizim pozisyon.
            their_position: Karşı pozisyon.

        Returns:
            Fark bilgisi.
        """
        gap = round(
            abs(
                our_position
                - their_position
            ), 2,
        )
        midpoint = round(
            (our_position + their_position)
            / 2, 2,
        )
        gap_percent = round(
            gap
            / max(our_position, 0.01)
            * 100, 1,
        )

        closable = gap_percent < 20
        difficulty = (
            "easy" if gap_percent < 10
            else "moderate"
            if gap_percent < 20
            else "hard"
            if gap_percent < 30
            else "very_hard"
        )

        self._stats[
            "gaps_calculated"
        ] += 1

        return {
            "gap": gap,
            "gap_percent": gap_percent,
            "midpoint": midpoint,
            "closable": closable,
            "difficulty": difficulty,
            "our_position": our_position,
            "their_position": their_position,
        }

    def detect_intent(
        self,
        offer_history: list[
            dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Niyet tespit eder.

        Args:
            offer_history: Teklif geçmişi.

        Returns:
            Niyet bilgisi.
        """
        if not offer_history:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "detected": False,
            }

        amounts = [
            h.get("amount", 0)
            for h in offer_history
        ]

        # Trend analizi
        if len(amounts) >= 2:
            diffs = [
                amounts[i] - amounts[i - 1]
                for i in range(
                    1, len(amounts),
                )
            ]
            avg_move = (
                sum(diffs) / len(diffs)
                if diffs else 0
            )

            if avg_move > 0:
                intent = "increasing"
                willingness = "moderate"
            elif avg_move < 0:
                intent = "decreasing"
                willingness = "high"
            else:
                intent = "firm"
                willingness = "low"
        else:
            intent = "initial"
            willingness = "unknown"
            avg_move = 0

        confidence = min(
            len(offer_history) * 25, 100,
        )

        self._stats[
            "intents_detected"
        ] += 1

        return {
            "intent": intent,
            "willingness": willingness,
            "avg_movement": round(
                avg_move, 2,
            ),
            "data_points": len(
                offer_history,
            ),
            "confidence": confidence,
            "detected": True,
        }

    def recommend_response(
        self,
        offer_amount: float,
        our_target: float,
        our_minimum: float,
        gap_percent: float = 0.0,
    ) -> dict[str, Any]:
        """Yanıt önerir.

        Args:
            offer_amount: Teklif.
            our_target: Hedef.
            our_minimum: Minimum.
            gap_percent: Fark yüzdesi.

        Returns:
            Öneri bilgisi.
        """
        if offer_amount >= our_target:
            action = "accept"
            reason = "meets_target"
            suggested = offer_amount
        elif offer_amount >= our_minimum:
            action = "counter"
            reason = "within_range"
            suggested = round(
                (offer_amount + our_target)
                / 2, 2,
            )
        elif gap_percent > 30:
            action = "reject"
            reason = "too_far_from_target"
            suggested = round(
                our_target * 0.95, 2,
            )
        else:
            action = "counter"
            reason = "negotiate_closer"
            suggested = round(
                our_minimum * 1.1, 2,
            )

        return {
            "action": action,
            "reason": reason,
            "suggested_amount": suggested,
            "offer_amount": offer_amount,
        }

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "offers_analyzed"
        ]

    @property
    def gap_count(self) -> int:
        """Fark analizi sayısı."""
        return self._stats[
            "gaps_calculated"
        ]
