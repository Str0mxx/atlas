"""ATLAS Iyilestirme Planlayici modulu.

Etki bazli onceliklendirme, efor tahmini,
risk degerlendirmesi, bagimlilik kontrolu ve uygulama plani.
"""

import logging
from typing import Any

from app.models.evolution import (
    ChangeSeverity,
    ImprovementPlan,
    ImprovementType,
    WeaknessReport,
    WeaknessType,
)

logger = logging.getLogger(__name__)

# Zayiflik tipi -> iyilestirme tipi eslesmesi
_WEAKNESS_TO_IMPROVEMENT: dict[WeaknessType, ImprovementType] = {
    WeaknessType.FAILURE: ImprovementType.BUG_FIX,
    WeaknessType.SLOW_OPERATION: ImprovementType.PERFORMANCE,
    WeaknessType.MISSING_CAPABILITY: ImprovementType.NEW_CAPABILITY,
    WeaknessType.ERROR_HOTSPOT: ImprovementType.BUG_FIX,
    WeaknessType.USER_COMPLAINT: ImprovementType.BUG_FIX,
    WeaknessType.RESOURCE_WASTE: ImprovementType.PERFORMANCE,
}

# Iyilestirme tipi -> temel efor
_BASE_EFFORT: dict[ImprovementType, float] = {
    ImprovementType.BUG_FIX: 10.0,
    ImprovementType.PERFORMANCE: 20.0,
    ImprovementType.NEW_CAPABILITY: 50.0,
    ImprovementType.REFACTOR: 30.0,
    ImprovementType.CONFIGURATION: 5.0,
    ImprovementType.DOCUMENTATION: 5.0,
}


class ImprovementPlanner:
    """Iyilestirme planlayici.

    Zayifliklardan iyilestirme planlari olusturur,
    onceliklendirir ve uygulama adimlari belirler.

    Attributes:
        _plans: Olusturulan planlar.
        _known_deps: Bilinen bagimliliklar.
    """

    def __init__(self) -> None:
        """Planlayiciyi baslatir."""
        self._plans: list[ImprovementPlan] = []
        self._known_deps: dict[str, list[str]] = {}

        logger.info("ImprovementPlanner baslatildi")

    def create_plan(self, weakness: WeaknessReport) -> ImprovementPlan:
        """Zayifliktan iyilestirme plani olusturur.

        Args:
            weakness: Zayiflik raporu.

        Returns:
            ImprovementPlan nesnesi.
        """
        imp_type = _WEAKNESS_TO_IMPROVEMENT.get(weakness.weakness_type, ImprovementType.BUG_FIX)
        effort = self._estimate_effort(weakness, imp_type)
        risk = self._assess_risk(weakness, imp_type)
        deps = self._check_dependencies(weakness.component)
        steps = self._generate_steps(weakness, imp_type)
        priority = self._calculate_priority(weakness.impact_score, effort, risk)

        plan = ImprovementPlan(
            title=f"{imp_type.value}: {weakness.component}",
            improvement_type=imp_type,
            target_component=weakness.component,
            description=weakness.description,
            expected_impact=weakness.impact_score,
            estimated_effort=effort,
            risk_level=risk,
            dependencies=deps,
            priority_score=priority,
            steps=steps,
        )

        self._plans.append(plan)
        logger.info("Plan olusturuldu: %s (oncelik=%.1f)", plan.title, priority)
        return plan

    def create_plans_from_weaknesses(self, weaknesses: list[WeaknessReport]) -> list[ImprovementPlan]:
        """Birden fazla zayifliktan planlar olusturur.

        Args:
            weaknesses: Zayiflik raporlari.

        Returns:
            ImprovementPlan listesi.
        """
        plans = [self.create_plan(w) for w in weaknesses]
        plans.sort(key=lambda p: p.priority_score, reverse=True)
        return plans

    def prioritize(self, plans: list[ImprovementPlan] | None = None) -> list[ImprovementPlan]:
        """Planlari onceliklendirir.

        Args:
            plans: Plan listesi (None ise mevcut planlar).

        Returns:
            Onceliklendirilmis planlar.
        """
        target = plans if plans is not None else self._plans
        return sorted(target, key=lambda p: p.priority_score, reverse=True)

    def add_dependency(self, component: str, depends_on: str) -> None:
        """Bagimlilik ekler.

        Args:
            component: Bilesen adi.
            depends_on: Bagimli oldugu bilesen.
        """
        deps = self._known_deps.setdefault(component, [])
        if depends_on not in deps:
            deps.append(depends_on)

    def get_plan(self, plan_id: str) -> ImprovementPlan | None:
        """Plan getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            ImprovementPlan veya None.
        """
        for plan in self._plans:
            if plan.id == plan_id:
                return plan
        return None

    def get_top_plans(self, count: int = 5) -> list[ImprovementPlan]:
        """En yuksek oncelikli planlari getirir.

        Args:
            count: Kac tane.

        Returns:
            ImprovementPlan listesi.
        """
        return self.prioritize()[:count]

    def _estimate_effort(self, weakness: WeaknessReport, imp_type: ImprovementType) -> float:
        """Efor tahmini yapar."""
        base = _BASE_EFFORT.get(imp_type, 20.0)

        # Ciddiyet carpani
        severity_mult = {
            ChangeSeverity.MINOR: 0.5,
            ChangeSeverity.MAJOR: 1.0,
            ChangeSeverity.CRITICAL: 2.0,
        }
        mult = severity_mult.get(weakness.severity, 1.0)

        effort = base * mult
        return min(effort, 100.0)

    def _assess_risk(self, weakness: WeaknessReport, imp_type: ImprovementType) -> ChangeSeverity:
        """Risk degerlendirmesi yapar."""
        if imp_type == ImprovementType.NEW_CAPABILITY:
            return ChangeSeverity.MAJOR
        if imp_type == ImprovementType.REFACTOR:
            return ChangeSeverity.MAJOR
        if weakness.severity == ChangeSeverity.CRITICAL:
            return ChangeSeverity.MAJOR
        if imp_type in (ImprovementType.CONFIGURATION, ImprovementType.DOCUMENTATION):
            return ChangeSeverity.MINOR
        return weakness.severity

    def _check_dependencies(self, component: str) -> list[str]:
        """Bagimliliklari kontrol eder."""
        # Dogrudan bagimliliklar
        direct = self._known_deps.get(component, [])
        # Bilesen adi ile eslesen bagimliliklar
        result = list(direct)
        for comp, deps in self._known_deps.items():
            if component in deps and comp not in result:
                result.append(comp)
        return result

    def _generate_steps(self, weakness: WeaknessReport, imp_type: ImprovementType) -> list[str]:
        """Uygulama adimlarini olusturur."""
        steps: list[str] = []

        if imp_type == ImprovementType.BUG_FIX:
            steps = [
                f"Hata analizi: {weakness.component}",
                "Kok neden tespiti",
                "Fix kodu uretimi",
                "Birim test yazimi",
                "Sandbox testi",
                "Deploy",
            ]
        elif imp_type == ImprovementType.PERFORMANCE:
            steps = [
                f"Performans profili: {weakness.component}",
                "Darboğaz tespiti",
                "Optimizasyon kodu",
                "Benchmark testi",
                "A/B karsilastirma",
                "Deploy",
            ]
        elif imp_type == ImprovementType.NEW_CAPABILITY:
            steps = [
                f"Gereksinim analizi: {weakness.component}",
                "Tasarim",
                "Kod uretimi",
                "Test yazimi",
                "Entegrasyon testi",
                "Onay istegi",
                "Deploy",
            ]
        elif imp_type == ImprovementType.REFACTOR:
            steps = [
                f"Kod analizi: {weakness.component}",
                "Refactoring plani",
                "Kod degisikligi",
                "Regresyon testi",
                "Deploy",
            ]
        elif imp_type == ImprovementType.CONFIGURATION:
            steps = [
                f"Konfigürasyon analizi: {weakness.component}",
                "Degisiklik uygulama",
                "Dogrulama",
            ]
        else:
            steps = [
                f"Analiz: {weakness.component}",
                "Degisiklik",
                "Dogrulama",
            ]

        return steps

    def _calculate_priority(self, impact: float, effort: float, risk: ChangeSeverity) -> float:
        """Oncelik puani hesaplar.

        Yuksek etki, dusuk efor ve dusuk risk -> yuksek oncelik.
        """
        risk_penalty = {
            ChangeSeverity.MINOR: 0.0,
            ChangeSeverity.MAJOR: 10.0,
            ChangeSeverity.CRITICAL: 25.0,
        }
        penalty = risk_penalty.get(risk, 0.0)

        # impact (0-10), effort (0-100)
        effort_normalized = effort / 10.0  # 0-10 arasi
        score = (impact * 8) - (effort_normalized * 2) - penalty + 30

        return max(0.0, min(score, 100.0))

    @property
    def plan_count(self) -> int:
        """Plan sayisi."""
        return len(self._plans)

    @property
    def plans(self) -> list[ImprovementPlan]:
        """Tum planlar."""
        return list(self._plans)
