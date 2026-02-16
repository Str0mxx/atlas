"""ATLAS Risk-Getiri Haritacısı.

Risk değerlendirme, getiri projeksiyonu,
etkin sınır, Sharpe oranı, risk-ayarlı getiri.
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class RiskReturnMapper:
    """Risk-getiri haritacısı.

    Risk ve getiri profillerini haritalandırır,
    Sharpe oranı ve risk-ayarlı getiri hesaplar.

    Attributes:
        _mappings: Haritalama kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Haritacıyı başlatır."""
        self._mappings: list[dict] = []
        self._stats = {
            "assessments_made": 0,
            "sharpe_calculated": 0,
        }
        logger.info(
            "RiskReturnMapper baslatildi",
        )

    @property
    def assessment_count(self) -> int:
        """Değerlendirme sayısı."""
        return self._stats[
            "assessments_made"
        ]

    @property
    def sharpe_count(self) -> int:
        """Sharpe hesaplama sayısı."""
        return self._stats[
            "sharpe_calculated"
        ]

    def assess_risk(
        self,
        investment_id: str,
        volatility: float = 0.0,
        market_risk: float = 0.5,
        credit_risk: float = 0.3,
        liquidity_risk: float = 0.2,
    ) -> dict[str, Any]:
        """Risk değerlendirir.

        Args:
            investment_id: Yatırım kimliği.
            volatility: Volatilite (0-1).
            market_risk: Pazar riski (0-1).
            credit_risk: Kredi riski (0-1).
            liquidity_risk: Likidite (0-1).

        Returns:
            Risk bilgisi.
        """
        composite = round(
            volatility * 0.3
            + market_risk * 0.3
            + credit_risk * 0.2
            + liquidity_risk * 0.2,
            3,
        )

        if composite >= 0.7:
            level = "very_high"
        elif composite >= 0.5:
            level = "high"
        elif composite >= 0.3:
            level = "moderate"
        elif composite >= 0.15:
            level = "low"
        else:
            level = "very_low"

        self._stats[
            "assessments_made"
        ] += 1

        return {
            "investment_id": investment_id,
            "composite_risk": composite,
            "level": level,
            "assessed": True,
        }

    def project_return(
        self,
        investment_id: str,
        base_return: float = 0.0,
        growth_factor: float = 1.0,
        years: int = 5,
    ) -> dict[str, Any]:
        """Getiri projeksiyonu yapar.

        Args:
            investment_id: Yatırım kimliği.
            base_return: Temel getiri (%).
            growth_factor: Büyüme faktörü.
            years: Yıl sayısı.

        Returns:
            Projeksiyon bilgisi.
        """
        annual = round(
            base_return * growth_factor,
            2,
        )
        cumulative = round(
            (
                (1 + annual / 100) ** years
                - 1
            )
            * 100,
            2,
        )

        return {
            "investment_id": investment_id,
            "annual_return": annual,
            "cumulative_return": cumulative,
            "years": years,
            "projected": True,
        }

    def calculate_efficient_frontier(
        self,
        investments: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Etkin sınır hesaplar.

        Args:
            investments: Yatırımlar
                [{name, return_pct, risk}].

        Returns:
            Etkin sınır bilgisi.
        """
        if investments is None:
            investments = []

        efficient = []
        for inv in investments:
            ret = inv.get(
                "return_pct", 0,
            )
            risk = inv.get("risk", 0)
            is_efficient = True

            for other in investments:
                o_ret = other.get(
                    "return_pct", 0,
                )
                o_risk = other.get(
                    "risk", 0,
                )
                if (
                    o_ret >= ret
                    and o_risk < risk
                    and other != inv
                ):
                    is_efficient = False
                    break

            if is_efficient:
                efficient.append(
                    inv.get("name", ""),
                )

        return {
            "total_investments": len(
                investments,
            ),
            "efficient_set": efficient,
            "efficient_count": len(
                efficient,
            ),
            "calculated": True,
        }

    def calculate_sharpe(
        self,
        investment_return: float = 0.0,
        risk_free_rate: float = 3.0,
        std_deviation: float = 1.0,
    ) -> dict[str, Any]:
        """Sharpe oranı hesaplar.

        Args:
            investment_return: Yatırım getirisi.
            risk_free_rate: Risksiz oran (%).
            std_deviation: Standart sapma (%).

        Returns:
            Sharpe bilgisi.
        """
        if std_deviation <= 0:
            std_deviation = 0.01

        sharpe = round(
            (
                investment_return
                - risk_free_rate
            )
            / std_deviation,
            3,
        )

        if sharpe >= 2.0:
            quality = "excellent"
        elif sharpe >= 1.0:
            quality = "good"
        elif sharpe >= 0.5:
            quality = "adequate"
        elif sharpe >= 0:
            quality = "poor"
        else:
            quality = "negative"

        self._stats[
            "sharpe_calculated"
        ] += 1

        return {
            "sharpe_ratio": sharpe,
            "quality": quality,
            "excess_return": round(
                investment_return
                - risk_free_rate,
                2,
            ),
            "calculated": True,
        }

    def risk_adjusted_return(
        self,
        investment_id: str,
        raw_return: float = 0.0,
        risk_score: float = 0.5,
    ) -> dict[str, Any]:
        """Risk-ayarlı getiri hesaplar.

        Args:
            investment_id: Yatırım kimliği.
            raw_return: Ham getiri (%).
            risk_score: Risk puanı (0-1).

        Returns:
            Risk-ayarlı bilgisi.
        """
        risk_penalty = risk_score * 100
        adjusted = round(
            raw_return
            - risk_penalty * 0.1,
            2,
        )

        return {
            "investment_id": investment_id,
            "raw_return": raw_return,
            "risk_adjusted_return": adjusted,
            "risk_penalty": round(
                risk_penalty * 0.1, 2,
            ),
            "attractive": adjusted > 0,
            "calculated": True,
        }
