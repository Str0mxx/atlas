"""ATLAS Finansal Raporlayıcı modülü.

P&L raporu, bilanço, nakit akış tablosu,
özel raporlar, görselleştirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FinancialReporter:
    """Finansal raporlayıcı.

    Finansal raporlar üretir.

    Attributes:
        _reports: Rapor kayıtları.
        _data: Finansal veri deposu.
    """

    def __init__(self) -> None:
        """Raporlayıcıyı başlatır."""
        self._reports: list[
            dict[str, Any]
        ] = []
        self._data: dict[str, Any] = {
            "revenues": [],
            "expenses": [],
            "assets": {},
            "liabilities": {},
        }
        self._counter = 0
        self._stats = {
            "reports_generated": 0,
            "pnl_reports": 0,
            "balance_sheets": 0,
            "cashflow_statements": 0,
        }

        logger.info(
            "FinancialReporter baslatildi",
        )

    def add_revenue(
        self,
        amount: float,
        category: str = "sales",
        period: str = "",
    ) -> dict[str, Any]:
        """Gelir ekler.

        Args:
            amount: Tutar.
            category: Kategori.
            period: Dönem.

        Returns:
            Ekleme bilgisi.
        """
        self._data["revenues"].append({
            "amount": amount,
            "category": category,
            "period": period,
            "timestamp": time.time(),
        })
        return {
            "amount": amount,
            "category": category,
            "added": True,
        }

    def add_expense(
        self,
        amount: float,
        category: str = "operations",
        period: str = "",
    ) -> dict[str, Any]:
        """Gider ekler.

        Args:
            amount: Tutar.
            category: Kategori.
            period: Dönem.

        Returns:
            Ekleme bilgisi.
        """
        self._data["expenses"].append({
            "amount": amount,
            "category": category,
            "period": period,
            "timestamp": time.time(),
        })
        return {
            "amount": amount,
            "category": category,
            "added": True,
        }

    def set_asset(
        self,
        name: str,
        value: float,
    ) -> dict[str, Any]:
        """Varlık ayarlar."""
        self._data["assets"][name] = value
        return {
            "name": name,
            "value": value,
            "set": True,
        }

    def set_liability(
        self,
        name: str,
        value: float,
    ) -> dict[str, Any]:
        """Borç ayarlar."""
        self._data["liabilities"][name] = value
        return {
            "name": name,
            "value": value,
            "set": True,
        }

    def generate_pnl(
        self,
        period: str = "",
    ) -> dict[str, Any]:
        """P&L raporu üretir.

        Args:
            period: Dönem filtresi.

        Returns:
            P&L raporu.
        """
        self._counter += 1
        rid = f"pnl_{self._counter}"

        revenues = self._data["revenues"]
        expenses = self._data["expenses"]

        if period:
            revenues = [
                r for r in revenues
                if r["period"] == period
            ]
            expenses = [
                e for e in expenses
                if e["period"] == period
            ]

        # Kategori bazlı gelir
        rev_by_cat: dict[str, float] = {}
        for r in revenues:
            cat = r["category"]
            rev_by_cat[cat] = (
                rev_by_cat.get(cat, 0)
                + r["amount"]
            )

        # Kategori bazlı gider
        exp_by_cat: dict[str, float] = {}
        for e in expenses:
            cat = e["category"]
            exp_by_cat[cat] = (
                exp_by_cat.get(cat, 0)
                + e["amount"]
            )

        total_rev = sum(rev_by_cat.values())
        total_exp = sum(exp_by_cat.values())
        net_income = total_rev - total_exp
        margin = (
            round(
                net_income / total_rev * 100,
                2,
            )
            if total_rev > 0 else 0.0
        )

        report = {
            "report_id": rid,
            "type": "pnl",
            "period": period or "all",
            "revenue": {
                "by_category": {
                    k: round(v, 2)
                    for k, v
                    in rev_by_cat.items()
                },
                "total": round(total_rev, 2),
            },
            "expenses": {
                "by_category": {
                    k: round(v, 2)
                    for k, v
                    in exp_by_cat.items()
                },
                "total": round(total_exp, 2),
            },
            "net_income": round(
                net_income, 2,
            ),
            "margin_percent": margin,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1
        self._stats["pnl_reports"] += 1

        return report

    def generate_balance_sheet(
        self,
    ) -> dict[str, Any]:
        """Bilanço üretir.

        Returns:
            Bilanço raporu.
        """
        self._counter += 1
        rid = f"bs_{self._counter}"

        total_assets = sum(
            self._data["assets"].values(),
        )
        total_liabilities = sum(
            self._data[
                "liabilities"
            ].values(),
        )
        equity = (
            total_assets - total_liabilities
        )

        report = {
            "report_id": rid,
            "type": "balance_sheet",
            "assets": {
                k: round(v, 2)
                for k, v
                in self._data["assets"].items()
            },
            "total_assets": round(
                total_assets, 2,
            ),
            "liabilities": {
                k: round(v, 2)
                for k, v in self._data[
                    "liabilities"
                ].items()
            },
            "total_liabilities": round(
                total_liabilities, 2,
            ),
            "equity": round(equity, 2),
            "balanced": True,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1
        self._stats["balance_sheets"] += 1

        return report

    def generate_cashflow_statement(
        self,
    ) -> dict[str, Any]:
        """Nakit akış tablosu üretir.

        Returns:
            Nakit akış raporu.
        """
        self._counter += 1
        rid = f"cfs_{self._counter}"

        total_inflows = sum(
            r["amount"]
            for r in self._data["revenues"]
        )
        total_outflows = sum(
            e["amount"]
            for e in self._data["expenses"]
        )
        net_flow = total_inflows - total_outflows

        report = {
            "report_id": rid,
            "type": "cashflow_statement",
            "operating": {
                "inflows": round(
                    total_inflows, 2,
                ),
                "outflows": round(
                    total_outflows, 2,
                ),
                "net": round(net_flow, 2),
            },
            "net_change": round(net_flow, 2),
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1
        self._stats[
            "cashflow_statements"
        ] += 1

        return report

    def generate_custom(
        self,
        title: str,
        metrics: dict[str, Any],
        period: str = "",
    ) -> dict[str, Any]:
        """Özel rapor üretir.

        Args:
            title: Rapor başlığı.
            metrics: Metrikler.
            period: Dönem.

        Returns:
            Özel rapor.
        """
        self._counter += 1
        rid = f"custom_{self._counter}"

        report = {
            "report_id": rid,
            "type": "custom",
            "title": title,
            "period": period or "all",
            "metrics": metrics,
            "generated_at": time.time(),
        }
        self._reports.append(report)
        self._stats["reports_generated"] += 1

        return report

    def get_visualization_data(
        self,
        chart_type: str = "bar",
    ) -> dict[str, Any]:
        """Görselleştirme verisi döndürür.

        Args:
            chart_type: Grafik tipi.

        Returns:
            Veri bilgisi.
        """
        rev_by_cat: dict[str, float] = {}
        for r in self._data["revenues"]:
            cat = r["category"]
            rev_by_cat[cat] = (
                rev_by_cat.get(cat, 0)
                + r["amount"]
            )

        exp_by_cat: dict[str, float] = {}
        for e in self._data["expenses"]:
            cat = e["category"]
            exp_by_cat[cat] = (
                exp_by_cat.get(cat, 0)
                + e["amount"]
            )

        return {
            "chart_type": chart_type,
            "revenue_data": rev_by_cat,
            "expense_data": exp_by_cat,
            "labels": list(
                set(
                    list(rev_by_cat.keys())
                    + list(exp_by_cat.keys())
                ),
            ),
        }

    @property
    def report_count(self) -> int:
        """Rapor sayısı."""
        return self._stats[
            "reports_generated"
        ]

    @property
    def pnl_count(self) -> int:
        """P&L rapor sayısı."""
        return self._stats["pnl_reports"]
