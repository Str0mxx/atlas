"""ATLAS Müzakere Strateji Planlayıcı modülü.

Strateji seçimi, BATNA hesaplama,
hedef belirleme, taktik planlama,
risk değerlendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NegotiationStrategyPlanner:
    """Müzakere strateji planlayıcı.

    Müzakere stratejilerini planlar.

    Attributes:
        _strategies: Strateji kayıtları.
        _batna: BATNA değerleri.
    """

    def __init__(
        self,
        default_strategy: str = "collaborative",
    ) -> None:
        """Planlayıcıyı başlatır.

        Args:
            default_strategy: Varsayılan strateji.
        """
        self._strategies: list[
            dict[str, Any]
        ] = []
        self._batna: dict[str, Any] = {}
        self._goals: list[
            dict[str, Any]
        ] = []
        self._tactics: list[
            dict[str, Any]
        ] = []
        self._default_strategy = default_strategy
        self._counter = 0
        self._stats = {
            "strategies_created": 0,
            "batna_calculated": 0,
            "goals_set": 0,
        }

        logger.info(
            "NegotiationStrategyPlanner "
            "baslatildi",
        )

    def select_strategy(
        self,
        context: str = "",
        relationship: str = "neutral",
        power_balance: str = "equal",
        importance: str = "medium",
    ) -> dict[str, Any]:
        """Strateji seçer.

        Args:
            context: Müzakere bağlamı.
            relationship: İlişki durumu.
            power_balance: Güç dengesi.
            importance: Önem derecesi.

        Returns:
            Strateji bilgisi.
        """
        self._counter += 1
        sid = f"strat_{self._counter}"

        # Strateji seçim mantığı
        if relationship == "long_term":
            strategy = "collaborative"
        elif power_balance == "strong":
            strategy = "competitive"
        elif importance == "low":
            strategy = "compromising"
        else:
            strategy = self._default_strategy

        # Taktikler
        tactics = self._plan_tactics(strategy)

        record = {
            "strategy_id": sid,
            "strategy": strategy,
            "context": context,
            "relationship": relationship,
            "power_balance": power_balance,
            "importance": importance,
            "tactics": tactics,
            "timestamp": time.time(),
        }
        self._strategies.append(record)
        self._stats["strategies_created"] += 1

        return {
            "strategy_id": sid,
            "strategy": strategy,
            "tactics": tactics,
            "created": True,
        }

    def calculate_batna(
        self,
        negotiation_id: str,
        alternatives: list[dict[str, Any]],
        current_best: float = 0.0,
    ) -> dict[str, Any]:
        """BATNA hesaplar.

        Args:
            negotiation_id: Müzakere ID.
            alternatives: Alternatifler.
            current_best: Mevcut en iyi.

        Returns:
            BATNA bilgisi.
        """
        if not alternatives:
            batna_value = current_best
            best_alt = "no_alternative"
        else:
            # En iyi alternatifi bul
            best = max(
                alternatives,
                key=lambda a: a.get(
                    "value", 0,
                ),
            )
            batna_value = best.get("value", 0)
            best_alt = best.get(
                "name", "unknown",
            )

        self._batna[negotiation_id] = {
            "value": batna_value,
            "best_alternative": best_alt,
            "alternatives_count": len(
                alternatives,
            ),
            "timestamp": time.time(),
        }
        self._stats["batna_calculated"] += 1

        return {
            "negotiation_id": negotiation_id,
            "batna_value": batna_value,
            "best_alternative": best_alt,
            "alternatives": len(alternatives),
            "calculated": True,
        }

    def set_goals(
        self,
        negotiation_id: str,
        target: float,
        minimum: float,
        optimistic: float = 0.0,
        priorities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Hedef belirler.

        Args:
            negotiation_id: Müzakere ID.
            target: Hedef değer.
            minimum: Minimum kabul.
            optimistic: İyimser hedef.
            priorities: Öncelikler.

        Returns:
            Hedef bilgisi.
        """
        self._counter += 1
        gid = f"goal_{self._counter}"

        if optimistic == 0.0:
            optimistic = target * 1.2

        goal = {
            "goal_id": gid,
            "negotiation_id": negotiation_id,
            "target": target,
            "minimum": minimum,
            "optimistic": optimistic,
            "priorities": priorities or [],
            "range": optimistic - minimum,
            "timestamp": time.time(),
        }
        self._goals.append(goal)
        self._stats["goals_set"] += 1

        return {
            "goal_id": gid,
            "target": target,
            "minimum": minimum,
            "optimistic": round(
                optimistic, 2,
            ),
            "range": round(
                optimistic - minimum, 2,
            ),
            "set": True,
        }

    def _plan_tactics(
        self,
        strategy: str,
    ) -> list[str]:
        """Taktik planlar."""
        tactics_map = {
            "collaborative": [
                "build_rapport",
                "share_interests",
                "brainstorm_options",
                "focus_on_value",
            ],
            "competitive": [
                "anchor_high",
                "leverage_power",
                "time_pressure",
                "limited_concessions",
            ],
            "compromising": [
                "split_difference",
                "mutual_concessions",
                "quick_resolution",
            ],
            "accommodating": [
                "show_goodwill",
                "prioritize_relationship",
                "flexible_terms",
            ],
            "avoiding": [
                "delay_decision",
                "gather_information",
                "wait_for_better_timing",
            ],
        }
        return tactics_map.get(
            strategy, ["negotiate_fairly"],
        )

    def assess_risk(
        self,
        negotiation_id: str,
        factors: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Risk değerlendirmesi yapar.

        Args:
            negotiation_id: Müzakere ID.
            factors: Risk faktörleri.

        Returns:
            Risk bilgisi.
        """
        factors = factors or {}

        risk_score = 0.0
        risks = []

        # BATNA yoksa risk yüksek
        if negotiation_id not in self._batna:
            risk_score += 30
            risks.append("no_batna")

        # Güç dengesi zayıfsa
        if factors.get(
            "power_balance",
        ) == "weak":
            risk_score += 25
            risks.append("weak_position")

        # Zaman baskısı varsa
        if factors.get("time_pressure", False):
            risk_score += 20
            risks.append("time_pressure")

        # Bilgi eksikliği
        if factors.get(
            "info_gap", False,
        ):
            risk_score += 15
            risks.append(
                "information_gap",
            )

        risk_level = (
            "low" if risk_score < 30
            else "medium" if risk_score < 60
            else "high"
        )

        return {
            "negotiation_id": negotiation_id,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risks": risks,
            "assessed": True,
        }

    def get_batna(
        self,
        negotiation_id: str,
    ) -> dict[str, Any] | None:
        """BATNA bilgisini döndürür."""
        return self._batna.get(
            negotiation_id,
        )

    @property
    def strategy_count(self) -> int:
        """Strateji sayısı."""
        return self._stats[
            "strategies_created"
        ]

    @property
    def goal_count(self) -> int:
        """Hedef sayısı."""
        return self._stats["goals_set"]
