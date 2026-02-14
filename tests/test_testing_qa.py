"""ATLAS Testing & Quality Assurance testleri."""

import pytest

from app.models.testing import (
    TestType,
    TestStatus,
    CoverageLevel,
    MutationType,
    QualityGate,
    ReportFormat,
    TestRecord,
    CoverageRecord,
    MutationRecord,
    QASnapshot,
)
from app.core.testing import (
    TestGenerator,
    TestRunner,
    CoverageAnalyzer,
    MutationTester,
    RegressionDetector,
    LoadTester,
    QualityScorer,
    TestReportGenerator,
    QAOrchestrator,
)


# ==================== Model Testleri ====================


class TestModels:
    """Model testleri."""

    def test_test_type_enum(self):
        assert TestType.UNIT == "unit"
        assert TestType.INTEGRATION == "integration"
        assert TestType.LOAD == "load"

    def test_test_status_enum(self):
        assert TestStatus.PASSED == "passed"
        assert TestStatus.FAILED == "failed"
        assert TestStatus.RUNNING == "running"

    def test_coverage_level_enum(self):
        assert CoverageLevel.LINE == "line"
        assert CoverageLevel.BRANCH == "branch"
        assert CoverageLevel.FUNCTION == "function"

    def test_mutation_type_enum(self):
        assert MutationType.ARITHMETIC == "arithmetic"
        assert MutationType.RELATIONAL == "relational"
        assert MutationType.LOGICAL == "logical"

    def test_quality_gate_enum(self):
        assert QualityGate.PASSED == "passed"
        assert QualityGate.FAILED == "failed"
        assert QualityGate.WARNING == "warning"

    def test_report_format_enum(self):
        assert ReportFormat.HTML == "html"
        assert ReportFormat.JSON == "json"
        assert ReportFormat.XML == "xml"

    def test_test_record_defaults(self):
        r = TestRecord(name="test1")
        assert r.name == "test1"
        assert r.test_id
        assert r.status == TestStatus.PENDING

    def test_coverage_record_defaults(self):
        r = CoverageRecord(module="mod1")
        assert r.module == "mod1"
        assert r.coverage_id
        assert r.percentage == 0.0

    def test_mutation_record_defaults(self):
        r = MutationRecord(original="+", mutated="-")
        assert r.mutation_id
        assert r.killed is False

    def test_qa_snapshot_defaults(self):
        s = QASnapshot()
        assert s.snapshot_id
        assert s.total_tests == 0
        assert s.gate_status == QualityGate.PASSED


# ==================== TestGenerator Testleri ====================


class TestTestGen:
    """TestGenerator testleri."""

    def test_generate_unit_test(self):
        g = TestGenerator()
        t = g.generate_unit_test("calculate_total")
        assert t["name"] == "test_calculate_total"
        assert t["type"] == "unit"
        assert "def test_calculate_total" in t["code"]
        assert g.generated_count == 1

    def test_generate_unit_with_params(self):
        g = TestGenerator()
        t = g.generate_unit_test(
            "add",
            params=[{"name": "a"}, {"name": "b"}],
        )
        assert "a, b" in t["code"]

    def test_generate_integration_test(self):
        g = TestGenerator()
        t = g.generate_integration_test(
            ["ServiceA", "ServiceB"],
            interaction="A calls B",
        )
        assert t["type"] == "integration"
        assert "servicea" in t["code"].lower()
        assert g.generated_count == 1

    def test_detect_edge_cases_string(self):
        g = TestGenerator()
        cases = g.detect_edge_cases(
            "process",
            param_types={"name": "string"},
        )
        descs = [c["description"] for c in cases]
        assert "empty_string" in descs
        assert "none_value" in descs
        assert "very_long_string" in descs

    def test_detect_edge_cases_int(self):
        g = TestGenerator()
        cases = g.detect_edge_cases(
            "calc",
            param_types={"count": "int"},
        )
        descs = [c["description"] for c in cases]
        assert "zero" in descs
        assert "negative" in descs
        assert "max_int" in descs

    def test_detect_edge_cases_float(self):
        g = TestGenerator()
        cases = g.detect_edge_cases(
            "calc",
            param_types={"score": "float"},
        )
        descs = [c["description"] for c in cases]
        assert "zero_float" in descs
        assert "infinity" in descs
        assert "nan" in descs

    def test_detect_edge_cases_list(self):
        g = TestGenerator()
        cases = g.detect_edge_cases(
            "process",
            param_types={"items": "list"},
        )
        descs = [c["description"] for c in cases]
        assert "empty_list" in descs

    def test_detect_edge_cases_empty(self):
        g = TestGenerator()
        cases = g.detect_edge_cases("fn")
        assert cases == []

    def test_generate_mock(self):
        g = TestGenerator()
        m = g.generate_mock(
            "Database",
            methods=["connect", "query"],
            return_values={"connect": "True"},
        )
        assert m["name"] == "MockDatabase"
        assert len(m["methods"]) == 2
        assert g.mock_count == 1

    def test_create_assertion_equal(self):
        g = TestGenerator()
        a = g.create_assertion("result", 42, "equal")
        assert "== 42" in a["code"]

    def test_create_assertion_true(self):
        g = TestGenerator()
        a = g.create_assertion("flag", True, "true")
        assert "is True" in a["code"]

    def test_create_assertion_none(self):
        g = TestGenerator()
        a = g.create_assertion("val", None, "none")
        assert "is None" in a["code"]

    def test_create_assertion_raises(self):
        g = TestGenerator()
        a = g.create_assertion("fn()", "ValueError", "raises")
        assert "pytest.raises" in a["code"]

    def test_register_template(self):
        g = TestGenerator()
        g.register_template("crud", "def test_{name}(): pass")
        assert g.template_count == 1

    def test_generate_from_template(self):
        g = TestGenerator()
        g.register_template("crud", "def test_{name}(): pass")
        t = g.generate_from_template("crud", {"name": "user"})
        assert t is not None
        assert "test_user" in t["code"]

    def test_generate_from_template_not_found(self):
        g = TestGenerator()
        assert g.generate_from_template("nope") is None


# ==================== TestRunner Testleri ====================


class TestTestRun:
    """TestRunner testleri."""

    def test_run_passing_test(self):
        r = TestRunner()
        result = r.run_test("test_ok", lambda: None)
        assert result["status"] == "passed"
        assert r.result_count == 1

    def test_run_failing_test(self):
        r = TestRunner(max_retries=0)
        result = r.run_test(
            "test_fail",
            lambda: (_ for _ in ()).throw(ValueError("bad")),
        )
        assert result["status"] == "failed"
        assert "bad" in result["error"]

    def test_retry_logic(self):
        counter = {"n": 0}
        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise RuntimeError("flaky")
        r = TestRunner(max_retries=3)
        result = r.run_test("test_flaky", flaky)
        assert result["status"] == "passed"

    def test_run_suite(self):
        r = TestRunner()
        tests = [
            {"name": "t1", "fn": lambda: None},
            {"name": "t2", "fn": lambda: None},
        ]
        result = r.run_suite("suite1", tests)
        assert result["total"] == 2
        assert result["passed"] == 2
        assert r.suite_count == 1

    def test_run_suite_with_failure(self):
        r = TestRunner(max_retries=0)
        tests = [
            {"name": "t1", "fn": lambda: None},
            {"name": "t2", "fn": lambda: 1/0},
        ]
        result = r.run_suite("s", tests)
        assert result["failed"] == 1

    def test_run_filtered_by_tags(self):
        r = TestRunner()
        tests = [
            {"name": "t1", "fn": lambda: None, "tags": ["fast"]},
            {"name": "t2", "fn": lambda: None, "tags": ["slow"]},
        ]
        result = r.run_filtered(tests, tags=["fast"])
        assert result["total"] == 1

    def test_run_filtered_by_name(self):
        r = TestRunner()
        tests = [
            {"name": "test_user_create", "fn": lambda: None},
            {"name": "test_order_create", "fn": lambda: None},
        ]
        result = r.run_filtered(tests, name_pattern="user")
        assert result["total"] == 1

    def test_get_summary(self):
        r = TestRunner()
        r.run_test("t1", lambda: None)
        r.run_test("t2", lambda: None)
        s = r.get_summary()
        assert s["total"] == 2
        assert s["passed"] == 2
        assert s["pass_rate"] == 1.0

    def test_get_failures(self):
        r = TestRunner(max_retries=0)
        r.run_test("t1", lambda: None)
        r.run_test("t2", lambda: 1/0)
        failures = r.get_failures()
        assert len(failures) == 1

    def test_reset(self):
        r = TestRunner()
        r.run_test("t1", lambda: None)
        r.reset()
        assert r.result_count == 0

    def test_pass_rate(self):
        r = TestRunner(max_retries=0)
        r.run_test("t1", lambda: None)
        r.run_test("t2", lambda: 1/0)
        assert r.pass_rate == 0.5

    def test_pass_rate_empty(self):
        r = TestRunner()
        assert r.pass_rate == 0.0

    def test_set_filter(self):
        r = TestRunner()
        r.set_filter("tag", "fast")
        assert r._filters["tag"] == "fast"


# ==================== CoverageAnalyzer Testleri ====================


class TestCoverageAnalyzer:
    """CoverageAnalyzer testleri."""

    def test_add_module_coverage(self):
        c = CoverageAnalyzer()
        r = c.add_module_coverage("mod1", 100, 85)
        assert r["line"]["percentage"] == 85.0
        assert c.module_count == 1

    def test_add_with_branches(self):
        c = CoverageAnalyzer()
        r = c.add_module_coverage(
            "mod1", 100, 90, 20, 15, 10, 8,
        )
        assert r["branch"]["percentage"] == 75.0
        assert r["function"]["percentage"] == 80.0

    def test_get_line_coverage_module(self):
        c = CoverageAnalyzer()
        c.add_module_coverage("m1", 100, 80)
        r = c.get_line_coverage("m1")
        assert r["percentage"] == 80.0

    def test_get_line_coverage_total(self):
        c = CoverageAnalyzer()
        c.add_module_coverage("m1", 100, 80)
        c.add_module_coverage("m2", 100, 60)
        r = c.get_line_coverage()
        assert r["percentage"] == 70.0

    def test_get_line_coverage_nonexistent(self):
        c = CoverageAnalyzer()
        r = c.get_line_coverage("nope")
        assert r["percentage"] == 0.0

    def test_get_branch_coverage(self):
        c = CoverageAnalyzer()
        c.add_module_coverage("m1", 100, 80, 20, 16)
        r = c.get_branch_coverage("m1")
        assert r["percentage"] == 80.0

    def test_get_branch_coverage_total(self):
        c = CoverageAnalyzer()
        c.add_module_coverage("m1", 100, 80, 10, 8)
        c.add_module_coverage("m2", 100, 80, 10, 6)
        r = c.get_branch_coverage()
        assert r["percentage"] == 70.0

    def test_get_function_coverage(self):
        c = CoverageAnalyzer()
        c.add_module_coverage(
            "m1", 100, 80, 0, 0, 10, 9,
        )
        r = c.get_function_coverage("m1")
        assert r["percentage"] == 90.0

    def test_get_function_coverage_total(self):
        c = CoverageAnalyzer()
        c.add_module_coverage(
            "m1", 100, 80, 0, 0, 10, 8,
        )
        r = c.get_function_coverage()
        assert r["percentage"] == 80.0

    def test_identify_gaps(self):
        c = CoverageAnalyzer(min_coverage=80.0)
        c.add_module_coverage("good", 100, 90)
        c.add_module_coverage("bad", 100, 50)
        gaps = c.identify_gaps()
        assert len(gaps) >= 1
        modules = [g["module"] for g in gaps]
        assert "bad" in modules

    def test_no_gaps(self):
        c = CoverageAnalyzer(min_coverage=50.0)
        c.add_module_coverage("m1", 100, 60)
        gaps = c.identify_gaps()
        assert len(gaps) == 0

    def test_set_threshold(self):
        c = CoverageAnalyzer()
        c.set_threshold("line", 90.0)
        assert c._thresholds["line"] == 90.0

    def test_meets_threshold_yes(self):
        c = CoverageAnalyzer(min_coverage=70.0)
        c.add_module_coverage("m1", 100, 80)
        assert c.meets_threshold() is True

    def test_meets_threshold_no(self):
        c = CoverageAnalyzer(min_coverage=90.0)
        c.add_module_coverage("m1", 100, 80)
        assert c.meets_threshold() is False

    def test_get_summary(self):
        c = CoverageAnalyzer()
        c.add_module_coverage("m1", 100, 85, 10, 8, 5, 4)
        s = c.get_summary()
        assert s["modules"] == 1
        assert s["line_coverage"] == 85.0

    def test_overall_coverage(self):
        c = CoverageAnalyzer()
        c.add_module_coverage("m1", 100, 75)
        assert c.overall_coverage == 75.0

    def test_empty_coverage(self):
        c = CoverageAnalyzer()
        r = c.get_line_coverage()
        assert r["percentage"] == 0.0


# ==================== MutationTester Testleri ====================


class TestMutationTester:
    """MutationTester testleri."""

    def test_generate_arithmetic_mutations(self):
        m = MutationTester()
        muts = m.generate_mutations("a + b", "arithmetic")
        assert len(muts) >= 1
        assert any("a - b" in mt["mutated_code"] for mt in muts)
        assert m.mutation_count >= 1

    def test_generate_relational_mutations(self):
        m = MutationTester()
        muts = m.generate_mutations("a == b", "relational")
        assert any("!=" in mt["mutated_code"] for mt in muts)

    def test_generate_logical_mutations(self):
        m = MutationTester()
        muts = m.generate_mutations("a and b", "logical")
        assert any("or" in mt["mutated_code"] for mt in muts)

    def test_generate_no_match(self):
        m = MutationTester()
        muts = m.generate_mutations("hello", "arithmetic")
        assert len(muts) == 0

    def test_run_mutation_killed(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        r = m.run_mutation(0, test_passed=False)
        assert r["killed"] is True

    def test_run_mutation_survived(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        r = m.run_mutation(0, test_passed=True)
        assert r["killed"] is False

    def test_get_mutation_score(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        m.generate_mutations("x == y", "relational")
        # Kill the first
        m.run_mutation(0, test_passed=False)
        score = m.get_mutation_score()
        assert score["total"] >= 2
        assert score["killed"] == 1

    def test_get_mutation_score_empty(self):
        m = MutationTester()
        score = m.get_mutation_score()
        assert score["score"] == 0.0

    def test_get_surviving_mutants(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        survivors = m.get_surviving_mutants()
        assert len(survivors) >= 1

    def test_get_test_strength_weak(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        s = m.get_test_strength()
        assert s["strength"] == "weak"

    def test_get_test_strength_excellent(self):
        m = MutationTester()
        muts = m.generate_mutations("a + b", "arithmetic")
        for mut in muts:
            m.run_mutation(mut["id"], test_passed=False)
        s = m.get_test_strength()
        assert s["strength"] == "excellent"

    def test_get_kill_ratio_by_type(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        m.run_mutation(0, test_passed=False)
        ratios = m.get_kill_ratio_by_type()
        assert "arithmetic" in ratios
        assert ratios["arithmetic"]["killed"] == 1

    def test_add_operator(self):
        m = MutationTester()
        m.add_operator("custom", "foo", "bar")
        muts = m.generate_mutations("foo()", "custom")
        assert len(muts) >= 1

    def test_killed_count(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        m.run_mutation(0, test_passed=False)
        assert m.killed_count == 1

    def test_survived_count(self):
        m = MutationTester()
        m.generate_mutations("a + b", "arithmetic")
        assert m.survived_count >= 1

    def test_meets_threshold(self):
        m = MutationTester(threshold=0.5)
        muts = m.generate_mutations("a + b", "arithmetic")
        for mut in muts:
            m.run_mutation(mut["id"], test_passed=False)
        score = m.get_mutation_score()
        assert score["meets_threshold"] is True


# ==================== RegressionDetector Testleri ====================


class TestRegressionDetector:
    """RegressionDetector testleri."""

    def test_set_baseline(self):
        rd = RegressionDetector()
        bl = rd.set_baseline("api", {"response_time": 50.0})
        assert bl["name"] == "api"
        assert rd.baseline_count == 1

    def test_compare_no_regression(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("api", {"response_time": 50.0})
        r = rd.compare_with_baseline("api", {"response_time": 52.0})
        assert r["has_regression"] is False

    def test_compare_with_regression(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("api", {"response_time": 50.0})
        r = rd.compare_with_baseline("api", {"response_time": 70.0})
        assert r["has_regression"] is True
        assert rd.regression_count >= 1

    def test_compare_with_improvement(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("api", {"response_time": 50.0})
        r = rd.compare_with_baseline("api", {"response_time": 30.0})
        assert len(r["improvements"]) >= 1

    def test_compare_no_baseline(self):
        rd = RegressionDetector()
        r = rd.compare_with_baseline("nope", {"x": 1})
        assert r["found"] is False

    def test_detect_performance_regression(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("ep", {"response_time": 50.0})
        r = rd.detect_performance_regression("ep", 80.0)
        assert r["regression"] is True
        assert rd.alert_count >= 1

    def test_detect_performance_no_regression(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("ep", {"response_time": 50.0})
        r = rd.detect_performance_regression("ep", 52.0)
        assert r["regression"] is False

    def test_detect_performance_no_baseline(self):
        rd = RegressionDetector()
        r = rd.detect_performance_regression("x", 50.0)
        assert r["regression"] is False

    def test_detect_behavior_change(self):
        rd = RegressionDetector()
        r = rd.detect_behavior_change("fn", {"a": 1}, {"a": 2})
        assert r["changed"] is True
        assert rd.regression_count >= 1

    def test_detect_behavior_no_change(self):
        rd = RegressionDetector()
        r = rd.detect_behavior_change("fn", {"a": 1}, {"a": 1})
        assert r["changed"] is False

    def test_get_regressions(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("api", {"t": 50.0})
        rd.compare_with_baseline("api", {"t": 100.0})
        regs = rd.get_regressions()
        assert len(regs) >= 1

    def test_get_alerts(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("x", {"response_time": 10.0})
        rd.detect_performance_regression("x", 50.0)
        alerts = rd.get_alerts()
        assert len(alerts) >= 1

    def test_clear_regressions(self):
        rd = RegressionDetector(tolerance=0.1)
        rd.set_baseline("x", {"t": 10.0})
        rd.compare_with_baseline("x", {"t": 50.0})
        count = rd.clear_regressions()
        assert count >= 1
        assert rd.regression_count == 0


# ==================== LoadTester Testleri ====================


class TestLoadTester:
    """LoadTester testleri."""

    def test_create_scenario(self):
        lt = LoadTester()
        s = lt.create_scenario("basic", "/api/test")
        assert s["name"] == "basic"
        assert s["endpoint"] == "/api/test"
        assert lt.scenario_count == 1

    def test_create_scenario_custom(self):
        lt = LoadTester()
        s = lt.create_scenario(
            "heavy", "/api/data",
            users=500, duration=120,
        )
        assert s["users"] == 500
        assert s["duration"] == 120

    def test_run_throughput_test(self):
        lt = LoadTester()
        r = lt.run_throughput_test("tp1", 100, 10)
        assert r["type"] == "throughput"
        assert r["total_requests"] == 1000
        assert r["throughput"] > 0
        assert lt.result_count == 1

    def test_run_stress_test(self):
        lt = LoadTester()
        r = lt.run_stress_test("stress1", 10, 1000, 100)
        assert r["type"] == "stress"
        assert r["breaking_point"] > 0
        assert len(r["steps"]) > 0

    def test_run_spike_test(self):
        lt = LoadTester()
        r = lt.run_spike_test("spike1", 10, 500)
        assert r["type"] == "spike"
        assert r["spike_response_ms"] > r["base_response_ms"]

    def test_run_endurance_test(self):
        lt = LoadTester()
        r = lt.run_endurance_test("endure1", 50, 2.0)
        assert r["type"] == "endurance"
        assert r["total_requests"] > 0

    def test_get_results_all(self):
        lt = LoadTester()
        lt.run_throughput_test("t1")
        lt.run_stress_test("s1")
        results = lt.get_results()
        assert len(results) == 2

    def test_get_results_filtered(self):
        lt = LoadTester()
        lt.run_throughput_test("t1")
        lt.run_stress_test("s1")
        results = lt.get_results("throughput")
        assert len(results) == 1

    def test_get_scenario(self):
        lt = LoadTester()
        lt.create_scenario("sc1", "/api")
        s = lt.get_scenario("sc1")
        assert s is not None
        assert s["name"] == "sc1"

    def test_get_scenario_none(self):
        lt = LoadTester()
        assert lt.get_scenario("nope") is None

    def test_endurance_memory_check(self):
        lt = LoadTester()
        r = lt.run_endurance_test("e1", 50, 0.5)
        assert "memory_leak_detected" in r


# ==================== QualityScorer Testleri ====================


class TestQualityScorer:
    """QualityScorer testleri."""

    def test_score_code_quality(self):
        q = QualityScorer()
        s = q.score_code_quality(
            "mod1",
            complexity=20,
            duplication=5,
            doc_coverage=80,
            lint_issues=2,
        )
        assert s["overall"] > 0
        assert q.metric_count == 1

    def test_score_code_quality_perfect(self):
        q = QualityScorer()
        s = q.score_code_quality(
            "mod1",
            complexity=0,
            duplication=0,
            doc_coverage=100,
            lint_issues=0,
        )
        assert s["overall"] >= 90

    def test_score_test_quality(self):
        q = QualityScorer()
        s = q.score_test_quality(
            "mod1",
            coverage=85,
            mutation_score=0.8,
            assertion_density=3.0,
            test_count=50,
        )
        assert s["overall"] > 0

    def test_calculate_maintainability(self):
        q = QualityScorer()
        m = q.calculate_maintainability(
            "mod1",
            complexity=10,
            lines_of_code=200,
            comment_ratio=0.15,
        )
        assert m["maintainability_index"] > 0
        assert m["grade"] in ("A", "B", "C", "D")

    def test_maintainability_grade_a(self):
        q = QualityScorer()
        m = q.calculate_maintainability(
            "simple",
            complexity=5,
            lines_of_code=50,
            comment_ratio=0.2,
        )
        assert m["grade"] in ("A", "B")

    def test_add_technical_debt(self):
        q = QualityScorer()
        d = q.add_technical_debt(
            "mod1", "needs refactoring", "high", 4.0,
        )
        assert d["severity"] == "high"
        assert q.debt_count == 1

    def test_get_technical_debt(self):
        q = QualityScorer()
        q.add_technical_debt("m1", "debt1", "high", 3.0)
        q.add_technical_debt("m2", "debt2", "low", 1.0)
        summary = q.get_technical_debt()
        assert summary["total_items"] == 2
        assert summary["total_hours"] == 4.0

    def test_add_quality_gate(self):
        q = QualityScorer()
        g = q.add_quality_gate("coverage", "line_coverage", 80.0)
        assert g["threshold"] == 80.0
        assert q.gate_count == 1

    def test_check_quality_gates_pass(self):
        q = QualityScorer()
        q.add_quality_gate("cov", "coverage", 80.0, ">=")
        r = q.check_quality_gates({"coverage": 85.0})
        assert r["all_passed"] is True

    def test_check_quality_gates_fail(self):
        q = QualityScorer()
        q.add_quality_gate("cov", "coverage", 80.0, ">=")
        r = q.check_quality_gates({"coverage": 70.0})
        assert r["all_passed"] is False

    def test_check_quality_gates_multiple(self):
        q = QualityScorer()
        q.add_quality_gate("cov", "coverage", 80.0)
        q.add_quality_gate("debt", "debt_hours", 10.0, "<=")
        r = q.check_quality_gates(
            {"coverage": 85.0, "debt_hours": 5.0},
        )
        assert r["all_passed"] is True
        assert r["passed_count"] == 2

    def test_get_overall_score(self):
        q = QualityScorer()
        q.score_code_quality("m1", complexity=10, doc_coverage=80)
        s = q.get_overall_score()
        assert s["score"] > 0
        assert s["modules"] == 1

    def test_get_overall_score_empty(self):
        q = QualityScorer()
        s = q.get_overall_score()
        assert s["score"] == 0.0


# ==================== TestReportGenerator Testleri ====================


class TestReportGen:
    """TestReportGenerator testleri."""

    def test_generate_html_report(self):
        rg = TestReportGenerator()
        results = [
            {"name": "t1", "status": "passed", "duration_ms": 10},
            {"name": "t2", "status": "failed", "duration_ms": 5},
        ]
        r = rg.generate_html_report(results)
        assert r["format"] == "html"
        assert "<html>" in r["content"]
        assert r["passed"] == 1
        assert r["failed"] == 1
        assert rg.report_count == 1

    def test_generate_junit_xml(self):
        rg = TestReportGenerator()
        results = [
            {"name": "t1", "status": "passed", "duration_ms": 100},
            {"name": "t2", "status": "failed", "error": "err", "duration_ms": 50},
        ]
        r = rg.generate_junit_xml(results, "MySuite")
        assert r["format"] == "junit_xml"
        assert '<?xml' in r["content"]
        assert 'testsuite' in r["content"]
        assert r["failures"] == 1

    def test_generate_junit_xml_error(self):
        rg = TestReportGenerator()
        results = [
            {"name": "t1", "status": "error", "error": "crash", "duration_ms": 0},
        ]
        r = rg.generate_junit_xml(results)
        assert r["errors"] == 1

    def test_generate_coverage_report(self):
        rg = TestReportGenerator()
        r = rg.generate_coverage_report(
            {"line_coverage": 85.0},
        )
        assert r["format"] == "coverage"
        assert r["data"]["line_coverage"] == 85.0

    def test_generate_trend_analysis_improving(self):
        rg = TestReportGenerator()
        points = [
            {"value": 70}, {"value": 75},
            {"value": 80}, {"value": 85},
        ]
        r = rg.generate_trend_analysis(points)
        assert r["trend"] == "improving"
        assert r["data_points"] == 4

    def test_generate_trend_analysis_declining(self):
        rg = TestReportGenerator()
        points = [
            {"value": 90}, {"value": 80}, {"value": 70},
        ]
        r = rg.generate_trend_analysis(points)
        assert r["trend"] == "declining"

    def test_generate_trend_analysis_stable(self):
        rg = TestReportGenerator()
        points = [{"value": 80}, {"value": 80}]
        r = rg.generate_trend_analysis(points)
        assert r["trend"] == "stable"

    def test_generate_trend_analysis_empty(self):
        rg = TestReportGenerator()
        r = rg.generate_trend_analysis([])
        assert r["trend"] == "stable"

    def test_generate_trend_analysis_single(self):
        rg = TestReportGenerator()
        r = rg.generate_trend_analysis([{"value": 50}])
        assert r["trend"] == "stable"

    def test_generate_executive_summary(self):
        rg = TestReportGenerator()
        r = rg.generate_executive_summary(
            test_results={"total": 100, "passed": 95, "failed": 5, "pass_rate": 0.95},
            coverage={"line_coverage": 85.0, "branch_coverage": 70.0},
            quality={"score": 82.0},
        )
        assert r["format"] == "executive_summary"
        assert r["tests"]["total"] == 100
        assert r["coverage"]["line"] == 85.0
        assert r["quality"]["score"] == 82.0

    def test_generate_executive_summary_minimal(self):
        rg = TestReportGenerator()
        r = rg.generate_executive_summary(
            test_results={"total": 10, "passed": 10},
        )
        assert "coverage" not in r
        assert "quality" not in r

    def test_get_report(self):
        rg = TestReportGenerator()
        rg.generate_html_report([])
        r = rg.get_report(0)
        assert r is not None

    def test_get_report_latest(self):
        rg = TestReportGenerator()
        rg.generate_html_report([], title="first")
        rg.generate_html_report([], title="second")
        r = rg.get_report(-1)
        assert r["title"] == "second"

    def test_get_report_empty(self):
        rg = TestReportGenerator()
        assert rg.get_report() is None

    def test_history_count(self):
        rg = TestReportGenerator()
        rg.generate_trend_analysis([{"value": 1}, {"value": 2}])
        assert rg.history_count == 2


# ==================== QAOrchestrator Testleri ====================


class TestQAOrchestrator:
    """QAOrchestrator testleri."""

    def test_init(self):
        qa = QAOrchestrator()
        assert qa.generator is not None
        assert qa.runner is not None
        assert qa.coverage is not None

    def test_run_qa_pipeline(self):
        qa = QAOrchestrator()
        tests = [
            {"name": "t1", "fn": lambda: None},
            {"name": "t2", "fn": lambda: None},
        ]
        r = qa.run_qa_pipeline(tests)
        assert r["test_results"]["total"] == 2
        assert r["test_results"]["passed"] == 2
        assert qa.pipeline_count == 1

    def test_run_qa_pipeline_with_coverage(self):
        qa = QAOrchestrator()
        tests = [{"name": "t1", "fn": lambda: None}]
        cov = {
            "mod1": {
                "total_lines": 100,
                "covered_lines": 85,
            },
        }
        r = qa.run_qa_pipeline(tests, coverage_data=cov)
        assert r["coverage"]["modules"] == 1

    def test_run_qa_pipeline_with_load(self):
        qa = QAOrchestrator()
        tests = [{"name": "t1", "fn": lambda: None}]
        r = qa.run_qa_pipeline(tests, run_load=True)
        assert r["load_test"] is not None

    def test_run_qa_pipeline_failures_notify(self):
        qa = QAOrchestrator()
        tests = [
            {"name": "t1", "fn": lambda: None},
            {"name": "t2", "fn": lambda: 1/0},
        ]
        qa.run_qa_pipeline(tests)
        assert qa.notification_count >= 1

    def test_check_quality_gate(self):
        qa = QAOrchestrator()
        qa.quality.add_quality_gate("cov", "coverage", 80.0)
        r = qa.check_quality_gate({"coverage": 85.0})
        assert r["all_passed"] is True

    def test_run_regression_check(self):
        qa = QAOrchestrator()
        qa.regression.set_baseline("api", {"t": 50.0})
        r = qa.run_regression_check("api", {"t": 52.0})
        assert r["has_regression"] is False

    def test_run_regression_check_with_regression(self):
        qa = QAOrchestrator()
        qa.regression.set_baseline("api", {"t": 50.0})
        qa.regression._tolerance = 0.1
        r = qa.run_regression_check("api", {"t": 100.0})
        assert r["has_regression"] is True
        assert qa.notification_count >= 1

    def test_get_analytics(self):
        qa = QAOrchestrator()
        qa.runner.run_test("t1", lambda: None)
        a = qa.get_analytics()
        assert a["total_tests_run"] == 1
        assert a["pass_rate"] > 0

    def test_snapshot(self):
        qa = QAOrchestrator()
        qa.runner.run_test("t1", lambda: None)
        s = qa.snapshot()
        assert s["tests_run"] == 1
        assert s["uptime"] >= 0


# ==================== Config Testleri ====================


class TestQAConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.qa_enabled is True
        assert s.min_coverage == 80.0
        assert s.mutation_threshold == 0.8
        assert s.load_test_users == 100
        assert s.quality_gate_enabled is True
