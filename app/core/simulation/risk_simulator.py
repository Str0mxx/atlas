"""ATLAS Risk Simulatoru modulu.

Risk olayi enjeksiyonu, basarisizlik yayilimi,
kurtarma simulasyonu, azaltma testi ve stres testi.
"""

import logging
import random
from typing import Any

from app.models.simulation import (
    RiskEvent,
    RiskLevel,
    WorldSnapshot,
)

logger = logging.getLogger(__name__)

# Bilesen -> olasi riskler
_COMPONENT_RISKS: dict[str, list[dict[str, Any]]] = {
    "database": [
        {"name": "Baglanti havuzu tukendi", "probability": 0.05, "impact": "high"},
        {"name": "Replikasyon gecikmesi", "probability": 0.08, "impact": "medium"},
        {"name": "Disk dolu", "probability": 0.03, "impact": "critical"},
    ],
    "api": [
        {"name": "Rate limit asildi", "probability": 0.1, "impact": "medium"},
        {"name": "Timeout", "probability": 0.08, "impact": "low"},
        {"name": "Auth hatasi", "probability": 0.04, "impact": "high"},
    ],
    "service": [
        {"name": "OOM kill", "probability": 0.04, "impact": "high"},
        {"name": "CPU spike", "probability": 0.1, "impact": "medium"},
        {"name": "Deadlock", "probability": 0.02, "impact": "critical"},
    ],
    "network": [
        {"name": "Paket kaybi", "probability": 0.06, "impact": "low"},
        {"name": "DNS hatasi", "probability": 0.03, "impact": "high"},
        {"name": "SSL hatasi", "probability": 0.02, "impact": "medium"},
    ],
}

_RISK_MAP: dict[str, RiskLevel] = {
    "negligible": RiskLevel.NEGLIGIBLE,
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
    "critical": RiskLevel.CRITICAL,
}


class RiskSimulator:
    """Risk simulasyon sistemi.

    Risk olaylarini enjekte eder, yayilimi simule eder
    ve kurtarma surelerini tahmin eder.

    Attributes:
        _events: Risk olaylari.
        _stress_results: Stres test sonuclari.
        _rng: Random number generator.
    """

    def __init__(self, seed: int | None = None) -> None:
        """Risk simulatorunu baslatir.

        Args:
            seed: Random seed.
        """
        self._events: list[RiskEvent] = []
        self._stress_results: list[dict[str, Any]] = []
        self._rng = random.Random(seed)

        logger.info("RiskSimulator baslatildi")

    def inject_risk(
        self,
        name: str,
        affected_components: list[str],
        probability: float = 0.5,
        impact: RiskLevel = RiskLevel.MEDIUM,
        description: str = "",
    ) -> RiskEvent:
        """Risk olayi enjekte eder.

        Args:
            name: Risk adi.
            affected_components: Etkilenen bilesenler.
            probability: Gerceklesme olasiligi.
            impact: Etki seviyesi.
            description: Aciklama.

        Returns:
            RiskEvent nesnesi.
        """
        propagation = self._simulate_propagation(affected_components)
        recovery_time = self._estimate_recovery(impact, len(affected_components))
        mitigation = self._suggest_mitigation(name, impact)

        event = RiskEvent(
            name=name,
            description=description or f"Risk olayi: {name}",
            probability=min(max(probability, 0.0), 1.0),
            impact=impact,
            affected_components=affected_components,
            propagation_path=propagation,
            recovery_time_seconds=recovery_time,
            mitigation_strategy=mitigation,
        )

        self._events.append(event)
        return event

    def simulate_failure_propagation(
        self,
        initial_component: str,
        dependency_map: dict[str, list[str]],
    ) -> list[str]:
        """Basarisizlik yayilimini simule eder.

        Args:
            initial_component: Baslangic bileseni.
            dependency_map: Bagimlilik haritasi.

        Returns:
            Etkilenen bilesenler listesi (sirali).
        """
        affected: list[str] = [initial_component]
        queue = [initial_component]
        visited: set[str] = {initial_component}

        while queue:
            current = queue.pop(0)
            dependents = dependency_map.get(current, [])
            for dep in dependents:
                if dep not in visited:
                    visited.add(dep)
                    affected.append(dep)
                    queue.append(dep)

        return affected

    def simulate_recovery(
        self,
        risk_event: RiskEvent,
        has_backup: bool = True,
        has_redundancy: bool = False,
    ) -> dict[str, Any]:
        """Kurtarma simulasyonu yapar.

        Args:
            risk_event: Risk olayi.
            has_backup: Yedek var mi.
            has_redundancy: Yedeklilik var mi.

        Returns:
            Kurtarma sonucu.
        """
        base_time = risk_event.recovery_time_seconds

        if has_redundancy:
            recovery_time = base_time * 0.2
            strategy = "Otomatik failover"
        elif has_backup:
            recovery_time = base_time * 0.5
            strategy = "Yedekten geri yukleme"
        else:
            recovery_time = base_time * 1.5
            strategy = "Manuel kurtarma"

        steps = self._generate_recovery_steps(risk_event, strategy)

        return {
            "event": risk_event.name,
            "strategy": strategy,
            "estimated_recovery_seconds": round(recovery_time, 1),
            "steps": steps,
            "data_loss_risk": not has_backup,
            "downtime_seconds": round(recovery_time * 0.8, 1),
        }

    def test_mitigation(
        self,
        risk_event: RiskEvent,
        mitigation_actions: list[str],
    ) -> dict[str, Any]:
        """Azaltma stratejisini test eder.

        Args:
            risk_event: Risk olayi.
            mitigation_actions: Azaltma aksiyonlari.

        Returns:
            Test sonucu.
        """
        effectiveness = min(len(mitigation_actions) * 0.2, 0.9)

        reduced_impact = self._reduce_impact(risk_event.impact, effectiveness)
        reduced_prob = risk_event.probability * (1.0 - effectiveness)

        return {
            "original_impact": risk_event.impact.value,
            "reduced_impact": reduced_impact.value,
            "original_probability": risk_event.probability,
            "reduced_probability": round(reduced_prob, 3),
            "effectiveness": round(effectiveness, 2),
            "actions_applied": mitigation_actions,
            "residual_risk": round(reduced_prob * self._risk_score(reduced_impact), 3),
        }

    def stress_test(
        self,
        components: list[str],
        load_factor: float = 2.0,
        duration_seconds: float = 300.0,
    ) -> dict[str, Any]:
        """Stres testi yapar.

        Args:
            components: Test edilecek bilesenler.
            load_factor: Yuk carpani.
            duration_seconds: Test suresi.

        Returns:
            Stres test sonucu.
        """
        results: dict[str, dict[str, Any]] = {}

        for component in components:
            failure_prob = min(0.1 * load_factor, 0.95)
            response_degradation = min(load_factor * 0.3, 0.9)
            would_fail = self._rng.random() < failure_prob

            results[component] = {
                "failure_probability": round(failure_prob, 3),
                "response_degradation": round(response_degradation, 2),
                "would_fail_under_stress": would_fail,
                "breaking_point_factor": round(1.0 / max(failure_prob, 0.01), 1),
            }

        # Genel sonuc
        failed = sum(1 for r in results.values() if r["would_fail_under_stress"])

        stress_result = {
            "components_tested": len(components),
            "load_factor": load_factor,
            "duration_seconds": duration_seconds,
            "results": results,
            "components_failed": failed,
            "system_stable": failed == 0,
            "weakest_component": min(
                results, key=lambda k: results[k]["breaking_point_factor"]
            ) if results else None,
        }

        self._stress_results.append(stress_result)
        return stress_result

    def get_risk_summary(self) -> dict[str, Any]:
        """Risk ozetini getirir.

        Returns:
            Ozet sozlugu.
        """
        if not self._events:
            return {"total_events": 0, "overall_risk": "low"}

        critical = sum(1 for e in self._events if e.impact == RiskLevel.CRITICAL)
        high = sum(1 for e in self._events if e.impact == RiskLevel.HIGH)

        if critical > 0:
            overall = "critical"
        elif high > 2:
            overall = "high"
        elif high > 0:
            overall = "medium"
        else:
            overall = "low"

        avg_prob = sum(e.probability for e in self._events) / len(self._events)

        return {
            "total_events": len(self._events),
            "critical_count": critical,
            "high_count": high,
            "average_probability": round(avg_prob, 3),
            "overall_risk": overall,
        }

    def _simulate_propagation(self, components: list[str]) -> list[str]:
        """Yayilim yolunu simule eder."""
        path = list(components)
        # Her bilesen icin olasi yayilim
        for comp in components:
            if comp in ("database", "service"):
                if "api" not in path:
                    path.append("api")
            if comp == "network":
                if "service" not in path:
                    path.append("service")
        return path

    def _estimate_recovery(self, impact: RiskLevel, component_count: int) -> float:
        """Kurtarma suresini tahmin eder."""
        base_times = {
            RiskLevel.NEGLIGIBLE: 30.0,
            RiskLevel.LOW: 120.0,
            RiskLevel.MEDIUM: 300.0,
            RiskLevel.HIGH: 900.0,
            RiskLevel.CRITICAL: 3600.0,
        }
        base = base_times.get(impact, 300.0)
        return base * (1.0 + (component_count - 1) * 0.3)

    def _suggest_mitigation(self, name: str, impact: RiskLevel) -> str:
        """Azaltma stratejisi onerir."""
        if impact == RiskLevel.CRITICAL:
            return "Acil mudahale: Yedek sisteme gec, olay ekibini bilgilendir"
        if impact == RiskLevel.HIGH:
            return "Oncelikli: Yedekten geri yukle, root cause analizi yap"
        if impact == RiskLevel.MEDIUM:
            return "Planli: Izle, gerekirse mudahale et"
        return "Dusuk oncelik: Kaydet ve izle"

    def _reduce_impact(self, impact: RiskLevel, effectiveness: float) -> RiskLevel:
        """Etki seviyesini dusurur."""
        levels = [
            RiskLevel.NEGLIGIBLE, RiskLevel.LOW, RiskLevel.MEDIUM,
            RiskLevel.HIGH, RiskLevel.CRITICAL,
        ]
        idx = levels.index(impact)
        reduction = int(effectiveness * 2)
        new_idx = max(0, idx - reduction)
        return levels[new_idx]

    def _risk_score(self, level: RiskLevel) -> float:
        """Risk puani hesaplar."""
        scores = {
            RiskLevel.NEGLIGIBLE: 0.1,
            RiskLevel.LOW: 0.3,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.7,
            RiskLevel.CRITICAL: 1.0,
        }
        return scores.get(level, 0.5)

    def _generate_recovery_steps(
        self, event: RiskEvent, strategy: str
    ) -> list[str]:
        """Kurtarma adimlarini olusturur."""
        steps = [
            f"1. {event.name} olayi tespit edildi",
            f"2. Etkilenen bilesenler: {', '.join(event.affected_components)}",
            f"3. Strateji: {strategy}",
        ]

        if event.impact in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            steps.append("4. Telegram ile bildirim gonder")
            steps.append("5. Insan onay bekle")
        else:
            steps.append("4. Otomatik kurtarma baslat")

        steps.append(f"{len(steps) + 1}. Dogrulama kontrolleri calistir")
        return steps

    def get_component_risks(self, component: str) -> list[RiskEvent]:
        """Bilesen risklerini olusturur.

        Args:
            component: Bilesen adi.

        Returns:
            RiskEvent listesi.
        """
        templates = _COMPONENT_RISKS.get(component, [])
        events: list[RiskEvent] = []

        for t in templates:
            event = RiskEvent(
                name=t["name"],
                description=f"{component}: {t['name']}",
                probability=t["probability"],
                impact=_RISK_MAP.get(t["impact"], RiskLevel.MEDIUM),
                affected_components=[component],
            )
            events.append(event)

        return events

    @property
    def event_count(self) -> int:
        """Risk olay sayisi."""
        return len(self._events)

    @property
    def stress_test_count(self) -> int:
        """Stres test sayisi."""
        return len(self._stress_results)
