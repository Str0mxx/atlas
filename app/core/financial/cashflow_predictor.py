"""ATLAS Nakit Akış Tahmincisi modülü.

Nakit akış tahmini, pist hesaplama,
senaryo modelleme, risk değerlendirme,
uyarı üretme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CashFlowPredictor:
    """Nakit akış tahmincisi.

    Gelecek nakit akışını tahmin eder.

    Attributes:
        _cash_flows: Nakit akış kayıtları.
        _scenarios: Senaryo modelleri.
    """

    def __init__(
        self,
        currency: str = "TRY",
    ) -> None:
        """Tahmincisini başlatır.

        Args:
            currency: Varsayılan para birimi.
        """
        self._cash_flows: list[
            dict[str, Any]
        ] = []
        self._scenarios: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._currency = currency
        self._counter = 0
        self._current_balance = 0.0
        self._stats = {
            "forecasts_made": 0,
            "scenarios_created": 0,
            "alerts_generated": 0,
        }

        logger.info(
            "CashFlowPredictor baslatildi",
        )

    def record_flow(
        self,
        amount: float,
        flow_type: str = "inflow",
        category: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Nakit akışı kaydeder.

        Args:
            amount: Tutar.
            flow_type: Akış tipi.
            category: Kategori.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        fid = f"cf_{self._counter}"

        signed_amount = (
            amount if flow_type == "inflow"
            else -amount
        )
        self._current_balance += signed_amount

        record = {
            "flow_id": fid,
            "amount": amount,
            "signed_amount": signed_amount,
            "flow_type": flow_type,
            "category": category,
            "description": description,
            "balance_after": round(
                self._current_balance, 2,
            ),
            "timestamp": time.time(),
        }
        self._cash_flows.append(record)

        return {
            "flow_id": fid,
            "amount": amount,
            "flow_type": flow_type,
            "balance": round(
                self._current_balance, 2,
            ),
            "recorded": True,
        }

    def forecast(
        self,
        periods: int = 3,
    ) -> dict[str, Any]:
        """Nakit akış tahmini yapar.

        Args:
            periods: Tahmin dönemi sayısı.

        Returns:
            Tahmin bilgisi.
        """
        if not self._cash_flows:
            return {
                "forecasts": [],
                "confidence": 0.0,
            }

        inflows = [
            r["amount"]
            for r in self._cash_flows
            if r["flow_type"] == "inflow"
        ]
        outflows = [
            r["amount"]
            for r in self._cash_flows
            if r["flow_type"] == "outflow"
        ]

        avg_inflow = (
            sum(inflows) / len(inflows)
            if inflows else 0.0
        )
        avg_outflow = (
            sum(outflows) / len(outflows)
            if outflows else 0.0
        )
        net_flow = avg_inflow - avg_outflow

        forecasts = []
        balance = self._current_balance
        for i in range(1, periods + 1):
            balance += net_flow
            forecasts.append({
                "period": i,
                "projected_inflow": round(
                    avg_inflow, 2,
                ),
                "projected_outflow": round(
                    avg_outflow, 2,
                ),
                "net_flow": round(
                    net_flow, 2,
                ),
                "projected_balance": round(
                    balance, 2,
                ),
            })

        confidence = min(
            len(self._cash_flows) / 10, 1.0,
        )
        self._stats["forecasts_made"] += 1

        return {
            "forecasts": forecasts,
            "current_balance": round(
                self._current_balance, 2,
            ),
            "confidence": round(
                confidence, 2,
            ),
        }

    def calculate_runway(
        self,
        monthly_burn: float | None = None,
    ) -> dict[str, Any]:
        """Pist hesaplar.

        Args:
            monthly_burn: Aylık yakım oranı.

        Returns:
            Pist bilgisi.
        """
        if monthly_burn is None:
            outflows = [
                r["amount"]
                for r in self._cash_flows
                if r["flow_type"] == "outflow"
            ]
            monthly_burn = (
                sum(outflows) / len(outflows)
                if outflows else 0.0
            )

        if monthly_burn <= 0:
            return {
                "runway_months": float("inf"),
                "status": "sustainable",
            }

        runway = (
            self._current_balance
            / monthly_burn
        )

        status = (
            "critical" if runway < 3
            else "warning" if runway < 6
            else "healthy" if runway < 12
            else "comfortable"
        )

        return {
            "runway_months": round(
                runway, 1,
            ),
            "monthly_burn": round(
                monthly_burn, 2,
            ),
            "current_balance": round(
                self._current_balance, 2,
            ),
            "status": status,
        }

    def create_scenario(
        self,
        name: str,
        inflow_change: float = 0.0,
        outflow_change: float = 0.0,
        periods: int = 6,
    ) -> dict[str, Any]:
        """Senaryo oluşturur.

        Args:
            name: Senaryo adı.
            inflow_change: Giriş değişimi %.
            outflow_change: Çıkış değişimi %.
            periods: Dönem sayısı.

        Returns:
            Senaryo bilgisi.
        """
        inflows = [
            r["amount"]
            for r in self._cash_flows
            if r["flow_type"] == "inflow"
        ]
        outflows = [
            r["amount"]
            for r in self._cash_flows
            if r["flow_type"] == "outflow"
        ]

        avg_in = (
            sum(inflows) / len(inflows)
            if inflows else 0.0
        )
        avg_out = (
            sum(outflows) / len(outflows)
            if outflows else 0.0
        )

        adj_in = avg_in * (
            1 + inflow_change / 100
        )
        adj_out = avg_out * (
            1 + outflow_change / 100
        )

        projections = []
        balance = self._current_balance
        for i in range(1, periods + 1):
            balance += adj_in - adj_out
            projections.append({
                "period": i,
                "balance": round(balance, 2),
            })

        scenario = {
            "name": name,
            "inflow_change": inflow_change,
            "outflow_change": outflow_change,
            "projections": projections,
            "final_balance": round(
                balance, 2,
            ),
        }
        self._scenarios[name] = scenario
        self._stats["scenarios_created"] += 1

        return {
            "name": name,
            "final_balance": round(
                balance, 2,
            ),
            "periods": periods,
            "created": True,
        }

    def assess_risk(
        self,
    ) -> dict[str, Any]:
        """Risk değerlendirmesi yapar.

        Returns:
            Risk bilgisi.
        """
        risks = []

        # Negatif bakiye riski
        if self._current_balance < 0:
            risks.append({
                "type": "negative_balance",
                "severity": "critical",
                "detail": (
                    f"Balance is "
                    f"{self._current_balance}"
                ),
            })

        # Düşük pist riski
        runway = self.calculate_runway()
        if isinstance(
            runway["runway_months"],
            (int, float),
        ) and runway[
            "runway_months"
        ] < 3:
            risks.append({
                "type": "low_runway",
                "severity": "high",
                "detail": (
                    f"Only "
                    f"{runway['runway_months']}"
                    f" months runway"
                ),
            })

        # Değişken gelir riski
        inflows = [
            r["amount"]
            for r in self._cash_flows
            if r["flow_type"] == "inflow"
        ]
        if len(inflows) >= 3:
            avg = sum(inflows) / len(inflows)
            variance = sum(
                (x - avg) ** 2
                for x in inflows
            ) / len(inflows)
            cv = (
                (variance ** 0.5) / avg
                if avg > 0 else 0
            )
            if cv > 0.5:
                risks.append({
                    "type": "volatile_income",
                    "severity": "medium",
                    "detail": (
                        f"Income CV: "
                        f"{cv:.2f}"
                    ),
                })

        risk_level = (
            "critical" if any(
                r["severity"] == "critical"
                for r in risks
            )
            else "high" if any(
                r["severity"] == "high"
                for r in risks
            )
            else "medium" if risks
            else "low"
        )

        return {
            "risk_level": risk_level,
            "risks": risks,
            "count": len(risks),
        }

    def generate_alerts(
        self,
        low_balance: float = 0.0,
    ) -> dict[str, Any]:
        """Uyarı üretir.

        Args:
            low_balance: Düşük bakiye eşiği.

        Returns:
            Uyarı bilgisi.
        """
        alerts = []

        if self._current_balance < (
            low_balance
        ):
            alerts.append({
                "type": "low_balance",
                "severity": "high",
                "message": (
                    f"Balance "
                    f"{self._current_balance} "
                    f"below threshold "
                    f"{low_balance}"
                ),
            })

        risk = self.assess_risk()
        for r in risk["risks"]:
            alerts.append({
                "type": r["type"],
                "severity": r["severity"],
                "message": r["detail"],
            })

        self._alerts = alerts
        self._stats[
            "alerts_generated"
        ] = len(alerts)

        return {
            "alerts": alerts,
            "count": len(alerts),
        }

    @property
    def current_balance(self) -> float:
        """Mevcut bakiye."""
        return round(
            self._current_balance, 2,
        )

    @property
    def flow_count(self) -> int:
        """Akış sayısı."""
        return len(self._cash_flows)

    @property
    def scenario_count(self) -> int:
        """Senaryo sayısı."""
        return len(self._scenarios)
