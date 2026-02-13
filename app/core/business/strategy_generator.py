"""ATLAS Strateji Uretici modulu.

Hedef ayristirma, aksiyon plani olusturma, kaynak tahmini,
risk degerlendirmesi ve ROI projeksiyonu islemleri.
"""

import logging
from typing import Any
from uuid import uuid4

from app.models.business import (
    ActionPriority,
    ActionStep,
    Opportunity,
    ResourceEstimate,
    RiskAssessment,
    Strategy,
    StrategyStatus,
)

logger = logging.getLogger(__name__)

# Risk olasilik-etki matrisi esikleri
_RISK_THRESHOLDS = {
    "low": 0.2,
    "medium": 0.5,
    "high": 0.8,
}


class StrategyGenerator:
    """Strateji uretici.

    Firsatlardan strateji olusturur, hedefleri alt gorevlere
    ayristirir, kaynak tahmini yapar, riskleri degerlendirir
    ve ROI projeksiyonu hesaplar.

    Attributes:
        _strategies: Uretilen stratejiler (id -> Strategy).
        _default_timeline_days: Varsayilan zaman cizgisi (gun).
        _risk_tolerance: Risk toleransi (0.0-1.0).
    """

    def __init__(self, default_timeline_days: int = 30, risk_tolerance: float = 0.5) -> None:
        """Strateji ureticiyi baslatir.

        Args:
            default_timeline_days: Varsayilan zaman cizgisi (gun).
            risk_tolerance: Risk toleransi (0.0-1.0).
        """
        self._strategies: dict[str, Strategy] = {}
        self._default_timeline_days = default_timeline_days
        self._risk_tolerance = max(0.0, min(1.0, risk_tolerance))

        logger.info(
            "StrategyGenerator baslatildi (timeline=%d gun, risk_tolerance=%.2f)",
            default_timeline_days,
            self._risk_tolerance,
        )

    def create_strategy(
        self,
        title: str,
        opportunity_id: str = "",
        goals: list[str] | None = None,
        timeline_days: int | None = None,
    ) -> Strategy:
        """Yeni strateji olusturur.

        Args:
            title: Strateji basligi.
            opportunity_id: Iliskili firsat ID.
            goals: Hedefler listesi.
            timeline_days: Zaman cizgisi (gun), None ise varsayilan.

        Returns:
            Olusturulan Strategy nesnesi.
        """
        strategy = Strategy(
            title=title,
            opportunity_id=opportunity_id,
            goals=goals or [],
            timeline_days=timeline_days or self._default_timeline_days,
        )
        self._strategies[strategy.id] = strategy
        logger.info("Strateji olusturuldu: %s (hedef=%d)", title, len(strategy.goals))
        return strategy

    def decompose_goals(self, strategy_id: str) -> list[ActionStep]:
        """Hedefleri alt gorevlere ayristirir.

        Her hedef icin bir aksiyon adimi olusturur ve
        stratejinin aksiyon planina ekler.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Olusturulan aksiyon adimlari listesi. Strateji bulunamazsa bos liste.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return []

        steps: list[ActionStep] = []
        for idx, goal in enumerate(strategy.goals):
            priority = ActionPriority.HIGH if idx == 0 else ActionPriority.MEDIUM
            step = ActionStep(
                description=f"Hedef: {goal}",
                priority=priority,
                estimated_duration_hours=max(1.0, strategy.timeline_days * 24 / max(1, len(strategy.goals))),
            )
            # Ilk adim disindakiler onceki adima bagimli
            if steps:
                step.dependencies = [steps[-1].id]
            steps.append(step)

        strategy.action_steps = steps
        logger.info("Hedef ayristirma: %s -> %d adim", strategy.title[:30], len(steps))
        return steps

    def create_action_plan(
        self,
        strategy_id: str,
        steps: list[dict[str, Any]],
    ) -> list[ActionStep]:
        """Manuel aksiyon plani olusturur.

        Args:
            strategy_id: Strateji ID.
            steps: Adim tanimlari listesi. Her adim:
                - description (str): Adim aciklamasi
                - priority (str, opsiyonel): Oncelik
                - duration_hours (float, opsiyonel): Sure
                - agent_type (str, opsiyonel): Agent tipi
                - resources (list[str], opsiyonel): Kaynaklar

        Returns:
            Olusturulan aksiyon adimlari. Strateji bulunamazsa bos liste.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return []

        action_steps: list[ActionStep] = []
        for step_def in steps:
            priority_str = step_def.get("priority", "medium")
            try:
                priority = ActionPriority(priority_str)
            except ValueError:
                priority = ActionPriority.MEDIUM

            step = ActionStep(
                description=step_def.get("description", ""),
                priority=priority,
                estimated_duration_hours=step_def.get("duration_hours", 1.0),
                agent_type=step_def.get("agent_type", ""),
                required_resources=step_def.get("resources", []),
            )
            action_steps.append(step)

        strategy.action_steps = action_steps
        logger.info("Aksiyon plani olusturuldu: %s -> %d adim", strategy.title[:30], len(action_steps))
        return action_steps

    def estimate_resources(self, strategy_id: str) -> list[ResourceEstimate]:
        """Strateji icin kaynak tahmini yapar.

        Aksiyon adimlarinin surelerine gore zaman, maliyet
        ve sistem kaynak tahminleri olusturur.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Kaynak tahminleri listesi. Strateji bulunamazsa bos liste.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return []

        total_hours = sum(s.estimated_duration_hours for s in strategy.action_steps)
        agent_types = {s.agent_type for s in strategy.action_steps if s.agent_type}

        resources: list[ResourceEstimate] = [
            ResourceEstimate(
                resource_type="time",
                amount=total_hours,
                unit="hours",
                confidence=0.7,
            ),
            ResourceEstimate(
                resource_type="cost",
                amount=total_hours * 50,
                unit="USD",
                confidence=0.5,
            ),
            ResourceEstimate(
                resource_type="agents",
                amount=float(max(1, len(agent_types))),
                unit="count",
                confidence=0.9,
            ),
        ]

        strategy.resources = resources
        logger.info("Kaynak tahmini: %s -> %.1f saat, $%.0f", strategy.title[:30], total_hours, total_hours * 50)
        return resources

    def assess_risks(self, strategy_id: str, custom_risks: list[dict[str, Any]] | None = None) -> list[RiskAssessment]:
        """Risk degerlendirmesi yapar.

        Standart riskleri ve varsa ozel riskleri degerlendirir.
        Risk skoru = olasilik * etki olarak hesaplanir.

        Args:
            strategy_id: Strateji ID.
            custom_risks: Ozel risk tanimlari listesi.

        Returns:
            Risk degerlendirmeleri. Strateji bulunamazsa bos liste.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return []

        risks: list[RiskAssessment] = []

        # Standart riskler
        default_risks = [
            {"description": "Kaynak yetersizligi", "probability": 0.3, "impact": 0.6},
            {"description": "Zaman asimi", "probability": 0.4, "impact": 0.5},
            {"description": "Pazar degisikligi", "probability": 0.2, "impact": 0.7},
        ]

        all_risks = default_risks + (custom_risks or [])

        for risk_def in all_risks:
            prob = risk_def.get("probability", 0.3)
            impact = risk_def.get("impact", 0.5)
            risk = RiskAssessment(
                description=risk_def.get("description", ""),
                probability=prob,
                impact=impact,
                mitigation=risk_def.get("mitigation", ""),
                risk_score=prob * impact,
            )
            risks.append(risk)

        strategy.risks = risks
        max_risk = max((r.risk_score for r in risks), default=0.0)
        logger.info("Risk degerlendirmesi: %s -> %d risk, max=%.2f", strategy.title[:30], len(risks), max_risk)
        return risks

    def project_roi(self, strategy_id: str, investment: float = 0.0) -> float:
        """ROI projeksiyonu hesaplar.

        Tahmini gelir (kaynak maliyetinin 3 kati) ile yatirimi
        karsilastirarak ROI yuzdesi hesaplar.

        Args:
            strategy_id: Strateji ID.
            investment: Toplam yatirim miktari. 0 ise kaynak tahmininden hesaplanir.

        Returns:
            Tahmini ROI yuzdesi. Strateji bulunamazsa 0.0.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return 0.0

        if investment <= 0:
            cost_resources = [r for r in strategy.resources if r.resource_type == "cost"]
            investment = sum(r.amount for r in cost_resources) if cost_resources else 1000.0

        # Basit ROI: tahmini gelir / yatirim
        estimated_revenue = investment * 3.0  # 3x multiplier varsayimi
        risk_factor = 1.0
        if strategy.risks:
            avg_risk = sum(r.risk_score for r in strategy.risks) / len(strategy.risks)
            risk_factor = max(0.2, 1.0 - avg_risk)

        roi = ((estimated_revenue * risk_factor - investment) / investment) * 100
        strategy.estimated_roi = roi
        logger.info("ROI projeksiyonu: %s -> %.1f%%", strategy.title[:30], roi)
        return roi

    def is_viable(self, strategy_id: str) -> bool:
        """Strateji uygulanabilir mi kontrol eder.

        ROI pozitif ve maksimum risk tolerans altinda ise
        strateji uygulanabilir kabul edilir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Uygulanabilirlik durumu.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        if strategy.estimated_roi <= 0:
            return False

        if strategy.risks:
            max_risk = max(r.risk_score for r in strategy.risks)
            if max_risk > self._risk_tolerance:
                return False

        return True

    def activate_strategy(self, strategy_id: str) -> bool:
        """Stratejiyi aktive eder.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Basarili mi.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False

        strategy.status = StrategyStatus.ACTIVE
        logger.info("Strateji aktive edildi: %s", strategy.title[:30])
        return True

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Strateji getirir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Strategy nesnesi veya None.
        """
        return self._strategies.get(strategy_id)

    @property
    def strategy_count(self) -> int:
        """Toplam strateji sayisi."""
        return len(self._strategies)

    @property
    def active_strategies(self) -> list[Strategy]:
        """Aktif stratejiler."""
        return [s for s in self._strategies.values() if s.status == StrategyStatus.ACTIVE]
