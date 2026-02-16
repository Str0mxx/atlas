"""ATLAS En Kötü Durum Analizcisi.

Olumsuzluk analizi, risk niceleme,
azaltma seçenekleri, hayatta kalma, stres testi.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorstCaseAnalyzer:
    """En kötü durum analizcisi.

    Senaryoların en kötü olasılıklarını
    analiz eder ve azaltma planları oluşturur.

    Attributes:
        _analyses: Analiz kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizcisi başlatır."""
        self._analyses: dict[
            str, dict
        ] = {}
        self._stats = {
            "analyses_performed": 0,
            "stress_tests_run": 0,
        }
        logger.info(
            "WorstCaseAnalyzer "
            "baslatildi",
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "analyses_performed"
        ]

    @property
    def stress_test_count(self) -> int:
        """Stres testi sayısı."""
        return self._stats[
            "stress_tests_run"
        ]

    def analyze_downside(
        self,
        scenario_id: str,
        potential_loss: float = 0.0,
        probability: float = 0.1,
        recovery_time_days: int = 30,
    ) -> dict[str, Any]:
        """Olumsuzluk analizi yapar.

        Args:
            scenario_id: Senaryo kimliği.
            potential_loss: Potansiyel kayıp.
            probability: Olasılık.
            recovery_time_days: Toparlanma.

        Returns:
            Olumsuzluk bilgisi.
        """
        expected_loss = round(
            potential_loss * probability,
            2,
        )

        if expected_loss >= 100000:
            severity = "catastrophic"
        elif expected_loss >= 50000:
            severity = "severe"
        elif expected_loss >= 10000:
            severity = "moderate"
        else:
            severity = "manageable"

        self._stats[
            "analyses_performed"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "potential_loss": potential_loss,
            "expected_loss": expected_loss,
            "severity": severity,
            "recovery_days": (
                recovery_time_days
            ),
            "analyzed": True,
        }

    def quantify_risk(
        self,
        scenario_id: str,
        impact: float = 0.0,
        probability: float = 0.0,
        controllability: float = 0.5,
    ) -> dict[str, Any]:
        """Riski nicelleştirir.

        Args:
            scenario_id: Senaryo kimliği.
            impact: Etki büyüklüğü (0-100).
            probability: Olasılık (0-1).
            controllability: Kontrol (0-1).

        Returns:
            Risk nicelemesi bilgisi.
        """
        risk_score = round(
            impact
            * probability
            * (1 - controllability),
            2,
        )

        if risk_score >= 30:
            level = "critical"
        elif risk_score >= 15:
            level = "high"
        elif risk_score >= 5:
            level = "medium"
        else:
            level = "low"

        self._stats[
            "analyses_performed"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "risk_score": risk_score,
            "level": level,
            "quantified": True,
        }

    def suggest_mitigation(
        self,
        scenario_id: str,
        risk_type: str = "financial",
        severity: str = "moderate",
    ) -> dict[str, Any]:
        """Azaltma seçenekleri önerir.

        Args:
            scenario_id: Senaryo kimliği.
            risk_type: Risk tipi.
            severity: Ciddiyet.

        Returns:
            Azaltma önerileri bilgisi.
        """
        mitigations = {
            "financial": [
                "diversify_revenue",
                "build_reserves",
                "hedge_exposure",
            ],
            "operational": [
                "redundant_systems",
                "cross_training",
                "backup_suppliers",
            ],
            "strategic": [
                "pivot_strategy",
                "exit_plan",
                "partnership",
            ],
            "reputational": [
                "crisis_communication",
                "brand_monitoring",
                "stakeholder_engagement",
            ],
        }

        suggestions = mitigations.get(
            risk_type,
            ["general_contingency"],
        )

        if severity in (
            "catastrophic",
            "severe",
        ):
            priority = "immediate"
        elif severity == "moderate":
            priority = "planned"
        else:
            priority = "monitoring"

        return {
            "scenario_id": scenario_id,
            "risk_type": risk_type,
            "suggestions": suggestions,
            "priority": priority,
            "suggested": True,
        }

    def plan_survival(
        self,
        scenario_id: str,
        cash_reserves: float = 0.0,
        monthly_burn: float = 1.0,
        revenue_drop_pct: float = 50.0,
    ) -> dict[str, Any]:
        """Hayatta kalma planı oluşturur.

        Args:
            scenario_id: Senaryo kimliği.
            cash_reserves: Nakit rezerv.
            monthly_burn: Aylık harcama.
            revenue_drop_pct: Gelir düşüşü %.

        Returns:
            Hayatta kalma bilgisi.
        """
        adjusted_burn = round(
            monthly_burn
            * (1 - revenue_drop_pct / 100),
            2,
        )

        if adjusted_burn <= 0:
            adjusted_burn = monthly_burn

        if adjusted_burn > 0:
            runway_months = round(
                cash_reserves
                / adjusted_burn,
                1,
            )
        else:
            runway_months = 999.0

        if runway_months >= 12:
            status = "comfortable"
        elif runway_months >= 6:
            status = "cautious"
        elif runway_months >= 3:
            status = "critical"
        else:
            status = "emergency"

        self._stats[
            "analyses_performed"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "runway_months": runway_months,
            "adjusted_burn": adjusted_burn,
            "status": status,
            "planned": True,
        }

    def stress_test(
        self,
        scenario_id: str,
        base_value: float = 100.0,
        shock_pct: float = -30.0,
        recovery_rate: float = 0.1,
        periods: int = 6,
    ) -> dict[str, Any]:
        """Stres testi yapar.

        Args:
            scenario_id: Senaryo kimliği.
            base_value: Temel değer.
            shock_pct: Şok yüzdesi.
            recovery_rate: Toparlanma oranı.
            periods: Dönem sayısı.

        Returns:
            Stres testi bilgisi.
        """
        shocked = round(
            base_value
            * (1 + shock_pct / 100),
            2,
        )
        current = shocked
        timeline = [base_value, shocked]

        for _ in range(periods):
            current = round(
                current
                * (1 + recovery_rate),
                2,
            )
            timeline.append(current)

        recovered = current >= base_value
        recovery_pct = round(
            (current - shocked)
            / max(
                abs(base_value - shocked),
                0.01,
            )
            * 100,
            1,
        )

        self._stats[
            "stress_tests_run"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "base_value": base_value,
            "shocked_value": shocked,
            "final_value": current,
            "recovered": recovered,
            "recovery_pct": recovery_pct,
            "timeline": timeline,
            "tested": True,
        }
