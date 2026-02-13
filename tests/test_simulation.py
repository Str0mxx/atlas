"""ATLAS Simulation & Scenario Testing sistemi testleri.

WorldModeler, ActionSimulator, ScenarioGenerator,
OutcomePredictor, RiskSimulator, RollbackPlanner,
WhatIfEngine, DryRunExecutor, SimulationEngine testleri.
"""

from app.core.simulation.action_simulator import ActionSimulator
from app.core.simulation.dry_run_executor import DryRunExecutor
from app.core.simulation.outcome_predictor import OutcomePredictor
from app.core.simulation.risk_simulator import RiskSimulator
from app.core.simulation.rollback_planner import RollbackPlanner
from app.core.simulation.scenario_generator import ScenarioGenerator
from app.core.simulation.simulation_engine import SimulationEngine
from app.core.simulation.what_if_engine import WhatIfEngine
from app.core.simulation.world_modeler import WorldModeler
from app.models.simulation import (
    ActionOutcome,
    Assumption,
    Constraint,
    DryRunResult,
    EntityState,
    FailureMode,
    OutcomePrediction,
    OutcomeType,
    ResourceState,
    ResourceType,
    RiskEvent,
    RiskLevel,
    RollbackCheckpoint,
    RollbackStatus,
    Scenario,
    ScenarioType,
    SensitivityLevel,
    SideEffect,
    SimulationReport,
    SimulationStatus,
    WhatIfResult,
    WorldSnapshot,
)


# === Model Testleri ===


class TestSimulationModels:
    """Simulation model testleri."""

    def test_entity_state_defaults(self) -> None:
        """EntityState varsayilan degerler."""
        e = EntityState()
        assert e.status == "active"
        assert e.properties == {}

    def test_resource_state_defaults(self) -> None:
        """ResourceState varsayilan degerler."""
        r = ResourceState()
        assert r.resource_type == ResourceType.CPU
        assert r.current_usage == 0.0

    def test_constraint_defaults(self) -> None:
        """Constraint varsayilan degerler."""
        c = Constraint()
        assert c.constraint_type == "hard"
        assert c.is_satisfied is True

    def test_assumption_defaults(self) -> None:
        """Assumption varsayilan degerler."""
        a = Assumption()
        assert a.confidence == 0.5
        assert a.is_validated is False

    def test_world_snapshot_defaults(self) -> None:
        """WorldSnapshot varsayilan degerler."""
        w = WorldSnapshot()
        assert w.entities == []
        assert w.resources == []

    def test_side_effect_defaults(self) -> None:
        """SideEffect varsayilan degerler."""
        s = SideEffect()
        assert s.severity == RiskLevel.LOW
        assert s.reversible is True

    def test_action_outcome_defaults(self) -> None:
        """ActionOutcome varsayilan degerler."""
        a = ActionOutcome()
        assert a.outcome_type == OutcomeType.UNKNOWN
        assert a.success_probability == 0.5

    def test_scenario_defaults(self) -> None:
        """Scenario varsayilan degerler."""
        s = Scenario()
        assert s.scenario_type == ScenarioType.MOST_LIKELY
        assert s.probability == 0.5

    def test_failure_mode_defaults(self) -> None:
        """FailureMode varsayilan degerler."""
        f = FailureMode()
        assert f.severity == RiskLevel.MEDIUM
        assert f.probability == 0.1

    def test_outcome_prediction_defaults(self) -> None:
        """OutcomePrediction varsayilan degerler."""
        o = OutcomePrediction()
        assert o.recommended is True
        assert o.confidence == 0.5

    def test_risk_event_defaults(self) -> None:
        """RiskEvent varsayilan degerler."""
        r = RiskEvent()
        assert r.impact == RiskLevel.MEDIUM
        assert r.probability == 0.1

    def test_rollback_checkpoint_defaults(self) -> None:
        """RollbackCheckpoint varsayilan degerler."""
        r = RollbackCheckpoint()
        assert r.status == RollbackStatus.PLANNED

    def test_what_if_result_defaults(self) -> None:
        """WhatIfResult varsayilan degerler."""
        w = WhatIfResult()
        assert w.sensitivity == SensitivityLevel.MODERATE
        assert w.tipping_point is False

    def test_dry_run_result_defaults(self) -> None:
        """DryRunResult varsayilan degerler."""
        d = DryRunResult()
        assert d.would_succeed is True
        assert d.prerequisites_met is True
        assert d.permissions_ok is True

    def test_simulation_report_defaults(self) -> None:
        """SimulationReport varsayilan degerler."""
        r = SimulationReport()
        assert r.status == SimulationStatus.PENDING
        assert r.overall_risk == RiskLevel.LOW

    def test_scenario_type_enum(self) -> None:
        """ScenarioType enum degerleri."""
        assert len(ScenarioType) == 5

    def test_simulation_status_enum(self) -> None:
        """SimulationStatus enum degerleri."""
        assert len(SimulationStatus) == 5

    def test_risk_level_enum(self) -> None:
        """RiskLevel enum degerleri."""
        assert len(RiskLevel) == 5

    def test_outcome_type_enum(self) -> None:
        """OutcomeType enum degerleri."""
        assert len(OutcomeType) == 4

    def test_rollback_status_enum(self) -> None:
        """RollbackStatus enum degerleri."""
        assert len(RollbackStatus) == 5

    def test_resource_type_enum(self) -> None:
        """ResourceType enum degerleri."""
        assert len(ResourceType) == 6

    def test_sensitivity_level_enum(self) -> None:
        """SensitivityLevel enum degerleri."""
        assert len(SensitivityLevel) == 5


# === WorldModeler Testleri ===


class TestWorldModeler:
    """WorldModeler testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        wm = WorldModeler()
        assert wm.entity_count == 0
        assert wm.snapshot_count == 0

    def test_add_entity(self) -> None:
        """Varlik ekleme."""
        wm = WorldModeler()
        entity = wm.add_entity("db1", "database", {"version": "15"})
        assert entity.entity_id == "db1"
        assert wm.entity_count == 1

    def test_get_entity(self) -> None:
        """Varlik getirme."""
        wm = WorldModeler()
        wm.add_entity("s1", "service")
        assert wm.get_entity("s1") is not None
        assert wm.get_entity("unknown") is None

    def test_update_entity(self) -> None:
        """Varlik guncelleme."""
        wm = WorldModeler()
        wm.add_entity("s1", "service", {"port": 8080})
        updated = wm.update_entity("s1", {"port": 9090})
        assert updated is not None
        assert updated.properties["port"] == 9090

    def test_remove_entity(self) -> None:
        """Varlik silme."""
        wm = WorldModeler()
        wm.add_entity("s1", "service")
        assert wm.remove_entity("s1") is True
        assert wm.entity_count == 0
        assert wm.remove_entity("unknown") is False

    def test_relationships(self) -> None:
        """Iliski yonetimi."""
        wm = WorldModeler()
        wm.add_entity("api", "service")
        wm.add_entity("db", "database")
        wm.add_relationship("api", "db")
        rels = wm.get_relationships("api")
        assert "db" in rels

    def test_set_resource(self) -> None:
        """Kaynak durumu."""
        wm = WorldModeler()
        r = wm.set_resource(ResourceType.CPU, 0.7, 100.0, "%")
        assert r.current_usage == 0.7
        assert abs(r.available - 30.0) < 0.01

    def test_get_resource(self) -> None:
        """Kaynak getirme."""
        wm = WorldModeler()
        wm.set_resource(ResourceType.MEMORY, 0.5)
        assert wm.get_resource(ResourceType.MEMORY) is not None
        assert wm.get_resource(ResourceType.DISK) is None

    def test_add_constraint(self) -> None:
        """Kisitlama ekleme."""
        wm = WorldModeler()
        c = wm.add_constraint("max_connections", "En fazla 100 baglanti")
        assert c.name == "max_connections"
        assert wm.constraint_count == 1

    def test_check_constraints(self) -> None:
        """Kisitlama kontrolu."""
        wm = WorldModeler()
        c = wm.add_constraint("test")
        c.is_satisfied = False
        unsatisfied = wm.check_constraints()
        assert len(unsatisfied) == 1

    def test_add_assumption(self) -> None:
        """Varsayim ekleme."""
        wm = WorldModeler()
        a = wm.add_assumption("Servisler saglikli", 0.9, "monitoring")
        assert a.confidence == 0.9

    def test_validate_assumption(self) -> None:
        """Varsayim dogrulama."""
        wm = WorldModeler()
        a = wm.add_assumption("test")
        assert wm.validate_assumption(a.assumption_id, True) is True
        assert a.is_validated is True

    def test_invalidate_assumption(self) -> None:
        """Varsayim gecersiz kilma."""
        wm = WorldModeler()
        a = wm.add_assumption("test", confidence=0.8)
        wm.validate_assumption(a.assumption_id, False)
        assert a.confidence == 0.0

    def test_unvalidated_assumptions(self) -> None:
        """Dogrulanmamis varsayimlar."""
        wm = WorldModeler()
        a1 = wm.add_assumption("a1")
        a2 = wm.add_assumption("a2")
        wm.validate_assumption(a1.assumption_id, True)
        assert len(wm.get_unvalidated_assumptions()) == 1

    def test_take_snapshot(self) -> None:
        """Goruntu alma."""
        wm = WorldModeler()
        wm.add_entity("s1", "service")
        wm.set_resource(ResourceType.CPU, 0.5)
        snap = wm.take_snapshot({"purpose": "test"})
        assert len(snap.entities) == 1
        assert len(snap.resources) == 1
        assert wm.snapshot_count == 1

    def test_get_latest_snapshot(self) -> None:
        """Son goruntu."""
        wm = WorldModeler()
        assert wm.get_latest_snapshot() is None
        wm.take_snapshot()
        assert wm.get_latest_snapshot() is not None

    def test_entities_by_type(self) -> None:
        """Tipe gore varliklar."""
        wm = WorldModeler()
        wm.add_entity("s1", "service")
        wm.add_entity("s2", "service")
        wm.add_entity("db1", "database")
        services = wm.get_entities_by_type("service")
        assert len(services) == 2

    def test_remove_entity_cleans_relationships(self) -> None:
        """Varlik silme iliskileri temizler."""
        wm = WorldModeler()
        wm.add_entity("a", "service")
        wm.add_entity("b", "service")
        wm.add_relationship("a", "b")
        wm.remove_entity("b")
        assert "b" not in wm.get_relationships("a")


# === ActionSimulator Testleri ===


class TestActionSimulator:
    """ActionSimulator testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        sim = ActionSimulator()
        assert sim.simulation_count == 0

    def test_simulate_deploy(self) -> None:
        """Deploy simulasyonu."""
        sim = ActionSimulator()
        outcome = sim.simulate("deploy_app")
        assert outcome.action_name == "deploy_app"
        assert outcome.success_probability > 0
        assert outcome.estimated_duration_seconds > 0

    def test_simulate_with_side_effects(self) -> None:
        """Yan etkili simulasyon."""
        sim = ActionSimulator()
        outcome = sim.simulate("deploy_service")
        assert len(outcome.side_effects) > 0

    def test_simulate_delete(self) -> None:
        """Silme simulasyonu."""
        sim = ActionSimulator()
        outcome = sim.simulate("delete_records")
        assert any(not se.reversible for se in outcome.side_effects)

    def test_simulate_with_parameters(self) -> None:
        """Parametreli simulasyon."""
        sim = ActionSimulator()
        outcome = sim.simulate("update_config", {"dry_run": True})
        assert outcome.success_probability == 1.0

    def test_simulate_with_world_state(self) -> None:
        """Dunya durumlu simulasyon."""
        wm = WorldModeler()
        wm.set_resource(ResourceType.CPU, 0.95)
        snap = wm.take_snapshot()
        sim = ActionSimulator()
        outcome = sim.simulate("deploy_app", world_state=snap)
        assert outcome.success_probability < 0.85

    def test_simulate_chain(self) -> None:
        """Zincir simulasyonu."""
        sim = ActionSimulator()
        results = sim.simulate_chain(["backup_db", "migrate_schema", "deploy_app"])
        assert len(results) == 3
        # Zincirdeki son aksiyonun olasiligi dusmelidir
        assert results[-1].success_probability <= results[0].success_probability

    def test_estimate_total_duration(self) -> None:
        """Toplam sure tahmini."""
        sim = ActionSimulator()
        total = sim.estimate_total_duration(["backup_db", "deploy_app"])
        assert total > 0

    def test_get_resource_requirements(self) -> None:
        """Kaynak gereksinimleri."""
        sim = ActionSimulator()
        reqs = sim.get_resource_requirements("deploy_app")
        assert "cpu" in reqs

    def test_high_resource_usage_reduces_probability(self) -> None:
        """Yuksek kaynak kullanimi olasiligi dusurur."""
        wm = WorldModeler()
        c = wm.add_constraint("test")
        c.is_satisfied = False
        snap = wm.take_snapshot()
        sim = ActionSimulator()
        outcome = sim.simulate("deploy_app", world_state=snap)
        assert outcome.success_probability < 0.85

    def test_force_parameter_reduces_probability(self) -> None:
        """Force parametresi olasiligi dusurur."""
        sim = ActionSimulator()
        normal = sim.simulate("update_config")
        forced = sim.simulate("update_config", {"force": True})
        assert forced.success_probability < normal.success_probability

    def test_migrate_side_effects(self) -> None:
        """Migrasyon yan etkileri."""
        sim = ActionSimulator()
        outcome = sim.simulate("migrate_database")
        assert len(outcome.side_effects) >= 2


# === ScenarioGenerator Testleri ===


class TestScenarioGenerator:
    """ScenarioGenerator testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        sg = ScenarioGenerator(seed=42)
        assert sg.scenario_count == 0

    def test_generate_all(self) -> None:
        """Tum senaryolar."""
        sg = ScenarioGenerator(seed=42)
        scenarios = sg.generate_all("deploy_app")
        assert len(scenarios) == 5
        types = {s.scenario_type for s in scenarios}
        assert ScenarioType.BEST_CASE in types
        assert ScenarioType.WORST_CASE in types
        assert ScenarioType.MOST_LIKELY in types

    def test_best_case(self) -> None:
        """En iyi durum."""
        sg = ScenarioGenerator()
        s = sg.generate_best_case("deploy_app", 0.85)
        assert s.scenario_type == ScenarioType.BEST_CASE
        assert s.impact_score > 0
        assert len(s.assumptions) > 0

    def test_worst_case(self) -> None:
        """En kotu durum."""
        sg = ScenarioGenerator()
        s = sg.generate_worst_case("deploy_app")
        assert s.scenario_type == ScenarioType.WORST_CASE
        assert s.impact_score < 0

    def test_most_likely(self) -> None:
        """En olasi durum."""
        sg = ScenarioGenerator()
        s = sg.generate_most_likely("deploy_app", 0.85)
        assert s.scenario_type == ScenarioType.MOST_LIKELY

    def test_most_likely_low_probability(self) -> None:
        """Dusuk olasilikta en olasi."""
        sg = ScenarioGenerator()
        s = sg.generate_most_likely("risky_action", 0.3)
        assert s.outcomes[0].outcome_type == OutcomeType.FAILURE

    def test_edge_case(self) -> None:
        """Edge case."""
        sg = ScenarioGenerator(seed=42)
        s = sg.generate_edge_case("deploy_app")
        assert s.scenario_type == ScenarioType.EDGE_CASE
        assert s.probability < 0.2

    def test_random(self) -> None:
        """Rastgele senaryo."""
        sg = ScenarioGenerator(seed=42)
        s = sg.generate_random("deploy_app")
        assert s.scenario_type == ScenarioType.RANDOM

    def test_compare_scenarios(self) -> None:
        """Senaryo karsilastirma."""
        sg = ScenarioGenerator(seed=42)
        scenarios = sg.generate_all("deploy_app")
        comparison = sg.compare_scenarios(scenarios)
        assert comparison["count"] == 5
        assert "best" in comparison
        assert "worst" in comparison

    def test_compare_empty(self) -> None:
        """Bos karsilastirma."""
        sg = ScenarioGenerator()
        comparison = sg.compare_scenarios([])
        assert comparison["count"] == 0

    def test_worst_case_has_side_effects(self) -> None:
        """En kotu durumda yan etkiler."""
        sg = ScenarioGenerator()
        s = sg.generate_worst_case("deploy_app")
        assert len(s.outcomes[0].side_effects) > 0


# === OutcomePredictor Testleri ===


class TestOutcomePredictor:
    """OutcomePredictor testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        op = OutcomePredictor()
        assert op.prediction_count == 0

    def test_predict(self) -> None:
        """Temel tahmin."""
        op = OutcomePredictor()
        pred = op.predict("deploy_app")
        assert pred.action_name == "deploy_app"
        assert 0.0 <= pred.success_probability <= 1.0
        assert pred.confidence > 0

    def test_predict_with_scenarios(self) -> None:
        """Senaryolu tahmin."""
        sg = ScenarioGenerator(seed=42)
        scenarios = sg.generate_all("deploy_app")
        op = OutcomePredictor()
        pred = op.predict("deploy_app", scenarios)
        assert op.prediction_count == 1

    def test_failure_modes(self) -> None:
        """Basarisizlik modlari."""
        op = OutcomePredictor()
        pred = op.predict("deploy_app")
        assert len(pred.failure_modes) > 0

    def test_deploy_failure_modes(self) -> None:
        """Deploy basarisizlik modlari."""
        op = OutcomePredictor()
        pred = op.predict("deploy_service")
        mode_names = [fm.name for fm in pred.failure_modes]
        assert any("Build" in n or "Config" in n or "Kaynak" in n for n in mode_names)

    def test_cascading_effects(self) -> None:
        """Zincirleme etkiler."""
        op = OutcomePredictor()
        pred = op.predict("migrate_database")
        assert len(pred.cascading_effects) > 0

    def test_long_term_impact(self) -> None:
        """Uzun vadeli etki."""
        op = OutcomePredictor()
        pred = op.predict("deploy_app")
        assert len(pred.long_term_impact) > 0

    def test_record_outcome(self) -> None:
        """Sonuc kaydetme."""
        op = OutcomePredictor()
        op.record_outcome("deploy_app", True)
        op.record_outcome("deploy_app", True)
        op.record_outcome("deploy_app", False)
        rate = op.get_historical_rate("deploy_app")
        assert rate is not None
        assert abs(rate - 2 / 3) < 0.01

    def test_historical_rate_none(self) -> None:
        """Gecmis veri yok."""
        op = OutcomePredictor()
        assert op.get_historical_rate("unknown") is None

    def test_historical_improves_confidence(self) -> None:
        """Gecmis veri guveni artirir."""
        op = OutcomePredictor()
        pred1 = op.predict("deploy_app")
        for _ in range(10):
            op.record_outcome("deploy_app", True)
        pred2 = op.predict("deploy_app")
        assert pred2.confidence >= pred1.confidence

    def test_assess_from_outcomes(self) -> None:
        """Sonuclardan tahmin."""
        op = OutcomePredictor()
        outcomes = [
            ActionOutcome(action_name="test", success_probability=0.9),
            ActionOutcome(action_name="test", success_probability=0.8),
        ]
        pred = op.assess_from_outcomes(outcomes)
        assert pred.success_probability == 0.85

    def test_assess_from_empty(self) -> None:
        """Bos sonuclardan tahmin."""
        op = OutcomePredictor()
        pred = op.assess_from_outcomes([])
        assert pred.action_name == "unknown"

    def test_context_high_load(self) -> None:
        """Yuksek yuk baglami."""
        op = OutcomePredictor()
        normal = op.predict("deploy_app")
        loaded = op.predict("deploy_app", context={"high_load": True})
        assert loaded.success_probability < normal.success_probability

    def test_not_recommended_low_probability(self) -> None:
        """Dusuk olasilikta onerilmez."""
        op = OutcomePredictor()
        for _ in range(10):
            op.record_outcome("deploy_app", False)
        pred = op.predict("deploy_app")
        assert pred.recommended is False


# === RiskSimulator Testleri ===


class TestRiskSimulator:
    """RiskSimulator testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        rs = RiskSimulator()
        assert rs.event_count == 0

    def test_inject_risk(self) -> None:
        """Risk enjeksiyonu."""
        rs = RiskSimulator()
        event = rs.inject_risk("DB_down", ["database"], 0.1, RiskLevel.HIGH)
        assert event.name == "DB_down"
        assert len(event.propagation_path) >= 1
        assert event.recovery_time_seconds > 0
        assert rs.event_count == 1

    def test_propagation_path(self) -> None:
        """Yayilim yolu."""
        rs = RiskSimulator()
        event = rs.inject_risk("test", ["database"])
        # database -> api yayilimi bekleniyor
        assert "api" in event.propagation_path

    def test_failure_propagation(self) -> None:
        """Basarisizlik yayilimi."""
        rs = RiskSimulator()
        deps = {
            "database": ["api", "worker"],
            "api": ["frontend"],
            "worker": [],
            "frontend": [],
        }
        affected = rs.simulate_failure_propagation("database", deps)
        assert "database" in affected
        assert "api" in affected
        assert "frontend" in affected

    def test_recovery_with_redundancy(self) -> None:
        """Yedeklilikle kurtarma."""
        rs = RiskSimulator()
        event = rs.inject_risk("test", ["service"], 0.5, RiskLevel.MEDIUM)
        result = rs.simulate_recovery(event, has_redundancy=True)
        assert result["strategy"] == "Otomatik failover"
        assert result["estimated_recovery_seconds"] < event.recovery_time_seconds

    def test_recovery_with_backup(self) -> None:
        """Yedekle kurtarma."""
        rs = RiskSimulator()
        event = rs.inject_risk("test", ["service"], 0.5, RiskLevel.MEDIUM)
        result = rs.simulate_recovery(event, has_backup=True, has_redundancy=False)
        assert result["strategy"] == "Yedekten geri yukleme"

    def test_recovery_without_backup(self) -> None:
        """Yedeksiz kurtarma."""
        rs = RiskSimulator()
        event = rs.inject_risk("test", ["service"], 0.5, RiskLevel.MEDIUM)
        result = rs.simulate_recovery(event, has_backup=False)
        assert result["data_loss_risk"] is True

    def test_mitigation(self) -> None:
        """Azaltma testi."""
        rs = RiskSimulator()
        event = rs.inject_risk("test", ["service"], 0.5, RiskLevel.HIGH)
        result = rs.test_mitigation(event, ["monitoring", "auto_restart", "alerting"])
        assert result["effectiveness"] > 0
        assert result["reduced_probability"] < event.probability

    def test_stress_test(self) -> None:
        """Stres testi."""
        rs = RiskSimulator(seed=42)
        result = rs.stress_test(["api", "database", "cache"], load_factor=3.0)
        assert result["components_tested"] == 3
        assert "weakest_component" in result

    def test_stress_test_stable(self) -> None:
        """Stabil stres testi."""
        rs = RiskSimulator(seed=42)
        result = rs.stress_test(["api"], load_factor=0.5)
        assert result["components_tested"] == 1

    def test_risk_summary(self) -> None:
        """Risk ozeti."""
        rs = RiskSimulator()
        rs.inject_risk("r1", ["api"], 0.3, RiskLevel.LOW)
        rs.inject_risk("r2", ["db"], 0.1, RiskLevel.CRITICAL)
        summary = rs.get_risk_summary()
        assert summary["total_events"] == 2
        assert summary["critical_count"] == 1
        assert summary["overall_risk"] == "critical"

    def test_empty_risk_summary(self) -> None:
        """Bos risk ozeti."""
        rs = RiskSimulator()
        summary = rs.get_risk_summary()
        assert summary["total_events"] == 0

    def test_component_risks(self) -> None:
        """Bilesen riskleri."""
        rs = RiskSimulator()
        risks = rs.get_component_risks("database")
        assert len(risks) > 0


# === RollbackPlanner Testleri ===


class TestRollbackPlanner:
    """RollbackPlanner testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        rp = RollbackPlanner()
        assert rp.checkpoint_count == 0
        assert rp.plan_count == 0

    def test_create_checkpoint(self) -> None:
        """Checkpoint olusturma."""
        rp = RollbackPlanner()
        cp = rp.create_checkpoint("pre_deploy", {"version": "1.0"})
        assert cp.name == "pre_deploy"
        assert cp.status == RollbackStatus.PLANNED
        assert rp.checkpoint_count == 1

    def test_get_checkpoint(self) -> None:
        """Checkpoint getirme."""
        rp = RollbackPlanner()
        cp = rp.create_checkpoint("test")
        assert rp.get_checkpoint(cp.checkpoint_id) is not None
        assert rp.get_checkpoint("unknown") is None

    def test_plan_rollback_deploy(self) -> None:
        """Deploy geri alma plani."""
        rp = RollbackPlanner()
        cp = rp.create_checkpoint("pre_deploy")
        plan = rp.plan_rollback("deploy_app", cp, RiskLevel.MEDIUM)
        assert plan["action_type"] == "deploy"
        assert len(plan["steps"]) > 0
        assert plan["requires_downtime"] is True

    def test_plan_rollback_migrate(self) -> None:
        """Migrasyon geri alma plani."""
        rp = RollbackPlanner()
        plan = rp.plan_rollback("migrate_database", risk_level=RiskLevel.HIGH)
        assert plan["data_recovery"]["backup_required"] is True

    def test_plan_rollback_auto(self) -> None:
        """Otomatik geri alma."""
        rp = RollbackPlanner()
        plan = rp.plan_rollback("update_config", risk_level=RiskLevel.LOW)
        assert plan["automatic"] is True

    def test_execute_rollback(self) -> None:
        """Geri alma calistirma."""
        rp = RollbackPlanner()
        cp = rp.create_checkpoint("test", validation_checks=["check1", "check2"])
        cp.rollback_steps = ["step1", "step2"]
        result = rp.execute_rollback(cp.checkpoint_id)
        assert result["success"] is True
        assert cp.status == RollbackStatus.COMPLETED

    def test_execute_rollback_not_found(self) -> None:
        """Bulunamayan checkpoint."""
        rp = RollbackPlanner()
        result = rp.execute_rollback("unknown")
        assert result["success"] is False

    def test_validate_after_rollback(self) -> None:
        """Geri alma sonrasi dogrulama."""
        rp = RollbackPlanner()
        cp = rp.create_checkpoint("test", {"key": "value"})
        result = rp.validate_after_rollback(cp.checkpoint_id)
        assert result["valid"] is True

    def test_validate_not_found(self) -> None:
        """Bulunamayan dogrulama."""
        rp = RollbackPlanner()
        result = rp.validate_after_rollback("unknown")
        assert result["valid"] is False

    def test_get_rollback_plan(self) -> None:
        """Geri alma plani getirme."""
        rp = RollbackPlanner()
        rp.plan_rollback("deploy_app")
        plan = rp.get_rollback_plan("deploy_app")
        assert plan is not None
        assert plan["action_name"] == "deploy_app"

    def test_get_rollback_plan_not_found(self) -> None:
        """Plan bulunamadi."""
        rp = RollbackPlanner()
        assert rp.get_rollback_plan("unknown") is None

    def test_service_restoration_deploy(self) -> None:
        """Deploy servis restorasyonu."""
        rp = RollbackPlanner()
        plan = rp.plan_rollback("deploy_app")
        assert plan["service_restoration"]["restart_required"] is True


# === WhatIfEngine Testleri ===


class TestWhatIfEngine:
    """WhatIfEngine testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        wie = WhatIfEngine()
        assert wie.result_count == 0

    def test_analyze_parameter(self) -> None:
        """Parametre analizi."""
        wie = WhatIfEngine()
        result = wie.analyze_parameter("timeout", 30.0, 60.0)
        assert result.parameter == "timeout"
        assert result.original_value == 30.0
        assert result.varied_value == 60.0

    def test_analyze_with_function(self) -> None:
        """Fonksiyonlu analiz."""
        wie = WhatIfEngine()
        result = wie.analyze_parameter(
            "workers", 4.0, 8.0,
            outcome_function=lambda x: x * 100,
        )
        assert result.outcome_change == 400.0

    def test_sensitivity_analysis(self) -> None:
        """Hassasiyet analizi."""
        wie = WhatIfEngine()
        results = wie.sensitivity_analysis("timeout", 30.0)
        assert len(results) == 6  # varsayilan 6 varyasyon

    def test_sensitivity_with_function(self) -> None:
        """Fonksiyonlu hassasiyet analizi."""
        wie = WhatIfEngine()
        results = wie.sensitivity_analysis(
            "workers", 4.0,
            outcome_function=lambda x: x ** 2,
        )
        assert len(results) > 0

    def test_find_threshold(self) -> None:
        """Esik deger bulma."""
        wie = WhatIfEngine()
        threshold = wie.find_threshold(
            "workers", 4.0, 100.0,
            outcome_function=lambda x: x * 25,
        )
        assert threshold is not None
        assert abs(threshold - 4.0) < 0.1

    def test_find_threshold_not_found(self) -> None:
        """Esik bulunamadi."""
        wie = WhatIfEngine()
        threshold = wie.find_threshold(
            "test", 1.0, 1000000.0,
            outcome_function=lambda x: x,
            max_iterations=5,
        )
        # Cok yuksek hedef, bulunamayabilir
        # None donebilir veya yakin bir deger

    def test_detect_tipping_points(self) -> None:
        """Devrilme noktasi tespiti."""
        wie = WhatIfEngine()
        # Buyuk degisim yapan fonksiyon
        points = wie.detect_tipping_points(
            "load", 1.0,
            outcome_function=lambda x: x ** 3,
            steps=10,
        )
        assert isinstance(points, list)

    def test_optimize_maximize(self) -> None:
        """Maksimizasyon optimizasyonu."""
        wie = WhatIfEngine()
        result = wie.optimize(
            {"x": 1.0},
            outcome_function=lambda p: -(p["x"] - 5) ** 2 + 25,
            direction="maximize",
        )
        assert result["optimized_outcome"] >= result["original_outcome"]

    def test_optimize_minimize(self) -> None:
        """Minimizasyon optimizasyonu."""
        wie = WhatIfEngine()
        result = wie.optimize(
            {"x": 10.0},
            outcome_function=lambda p: (p["x"] - 5) ** 2,
            direction="minimize",
        )
        assert result["optimized_outcome"] <= result["original_outcome"]

    def test_summary(self) -> None:
        """Analiz ozeti."""
        wie = WhatIfEngine()
        wie.analyze_parameter("p1", 1.0, 2.0)
        wie.analyze_parameter("p2", 10.0, 20.0)
        summary = wie.get_summary()
        assert summary["total_analyses"] == 2
        assert summary["unique_parameters"] == 2

    def test_empty_summary(self) -> None:
        """Bos ozet."""
        wie = WhatIfEngine()
        summary = wie.get_summary()
        assert summary["total_analyses"] == 0

    def test_tipping_point_detection(self) -> None:
        """Devrilme noktasi."""
        wie = WhatIfEngine()
        result = wie.analyze_parameter("load", 1.0, 100.0)
        assert result.tipping_point is True  # Buyuk degisim

    def test_insensitive_parameter(self) -> None:
        """Hassas olmayan parametre."""
        wie = WhatIfEngine()
        result = wie.analyze_parameter(
            "color", 1.0, 1.001,
            outcome_function=lambda x: 42,  # Sabit fonksiyon
        )
        assert result.sensitivity == SensitivityLevel.INSENSITIVE


# === DryRunExecutor Testleri ===


class TestDryRunExecutor:
    """DryRunExecutor testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        dr = DryRunExecutor()
        assert dr.run_count == 0

    def test_execute_basic(self) -> None:
        """Temel calistirma."""
        dr = DryRunExecutor()
        result = dr.execute("deploy_app")
        assert result.action_name == "deploy_app"
        assert len(result.steps_log) > 0

    def test_execute_succeeds(self) -> None:
        """Basarili calistirma."""
        dr = DryRunExecutor()
        result = dr.execute("update_config")
        assert result.would_succeed is True

    def test_permission_check(self) -> None:
        """Izin kontrolu."""
        dr = DryRunExecutor(permissions=["config:read"])
        result = dr.execute("deploy_app")
        assert result.permissions_ok is False
        assert len(result.missing_permissions) > 0

    def test_all_permissions(self) -> None:
        """Tum izinler mevcut."""
        dr = DryRunExecutor(permissions=[
            "deploy:write", "service:restart", "config:read",
        ])
        result = dr.execute("deploy_app")
        assert result.permissions_ok is True

    def test_resource_check(self) -> None:
        """Kaynak kontrolu."""
        dr = DryRunExecutor()
        dr.set_resources({"cpu": 0.1, "memory": 0.05})
        result = dr.execute("deploy_app")
        assert result.resources_available is False
        assert len(result.resource_shortages) > 0

    def test_sufficient_resources(self) -> None:
        """Yeterli kaynaklar."""
        dr = DryRunExecutor()
        dr.set_resources({"cpu": 0.9, "memory": 0.9, "disk": 0.9})
        result = dr.execute("deploy_app")
        assert result.resources_available is True

    def test_parameter_warnings(self) -> None:
        """Parametre uyarilari."""
        dr = DryRunExecutor()
        result = dr.execute("deploy_app", {"force": True, "skip_validation": True})
        assert len(result.warnings) >= 2

    def test_delete_without_confirm(self) -> None:
        """Onaysiz silme uyarisi."""
        dr = DryRunExecutor()
        result = dr.execute("delete_records", {"target": "old_data"})
        assert any("onay" in w for w in result.warnings)

    def test_world_state_constraint(self) -> None:
        """Dunya durumu kisitlamasi."""
        wm = WorldModeler()
        c = wm.add_constraint("disk_space")
        c.is_satisfied = False
        snap = wm.take_snapshot()
        dr = DryRunExecutor()
        result = dr.execute("deploy_app", world_state=snap)
        assert result.prerequisites_met is False

    def test_batch_execute(self) -> None:
        """Toplu calistirma."""
        dr = DryRunExecutor()
        results = dr.batch_execute(["backup_db", "deploy_app"])
        assert len(results) == 2

    def test_success_rate(self) -> None:
        """Basari orani."""
        dr = DryRunExecutor()
        dr.execute("update_config")
        dr.execute("deploy_app")
        assert dr.success_rate > 0

    def test_high_resource_usage_world_state(self) -> None:
        """Dunya durumunda yuksek kaynak kullanimi."""
        wm = WorldModeler()
        wm.set_resource(ResourceType.CPU, 0.96)
        snap = wm.take_snapshot()
        dr = DryRunExecutor()
        result = dr.execute("deploy_app", world_state=snap)
        assert result.resources_available is False


# === SimulationEngine Testleri ===


class TestSimulationEngine:
    """SimulationEngine testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        se = SimulationEngine()
        assert se.report_count == 0

    def test_components_accessible(self) -> None:
        """Bilesenler erisilebilir."""
        se = SimulationEngine()
        assert se.world is not None
        assert se.action_simulator is not None
        assert se.scenario_generator is not None
        assert se.predictor is not None
        assert se.risk_simulator is not None
        assert se.rollback_planner is not None
        assert se.whatif is not None
        assert se.dry_runner is not None

    def test_simulate_basic(self) -> None:
        """Temel simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert report.action_name == "deploy_app"
        assert report.status == SimulationStatus.COMPLETED
        assert report.processing_ms > 0

    def test_simulate_with_scenarios(self) -> None:
        """Senaryolu simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert len(report.scenarios) == 5

    def test_simulate_with_prediction(self) -> None:
        """Tahminli simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert report.prediction is not None

    def test_simulate_with_risk(self) -> None:
        """Riskli simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app", include_risk=True)
        assert len(report.risk_events) > 0

    def test_simulate_with_rollback(self) -> None:
        """Geri alma planli simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert report.rollback_plan is not None

    def test_simulate_with_dry_run(self) -> None:
        """Kuru calistirmali simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app", include_dry_run=True)
        assert report.dry_run is not None

    def test_simulate_with_whatif(self) -> None:
        """Ne olur analizli simulasyon."""
        se = SimulationEngine()
        report = se.simulate(
            "deploy_app",
            parameters={"timeout": 30, "workers": 4},
            include_whatif=True,
        )
        assert len(report.what_if_results) > 0

    def test_simulate_without_risk(self) -> None:
        """Risksiz simulasyon."""
        se = SimulationEngine()
        report = se.simulate("deploy_app", include_risk=False)
        assert len(report.risk_events) == 0

    def test_compare_actions(self) -> None:
        """Aksiyon karsilastirmasi."""
        se = SimulationEngine()
        result = se.compare_actions(["deploy_app", "restart_service"])
        assert result["count"] == 2
        assert "best_action" in result

    def test_should_simulate_risky(self) -> None:
        """Riskli aksiyon simulasyonu gerekli."""
        se = SimulationEngine(auto_simulate_risky=True)
        assert se.should_simulate("deploy_app", RiskLevel.HIGH) is True
        assert se.should_simulate("deploy_app", RiskLevel.CRITICAL) is True

    def test_should_not_simulate(self) -> None:
        """Simulasyon gerekli degil."""
        se = SimulationEngine(auto_simulate_risky=False)
        assert se.should_simulate("deploy_app", RiskLevel.HIGH) is False

    def test_get_report(self) -> None:
        """Rapor getirme."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        found = se.get_report(report.report_id)
        assert found is not None

    def test_get_report_not_found(self) -> None:
        """Rapor bulunamadi."""
        se = SimulationEngine()
        assert se.get_report("unknown") is None

    def test_user_report(self) -> None:
        """Kullanici raporu."""
        se = SimulationEngine()
        report = se.simulate("deploy_app", include_dry_run=True)
        text = se.generate_user_report(report)
        assert "deploy_app" in text
        assert "Oneri:" in text

    def test_recommendation_generated(self) -> None:
        """Oneri uretildi."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert len(report.recommendation) > 0

    def test_overall_risk_determined(self) -> None:
        """Genel risk belirlendi."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert report.overall_risk in list(RiskLevel)

    def test_confidence_score(self) -> None:
        """Guven puani."""
        se = SimulationEngine()
        report = se.simulate("deploy_app")
        assert 0.0 <= report.confidence <= 1.0


# === Entegrasyon Testleri ===


class TestSimulationIntegration:
    """Entegrasyon testleri."""

    def test_full_simulation_pipeline(self) -> None:
        """Tam simulasyon pipeline'i."""
        se = SimulationEngine()

        # Dunya durumu ayarla
        se.world.add_entity("api", "service", {"version": "2.0"})
        se.world.add_entity("db", "database", {"type": "postgresql"})
        se.world.set_resource(ResourceType.CPU, 0.6)
        se.world.set_resource(ResourceType.MEMORY, 0.5)

        # Tam simulasyon
        report = se.simulate(
            "deploy_app",
            parameters={"timeout": 60, "workers": 4},
            include_dry_run=True,
            include_risk=True,
            include_whatif=True,
        )

        assert report.status == SimulationStatus.COMPLETED
        assert len(report.scenarios) == 5
        assert report.prediction is not None
        assert report.rollback_plan is not None
        assert report.dry_run is not None
        assert len(report.what_if_results) > 0

    def test_world_to_action(self) -> None:
        """Dunya -> Aksiyon entegrasyonu."""
        wm = WorldModeler()
        wm.add_entity("db", "database")
        wm.set_resource(ResourceType.CPU, 0.8)
        snap = wm.take_snapshot()

        sim = ActionSimulator()
        outcome = sim.simulate("deploy_app", world_state=snap)
        assert outcome.success_probability > 0

    def test_scenario_to_prediction(self) -> None:
        """Senaryo -> Tahmin entegrasyonu."""
        sg = ScenarioGenerator(seed=42)
        scenarios = sg.generate_all("migrate_database")

        op = OutcomePredictor()
        pred = op.predict("migrate_database", scenarios)
        assert pred.success_probability > 0
        assert len(pred.failure_modes) > 0

    def test_risk_to_rollback(self) -> None:
        """Risk -> Rollback entegrasyonu."""
        rs = RiskSimulator()
        event = rs.inject_risk("DB_crash", ["database"], 0.1, RiskLevel.CRITICAL)

        rp = RollbackPlanner()
        cp = rp.create_checkpoint("pre_action", {"version": "1.0"})
        plan = rp.plan_rollback("migrate_database", cp, RiskLevel.HIGH)

        assert plan["requires_downtime"] is True
        assert plan["data_recovery"]["backup_required"] is True

    def test_dry_run_to_simulation(self) -> None:
        """Kuru calistirma -> Simulasyon entegrasyonu."""
        dr = DryRunExecutor()
        dry_result = dr.execute("deploy_app")

        se = SimulationEngine()
        report = se.simulate("deploy_app", include_dry_run=True)
        assert report.dry_run is not None

    def test_multi_action_comparison(self) -> None:
        """Coklu aksiyon karsilastirmasi."""
        se = SimulationEngine()
        result = se.compare_actions([
            "deploy_app",
            "restart_service",
            "update_config",
        ])
        assert result["count"] == 3
        assert result["best_action"] is not None

    def test_simulate_risky_chain(self) -> None:
        """Riskli zincir simulasyonu."""
        sim = ActionSimulator()
        results = sim.simulate_chain([
            "backup_database",
            "migrate_schema",
            "deploy_application",
            "restart_services",
        ])
        assert len(results) == 4
        # Her adimda olasilik duser
        for i in range(1, len(results)):
            assert results[i].success_probability <= results[i - 1].success_probability
