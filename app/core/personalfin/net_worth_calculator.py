"""
Net değer hesaplayıcı modülü.

Varlık takibi, borç takibi, net değer
hesaplama, tarihsel trend ve
projeksiyon sağlar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NetWorthCalculator:
    """Net değer hesaplayıcı.

    Varlıkları ve borçları takip eder,
    net değer hesaplar ve trend analizi
    yapar.

    Attributes:
        _assets: Varlıklar.
        _liabilities: Borçlar.
        _history: Tarihçe.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._assets: list[dict] = []
        self._liabilities: list[dict] = []
        self._history: list[dict] = []
        self._stats: dict[str, int] = {
            "calculations": 0,
        }
        logger.info(
            "NetWorthCalculator "
            "baslatildi"
        )

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats["calculations"]

    def add_asset(
        self,
        name: str = "Asset",
        value: float = 0.0,
        asset_type: str = "cash",
    ) -> dict[str, Any]:
        """Varlık ekler.

        Args:
            name: Varlık adı.
            value: Değer.
            asset_type: Varlık türü.

        Returns:
            Varlık bilgisi.
        """
        try:
            asset = {
                "name": name,
                "value": value,
                "type": asset_type,
            }
            self._assets.append(asset)
            total = sum(
                a["value"]
                for a in self._assets
            )

            return {
                "name": name,
                "value": value,
                "type": asset_type,
                "total_assets": round(
                    total, 2
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(
                f"Varlik ekleme "
                f"hatasi: {e}"
            )
            return {
                "name": name,
                "added": False,
                "error": str(e),
            }

    def add_liability(
        self,
        name: str = "Liability",
        amount: float = 0.0,
        liability_type: str = "loan",
    ) -> dict[str, Any]:
        """Borç ekler.

        Args:
            name: Borç adı.
            amount: Tutar.
            liability_type: Borç türü.

        Returns:
            Borç bilgisi.
        """
        try:
            liability = {
                "name": name,
                "amount": amount,
                "type": liability_type,
            }
            self._liabilities.append(
                liability
            )
            total = sum(
                l["amount"]
                for l in self._liabilities
            )

            return {
                "name": name,
                "amount": amount,
                "type": liability_type,
                "total_liabilities": round(
                    total, 2
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(
                f"Borc ekleme hatasi: {e}"
            )
            return {
                "name": name,
                "added": False,
                "error": str(e),
            }

    def calculate_net_worth(
        self,
    ) -> dict[str, Any]:
        """Net değer hesaplar.

        Returns:
            Net değer bilgisi.
        """
        try:
            total_assets = sum(
                a["value"]
                for a in self._assets
            )
            total_liabilities = sum(
                l["amount"]
                for l in self._liabilities
            )
            net_worth = round(
                total_assets
                - total_liabilities,
                2,
            )

            if net_worth > 0:
                status = "positive"
            elif net_worth < 0:
                status = "negative"
            else:
                status = "zero"

            self._stats[
                "calculations"
            ] += 1
            self._history.append(
                {"net_worth": net_worth}
            )

            return {
                "total_assets": round(
                    total_assets, 2
                ),
                "total_liabilities": round(
                    total_liabilities, 2
                ),
                "net_worth": net_worth,
                "asset_count": len(
                    self._assets
                ),
                "liability_count": len(
                    self._liabilities
                ),
                "status": status,
                "calculated": True,
            }

        except Exception as e:
            logger.error(
                f"Net deger hesaplama "
                f"hatasi: {e}"
            )
            return {
                "total_assets": 0.0,
                "total_liabilities": 0.0,
                "net_worth": 0.0,
                "status": "unknown",
                "calculated": False,
                "error": str(e),
            }

    def get_trend(
        self,
    ) -> dict[str, Any]:
        """Tarihsel trend döndürür.

        Returns:
            Trend bilgisi.
        """
        try:
            values = [
                h["net_worth"]
                for h in self._history
            ]

            if len(values) < 2:
                trend = "insufficient_data"
                change = 0.0
            else:
                change = round(
                    values[-1] - values[0], 2
                )
                if change > 0:
                    trend = "improving"
                elif change < 0:
                    trend = "declining"
                else:
                    trend = "stable"

            return {
                "data_points": len(values),
                "change": change,
                "trend": trend,
                "latest": (
                    values[-1]
                    if values
                    else 0.0
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(
                f"Trend sorgulama "
                f"hatasi: {e}"
            )
            return {
                "data_points": 0,
                "change": 0.0,
                "trend": "unknown",
                "retrieved": False,
                "error": str(e),
            }

    def project_net_worth(
        self,
        monthly_savings: float = 5000.0,
        months: int = 12,
        growth_rate: float = 5.0,
    ) -> dict[str, Any]:
        """Net değer projeksiyonu yapar.

        Args:
            monthly_savings: Aylık tasarruf.
            months: Dönem (ay).
            growth_rate: Yıllık büyüme oranı.

        Returns:
            Projeksiyon bilgisi.
        """
        try:
            current = 0.0
            if self._history:
                current = self._history[
                    -1
                ]["net_worth"]

            monthly_growth = (
                growth_rate / 100 / 12
            )
            projected = current
            for _ in range(months):
                projected = (
                    projected
                    * (1 + monthly_growth)
                    + monthly_savings
                )

            projected = round(projected, 2)
            gain = round(
                projected - current, 2
            )

            return {
                "current": current,
                "projected": projected,
                "gain": gain,
                "months": months,
                "monthly_savings": (
                    monthly_savings
                ),
                "growth_rate": growth_rate,
                "projected_ok": True,
            }

        except Exception as e:
            logger.error(
                f"Projeksiyon hatasi: {e}"
            )
            return {
                "current": 0.0,
                "projected": 0.0,
                "gain": 0.0,
                "projected_ok": False,
                "error": str(e),
            }
