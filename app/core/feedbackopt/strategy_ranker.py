"""ATLAS Strateji Sıralayıcı modülü.

Strateji puanlama, performans sıralama,
etkinlik ölçümü, karşılaştırma analizi,
en iyi uygulama çıkarma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class StrategyRanker:
    """Strateji sıralayıcı.

    Stratejileri performanslarına göre sıralar.

    Attributes:
        _strategies: Strateji kayıtları.
        _rankings: Sıralama geçmişi.
    """

    def __init__(self) -> None:
        """Sıralayıcıyı başlatır."""
        self._strategies: dict[
            str, dict[str, Any]
        ] = {}
        self._rankings: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "strategies_scored": 0,
            "rankings_generated": 0,
        }

        logger.info(
            "StrategyRanker baslatildi",
        )

    def score_strategy(
        self,
        strategy_id: str,
        success_rate: float = 0.0,
        efficiency: float = 0.0,
        cost: float = 0.0,
        user_satisfaction: float = 0.0,
    ) -> dict[str, Any]:
        """Strateji puanlar.

        Args:
            strategy_id: Strateji ID.
            success_rate: Başarı oranı.
            efficiency: Verimlilik.
            cost: Maliyet (düşük=iyi).
            user_satisfaction: Kullanıcı memnuniyeti.

        Returns:
            Puanlama bilgisi.
        """
        # Maliyet ters çevrilir
        cost_score = max(
            100 - cost, 0,
        )
        total = round(
            success_rate * 0.35
            + efficiency * 0.25
            + cost_score * 0.15
            + user_satisfaction * 0.25,
            1,
        )

        self._strategies[strategy_id] = {
            "strategy_id": strategy_id,
            "success_rate": success_rate,
            "efficiency": efficiency,
            "cost": cost,
            "user_satisfaction": (
                user_satisfaction
            ),
            "total_score": total,
            "timestamp": time.time(),
        }
        self._stats[
            "strategies_scored"
        ] += 1

        return {
            "strategy_id": strategy_id,
            "total_score": total,
            "scored": True,
        }

    def rank_performance(
        self,
        top_n: int = 10,
    ) -> dict[str, Any]:
        """Performans sıralaması yapar.

        Args:
            top_n: Üst N.

        Returns:
            Sıralama bilgisi.
        """
        if not self._strategies:
            return {
                "rankings": [],
                "ranked": False,
            }

        sorted_strats = sorted(
            self._strategies.values(),
            key=lambda s: s["total_score"],
            reverse=True,
        )[:top_n]

        rankings = [
            {
                "rank": i + 1,
                "strategy_id": s[
                    "strategy_id"
                ],
                "score": s["total_score"],
            }
            for i, s in enumerate(
                sorted_strats,
            )
        ]

        self._rankings.append({
            "rankings": rankings,
            "timestamp": time.time(),
        })
        self._stats[
            "rankings_generated"
        ] += 1

        return {
            "rankings": rankings,
            "total_strategies": len(
                self._strategies,
            ),
            "ranked": True,
        }

    def measure_effectiveness(
        self,
        strategy_id: str,
        target: float = 80.0,
    ) -> dict[str, Any]:
        """Etkinlik ölçer.

        Args:
            strategy_id: Strateji ID.
            target: Hedef puan.

        Returns:
            Etkinlik bilgisi.
        """
        strat = self._strategies.get(
            strategy_id,
        )
        if not strat:
            return {
                "strategy_id": strategy_id,
                "measured": False,
            }

        score = strat["total_score"]
        effectiveness = round(
            score / target * 100, 1,
        ) if target > 0 else 0.0

        level = (
            "excellent"
            if effectiveness >= 120
            else "good"
            if effectiveness >= 100
            else "acceptable"
            if effectiveness >= 80
            else "poor"
        )

        return {
            "strategy_id": strategy_id,
            "score": score,
            "target": target,
            "effectiveness_pct": (
                effectiveness
            ),
            "level": level,
            "measured": True,
        }

    def compare_strategies(
        self,
        strategy_a: str,
        strategy_b: str,
    ) -> dict[str, Any]:
        """Strateji karşılaştırır.

        Args:
            strategy_a: Strateji A.
            strategy_b: Strateji B.

        Returns:
            Karşılaştırma bilgisi.
        """
        sa = self._strategies.get(
            strategy_a,
        )
        sb = self._strategies.get(
            strategy_b,
        )

        if not sa or not sb:
            return {
                "compared": False,
                "reason": "Strategy not found",
            }

        diff = round(
            sa["total_score"]
            - sb["total_score"],
            1,
        )
        winner = (
            strategy_a if diff > 0
            else strategy_b if diff < 0
            else "tie"
        )

        return {
            "strategy_a": strategy_a,
            "score_a": sa["total_score"],
            "strategy_b": strategy_b,
            "score_b": sb["total_score"],
            "difference": abs(diff),
            "winner": winner,
            "compared": True,
        }

    def extract_best_practices(
        self,
        min_score: float = 75.0,
    ) -> dict[str, Any]:
        """En iyi uygulamaları çıkarır.

        Args:
            min_score: Min puan.

        Returns:
            Uygulama bilgisi.
        """
        top = [
            s for s
            in self._strategies.values()
            if s["total_score"] >= min_score
        ]

        if not top:
            return {
                "practices": [],
                "extracted": False,
            }

        practices = []
        for s in top:
            if s["success_rate"] >= 80:
                practices.append({
                    "strategy": s[
                        "strategy_id"
                    ],
                    "factor": "high_success",
                    "value": s[
                        "success_rate"
                    ],
                })
            if s["efficiency"] >= 80:
                practices.append({
                    "strategy": s[
                        "strategy_id"
                    ],
                    "factor": (
                        "high_efficiency"
                    ),
                    "value": s["efficiency"],
                })

        return {
            "practices": practices,
            "practice_count": len(practices),
            "top_strategies": len(top),
            "extracted": True,
        }

    @property
    def strategy_count(self) -> int:
        """Strateji sayısı."""
        return self._stats[
            "strategies_scored"
        ]

    @property
    def ranking_count(self) -> int:
        """Sıralama sayısı."""
        return self._stats[
            "rankings_generated"
        ]
