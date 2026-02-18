"""
Nakit akis grafigi modulu.

Giris/cikis, net nakit akisi,
pist hesaplama, tahmin katmani,
kritik noktalar.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CashFlowGraph:
    """Nakit akis grafigi.

    Attributes:
        _flows: Nakit akis kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Grafigi baslatir."""
        self._flows: list[dict] = []
        self._stats: dict[str, int] = {
            "flows_recorded": 0,
            "forecasts_generated": 0,
        }
        logger.info(
            "CashFlowGraph baslatildi"
        )

    @property
    def flow_count(self) -> int:
        """Akis sayisi."""
        return len(self._flows)

    def record_flow(
        self,
        amount: float = 0.0,
        flow_type: str = "inflow",
        source: str = "",
        period: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Nakit akisi kaydeder.

        Args:
            amount: Tutar.
            flow_type: Akis turu (inflow/outflow).
            source: Kaynak.
            period: Donem.
            description: Aciklama.

        Returns:
            Kayit bilgisi.
        """
        try:
            fid = f"cf_{uuid4()!s:.8}"
            flow = {
                "flow_id": fid,
                "amount": abs(amount),
                "flow_type": flow_type,
                "source": source,
                "period": period,
                "description": description,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._flows.append(flow)
            self._stats[
                "flows_recorded"
            ] += 1

            return {
                "flow_id": fid,
                "amount": abs(amount),
                "flow_type": flow_type,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_inflow_outflow(
        self,
    ) -> dict[str, Any]:
        """Giris/cikis ozeti getirir.

        Returns:
            Giris/cikis bilgisi.
        """
        try:
            inflow = sum(
                f["amount"]
                for f in self._flows
                if f["flow_type"] == "inflow"
            )
            outflow = sum(
                f["amount"]
                for f in self._flows
                if f["flow_type"] == "outflow"
            )
            net = inflow - outflow

            return {
                "total_inflow": round(
                    inflow, 2
                ),
                "total_outflow": round(
                    outflow, 2
                ),
                "net_cash_flow": round(
                    net, 2
                ),
                "is_positive": net >= 0,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_period_breakdown(
        self,
    ) -> dict[str, Any]:
        """Donem bazli dagilim getirir.

        Returns:
            Donem dagilimi.
        """
        try:
            periods: dict[
                str, dict[str, float]
            ] = {}
            for f in self._flows:
                period = f.get(
                    "period", "unknown"
                )
                if period not in periods:
                    periods[period] = {
                        "inflow": 0.0,
                        "outflow": 0.0,
                    }
                periods[period][
                    f["flow_type"]
                ] += f["amount"]

            data = [
                {
                    "period": p,
                    "inflow": round(
                        d["inflow"], 2
                    ),
                    "outflow": round(
                        d["outflow"], 2
                    ),
                    "net": round(
                        d["inflow"]
                        - d["outflow"],
                        2,
                    ),
                }
                for p, d in sorted(
                    periods.items()
                )
            ]

            return {
                "periods": data,
                "period_count": len(data),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def calculate_runway(
        self,
        current_balance: float = 0.0,
    ) -> dict[str, Any]:
        """Pist hesaplar.

        Args:
            current_balance: Mevcut bakiye.

        Returns:
            Pist bilgisi.
        """
        try:
            periods: dict[
                str, float
            ] = {}
            for f in self._flows:
                period = f.get(
                    "period", "unknown"
                )
                if period not in periods:
                    periods[period] = 0.0
                if f["flow_type"] == "outflow":
                    periods[period] += f[
                        "amount"
                    ]

            if not periods:
                return {
                    "runway_months": 0,
                    "avg_burn": 0.0,
                    "calculated": True,
                }

            avg_burn = sum(
                periods.values()
            ) / len(periods)

            runway_months = (
                int(
                    current_balance / avg_burn
                )
                if avg_burn > 0
                else 999
            )

            if runway_months < 3:
                status = "critical"
            elif runway_months < 6:
                status = "warning"
            elif runway_months < 12:
                status = "adequate"
            else:
                status = "healthy"

            return {
                "current_balance": round(
                    current_balance, 2
                ),
                "avg_monthly_burn": round(
                    avg_burn, 2
                ),
                "runway_months": (
                    runway_months
                ),
                "status": status,
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def forecast_cashflow(
        self,
        months: int = 6,
        current_balance: float = 0.0,
    ) -> dict[str, Any]:
        """Nakit akis tahmini yapar.

        Args:
            months: Tahmin donemi.
            current_balance: Mevcut bakiye.

        Returns:
            Tahmin bilgisi.
        """
        try:
            periods: dict[
                str, dict[str, float]
            ] = {}
            for f in self._flows:
                period = f.get(
                    "period", "unknown"
                )
                if period not in periods:
                    periods[period] = {
                        "inflow": 0.0,
                        "outflow": 0.0,
                    }
                periods[period][
                    f["flow_type"]
                ] += f["amount"]

            if not periods:
                return {
                    "forecast": [],
                    "forecasted": True,
                }

            avg_in = sum(
                d["inflow"]
                for d in periods.values()
            ) / len(periods)
            avg_out = sum(
                d["outflow"]
                for d in periods.values()
            ) / len(periods)

            forecast = []
            balance = current_balance
            critical_point = None

            for i in range(1, months + 1):
                net = avg_in - avg_out
                balance += net
                point = {
                    "month": i,
                    "projected_inflow": round(
                        avg_in, 2
                    ),
                    "projected_outflow": round(
                        avg_out, 2
                    ),
                    "net_flow": round(net, 2),
                    "projected_balance": round(
                        balance, 2
                    ),
                }
                forecast.append(point)

                if (
                    balance < 0
                    and critical_point is None
                ):
                    critical_point = i

            self._stats[
                "forecasts_generated"
            ] += 1

            return {
                "forecast": forecast,
                "months": months,
                "avg_monthly_inflow": round(
                    avg_in, 2
                ),
                "avg_monthly_outflow": round(
                    avg_out, 2
                ),
                "critical_month": (
                    critical_point
                ),
                "forecasted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "forecasted": False,
                "error": str(e),
            }

    def find_critical_points(
        self,
    ) -> dict[str, Any]:
        """Kritik noktalari bulur.

        Returns:
            Kritik noktalar.
        """
        try:
            breakdown = (
                self.get_period_breakdown()
            )
            periods = breakdown.get(
                "periods", []
            )

            critical = []
            for p in periods:
                if p["net"] < 0:
                    critical.append({
                        "period": p["period"],
                        "net_flow": p["net"],
                        "severity": (
                            "high"
                            if p["net"] < -10000
                            else "medium"
                            if p["net"] < -5000
                            else "low"
                        ),
                    })

            return {
                "critical_points": critical,
                "critical_count": len(
                    critical
                ),
                "has_critical": len(critical)
                > 0,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
