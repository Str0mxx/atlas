"""
Kişisel yatırım takipçisi modülü.

Portföy takibi, performans analizi,
dağılım görünümü, temettü takibi
ve vergi etkileri sağlar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PersonalInvestmentTracker:
    """Kişisel yatırım takipçisi.

    Yatırım portföyünü takip eder,
    performans analizi ve dağılım
    görünümü sağlar.

    Attributes:
        _holdings: Yatırım varlıkları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._holdings: list[dict] = []
        self._stats: dict[str, int] = {
            "holdings_tracked": 0,
        }
        logger.info(
            "PersonalInvestmentTracker "
            "baslatildi"
        )

    @property
    def holding_count(self) -> int:
        """Yatırım sayısı."""
        return len(self._holdings)

    def add_holding(
        self,
        name: str = "Stock",
        inv_type: str = "stocks",
        amount: float = 0.0,
        cost_basis: float = 0.0,
    ) -> dict[str, Any]:
        """Yatırım ekler.

        Args:
            name: Yatırım adı.
            inv_type: Yatırım türü.
            amount: Mevcut değer.
            cost_basis: Maliyet.

        Returns:
            Yatırım bilgisi.
        """
        try:
            hid = f"inv_{uuid4()!s:.8}"
            holding = {
                "holding_id": hid,
                "name": name,
                "type": inv_type,
                "current_value": amount,
                "cost_basis": cost_basis,
                "dividends": 0.0,
            }
            self._holdings.append(holding)
            self._stats[
                "holdings_tracked"
            ] += 1

            gain = round(
                amount - cost_basis, 2
            )
            gain_pct = round(
                (
                    gain
                    / max(cost_basis, 1)
                )
                * 100,
                1,
            )

            return {
                "holding_id": hid,
                "name": name,
                "type": inv_type,
                "current_value": amount,
                "gain": gain,
                "gain_pct": gain_pct,
                "added": True,
            }

        except Exception as e:
            logger.error(
                f"Yatirim ekleme "
                f"hatasi: {e}"
            )
            return {
                "holding_id": "",
                "name": name,
                "added": False,
                "error": str(e),
            }

    def analyze_performance(
        self,
    ) -> dict[str, Any]:
        """Portföy performansı analiz eder.

        Returns:
            Performans analizi.
        """
        try:
            if not self._holdings:
                return {
                    "total_value": 0.0,
                    "total_cost": 0.0,
                    "total_gain": 0.0,
                    "return_pct": 0.0,
                    "analyzed": True,
                }

            total_val = sum(
                h["current_value"]
                for h in self._holdings
            )
            total_cost = sum(
                h["cost_basis"]
                for h in self._holdings
            )
            total_gain = round(
                total_val - total_cost, 2
            )
            ret_pct = round(
                (
                    total_gain
                    / max(total_cost, 1)
                )
                * 100,
                1,
            )

            return {
                "total_value": round(
                    total_val, 2
                ),
                "total_cost": round(
                    total_cost, 2
                ),
                "total_gain": total_gain,
                "return_pct": ret_pct,
                "holding_count": len(
                    self._holdings
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(
                f"Performans analiz "
                f"hatasi: {e}"
            )
            return {
                "total_value": 0.0,
                "total_gain": 0.0,
                "return_pct": 0.0,
                "analyzed": False,
                "error": str(e),
            }

    def view_allocation(
        self,
    ) -> dict[str, Any]:
        """Dağılım görünümü sağlar.

        Returns:
            Dağılım bilgisi.
        """
        try:
            if not self._holdings:
                return {
                    "allocation": {},
                    "type_count": 0,
                    "diversified": False,
                    "viewed": True,
                }

            total = sum(
                h["current_value"]
                for h in self._holdings
            )
            by_type: dict[str, float] = {}
            for h in self._holdings:
                t = h["type"]
                by_type[t] = (
                    by_type.get(t, 0)
                    + h["current_value"]
                )

            allocation = {
                t: round(
                    (v / max(total, 1)) * 100,
                    1,
                )
                for t, v in by_type.items()
            }

            diversified = len(by_type) >= 3

            return {
                "allocation": allocation,
                "type_count": len(by_type),
                "diversified": diversified,
                "total_value": round(
                    total, 2
                ),
                "viewed": True,
            }

        except Exception as e:
            logger.error(
                f"Dagilim goruntuleme "
                f"hatasi: {e}"
            )
            return {
                "allocation": {},
                "type_count": 0,
                "diversified": False,
                "viewed": False,
                "error": str(e),
            }

    def track_dividends(
        self,
        holding_id: str,
        dividend: float = 0.0,
    ) -> dict[str, Any]:
        """Temettü takibi yapar.

        Args:
            holding_id: Yatırım ID.
            dividend: Temettü tutarı.

        Returns:
            Temettü bilgisi.
        """
        try:
            for h in self._holdings:
                if h["holding_id"] == (
                    holding_id
                ):
                    h["dividends"] += (
                        dividend
                    )
                    yield_pct = round(
                        (
                            h["dividends"]
                            / max(
                                h[
                                    "current_value"
                                ],
                                1,
                            )
                        )
                        * 100,
                        2,
                    )

                    return {
                        "holding_id": (
                            holding_id
                        ),
                        "dividend": dividend,
                        "total_dividends": (
                            round(
                                h[
                                    "dividends"
                                ],
                                2,
                            )
                        ),
                        "yield_pct": (
                            yield_pct
                        ),
                        "tracked": True,
                    }

            return {
                "holding_id": holding_id,
                "tracked": False,
                "error": "holding_not_found",
            }

        except Exception as e:
            logger.error(
                f"Temettu takip "
                f"hatasi: {e}"
            )
            return {
                "holding_id": holding_id,
                "tracked": False,
                "error": str(e),
            }

    def calculate_tax(
        self,
        gains: float = 0.0,
        tax_rate: float = 15.0,
        holding_period_months: int = 12,
    ) -> dict[str, Any]:
        """Vergi etkisi hesaplar.

        Args:
            gains: Kazanç.
            tax_rate: Vergi oranı.
            holding_period_months: Elde tutma.

        Returns:
            Vergi bilgisi.
        """
        try:
            if holding_period_months >= 12:
                effective_rate = (
                    tax_rate * 0.5
                )
                term = "long_term"
            else:
                effective_rate = tax_rate
                term = "short_term"

            tax = round(
                gains * effective_rate / 100,
                2,
            )
            after_tax = round(
                gains - tax, 2
            )

            return {
                "gains": gains,
                "tax_rate": effective_rate,
                "term": term,
                "tax_amount": tax,
                "after_tax_gains": after_tax,
                "calculated": True,
            }

        except Exception as e:
            logger.error(
                f"Vergi hesaplama "
                f"hatasi: {e}"
            )
            return {
                "gains": gains,
                "tax_amount": 0.0,
                "after_tax_gains": gains,
                "calculated": False,
                "error": str(e),
            }
