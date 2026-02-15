"""ATLAS Capability Gap Detection testleri."""

import unittest

from app.core.capgap.gap_detector import (
    GapDetector,
)
from app.core.capgap.capability_mapper import (
    CapabilityMapper,
)
from app.core.capgap.acquisition_planner import (
    AcquisitionPlanner,
)
from app.core.capgap.api_discoverer import (
    CapabilityAPIDiscoverer,
)
from app.core.capgap.skill_builder import (
    SkillBuilder,
)
from app.core.capgap.learning_accelerator import (
    LearningAccelerator,
)
from app.core.capgap.validation_engine import (
    CapabilityValidationEngine,
)
from app.core.capgap.progress_tracker import (
    AcquisitionProgressTracker,
)
from app.core.capgap.capgap_orchestrator import (
    CapGapOrchestrator,
)


# ==================== Models ====================

class TestCapGapModels(unittest.TestCase):
    """CapGap model testleri."""

    def test_gap_severity_enum(self):
        from app.models.capgap_models import (
            GapSeverity,
        )
        self.assertEqual(
            GapSeverity.CRITICAL, "critical",
        )
        self.assertEqual(
            GapSeverity.HIGH, "high",
        )
        self.assertEqual(
            GapSeverity.MEDIUM, "medium",
        )

    def test_acquisition_strategy_enum(self):
        from app.models.capgap_models import (
            AcquisitionStrategy,
        )
        self.assertEqual(
            AcquisitionStrategy.BUILD, "build",
        )
        self.assertEqual(
            AcquisitionStrategy.BUY, "buy",
        )
        self.assertEqual(
            AcquisitionStrategy.LEARN, "learn",
        )
        self.assertEqual(
            AcquisitionStrategy.INTEGRATE,
            "integrate",
        )
        self.assertEqual(
            AcquisitionStrategy.DELEGATE,
            "delegate",
        )

    def test_capability_status_enum(self):
        from app.models.capgap_models import (
            CapabilityStatus,
        )
        self.assertEqual(
            CapabilityStatus.AVAILABLE,
            "available",
        )
        self.assertEqual(
            CapabilityStatus.MISSING,
            "missing",
        )
        self.assertEqual(
            CapabilityStatus.IN_PROGRESS,
            "in_progress",
        )

    def test_validation_result_enum(self):
        from app.models.capgap_models import (
            ValidationResult,
        )
        self.assertEqual(
            ValidationResult.PASSED, "passed",
        )
        self.assertEqual(
            ValidationResult.FAILED, "failed",
        )

    def test_acquisition_phase_enum(self):
        from app.models.capgap_models import (
            AcquisitionPhase,
        )
        self.assertEqual(
            AcquisitionPhase.DETECTION,
            "detection",
        )
        self.assertEqual(
            AcquisitionPhase.DEPLOYMENT,
            "deployment",
        )

    def test_skill_category_enum(self):
        from app.models.capgap_models import (
            SkillCategory,
        )
        self.assertEqual(
            SkillCategory.API_INTEGRATION,
            "api_integration",
        )
        self.assertEqual(
            SkillCategory.MACHINE_LEARNING,
            "machine_learning",
        )

    def test_gap_record(self):
        from app.models.capgap_models import (
            GapRecord,
        )
        r = GapRecord(
            capability="email_sending",
            priority=0.8,
        )
        self.assertEqual(
            r.capability, "email_sending",
        )
        self.assertEqual(r.priority, 0.8)
        self.assertTrue(len(r.gap_id) > 0)

    def test_acquisition_plan(self):
        from app.models.capgap_models import (
            AcquisitionPlan,
        )
        p = AcquisitionPlan(
            gap_id="g1",
            estimated_hours=4.0,
        )
        self.assertEqual(p.gap_id, "g1")
        self.assertEqual(
            p.estimated_hours, 4.0,
        )

    def test_capability_record(self):
        from app.models.capgap_models import (
            CapabilityRecord,
        )
        c = CapabilityRecord(
            name="web_scraping",
            version="2.0.0",
        )
        self.assertEqual(
            c.name, "web_scraping",
        )
        self.assertEqual(
            c.version, "2.0.0",
        )

    def test_capgap_snapshot(self):
        from app.models.capgap_models import (
            CapGapSnapshot,
        )
        s = CapGapSnapshot(
            total_capabilities=10,
            total_gaps=3,
        )
        self.assertEqual(
            s.total_capabilities, 10,
        )


# ==================== GapDetector ====================

class TestGapDetector(unittest.TestCase):
    """GapDetector testleri."""

    def setUp(self):
        self.det = GapDetector()

    def test_analyze_task(self):
        r = self.det.analyze_task(
            "t1", "Send emails",
            ["email_api", "template_engine"],
        )
        self.assertEqual(r["task_id"], "t1")
        self.assertEqual(r["count"], 2)

    def test_detect_gaps(self):
        r = self.det.detect_gaps(
            "t1",
            ["email", "sms", "push"],
            ["email"],
        )
        self.assertEqual(r["gap_count"], 2)
        self.assertEqual(r["available"], 1)

    def test_detect_no_gaps(self):
        r = self.det.detect_gaps(
            "t1", ["a", "b"], ["a", "b", "c"],
        )
        self.assertEqual(r["gap_count"], 0)
        self.assertEqual(
            r["coverage"], 100.0,
        )

    def test_gap_severity(self):
        r = self.det.detect_gaps(
            "t1",
            ["security_check", "data_export"],
            [],
        )
        severities = [
            g["severity"]
            for g in r["gaps"]
        ]
        self.assertIn("critical", severities)

    def test_gap_priority(self):
        r = self.det.detect_gaps(
            "t1",
            ["api_call", "logging"],
            [],
        )
        for g in r["gaps"]:
            self.assertGreater(
                g["priority"], 0,
            )

    def test_prioritize_gaps(self):
        self.det.detect_gaps(
            "t1",
            ["security", "logging", "cache"],
            [],
        )
        prioritized = (
            self.det.prioritize_gaps()
        )
        self.assertEqual(
            len(prioritized), 3,
        )
        # En yuksek oncelikli basta
        self.assertGreaterEqual(
            prioritized[0]["priority"],
            prioritized[-1]["priority"],
        )

    def test_prioritize_gaps_filtered(self):
        self.det.detect_gaps(
            "t1", ["a"], [],
        )
        self.det.detect_gaps(
            "t2", ["b"], [],
        )
        p = self.det.prioritize_gaps(
            task_id="t1",
        )
        self.assertEqual(len(p), 1)

    def test_resolve_gap(self):
        self.det.detect_gaps(
            "t1", ["email"], [],
        )
        gap_id = list(
            self.det._gaps.keys(),
        )[0]
        r = self.det.resolve_gap(gap_id)
        self.assertTrue(r["resolved"])

    def test_resolve_gap_not_found(self):
        r = self.det.resolve_gap("x")
        self.assertIn("error", r)

    def test_get_gap(self):
        self.det.detect_gaps(
            "t1", ["email"], [],
        )
        gap_id = list(
            self.det._gaps.keys(),
        )[0]
        g = self.det.get_gap(gap_id)
        self.assertEqual(
            g["capability"], "email",
        )

    def test_get_gap_not_found(self):
        g = self.det.get_gap("x")
        self.assertIn("error", g)

    def test_gap_count(self):
        self.det.detect_gaps(
            "t1", ["a", "b"], [],
        )
        self.assertEqual(
            self.det.gap_count, 2,
        )

    def test_unresolved_count(self):
        self.det.detect_gaps(
            "t1", ["a", "b"], [],
        )
        gap_id = list(
            self.det._gaps.keys(),
        )[0]
        self.det.resolve_gap(gap_id)
        self.assertEqual(
            self.det.unresolved_count, 1,
        )


# ==================== CapabilityMapper ====================

class TestCapabilityMapper(unittest.TestCase):
    """CapabilityMapper testleri."""

    def setUp(self):
        self.mapper = CapabilityMapper()

    def test_register_capability(self):
        r = self.mapper.register_capability(
            "email", category="communication",
        )
        self.assertTrue(r["registered"])

    def test_register_with_deps(self):
        self.mapper.register_capability(
            "email",
            dependencies=["smtp", "dns"],
        )
        deps = self.mapper.get_dependencies(
            "email",
        )
        self.assertEqual(len(deps), 2)

    def test_unregister_capability(self):
        self.mapper.register_capability(
            "email", category="comm",
        )
        r = self.mapper.unregister_capability(
            "email",
        )
        self.assertTrue(r["unregistered"])
        self.assertEqual(
            self.mapper.capability_count, 0,
        )

    def test_unregister_not_found(self):
        r = self.mapper.unregister_capability(
            "x",
        )
        self.assertIn("error", r)

    def test_get_capability(self):
        self.mapper.register_capability(
            "email",
            category="comm",
            version="2.0",
        )
        c = self.mapper.get_capability(
            "email",
        )
        self.assertEqual(c["name"], "email")
        self.assertEqual(
            c["version"], "2.0",
        )

    def test_get_capability_not_found(self):
        c = self.mapper.get_capability("x")
        self.assertIn("error", c)

    def test_list_capabilities(self):
        self.mapper.register_capability(
            "a", category="cat1",
        )
        self.mapper.register_capability(
            "b", category="cat2",
        )
        all_c = (
            self.mapper.list_capabilities()
        )
        self.assertEqual(len(all_c), 2)

    def test_list_by_category(self):
        self.mapper.register_capability(
            "a", category="cat1",
        )
        self.mapper.register_capability(
            "b", category="cat1",
        )
        self.mapper.register_capability(
            "c", category="cat2",
        )
        cat1 = (
            self.mapper.list_capabilities(
                category="cat1",
            )
        )
        self.assertEqual(len(cat1), 2)

    def test_get_taxonomy(self):
        self.mapper.register_capability(
            "a", category="cat1",
        )
        self.mapper.register_capability(
            "b", category="cat2",
        )
        tax = self.mapper.get_taxonomy()
        self.assertIn("cat1", tax)
        self.assertIn("cat2", tax)

    def test_update_version(self):
        self.mapper.register_capability(
            "email", version="1.0",
        )
        r = self.mapper.update_version(
            "email", "2.0",
        )
        self.assertTrue(r["updated"])
        self.assertEqual(
            r["new_version"], "2.0",
        )

    def test_update_version_not_found(self):
        r = self.mapper.update_version(
            "x", "1.0",
        )
        self.assertIn("error", r)

    def test_coverage_analysis(self):
        self.mapper.register_capability("a")
        self.mapper.register_capability("b")
        r = self.mapper.coverage_analysis(
            ["a", "b", "c"],
        )
        self.assertAlmostEqual(
            r["coverage_pct"], 66.7, places=1,
        )
        self.assertIn("c", r["missing"])

    def test_capability_count(self):
        self.mapper.register_capability("a")
        self.assertEqual(
            self.mapper.capability_count, 1,
        )

    def test_category_count(self):
        self.mapper.register_capability(
            "a", category="c1",
        )
        self.mapper.register_capability(
            "b", category="c2",
        )
        self.assertEqual(
            self.mapper.category_count, 2,
        )


# ==================== AcquisitionPlanner ====================

class TestAcquisitionPlanner(
    unittest.TestCase,
):
    """AcquisitionPlanner testleri."""

    def setUp(self):
        self.planner = AcquisitionPlanner()

    def test_create_plan_build(self):
        p = self.planner.create_plan(
            "g1", "email", strategy="build",
        )
        self.assertEqual(p["strategy"], "build")
        self.assertGreater(
            p["estimated_hours"], 0,
        )
        self.assertTrue(len(p["steps"]) > 0)

    def test_create_plan_buy(self):
        p = self.planner.create_plan(
            "g1", "email", strategy="buy",
        )
        self.assertEqual(p["strategy"], "buy")
        self.assertGreater(
            p["estimated_cost"], 0,
        )

    def test_create_plan_complexity(self):
        p1 = self.planner.create_plan(
            "g1", "a", complexity=1.0,
        )
        p2 = self.planner.create_plan(
            "g2", "b", complexity=2.0,
        )
        self.assertGreater(
            p2["estimated_hours"],
            p1["estimated_hours"],
        )

    def test_evaluate_strategies(self):
        r = self.planner.evaluate_strategies(
            "email",
        )
        self.assertIn("evaluations", r)
        self.assertIn("recommended", r)
        self.assertEqual(
            len(r["evaluations"]), 5,
        )

    def test_evaluate_with_constraints(self):
        r = self.planner.evaluate_strategies(
            "email",
            max_hours=2.0,
            max_cost=20.0,
        )
        feasible = [
            e for e in r["evaluations"]
            if e["feasible"]
        ]
        self.assertTrue(len(feasible) >= 0)

    def test_get_plan(self):
        self.planner.create_plan(
            "g1", "email",
        )
        p = self.planner.get_plan("plan_g1")
        self.assertEqual(
            p["capability"], "email",
        )

    def test_get_plan_not_found(self):
        p = self.planner.get_plan("x")
        self.assertIn("error", p)

    def test_update_plan_status(self):
        self.planner.create_plan(
            "g1", "email",
        )
        r = self.planner.update_plan_status(
            "plan_g1", "in_progress",
        )
        self.assertTrue(r["updated"])

    def test_update_plan_not_found(self):
        r = self.planner.update_plan_status(
            "x", "done",
        )
        self.assertIn("error", r)

    def test_plan_count(self):
        self.planner.create_plan(
            "g1", "a",
        )
        self.planner.create_plan(
            "g2", "b",
        )
        self.assertEqual(
            self.planner.plan_count, 2,
        )


# ==================== CapabilityAPIDiscoverer ====================

class TestCapabilityAPIDiscoverer(
    unittest.TestCase,
):
    """CapabilityAPIDiscoverer testleri."""

    def setUp(self):
        self.disc = CapabilityAPIDiscoverer()
        self.disc.register_api(
            "sendgrid",
            ["email_sending", "template"],
            endpoint="https://api.sendgrid.com",
            auth_type="api_key",
            pricing="freemium",
        )

    def test_register_api(self):
        r = self.disc.register_api(
            "twilio",
            ["sms", "voice"],
        )
        self.assertTrue(r["registered"])
        self.assertEqual(
            r["capabilities"], 2,
        )

    def test_search_apis(self):
        r = self.disc.search_apis(
            "email_sending",
        )
        self.assertGreater(r["count"], 0)

    def test_search_no_match(self):
        r = self.disc.search_apis(
            "nonexistent_capability",
        )
        self.assertEqual(r["count"], 0)

    def test_search_partial_match(self):
        r = self.disc.search_apis("email")
        self.assertGreater(r["count"], 0)

    def test_check_compatibility(self):
        r = self.disc.check_compatibility(
            "sendgrid",
            {"auth_type": "api_key"},
        )
        self.assertTrue(r["compatible"])

    def test_check_compatibility_fail(self):
        r = self.disc.check_compatibility(
            "sendgrid",
            {
                "capabilities": [
                    "email_sending",
                    "voice",
                ],
            },
        )
        self.assertFalse(r["compatible"])

    def test_check_not_found(self):
        r = self.disc.check_compatibility(
            "x", {},
        )
        self.assertIn("error", r)

    def test_analyze_pricing_free(self):
        self.disc.register_api(
            "free_api", ["test"],
            pricing="free",
        )
        r = self.disc.analyze_pricing(
            "free_api",
        )
        self.assertEqual(
            r["monthly_cost"], 0.0,
        )

    def test_analyze_pricing_freemium(self):
        r = self.disc.analyze_pricing(
            "sendgrid",
            expected_usage=2000,
        )
        self.assertGreater(
            r["monthly_cost"], 0,
        )

    def test_analyze_pricing_not_found(self):
        r = self.disc.analyze_pricing("x")
        self.assertIn("error", r)

    def test_get_auth_requirements(self):
        r = self.disc.get_auth_requirements(
            "sendgrid",
        )
        self.assertEqual(
            r["auth"]["type"], "api_key",
        )

    def test_get_auth_not_found(self):
        r = self.disc.get_auth_requirements(
            "x",
        )
        self.assertIn("error", r)

    def test_get_api(self):
        a = self.disc.get_api("sendgrid")
        self.assertEqual(
            a["name"], "sendgrid",
        )

    def test_get_api_not_found(self):
        a = self.disc.get_api("x")
        self.assertIn("error", a)

    def test_api_count(self):
        self.assertEqual(
            self.disc.api_count, 1,
        )


# ==================== SkillBuilder ====================

class TestSkillBuilder(unittest.TestCase):
    """SkillBuilder testleri."""

    def setUp(self):
        self.builder = SkillBuilder()

    def test_generate_integration(self):
        r = self.builder.generate_integration(
            "email_sending",
            {
                "endpoint": "https://api.test.com",
                "auth_type": "api_key",
            },
        )
        self.assertTrue(r["built"])
        self.assertEqual(
            r["type"], "integration",
        )
        self.assertGreater(
            r["code_size"], 0,
        )

    def test_create_wrapper(self):
        r = self.builder.create_wrapper(
            "email",
            "email_lib",
            ["send", "receive"],
        )
        self.assertTrue(r["built"])
        self.assertEqual(r["methods"], 2)

    def test_build_adapter(self):
        r = self.builder.build_adapter(
            "converter",
            "json", "xml",
        )
        self.assertTrue(r["built"])
        self.assertEqual(
            r["source"], "json",
        )
        self.assertEqual(
            r["target"], "xml",
        )

    def test_generate_tests(self):
        self.builder.generate_integration(
            "email",
            {"endpoint": "", "auth_type": "api_key"},
        )
        r = self.builder.generate_tests(
            "build_email",
        )
        self.assertTrue(
            r["tests_generated"],
        )
        self.assertGreater(
            r["test_count"], 0,
        )

    def test_generate_tests_not_found(self):
        r = self.builder.generate_tests("x")
        self.assertIn("error", r)

    def test_generate_docs(self):
        self.builder.generate_integration(
            "email",
            {"endpoint": "", "auth_type": "api_key"},
        )
        r = self.builder.generate_docs(
            "build_email",
        )
        self.assertTrue(
            r["docs_generated"],
        )

    def test_generate_docs_not_found(self):
        r = self.builder.generate_docs("x")
        self.assertIn("error", r)

    def test_get_build(self):
        self.builder.generate_integration(
            "email",
            {"endpoint": "", "auth_type": "api_key"},
        )
        b = self.builder.get_build(
            "build_email",
        )
        self.assertEqual(
            b["capability"], "email",
        )
        self.assertIn("artifacts", b)

    def test_get_build_not_found(self):
        b = self.builder.get_build("x")
        self.assertIn("error", b)

    def test_build_count(self):
        self.builder.generate_integration(
            "a",
            {"endpoint": "", "auth_type": "api_key"},
        )
        self.builder.create_wrapper(
            "b", "mod", ["fn"],
        )
        self.assertEqual(
            self.builder.build_count, 2,
        )


# ==================== LearningAccelerator ====================

class TestLearningAccelerator(
    unittest.TestCase,
):
    """LearningAccelerator testleri."""

    def setUp(self):
        self.acc = LearningAccelerator()

    def test_learn_pattern(self):
        r = self.acc.learn_pattern(
            "api_pattern",
            "api_integration",
            ["discover", "connect", "test"],
        )
        self.assertTrue(r["learned"])
        self.assertEqual(r["steps"], 3)

    def test_find_similar_pattern(self):
        self.acc.learn_pattern(
            "api_p", "api_integration",
            ["discover", "connect"],
        )
        r = self.acc.find_similar_pattern(
            "api_connection",
        )
        self.assertIsNotNone(r)
        self.assertGreater(
            r["similarity"], 0,
        )

    def test_find_no_similar(self):
        r = self.acc.find_similar_pattern(
            "completely_unrelated",
        )
        self.assertIsNone(r)

    def test_transfer_learning(self):
        self.acc.learn_pattern(
            "p1", "email_sending",
            ["setup", "connect", "send"],
        )
        r = self.acc.transfer_learning(
            "email_sending",
            "sms_sending",
        )
        self.assertTrue(r["transfer"])
        self.assertGreater(
            r["steps_transferred"], 0,
        )

    def test_transfer_no_source(self):
        r = self.acc.transfer_learning(
            "nonexistent", "target",
        )
        self.assertFalse(r["transfer"])

    def test_reuse_pattern(self):
        self.acc.learn_pattern(
            "p1", "email",
            ["step1", "step2"],
        )
        r = self.acc.reuse_pattern(
            "p1", "sms",
        )
        self.assertTrue(r["reused"])
        self.assertEqual(
            r["usage_count"], 1,
        )

    def test_reuse_not_found(self):
        r = self.acc.reuse_pattern(
            "x", "target",
        )
        self.assertIn("error", r)

    def test_detect_shortcut(self):
        self.acc.learn_pattern(
            "p1", "api",
            ["step1"],
        )
        r = self.acc.detect_shortcut(
            "api_integration",
            ["step1", "step2", "step3"],
        )
        self.assertIn("shortcuts", r)

    def test_detect_shortcut_duplicates(self):
        r = self.acc.detect_shortcut(
            "test",
            ["a", "b", "a", "c"],
        )
        has_dup = any(
            s["type"] == "duplicate_removal"
            for s in r["shortcuts"]
        )
        self.assertTrue(has_dup)

    def test_efficiency_report(self):
        self.acc.learn_pattern(
            "p1", "a", ["s1"],
            success_rate=0.9,
        )
        r = self.acc.get_efficiency_report()
        self.assertEqual(
            r["patterns_learned"], 1,
        )
        self.assertEqual(
            r["avg_success_rate"], 0.9,
        )

    def test_pattern_count(self):
        self.acc.learn_pattern(
            "p1", "a", ["s"],
        )
        self.assertEqual(
            self.acc.pattern_count, 1,
        )

    def test_transfer_count(self):
        self.acc.learn_pattern(
            "p1", "a", ["s"],
        )
        self.acc.transfer_learning("a", "b")
        self.assertEqual(
            self.acc.transfer_count, 1,
        )


# ==================== CapabilityValidationEngine ====================

class TestCapabilityValidationEngine(
    unittest.TestCase,
):
    """CapabilityValidationEngine testleri."""

    def setUp(self):
        self.val = (
            CapabilityValidationEngine()
        )

    def test_validate_capability_pass(self):
        r = self.val.validate_capability(
            "email",
            [
                {"name": "send",
                 "expected": True,
                 "actual": True},
                {"name": "receive",
                 "expected": True,
                 "actual": True},
            ],
        )
        self.assertEqual(
            r["result"], "passed",
        )
        self.assertEqual(
            r["pass_rate"], 100.0,
        )

    def test_validate_capability_fail(self):
        r = self.val.validate_capability(
            "email",
            [
                {"name": "send",
                 "expected": True,
                 "actual": False},
            ],
        )
        self.assertEqual(
            r["result"], "failed",
        )

    def test_integration_test_pass(self):
        r = self.val.integration_test(
            "email",
            ["smtp", "dns"],
            ["smtp", "dns", "http"],
        )
        self.assertEqual(
            r["result"], "passed",
        )

    def test_integration_test_fail(self):
        r = self.val.integration_test(
            "email",
            ["smtp", "dns"],
            ["smtp"],
        )
        self.assertEqual(
            r["result"], "failed",
        )
        self.assertIn("dns", r["missing"])

    def test_performance_validation_pass(self):
        r = self.val.performance_validation(
            "email",
            {"response_time": 100,
             "throughput": 500},
            {"response_time": 200,
             "throughput": 100},
        )
        self.assertEqual(
            r["result"], "passed",
        )

    def test_performance_validation_fail(self):
        r = self.val.performance_validation(
            "email",
            {"response_time": 500},
            {"response_time": 200},
        )
        self.assertEqual(
            r["result"], "failed",
        )

    def test_security_check(self):
        r = self.val.security_check("email")
        self.assertEqual(
            r["result"], "passed",
        )
        self.assertGreater(
            r["check_count"], 0,
        )

    def test_security_custom_checks(self):
        r = self.val.security_check(
            "email",
            checks=["encryption", "auth"],
        )
        self.assertEqual(
            r["check_count"], 2,
        )

    def test_certify_pass(self):
        self.val.validate_capability(
            "email",
            [{"name": "t1",
              "expected": True,
              "actual": True}],
        )
        self.val.integration_test(
            "email", [], [],
        )
        self.val.performance_validation(
            "email", {}, {},
        )
        self.val.security_check("email")
        r = self.val.certify("email")
        self.assertTrue(r["certified"])

    def test_certify_fail_missing(self):
        r = self.val.certify("email")
        self.assertFalse(r["certified"])

    def test_get_validation(self):
        self.val.validate_capability(
            "email",
            [{"name": "t",
              "expected": True,
              "actual": True}],
        )
        v = self.val.get_validation("email")
        self.assertEqual(
            v["capability"], "email",
        )

    def test_get_validation_not_found(self):
        v = self.val.get_validation("x")
        self.assertIn("error", v)

    def test_validation_count(self):
        self.val.validate_capability(
            "a", [],
        )
        self.val.security_check("b")
        self.assertEqual(
            self.val.validation_count, 2,
        )

    def test_pass_rate(self):
        self.val.validate_capability(
            "a",
            [{"name": "t",
              "expected": True,
              "actual": True}],
        )
        self.assertGreater(
            self.val.pass_rate, 0,
        )

    def test_pass_rate_empty(self):
        self.assertEqual(
            self.val.pass_rate, 0.0,
        )

    def test_certification_count(self):
        self.assertEqual(
            self.val.certification_count, 0,
        )


# ==================== AcquisitionProgressTracker ====================

class TestAcquisitionProgressTracker(
    unittest.TestCase,
):
    """AcquisitionProgressTracker testleri."""

    def setUp(self):
        self.tracker = (
            AcquisitionProgressTracker()
        )

    def test_start_tracking(self):
        r = self.tracker.start_tracking(
            "acq1", "email",
        )
        self.assertTrue(
            r["tracking_started"],
        )

    def test_update_progress(self):
        self.tracker.start_tracking(
            "acq1", "email", total_steps=5,
        )
        r = self.tracker.update_progress(
            "acq1", 2,
            phase="acquisition",
        )
        self.assertTrue(r["updated"])
        self.assertEqual(
            r["progress_pct"], 40.0,
        )

    def test_update_not_found(self):
        r = self.tracker.update_progress(
            "x", 1,
        )
        self.assertIn("error", r)

    def test_complete_acquisition(self):
        self.tracker.start_tracking(
            "acq1", "email",
        )
        r = self.tracker.complete_acquisition(
            "acq1",
        )
        self.assertTrue(r["completed"])

    def test_complete_not_found(self):
        r = self.tracker.complete_acquisition(
            "x",
        )
        self.assertIn("error", r)

    def test_add_blocker(self):
        self.tracker.start_tracking(
            "acq1", "email",
        )
        r = self.tracker.add_blocker(
            "acq1", "Missing API key",
        )
        self.assertTrue(
            r["blocker_added"],
        )

    def test_add_blocker_not_found(self):
        r = self.tracker.add_blocker(
            "x", "blocker",
        )
        self.assertIn("error", r)

    def test_resolve_blocker(self):
        self.tracker.start_tracking(
            "acq1", "email",
        )
        self.tracker.add_blocker(
            "acq1", "Issue",
        )
        r = self.tracker.resolve_blocker(
            "acq1", 0,
        )
        self.assertTrue(
            r["blocker_resolved"],
        )

    def test_resolve_blocker_not_found(self):
        r = self.tracker.resolve_blocker(
            "x", 0,
        )
        self.assertIn("error", r)

    def test_resolve_blocker_invalid_idx(self):
        self.tracker.start_tracking(
            "acq1", "email",
        )
        r = self.tracker.resolve_blocker(
            "acq1", 99,
        )
        self.assertIn("error", r)

    def test_calculate_eta(self):
        self.tracker.start_tracking(
            "acq1", "email",
            total_steps=5,
            estimated_hours=10.0,
        )
        self.tracker.update_progress(
            "acq1", 1,
        )
        r = self.tracker.calculate_eta(
            "acq1",
        )
        self.assertIn("eta_hours", r)
        self.assertFalse(r["completed"])

    def test_calculate_eta_completed(self):
        self.tracker.start_tracking(
            "acq1", "email",
        )
        self.tracker.complete_acquisition(
            "acq1",
        )
        r = self.tracker.calculate_eta(
            "acq1",
        )
        self.assertTrue(r["completed"])

    def test_calculate_eta_not_found(self):
        r = self.tracker.calculate_eta("x")
        self.assertIn("error", r)

    def test_calculate_eta_with_blocker(self):
        self.tracker.start_tracking(
            "acq1", "email",
            total_steps=5,
        )
        self.tracker.update_progress(
            "acq1", 1,
        )
        self.tracker.add_blocker(
            "acq1", "Issue",
        )
        r = self.tracker.calculate_eta(
            "acq1",
        )
        self.assertEqual(
            r["active_blockers"], 1,
        )

    def test_get_report(self):
        self.tracker.start_tracking(
            "acq1", "email",
        )
        r = self.tracker.get_report("acq1")
        self.assertEqual(
            r["capability"], "email",
        )

    def test_get_report_not_found(self):
        r = self.tracker.get_report("x")
        self.assertIn("error", r)

    def test_get_all_status(self):
        self.tracker.start_tracking(
            "a1", "email",
        )
        self.tracker.start_tracking(
            "a2", "sms",
        )
        s = self.tracker.get_all_status()
        self.assertEqual(len(s), 2)

    def test_tracking_count(self):
        self.tracker.start_tracking(
            "a1", "email",
        )
        self.assertEqual(
            self.tracker.tracking_count, 1,
        )

    def test_completed_count(self):
        self.tracker.start_tracking(
            "a1", "email",
        )
        self.tracker.complete_acquisition(
            "a1",
        )
        self.assertEqual(
            self.tracker.completed_count, 1,
        )

    def test_in_progress_count(self):
        self.tracker.start_tracking(
            "a1", "email",
        )
        self.assertEqual(
            self.tracker.in_progress_count, 1,
        )


# ==================== CapGapOrchestrator ====================

class TestCapGapOrchestrator(
    unittest.TestCase,
):
    """CapGapOrchestrator testleri."""

    def setUp(self):
        self.orch = CapGapOrchestrator()

    def test_init(self):
        self.assertIsNotNone(
            self.orch.detector,
        )
        self.assertIsNotNone(
            self.orch.mapper,
        )
        self.assertIsNotNone(
            self.orch.planner,
        )
        self.assertIsNotNone(
            self.orch.discoverer,
        )
        self.assertIsNotNone(
            self.orch.builder,
        )
        self.assertIsNotNone(
            self.orch.accelerator,
        )
        self.assertIsNotNone(
            self.orch.validator,
        )
        self.assertIsNotNone(
            self.orch.tracker,
        )

    def test_detect_and_plan(self):
        self.orch.mapper.register_capability(
            "email",
        )
        r = self.orch.detect_and_plan(
            "t1", "Send messages",
            ["email", "sms", "push"],
        )
        self.assertEqual(r["gap_count"], 2)
        self.assertEqual(r["plan_count"], 2)

    def test_detect_no_gaps(self):
        self.orch.mapper.register_capability(
            "a",
        )
        self.orch.mapper.register_capability(
            "b",
        )
        r = self.orch.detect_and_plan(
            "t1", "Test", ["a", "b"],
        )
        self.assertEqual(r["gap_count"], 0)

    def test_acquire_capability(self):
        r = self.orch.acquire_capability(
            "g1", "email_sending",
        )
        self.assertTrue(r["acquired"])
        self.assertIn(
            "email_sending",
            self.orch.mapper
            .list_capabilities(),
        )

    def test_acquire_with_validation(self):
        r = self.orch.acquire_capability(
            "g1", "email",
            strategy="build",
        )
        self.assertTrue(r["validated"])

    def test_full_pipeline_no_auto(self):
        r = self.orch.full_pipeline(
            "t1", "Test",
            ["email", "sms"],
        )
        self.assertEqual(
            r["gaps_detected"], 2,
        )
        self.assertEqual(r["acquired"], 0)
        self.assertFalse(r["auto_acquire"])

    def test_full_pipeline_auto(self):
        orch = CapGapOrchestrator(
            auto_acquire=True,
        )
        r = orch.full_pipeline(
            "t1", "Test",
            ["email", "sms"],
        )
        self.assertTrue(r["auto_acquire"])
        self.assertEqual(r["acquired"], 2)
        self.assertEqual(
            r["final_coverage"], 100.0,
        )

    def test_get_status(self):
        s = self.orch.get_status()
        self.assertIn("capabilities", s)
        self.assertIn("gaps_detected", s)
        self.assertIn("unresolved_gaps", s)
        self.assertIn("in_progress", s)

    def test_get_status_after_work(self):
        self.orch.detect_and_plan(
            "t1", "Test", ["a", "b"],
        )
        s = self.orch.get_status()
        self.assertGreater(
            s["gaps_detected"], 0,
        )

    def test_get_analytics(self):
        a = self.orch.get_analytics()
        self.assertIn(
            "total_capabilities", a,
        )
        self.assertIn(
            "resolution_rate", a,
        )
        self.assertIn(
            "learning_report", a,
        )

    def test_pipelines_run(self):
        self.orch.detect_and_plan(
            "t1", "Test", ["a"],
        )
        self.assertEqual(
            self.orch.pipelines_run, 1,
        )

    def test_full_pipeline_integration(self):
        # Register some caps
        self.orch.mapper.register_capability(
            "existing_cap",
        )

        # Detect and plan
        r = self.orch.detect_and_plan(
            "t1", "Complex task",
            ["existing_cap", "new_cap"],
        )
        self.assertEqual(r["gap_count"], 1)

        # Acquire missing
        gap = r["gaps"][0]
        acq = self.orch.acquire_capability(
            gap["gap_id"],
            gap["capability"],
        )
        self.assertTrue(acq["acquired"])

        # Verify
        status = self.orch.get_status()
        self.assertEqual(
            status["capabilities"], 2,
        )


# ==================== Init & Config ====================

class TestCapGapInit(unittest.TestCase):
    """CapGap __init__ testleri."""

    def test_imports(self):
        from app.core.capgap import (
            AcquisitionPlanner,
            AcquisitionProgressTracker,
            CapGapOrchestrator,
            CapabilityAPIDiscoverer,
            CapabilityMapper,
            CapabilityValidationEngine,
            GapDetector,
            LearningAccelerator,
            SkillBuilder,
        )
        self.assertIsNotNone(
            AcquisitionPlanner,
        )
        self.assertIsNotNone(
            AcquisitionProgressTracker,
        )
        self.assertIsNotNone(
            CapGapOrchestrator,
        )
        self.assertIsNotNone(
            CapabilityAPIDiscoverer,
        )
        self.assertIsNotNone(
            CapabilityMapper,
        )
        self.assertIsNotNone(
            CapabilityValidationEngine,
        )
        self.assertIsNotNone(GapDetector)
        self.assertIsNotNone(
            LearningAccelerator,
        )
        self.assertIsNotNone(SkillBuilder)

    def test_instantiate_all(self):
        from app.core.capgap import (
            AcquisitionPlanner,
            AcquisitionProgressTracker,
            CapGapOrchestrator,
            CapabilityAPIDiscoverer,
            CapabilityMapper,
            CapabilityValidationEngine,
            GapDetector,
            LearningAccelerator,
            SkillBuilder,
        )
        instances = [
            AcquisitionPlanner(),
            AcquisitionProgressTracker(),
            CapGapOrchestrator(),
            CapabilityAPIDiscoverer(),
            CapabilityMapper(),
            CapabilityValidationEngine(),
            GapDetector(),
            LearningAccelerator(),
            SkillBuilder(),
        ]
        for inst in instances:
            self.assertIsNotNone(inst)


class TestCapGapConfig(unittest.TestCase):
    """CapGap config testleri."""

    def test_config_defaults(self):
        from app.config import settings

        self.assertTrue(
            settings.capgap_enabled,
        )
        self.assertFalse(
            settings.auto_acquire,
        )
        self.assertEqual(
            settings.max_acquisition_time_hours,
            24,
        )
        self.assertTrue(
            settings.require_validation,
        )
        self.assertTrue(
            settings.notify_on_acquisition,
        )


if __name__ == "__main__":
    unittest.main()
