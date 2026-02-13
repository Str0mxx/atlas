"""ATLAS Simulasyon Orkestratoru modulu.

Tam simulasyon pipeline, coklu senaryo karsilastirmasi,
oneri uretimi, guven puanlama ve kullanici raporlari.
"""

import logging
import time
from typing import Any

from app.core.simulation.action_simulator import ActionSimulator
from app.core.simulation.dry_run_executor import DryRunExecutor
from app.core.simulation.outcome_predictor import OutcomePredictor
from app.core.simulation.risk_simulator import RiskSimulator
from app.core.simulation.rollback_planner import RollbackPlanner
from app.core.simulation.scenario_generator import ScenarioGenerator
from app.core.simulation.what_if_engine import WhatIfEngine
from app.core.simulation.world_modeler import WorldModeler
from app.models.simulation import (
    RiskLevel,
    SimulationReport,
    SimulationStatus,
)

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Simulasyon orkestratoru.

    Tum simulasyon bilesenlerini koordine eder
    ve kapsamli simulasyon raporlari uretir.

    Attributes:
        _world: Dunya modelleyici.
        _action_sim: Aksiyon simulatoru.
        _scenario_gen: Senaryo uretici.
        _predictor: Sonuc tahmincisi.
        _risk_sim: Risk simulatoru.
        _rollback: Geri alma planlayici.
        _whatif: Ne olur motoru.
        _dry_run: Kuru calistirici.
        _reports: Rapor gecmisi.
    """

    def __init__(
        self,
        simulation_depth: int = 3,
        auto_simulate_risky: bool = True,
        dry_run_default: bool = False,
    ) -> None:
        """Simulasyon motorunu baslatir.

        Args:
            simulation_depth: Simulasyon derinligi.
            auto_simulate_risky: Riskli islemlerde otomatik simule et.
            dry_run_default: Varsayilan kuru calistirma.
        """
        self._world = WorldModeler()
        self._action_sim = ActionSimulator()
        self._scenario_gen = ScenarioGenerator()
        self._predictor = OutcomePredictor()
        self._risk_sim = RiskSimulator()
        self._rollback = RollbackPlanner()
        self._whatif = WhatIfEngine()
        self._dry_run = DryRunExecutor()

        self._simulation_depth = simulation_depth
        self._auto_simulate_risky = auto_simulate_risky
        self._dry_run_default = dry_run_default

        self._reports: list[SimulationReport] = []

        logger.info(
            "SimulationEngine baslatildi (depth=%d, auto_risky=%s)",
            simulation_depth, auto_simulate_risky,
        )

    def simulate(
        self,
        action_name: str,
        parameters: dict[str, Any] | None = None,
        include_dry_run: bool | None = None,
        include_risk: bool = True,
        include_whatif: bool = False,
    ) -> SimulationReport:
        """Tam simulasyon pipeline'i calistirir.

        Args:
            action_name: Aksiyon adi.
            parameters: Aksiyon parametreleri.
            include_dry_run: Kuru calistirma dahil et.
            include_risk: Risk simulasyonu dahil et.
            include_whatif: Ne olur analizi dahil et.

        Returns:
            SimulationReport nesnesi.
        """
        start = time.monotonic()

        report = SimulationReport(
            action_name=action_name,
            status=SimulationStatus.RUNNING,
        )

        try:
            # 1. Dunya goruntusu
            world_state = self._world.take_snapshot({"action": action_name})

            # 2. Aksiyon simulasyonu
            action_outcome = self._action_sim.simulate(
                action_name, parameters, world_state
            )

            # 3. Senaryo uretimi
            scenarios = self._scenario_gen.generate_all(
                action_name,
                base_probability=action_outcome.success_probability,
                parameters=parameters,
            )
            report.scenarios = scenarios

            # 4. Sonuc tahmini
            prediction = self._predictor.predict(
                action_name, scenarios
            )
            report.prediction = prediction

            # 5. Risk simulasyonu
            if include_risk:
                risk_events = self._simulate_risks(action_name, action_outcome)
                report.risk_events = risk_events

            # 6. Geri alma plani
            checkpoint = self._rollback.create_checkpoint(
                f"Pre-{action_name}",
                state_snapshot={"action": action_name, "params": parameters or {}},
            )
            risk_level = self._determine_overall_risk(report)
            rollback_plan = self._rollback.plan_rollback(
                action_name, checkpoint, risk_level
            )
            report.rollback_plan = checkpoint

            # 7. Kuru calistirma
            dry_run = include_dry_run if include_dry_run is not None else self._dry_run_default
            if dry_run:
                dr_result = self._dry_run.execute(
                    action_name, parameters, world_state
                )
                report.dry_run = dr_result

            # 8. Ne olur analizi
            if include_whatif and parameters:
                whatif_results = self._run_whatif(parameters)
                report.what_if_results = whatif_results

            # Genel risk
            report.overall_risk = risk_level
            report.confidence = prediction.confidence
            report.recommendation = self._generate_recommendation(report)
            report.status = SimulationStatus.COMPLETED

        except Exception as e:
            logger.error("Simulasyon hatasi: %s", e)
            report.status = SimulationStatus.FAILED
            report.recommendation = f"Simulasyon hatasi: {e}"

        elapsed = (time.monotonic() - start) * 1000
        report.processing_ms = round(elapsed, 2)

        self._reports.append(report)
        return report

    def compare_actions(
        self, actions: list[str], parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Birden fazla aksiyonu karsilastirir.

        Args:
            actions: Aksiyon listesi.
            parameters: Ortak parametreler.

        Returns:
            Karsilastirma sonucu.
        """
        reports: list[SimulationReport] = []
        for action in actions:
            report = self.simulate(action, parameters)
            reports.append(report)

        if not reports:
            return {"count": 0, "recommendation": "Aksiyon yok"}

        # En iyi aksiyonu sec
        best = max(reports, key=lambda r: r.confidence)
        worst = min(reports, key=lambda r: r.confidence)

        comparison = {
            "count": len(reports),
            "actions": [],
            "best_action": best.action_name,
            "worst_action": worst.action_name,
        }

        for r in reports:
            comparison["actions"].append({
                "name": r.action_name,
                "confidence": r.confidence,
                "risk": r.overall_risk.value,
                "recommended": r.recommendation,
                "scenarios_count": len(r.scenarios),
            })

        return comparison

    def should_simulate(self, action_name: str, risk_level: RiskLevel) -> bool:
        """Simulasyon gerekli mi kontrol eder.

        Args:
            action_name: Aksiyon adi.
            risk_level: Risk seviyesi.

        Returns:
            Simulasyon gerekli ise True.
        """
        if not self._auto_simulate_risky:
            return False

        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True

        risky_actions = {"deploy", "migrate", "delete", "restart"}
        action_type = self._detect_action_type(action_name)
        return action_type in risky_actions

    def get_report(self, report_id: str) -> SimulationReport | None:
        """Raporu getirir.

        Args:
            report_id: Rapor ID.

        Returns:
            SimulationReport veya None.
        """
        for report in self._reports:
            if report.report_id == report_id:
                return report
        return None

    def generate_user_report(self, report: SimulationReport) -> str:
        """Kullanici dostu rapor olusturur.

        Args:
            report: Simulasyon raporu.

        Returns:
            Formatlanmis rapor metni.
        """
        lines: list[str] = [
            f"=== Simulasyon Raporu: {report.action_name} ===",
            f"Durum: {report.status.value}",
            f"Risk: {report.overall_risk.value}",
            f"Guven: %{report.confidence * 100:.0f}",
            f"Sure: {report.processing_ms:.1f}ms",
            "",
        ]

        # Senaryolar
        if report.scenarios:
            lines.append(f"--- Senaryolar ({len(report.scenarios)}) ---")
            for s in report.scenarios:
                lines.append(f"  {s.scenario_type.value}: {s.name} (p={s.probability})")
            lines.append("")

        # Tahmin
        if report.prediction:
            lines.append("--- Tahmin ---")
            lines.append(f"  Basari: %{report.prediction.success_probability * 100:.0f}")
            lines.append(f"  Onerilen: {'Evet' if report.prediction.recommended else 'Hayir'}")
            if report.prediction.failure_modes:
                lines.append(f"  Basarisizlik modlari: {len(report.prediction.failure_modes)}")
            lines.append("")

        # Risk
        if report.risk_events:
            lines.append(f"--- Riskler ({len(report.risk_events)}) ---")
            for r in report.risk_events:
                lines.append(f"  {r.impact.value}: {r.name}")
            lines.append("")

        # Kuru calistirma
        if report.dry_run:
            lines.append("--- Kuru Calistirma ---")
            lines.append(f"  Basarili olur mu: {'Evet' if report.dry_run.would_succeed else 'Hayir'}")
            if report.dry_run.missing_prerequisites:
                lines.append(f"  Eksik: {', '.join(report.dry_run.missing_prerequisites)}")
            lines.append("")

        # Oneri
        lines.append(f">>> Oneri: {report.recommendation}")

        return "\n".join(lines)

    def _simulate_risks(
        self, action_name: str, action_outcome: Any
    ) -> list[Any]:
        """Riskleri simule eder."""
        action_type = self._detect_action_type(action_name)

        # Yan etkilerden risk olaylari olustur
        risks = []
        for se in action_outcome.side_effects:
            event = self._risk_sim.inject_risk(
                name=se.description,
                affected_components=[se.affected_entity],
                probability=se.probability,
                impact=se.severity,
            )
            risks.append(event)

        # Bilesen riskleri
        component_risks = self._risk_sim.get_component_risks(
            "database" if action_type == "migrate" else "service"
        )
        risks.extend(component_risks)

        return risks

    def _run_whatif(self, parameters: dict[str, Any]) -> list[Any]:
        """Ne olur analizi calistirir."""
        results = []
        for key, value in parameters.items():
            if isinstance(value, (int, float)):
                result = self._whatif.analyze_parameter(
                    key, float(value), float(value) * 1.5
                )
                results.append(result)
        return results

    def _determine_overall_risk(self, report: SimulationReport) -> RiskLevel:
        """Genel risk seviyesini belirler."""
        # Prediction kontrolu
        if report.prediction:
            if report.prediction.success_probability < 0.5:
                return RiskLevel.CRITICAL
            if report.prediction.success_probability < 0.7:
                return RiskLevel.HIGH

            # Kritik basarisizlik modu varsa
            for fm in report.prediction.failure_modes:
                if fm.severity == RiskLevel.CRITICAL and fm.probability > 0.1:
                    return RiskLevel.HIGH

        # Risk olaylari
        if report.risk_events:
            critical = sum(1 for e in report.risk_events if e.impact == RiskLevel.CRITICAL)
            if critical > 0:
                return RiskLevel.HIGH

        # Senaryolar
        if report.scenarios:
            worst = min(s.impact_score for s in report.scenarios)
            if worst < -0.6:
                return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _generate_recommendation(self, report: SimulationReport) -> str:
        """Oneri uretir."""
        if report.overall_risk == RiskLevel.CRITICAL:
            return "DURDURUN: Cok yuksek risk, alternatif arastin"

        if report.overall_risk == RiskLevel.HIGH:
            return "DIKKAT: Yuksek risk, onay alin ve hazirlik yapin"

        if report.prediction and not report.prediction.recommended:
            return "ONERILMEZ: Basarisizlik olasiligi yuksek"

        if report.dry_run and not report.dry_run.would_succeed:
            return "BEKLEYIN: On kosullar karsilanmiyor"

        if report.overall_risk == RiskLevel.MEDIUM:
            return "DIKKATLI DEVAM: Orta risk, izleme ile devam edin"

        return "GUVENLI: Devam edilebilir"

    def _detect_action_type(self, action_name: str) -> str:
        """Aksiyon tipini tespit eder."""
        lower = action_name.lower()
        for t in ("deploy", "migrate", "delete", "restart", "update", "send", "backup", "create"):
            if t in lower:
                return t
        return "update"

    @property
    def world(self) -> WorldModeler:
        """Dunya modelleyici."""
        return self._world

    @property
    def action_simulator(self) -> ActionSimulator:
        """Aksiyon simulatoru."""
        return self._action_sim

    @property
    def scenario_generator(self) -> ScenarioGenerator:
        """Senaryo uretici."""
        return self._scenario_gen

    @property
    def predictor(self) -> OutcomePredictor:
        """Sonuc tahmincisi."""
        return self._predictor

    @property
    def risk_simulator(self) -> RiskSimulator:
        """Risk simulatoru."""
        return self._risk_sim

    @property
    def rollback_planner(self) -> RollbackPlanner:
        """Geri alma planlayici."""
        return self._rollback

    @property
    def whatif(self) -> WhatIfEngine:
        """Ne olur motoru."""
        return self._whatif

    @property
    def dry_runner(self) -> DryRunExecutor:
        """Kuru calistirici."""
        return self._dry_run

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)
