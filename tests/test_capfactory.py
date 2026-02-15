"""ATLAS Runtime Capability Factory testleri."""

import time

import pytest

from app.core.capfactory.auto_tester import (
    CapabilityAutoTester,
)
from app.core.capfactory.capfactory_orchestrator import (
    CapFactoryOrchestrator,
)
from app.core.capfactory.capability_registry import (
    RuntimeCapabilityRegistry,
)
from app.core.capfactory.need_analyzer import (
    NeedAnalyzer,
)
from app.core.capfactory.rapid_prototyper import (
    RapidPrototyper,
)
from app.core.capfactory.rollback_on_failure import (
    RollbackOnFailure,
)
from app.core.capfactory.safe_deployer import (
    SafeDeployer,
)
from app.core.capfactory.sandbox_environment import (
    SandboxEnvironment,
)
from app.core.capfactory.solution_architect import (
    SolutionArchitect,
)
from app.models.capfactory_models import (
    CapabilityRecord,
    CapabilityStatus,
    CapFactorySnapshot,
    ComplexityLevel,
    DeploymentRecord,
    DeploymentStage,
    RollbackReason,
    SandboxState,
    TestResult,
    TestType,
)


# ==================== Models ====================

class TestCapFactoryModels:
    """CapFactory model testleri."""

    def test_capability_status_enum(self):
        assert CapabilityStatus.DRAFT == "draft"
        assert CapabilityStatus.BUILDING == "building"
        assert CapabilityStatus.TESTING == "testing"
        assert CapabilityStatus.DEPLOYED == "deployed"
        assert CapabilityStatus.DEPRECATED == "deprecated"

    def test_complexity_level_enum(self):
        assert ComplexityLevel.TRIVIAL == "trivial"
        assert ComplexityLevel.SIMPLE == "simple"
        assert ComplexityLevel.MODERATE == "moderate"
        assert ComplexityLevel.COMPLEX == "complex"
        assert ComplexityLevel.EXTREME == "extreme"

    def test_deployment_stage_enum(self):
        assert DeploymentStage.CANARY == "canary"
        assert DeploymentStage.STAGING == "staging"
        assert DeploymentStage.PARTIAL == "partial"
        assert DeploymentStage.FULL == "full"
        assert DeploymentStage.ROLLED_BACK == "rolled_back"

    def test_test_type_enum(self):
        assert TestType.UNIT == "unit"
        assert TestType.INTEGRATION == "integration"
        assert TestType.PERFORMANCE == "performance"
        assert TestType.SECURITY == "security"
        assert TestType.EDGE_CASE == "edge_case"

    def test_rollback_reason_enum(self):
        assert RollbackReason.TEST_FAILURE == "test_failure"
        assert RollbackReason.HEALTH_CHECK == "health_check"
        assert RollbackReason.PERFORMANCE == "performance"
        assert RollbackReason.SECURITY == "security"
        assert RollbackReason.MANUAL == "manual"

    def test_sandbox_state_enum(self):
        assert SandboxState.IDLE == "idle"
        assert SandboxState.RUNNING == "running"
        assert SandboxState.COMPLETED == "completed"
        assert SandboxState.FAILED == "failed"
        assert SandboxState.CLEANED == "cleaned"

    def test_capability_record_model(self):
        cr = CapabilityRecord(name="test_cap")
        assert cr.capability_id
        assert cr.name == "test_cap"
        assert cr.status == CapabilityStatus.DRAFT
        assert cr.complexity == ComplexityLevel.MODERATE
        assert cr.version == "1.0.0"

    def test_deployment_record_model(self):
        dr = DeploymentRecord(capability_id="c1")
        assert dr.deployment_id
        assert dr.capability_id == "c1"
        assert dr.stage == DeploymentStage.CANARY
        assert dr.healthy is True

    def test_test_result_model(self):
        tr = TestResult(passed=True, coverage=95.0)
        assert tr.test_id
        assert tr.test_type == TestType.UNIT
        assert tr.passed is True
        assert tr.coverage == 95.0

    def test_capfactory_snapshot_model(self):
        snap = CapFactorySnapshot()
        assert snap.snapshot_id
        assert snap.total_capabilities == 0
        assert snap.total_deployments == 0
        assert snap.total_rollbacks == 0
        assert snap.active_sandboxes == 0


# ==================== NeedAnalyzer ====================

class TestNeedAnalyzer:
    """NeedAnalyzer testleri."""

    def test_init(self):
        na = NeedAnalyzer()
        assert na.analysis_count == 0
        assert na.gap_count == 0

    def test_analyze_request_basic(self):
        na = NeedAnalyzer()
        result = na.analyze_request(
            "parse JSON data from API",
        )
        assert result["analysis_id"] == "analysis_1"
        assert "keywords" in result
        assert "complexity" in result
        assert "feasible" in result
        assert na.analysis_count == 1

    def test_analyze_request_simple(self):
        na = NeedAnalyzer()
        result = na.analyze_request("sort items")
        assert result["complexity"] == "simple"

    def test_analyze_request_complex(self):
        na = NeedAnalyzer()
        result = na.analyze_request(
            "predict future sales using ml model",
        )
        assert result["complexity"] == "complex"

    def test_analyze_request_extreme(self):
        na = NeedAnalyzer()
        result = na.analyze_request(
            "build realtime distributed system",
        )
        assert result["complexity"] == "extreme"

    def test_analyze_request_with_context(self):
        na = NeedAnalyzer()
        result = na.analyze_request(
            "fetch data",
            context={"source": "api"},
        )
        assert result["context"]["source"] == "api"

    def test_register_capability(self):
        na = NeedAnalyzer()
        result = na.register_capability(
            "data_parser",
            ["parse", "json", "xml"],
        )
        assert result["registered"] is True

    def test_capability_mapping(self):
        na = NeedAnalyzer()
        na.register_capability(
            "data_parser",
            ["parse", "json"],
            available=True,
        )
        result = na.analyze_request("parse json")
        assert "data_parser" in result[
            "required_capabilities"
        ]

    def test_gap_identification(self):
        na = NeedAnalyzer()
        na.register_capability(
            "parser", ["parse"],
            available=False,
        )
        result = na.analyze_request("parse data")
        assert len(result["gaps"]) > 0

    def test_feasibility_many_gaps(self):
        na = NeedAnalyzer()
        for i in range(6):
            na.register_capability(
                f"cap_{i}", [f"kw{i}"],
                available=False,
            )
        request = " ".join(
            f"kw{i}" for i in range(6)
        )
        result = na.analyze_request(request)
        assert result["feasible"] is False

    def test_get_analysis(self):
        na = NeedAnalyzer()
        a = na.analyze_request("test request")
        got = na.get_analysis(a["analysis_id"])
        assert got["request"] == "test request"

    def test_get_analysis_not_found(self):
        na = NeedAnalyzer()
        result = na.get_analysis("nonexistent")
        assert result.get("error") == "analysis_not_found"

    def test_get_analyses(self):
        na = NeedAnalyzer()
        na.analyze_request("first")
        na.analyze_request("second")
        results = na.get_analyses()
        assert len(results) == 2


# ==================== SolutionArchitect ====================

class TestSolutionArchitect:
    """SolutionArchitect testleri."""

    def test_init(self):
        sa = SolutionArchitect()
        assert sa.design_count == 0
        assert sa.component_count == 6

    def test_design_architecture(self):
        sa = SolutionArchitect()
        analysis = {
            "analysis_id": "a1",
            "keywords": ["http", "parse"],
            "complexity": "moderate",
            "gaps": [],
        }
        result = sa.design_architecture(analysis)
        assert result["design_id"] == "design_1"
        assert len(result["components"]) > 0
        assert "integration_plan" in result
        assert "resource_estimate" in result
        assert sa.design_count == 1

    def test_design_with_api_keyword(self):
        sa = SolutionArchitect()
        analysis = {
            "keywords": ["api", "fetch"],
            "complexity": "simple",
            "gaps": [],
        }
        result = sa.design_architecture(analysis)
        comp_names = [
            c["name"] for c in result["components"]
        ]
        assert "http_client" in comp_names

    def test_design_with_ml_keyword(self):
        sa = SolutionArchitect()
        analysis = {
            "keywords": ["ml", "predict"],
            "complexity": "complex",
            "gaps": [],
        }
        result = sa.design_architecture(analysis)
        comp_names = [
            c["name"] for c in result["components"]
        ]
        assert "ml_pipeline" in comp_names

    def test_design_dependencies(self):
        sa = SolutionArchitect()
        analysis = {
            "keywords": ["ml"],
            "complexity": "complex",
            "gaps": [],
        }
        result = sa.design_architecture(analysis)
        assert len(result["dependencies"]) > 0

    def test_design_resource_estimate(self):
        sa = SolutionArchitect()
        analysis = {
            "keywords": ["cache", "auth"],
            "complexity": "moderate",
            "gaps": [],
        }
        result = sa.design_architecture(analysis)
        est = result["resource_estimate"]
        assert est["estimated_time_minutes"] > 0
        assert est["memory_mb"] > 0

    def test_design_no_matching_keywords(self):
        sa = SolutionArchitect()
        analysis = {
            "keywords": ["xyz_unknown"],
            "complexity": "trivial",
            "gaps": [],
        }
        result = sa.design_architecture(analysis)
        assert len(result["components"]) >= 1

    def test_add_component(self):
        sa = SolutionArchitect()
        result = sa.add_component(
            "custom_module", "processor", 3,
        )
        assert result["added"] is True
        assert sa.component_count == 7

    def test_get_design(self):
        sa = SolutionArchitect()
        d = sa.design_architecture({
            "keywords": [], "complexity": "simple",
            "gaps": [],
        })
        got = sa.get_design(d["design_id"])
        assert got["design_id"] == d["design_id"]

    def test_get_design_not_found(self):
        sa = SolutionArchitect()
        result = sa.get_design("nonexistent")
        assert result.get("error") == "design_not_found"

    def test_get_designs(self):
        sa = SolutionArchitect()
        sa.design_architecture({
            "keywords": [], "complexity": "simple",
            "gaps": [],
        })
        sa.design_architecture({
            "keywords": [], "complexity": "moderate",
            "gaps": [],
        })
        results = sa.get_designs()
        assert len(results) == 2


# ==================== RapidPrototyper ====================

class TestRapidPrototyper:
    """RapidPrototyper testleri."""

    def test_init(self):
        rp = RapidPrototyper()
        assert rp.prototype_count == 0
        assert rp.template_count == 4
        assert rp.iteration_count == 0

    def test_create_prototype(self):
        rp = RapidPrototyper()
        design = {
            "design_id": "d1",
            "components": [
                {"name": "parser", "type": "transformer"},
            ],
        }
        result = rp.create_prototype(design, "MyProto")
        assert result["prototype_id"] == "proto_1"
        assert result["name"] == "MyProto"
        assert result["component_count"] == 1
        assert len(result["code_parts"]) == 1
        assert rp.prototype_count == 1

    def test_create_prototype_multiple_components(self):
        rp = RapidPrototyper()
        design = {
            "design_id": "d1",
            "components": [
                {"name": "api", "type": "connector"},
                {"name": "cache", "type": "handler"},
            ],
        }
        result = rp.create_prototype(design)
        assert result["component_count"] == 2
        assert len(result["api_stubs"]) == 2

    def test_create_prototype_with_template(self):
        rp = RapidPrototyper()
        design = {
            "design_id": "d1",
            "components": [
                {"name": "svc", "type": "service"},
            ],
        }
        result = rp.create_prototype(design)
        code = result["code_parts"][0]["code"]
        assert "Service" in code

    def test_iterate(self):
        rp = RapidPrototyper()
        design = {
            "design_id": "d1",
            "components": [
                {"name": "x", "type": "handler"},
            ],
        }
        proto = rp.create_prototype(design)
        result = rp.iterate(
            proto["prototype_id"],
            {"add_logging": True},
        )
        assert result["iteration"] == 2
        assert rp.iteration_count == 1

    def test_iterate_not_found(self):
        rp = RapidPrototyper()
        result = rp.iterate(
            "nonexistent", {"x": 1},
        )
        assert result.get("error") == "prototype_not_found"

    def test_add_template(self):
        rp = RapidPrototyper()
        result = rp.add_template(
            "worker",
            "class {name}Worker: ...",
            "worker",
        )
        assert result["added"] is True
        assert rp.template_count == 5

    def test_get_prototype(self):
        rp = RapidPrototyper()
        design = {"design_id": "d1", "components": []}
        proto = rp.create_prototype(design)
        got = rp.get_prototype(
            proto["prototype_id"],
        )
        assert got["prototype_id"] == proto[
            "prototype_id"
        ]

    def test_get_prototype_not_found(self):
        rp = RapidPrototyper()
        result = rp.get_prototype("nonexistent")
        assert result.get("error") == "prototype_not_found"


# ==================== SandboxEnvironment ====================

class TestSandboxEnvironment:
    """SandboxEnvironment testleri."""

    def test_init(self):
        sb = SandboxEnvironment()
        assert sb.sandbox_count == 0
        assert sb.active_count == 0
        assert sb.execution_count == 0

    def test_create_sandbox(self):
        sb = SandboxEnvironment()
        result = sb.create_sandbox("test_sb")
        assert result["sandbox_id"] == "sandbox_1"
        assert result["state"] == "idle"
        assert sb.sandbox_count == 1
        assert sb.active_count == 1

    def test_execute(self):
        sb = SandboxEnvironment()
        s = sb.create_sandbox()
        result = sb.execute(
            s["sandbox_id"], "print('hello')",
        )
        assert result["success"] is True
        assert result["output"]["result"] == (
            "executed_successfully"
        )
        assert sb.execution_count == 1

    def test_execute_with_inputs(self):
        sb = SandboxEnvironment()
        s = sb.create_sandbox()
        result = sb.execute(
            s["sandbox_id"], "code",
            {"key": "value"},
        )
        assert result["success"] is True

    def test_execute_not_found(self):
        sb = SandboxEnvironment()
        result = sb.execute("nonexistent", "code")
        assert result.get("error") == "sandbox_not_found"

    def test_execute_resource_limit(self):
        sb = SandboxEnvironment(max_memory_mb=10)
        s = sb.create_sandbox()
        # Use up memory
        sandbox = sb._sandboxes[s["sandbox_id"]]
        sandbox["resource_usage"]["memory_mb"] = 10
        result = sb.execute(s["sandbox_id"], "code")
        assert result["success"] is False
        assert "resource_limit" in result["error"]

    def test_get_state(self):
        sb = SandboxEnvironment()
        s = sb.create_sandbox()
        state = sb.get_state(s["sandbox_id"])
        assert state["state"] == "idle"
        assert state["executions"] == 0

    def test_get_state_not_found(self):
        sb = SandboxEnvironment()
        result = sb.get_state("nonexistent")
        assert result.get("error") == "sandbox_not_found"

    def test_set_resource_limit(self):
        sb = SandboxEnvironment()
        result = sb.set_resource_limit(
            "memory_mb", 1024,
        )
        assert result["limit"] == 1024

    def test_cleanup(self):
        sb = SandboxEnvironment()
        s = sb.create_sandbox()
        sb.execute(s["sandbox_id"], "code")
        result = sb.cleanup(s["sandbox_id"])
        assert result["cleaned"] is True
        state = sb.get_state(s["sandbox_id"])
        assert state["state"] == "cleaned"

    def test_cleanup_not_found(self):
        sb = SandboxEnvironment()
        result = sb.cleanup("nonexistent")
        assert result.get("error") == "sandbox_not_found"

    def test_cleanup_all(self):
        sb = SandboxEnvironment()
        sb.create_sandbox("s1")
        sb.create_sandbox("s2")
        result = sb.cleanup_all()
        assert result["cleaned_count"] == 2

    def test_destroy(self):
        sb = SandboxEnvironment()
        s = sb.create_sandbox()
        result = sb.destroy(s["sandbox_id"])
        assert result["destroyed"] is True
        assert sb.active_count == 0

    def test_destroy_not_found(self):
        sb = SandboxEnvironment()
        result = sb.destroy("nonexistent")
        assert result.get("error") == "sandbox_not_found"


# ==================== CapabilityAutoTester ====================

class TestCapabilityAutoTester:
    """CapabilityAutoTester testleri."""

    def test_init(self):
        t = CapabilityAutoTester()
        assert t.suite_count == 0
        assert t.total_tests_run == 0
        assert t.pass_rate == 0.0

    def test_generate_tests(self):
        t = CapabilityAutoTester()
        proto = {
            "prototype_id": "p1",
            "code_parts": [
                {"component": "parser"},
                {"component": "handler"},
            ],
        }
        result = t.generate_tests(proto)
        assert result["suite_id"] == "suite_1"
        assert result["test_count"] > 0
        assert result["status"] == "generated"
        assert t.suite_count == 1

    def test_generate_tests_specific_types(self):
        t = CapabilityAutoTester()
        proto = {
            "prototype_id": "p1",
            "code_parts": [{"component": "x"}],
        }
        result = t.generate_tests(
            proto, ["performance", "security"],
        )
        types = {
            test["type"] for test in result["tests"]
        }
        assert "performance" in types
        assert "security" in types

    def test_run_tests(self):
        t = CapabilityAutoTester()
        proto = {
            "prototype_id": "p1",
            "code_parts": [{"component": "x"}],
        }
        suite = t.generate_tests(proto)
        result = t.run_tests(suite["suite_id"])
        assert result["total"] > 0
        assert result["passed"] >= 0
        assert "coverage" in result
        assert t.total_tests_run > 0

    def test_run_tests_not_found(self):
        t = CapabilityAutoTester()
        result = t.run_tests("nonexistent")
        assert result.get("error") == "suite_not_found"

    def test_run_specific_type(self):
        t = CapabilityAutoTester()
        proto = {
            "prototype_id": "p1",
            "code_parts": [
                {"component": "a"},
                {"component": "b"},
            ],
        }
        suite = t.generate_tests(proto)
        result = t.run_specific_type(
            suite["suite_id"], "unit",
        )
        assert result["total"] > 0

    def test_run_specific_type_not_found(self):
        t = CapabilityAutoTester()
        result = t.run_specific_type(
            "nonexistent", "unit",
        )
        assert result.get("error") == "suite_not_found"

    def test_get_coverage(self):
        t = CapabilityAutoTester()
        proto = {
            "prototype_id": "p1",
            "code_parts": [{"component": "x"}],
        }
        suite = t.generate_tests(proto)
        t.run_tests(suite["suite_id"])
        result = t.get_coverage(suite["suite_id"])
        assert result["coverage"] > 0
        assert "meets_minimum" in result

    def test_get_coverage_no_results(self):
        t = CapabilityAutoTester()
        result = t.get_coverage("unknown")
        assert result["coverage"] == 0.0
        assert result["meets_minimum"] is False

    def test_pass_rate(self):
        t = CapabilityAutoTester()
        proto = {
            "prototype_id": "p1",
            "code_parts": [{"component": "x"}],
        }
        suite = t.generate_tests(proto)
        t.run_tests(suite["suite_id"])
        assert t.pass_rate > 0

    def test_min_coverage_setting(self):
        t = CapabilityAutoTester(min_coverage=90.0)
        proto = {
            "prototype_id": "p1",
            "code_parts": [{"component": "x"}],
        }
        suite = t.generate_tests(proto)
        t.run_tests(suite["suite_id"])
        cov = t.get_coverage(suite["suite_id"])
        assert cov["min_required"] == 90.0


# ==================== SafeDeployer ====================

class TestSafeDeployer:
    """SafeDeployer testleri."""

    def test_init(self):
        sd = SafeDeployer()
        assert sd.deployment_count == 0
        assert sd.rollback_count == 0
        assert sd.active_deployment_count == 0

    def test_deploy(self):
        sd = SafeDeployer()
        result = sd.deploy("cap_1")
        assert result["deployment_id"] == "deploy_1"
        assert result["stage"] == "canary"
        assert result["status"] == "active"
        assert sd.deployment_count == 1
        assert sd.active_deployment_count == 1

    def test_deploy_staging(self):
        sd = SafeDeployer()
        result = sd.deploy("cap_1", stage="staging")
        assert result["stage"] == "staging"

    def test_deploy_auto_promote(self):
        sd = SafeDeployer()
        result = sd.deploy(
            "cap_1", auto_promote=True,
        )
        dep = sd.get_deployment(
            result["deployment_id"],
        )
        assert dep["stage"] == "staging"

    def test_check_health(self):
        sd = SafeDeployer()
        dep = sd.deploy("cap_1")
        result = sd.check_health(
            dep["deployment_id"],
        )
        assert result["healthy"] is True
        assert result["error_rate"] == 0.0

    def test_check_health_not_found(self):
        sd = SafeDeployer()
        result = sd.check_health("nonexistent")
        assert result.get("error") == "deployment_not_found"

    def test_promote(self):
        sd = SafeDeployer()
        dep = sd.deploy("cap_1")
        result = sd.promote(dep["deployment_id"])
        assert result["promoted"] is True
        assert result["from_stage"] == "canary"
        assert result["to_stage"] == "staging"

    def test_promote_at_final_stage(self):
        sd = SafeDeployer()
        dep = sd.deploy("cap_1", stage="full")
        result = sd.promote(dep["deployment_id"])
        assert result["promoted"] is False

    def test_promote_not_found(self):
        sd = SafeDeployer()
        result = sd.promote("nonexistent")
        assert result.get("error") == "deployment_not_found"

    def test_rollback(self):
        sd = SafeDeployer()
        dep = sd.deploy("cap_1")
        result = sd.rollback(
            dep["deployment_id"], "test_failure",
        )
        assert result["rolled_back"] is True
        assert result["reason"] == "test_failure"
        assert sd.rollback_count == 1

    def test_rollback_not_found(self):
        sd = SafeDeployer()
        result = sd.rollback("nonexistent")
        assert result.get("error") == "deployment_not_found"

    def test_monitor(self):
        sd = SafeDeployer()
        dep = sd.deploy("cap_1")
        sd.check_health(dep["deployment_id"])
        sd.check_health(dep["deployment_id"])
        result = sd.monitor(dep["deployment_id"])
        assert result["total_checks"] == 2
        assert result["uptime_percent"] == 100.0

    def test_monitor_not_found(self):
        sd = SafeDeployer()
        result = sd.monitor("nonexistent")
        assert result.get("error") == "deployment_not_found"

    def test_get_deployments(self):
        sd = SafeDeployer()
        sd.deploy("cap_1")
        sd.deploy("cap_2", stage="staging")
        results = sd.get_deployments()
        assert len(results) == 2

    def test_get_deployments_by_stage(self):
        sd = SafeDeployer()
        sd.deploy("cap_1", stage="canary")
        sd.deploy("cap_2", stage="staging")
        results = sd.get_deployments(stage="canary")
        assert len(results) == 1


# ==================== RuntimeCapabilityRegistry ====================

class TestRuntimeCapabilityRegistry:
    """RuntimeCapabilityRegistry testleri."""

    def test_init(self):
        reg = RuntimeCapabilityRegistry()
        assert reg.registered_count == 0
        assert reg.active_count == 0
        assert reg.deprecated_count == 0

    def test_register(self):
        reg = RuntimeCapabilityRegistry()
        result = reg.register(
            "json_parser", version="1.0.0",
            description="Parse JSON data",
            tags=["parser", "json"],
        )
        assert result["capability_id"] == "cap_1"
        assert result["registered"] is True
        assert reg.registered_count == 1
        assert reg.active_count == 1

    def test_update_version(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("parser")
        result = reg.update_version(
            cap["capability_id"], "2.0.0",
        )
        assert result["updated"] is True
        assert result["new_version"] == "2.0.0"
        assert result["old_version"] == "1.0.0"

    def test_update_version_not_found(self):
        reg = RuntimeCapabilityRegistry()
        result = reg.update_version(
            "nonexistent", "2.0.0",
        )
        assert result.get("error") == "capability_not_found"

    def test_record_usage(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("parser")
        result = reg.record_usage(
            cap["capability_id"],
        )
        assert result["invocations"] == 1
        assert result["success"] is True

    def test_record_usage_failure(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("parser")
        reg.record_usage(
            cap["capability_id"], success=False,
        )
        stats = reg.get_usage_stats(
            cap["capability_id"],
        )
        assert stats["failures"] == 1

    def test_record_usage_not_found(self):
        reg = RuntimeCapabilityRegistry()
        result = reg.record_usage("nonexistent")
        assert result.get("error") == "capability_not_found"

    def test_get_usage_stats(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("parser")
        reg.record_usage(cap["capability_id"])
        reg.record_usage(cap["capability_id"])
        reg.record_usage(
            cap["capability_id"], success=False,
        )
        stats = reg.get_usage_stats(
            cap["capability_id"],
        )
        assert stats["invocations"] == 3
        assert stats["successes"] == 2
        assert stats["failures"] == 1
        assert stats["success_rate"] == 66.7

    def test_deprecate(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("old_parser")
        result = reg.deprecate(
            cap["capability_id"],
            "replaced by new version",
        )
        assert result["deprecated"] is True
        assert reg.deprecated_count == 1
        assert reg.active_count == 0

    def test_deprecate_not_found(self):
        reg = RuntimeCapabilityRegistry()
        result = reg.deprecate("nonexistent")
        assert result.get("error") == "capability_not_found"

    def test_discover_by_query(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(
            "json_parser",
            description="Parse JSON data",
        )
        reg.register(
            "xml_parser",
            description="Parse XML data",
        )
        reg.register(
            "email_sender",
            description="Send emails",
        )
        results = reg.discover(query="parser")
        assert len(results) == 2

    def test_discover_by_tags(self):
        reg = RuntimeCapabilityRegistry()
        reg.register(
            "parser", tags=["data", "text"],
        )
        reg.register(
            "sender", tags=["comm", "email"],
        )
        results = reg.discover(tags=["data"])
        assert len(results) == 1

    def test_discover_active_only(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("old")
        reg.register("new")
        reg.deprecate(cap["capability_id"])
        results = reg.discover(active_only=True)
        assert len(results) == 1

    def test_get_capability(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("test")
        got = reg.get_capability(
            cap["capability_id"],
        )
        assert got["name"] == "test"

    def test_get_capability_not_found(self):
        reg = RuntimeCapabilityRegistry()
        result = reg.get_capability("nonexistent")
        assert result.get("error") == "capability_not_found"

    def test_list_capabilities(self):
        reg = RuntimeCapabilityRegistry()
        reg.register("a")
        reg.register("b")
        results = reg.list_capabilities()
        assert len(results) == 2

    def test_list_capabilities_by_status(self):
        reg = RuntimeCapabilityRegistry()
        cap = reg.register("a")
        reg.register("b")
        reg.deprecate(cap["capability_id"])
        active = reg.list_capabilities(
            status="active",
        )
        assert len(active) == 1


# ==================== RollbackOnFailure ====================

class TestRollbackOnFailure:
    """RollbackOnFailure testleri."""

    def test_init(self):
        rb = RollbackOnFailure()
        assert rb.rollback_count == 0
        assert rb.failure_count == 0
        assert rb.rule_count == 0

    def test_create_checkpoint(self):
        rb = RollbackOnFailure()
        result = rb.create_checkpoint(
            "cap_1", {"version": "1.0"},
        )
        assert result["checkpoint_created"] is True

    def test_detect_failure_auto_rollback(self):
        rb = RollbackOnFailure(auto_rollback=True)
        rb.create_checkpoint(
            "cap_1", {"version": "1.0"},
        )
        result = rb.detect_failure(
            "cap_1", "connection error", "high",
        )
        assert result["failure_detected"] is True
        assert result["rollback_performed"] is True
        assert rb.failure_count == 1
        assert rb.rollback_count == 1

    def test_detect_failure_no_auto_rollback(self):
        rb = RollbackOnFailure(auto_rollback=False)
        result = rb.detect_failure(
            "cap_1", "error", "low",
        )
        assert result["failure_detected"] is True
        assert result["auto_rollback"] is False

    def test_manual_rollback(self):
        rb = RollbackOnFailure()
        rb.create_checkpoint(
            "cap_1", {"v": "1.0"},
        )
        result = rb.rollback("cap_1", "manual fix")
        assert result["rolled_back"] is True
        assert result["state_restored"] is True
        assert result["reason"] == "manual fix"

    def test_rollback_without_checkpoint(self):
        rb = RollbackOnFailure()
        result = rb.rollback("cap_1")
        assert result["rolled_back"] is True
        assert result["state_restored"] is False

    def test_add_failure_rule(self):
        rb = RollbackOnFailure()
        result = rb.add_failure_rule(
            "timeout_rule",
            "timeout > 30",
            "rollback",
        )
        assert result["added"] is True
        assert rb.rule_count == 1

    def test_post_mortem(self):
        rb = RollbackOnFailure()
        rb.create_checkpoint("cap_1", {})
        rollback = rb.rollback("cap_1", "test")
        result = rb.post_mortem(
            rollback["rollback_id"],
        )
        assert result["capability_id"] == "cap_1"
        assert result["reason"] == "test"
        assert "recommendation" in result

    def test_post_mortem_not_found(self):
        rb = RollbackOnFailure()
        result = rb.post_mortem("nonexistent")
        assert result.get("error") == "rollback_not_found"

    def test_get_rollbacks(self):
        rb = RollbackOnFailure()
        rb.rollback("cap_1", "reason1")
        rb.rollback("cap_2", "reason2")
        results = rb.get_rollbacks()
        assert len(results) == 2

    def test_get_rollbacks_by_capability(self):
        rb = RollbackOnFailure()
        rb.rollback("cap_1", "r1")
        rb.rollback("cap_2", "r2")
        rb.rollback("cap_1", "r3")
        results = rb.get_rollbacks(
            capability_id="cap_1",
        )
        assert len(results) == 2


# ==================== CapFactoryOrchestrator ====================

class TestCapFactoryOrchestrator:
    """CapFactoryOrchestrator testleri."""

    def test_init(self):
        o = CapFactoryOrchestrator()
        assert o.capabilities_created == 0

    def test_create_capability(self):
        o = CapFactoryOrchestrator()
        result = o.create_capability(
            "parse JSON data from API",
            name="json_parser",
        )
        assert result["success"] is True
        assert result["capability_id"] is not None
        assert result["analysis"] is not None
        assert result["design"] is not None
        assert result["prototype"] is not None
        assert result["test_result"] is not None
        assert result["registration"] is not None
        assert o.capabilities_created == 1

    def test_create_capability_with_auto_deploy(self):
        o = CapFactoryOrchestrator(auto_deploy=True)
        result = o.create_capability(
            "transform data format",
        )
        assert result["success"] is True
        assert result["deployment"] is not None

    def test_create_capability_no_auto_deploy(self):
        o = CapFactoryOrchestrator(
            auto_deploy=False,
        )
        result = o.create_capability(
            "validate input",
        )
        assert result["success"] is True
        assert result["deployment"] is None

    def test_create_capability_with_context(self):
        o = CapFactoryOrchestrator()
        result = o.create_capability(
            "fetch api data",
            context={"source": "external"},
        )
        assert result["success"] is True
        assert result["analysis"]["context"][
            "source"
        ] == "external"

    def test_get_analytics(self):
        o = CapFactoryOrchestrator()
        o.create_capability("sort data items")
        analytics = o.get_analytics()
        assert analytics["capabilities_created"] == 1
        assert analytics["pipeline_runs"] == 1
        assert analytics["total_analyses"] == 1
        assert analytics["total_designs"] == 1
        assert analytics["total_prototypes"] == 1
        assert analytics["total_tests_run"] > 0

    def test_get_status(self):
        o = CapFactoryOrchestrator()
        status = o.get_status()
        assert "capabilities_created" in status
        assert "pipeline_runs" in status
        assert "active_deployments" in status
        assert "registered_capabilities" in status

    def test_full_pipeline(self):
        o = CapFactoryOrchestrator(
            auto_deploy=True,
        )
        # Create capability
        result = o.create_capability(
            "http api fetch data parser",
            name="api_fetcher",
        )
        assert result["success"] is True

        # Verify analytics
        analytics = o.get_analytics()
        assert analytics["capabilities_created"] == 1
        assert analytics["successful_deployments"] == 1
        assert analytics["registered_capabilities"] == 1

    def test_multiple_capabilities(self):
        o = CapFactoryOrchestrator()
        o.create_capability("sort items")
        o.create_capability("filter data")
        o.create_capability("validate input")
        assert o.capabilities_created == 3
        analytics = o.get_analytics()
        assert analytics["pipeline_runs"] == 3


# ==================== Config ====================

class TestCapFactoryConfig:
    """CapFactory config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.capfactory_enabled is True
        assert s.sandbox_timeout_seconds == 60
        assert s.capfactory_auto_deploy is False
        assert s.min_test_coverage == 80.0
        assert s.capfactory_rollback_on_failure is True


# ==================== Imports ====================

class TestCapFactoryImports:
    """CapFactory import testleri."""

    def test_import_all_from_init(self):
        from app.core.capfactory import (
            CapFactoryOrchestrator,
            CapabilityAutoTester,
            NeedAnalyzer,
            RapidPrototyper,
            RollbackOnFailure,
            RuntimeCapabilityRegistry,
            SafeDeployer,
            SandboxEnvironment,
            SolutionArchitect,
        )
        assert CapFactoryOrchestrator is not None
        assert CapabilityAutoTester is not None
        assert NeedAnalyzer is not None
        assert RapidPrototyper is not None
        assert RollbackOnFailure is not None
        assert RuntimeCapabilityRegistry is not None
        assert SafeDeployer is not None
        assert SandboxEnvironment is not None
        assert SolutionArchitect is not None

    def test_import_all_models(self):
        from app.models.capfactory_models import (
            CapabilityRecord,
            CapabilityStatus,
            CapFactorySnapshot,
            ComplexityLevel,
            DeploymentRecord,
            DeploymentStage,
            RollbackReason,
            SandboxState,
            TestResult,
            TestType,
        )
        assert CapabilityRecord is not None
        assert CapabilityStatus is not None
        assert CapFactorySnapshot is not None
        assert ComplexityLevel is not None
        assert DeploymentRecord is not None
        assert DeploymentStage is not None
        assert RollbackReason is not None
        assert SandboxState is not None
        assert TestResult is not None
        assert TestType is not None
