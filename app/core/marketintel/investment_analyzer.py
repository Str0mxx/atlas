"""ATLAS Yatırım Analizcisi modülü.

Fonlama takibi, yatırım kalıpları,
değerleme trendleri, yatırımcı eşleme,
anlaşma akışı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class InvestmentAnalyzer:
    """Yatırım analizcisi.

    Yatırım ve fonlama verilerini analiz eder.

    Attributes:
        _investments: Yatırım kayıtları.
        _investors: Yatırımcı haritası.
    """

    def __init__(self) -> None:
        """Analizciyı başlatır."""
        self._investments: list[
            dict[str, Any]
        ] = []
        self._investors: dict[
            str, dict[str, Any]
        ] = {}
        self._deals: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "investments_tracked": 0,
            "investors_mapped": 0,
            "deals_analyzed": 0,
        }

        logger.info(
            "InvestmentAnalyzer baslatildi",
        )

    def track_investment(
        self,
        company: str,
        amount: float,
        round_type: str = "seed",
        investors: list[str] | None = None,
        sector: str = "",
    ) -> dict[str, Any]:
        """Yatırımı takip eder.

        Args:
            company: Şirket.
            amount: Miktar.
            round_type: Tur tipi.
            investors: Yatırımcılar.
            sector: Sektör.

        Returns:
            Takip bilgisi.
        """
        self._counter += 1
        iid = f"inv_{self._counter}"

        investment = {
            "investment_id": iid,
            "company": company,
            "amount": amount,
            "round_type": round_type,
            "investors": investors or [],
            "sector": sector,
            "tracked_at": time.time(),
        }
        self._investments.append(investment)
        self._stats[
            "investments_tracked"
        ] += 1

        return {
            "investment_id": iid,
            "company": company,
            "amount": amount,
            "round_type": round_type,
            "tracked": True,
        }

    def analyze_patterns(
        self,
        sector: str | None = None,
    ) -> dict[str, Any]:
        """Yatırım kalıplarını analiz eder.

        Args:
            sector: Sektör filtresi.

        Returns:
            Analiz bilgisi.
        """
        investments = self._investments
        if sector:
            investments = [
                i for i in investments
                if i["sector"] == sector
            ]

        if not investments:
            return {
                "total": 0,
                "patterns": [],
            }

        total_amount = sum(
            i["amount"] for i in investments
        )
        avg_amount = (
            total_amount / len(investments)
        )

        # Tur dağılımı
        rounds: dict[str, int] = {}
        for inv in investments:
            rt = inv["round_type"]
            rounds[rt] = rounds.get(rt, 0) + 1

        return {
            "total_investments": len(
                investments,
            ),
            "total_amount": total_amount,
            "avg_amount": round(
                avg_amount, 2,
            ),
            "round_distribution": rounds,
            "top_round": max(
                rounds,
                key=rounds.get,
            ) if rounds else None,
        }

    def get_valuation_trends(
        self,
        company: str | None = None,
    ) -> dict[str, Any]:
        """Değerleme trendlerini getirir.

        Args:
            company: Şirket filtresi.

        Returns:
            Trend bilgisi.
        """
        investments = self._investments
        if company:
            investments = [
                i for i in investments
                if i["company"] == company
            ]

        if not investments:
            return {
                "valuations": [],
                "trend": "insufficient_data",
            }

        amounts = [
            i["amount"]
            for i in investments
        ]
        trend = (
            "increasing"
            if len(amounts) >= 2
            and amounts[-1] > amounts[0]
            else "stable"
            if len(amounts) < 2
            else "decreasing"
        )

        return {
            "valuations": amounts,
            "trend": trend,
            "latest": amounts[-1],
            "count": len(amounts),
        }

    def map_investor(
        self,
        name: str,
        focus_areas: list[str] | None = None,
        portfolio_size: int = 0,
        avg_check_size: float = 0.0,
    ) -> dict[str, Any]:
        """Yatırımcı haritalar.

        Args:
            name: Yatırımcı adı.
            focus_areas: Odak alanları.
            portfolio_size: Portföy boyutu.
            avg_check_size: Ort. yatırım.

        Returns:
            Haritalama bilgisi.
        """
        self._counter += 1
        mid = f"imap_{self._counter}"

        investor = {
            "investor_id": mid,
            "name": name,
            "focus_areas": focus_areas or [],
            "portfolio_size": portfolio_size,
            "avg_check_size": avg_check_size,
            "investments": [],
            "mapped_at": time.time(),
        }
        self._investors[mid] = investor
        self._stats["investors_mapped"] += 1

        return {
            "investor_id": mid,
            "name": name,
            "mapped": True,
        }

    def analyze_deal_flow(
        self,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Anlaşma akışını analiz eder.

        Args:
            period_days: Dönem (gün).

        Returns:
            Analiz bilgisi.
        """
        cutoff = (
            time.time()
            - period_days * 86400
        )
        recent = [
            i for i in self._investments
            if i["tracked_at"] >= cutoff
        ]

        total = sum(
            i["amount"] for i in recent
        )

        return {
            "period_days": period_days,
            "deal_count": len(recent),
            "total_amount": total,
            "avg_deal": round(
                total / max(len(recent), 1),
                2,
            ),
        }

    @property
    def investment_count(self) -> int:
        """Yatırım sayısı."""
        return self._stats[
            "investments_tracked"
        ]

    @property
    def investor_count(self) -> int:
        """Yatırımcı sayısı."""
        return len(self._investors)
