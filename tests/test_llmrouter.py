"""
Multi-LLM Router & Orchestrator testleri.
"""

import pytest

from app.core.llmrouter.model_registry import (
    ModelRegistry,
)
from app.core.llmrouter.task_complexity_analyzer import (
    TaskComplexityAnalyzer,
)
from app.core.llmrouter.model_selector import (
    ModelSelector,
)
from app.core.llmrouter.fallback_router import (
    FallbackRouter,
)
from app.core.llmrouter.cost_per_token_tracker import (
    CostPerTokenTracker,
)
from app.core.llmrouter.latency_optimizer import (
    LatencyOptimizer,
)
from app.core.llmrouter.model_performance_comparator import (
    ModelPerformanceComparator,
)
from app.core.llmrouter.provider_health_monitor import (
    ProviderHealthMonitor,
)
from app.core.llmrouter.llmrouter_orchestrator import (
    LLMRouterOrchestrator,
)


# ============================================================
# ModelRegistry Testleri
# ============================================================
class TestModelRegistry:
    """ModelRegistry testleri."""

    def setup_method(self):
        self.reg = ModelRegistry()

    def test_init(self):
        assert self.reg.model_count == 0
        s = self.reg.get_summary()
        assert s["retrieved"] is True

    def test_register_provider(self):
        r = self.reg.register_provider(
            name="openai",
            api_type="rest",
            base_url="https://api.openai.com",
        )
        assert r["registered"] is True
        assert r["name"] == "openai"

    def test_register_model(self):
        r = self.reg.register_model(
            model_id="gpt-4",
            provider="openai",
            name="GPT-4",
            capabilities=["text_generation", "reasoning"],
            max_tokens=8192,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            context_window=128000,
        )
        assert r["registered"] is True
        assert self.reg.model_count == 1

    def test_register_model_invalid_capability(self):
        r = self.reg.register_model(
            model_id="m1",
            capabilities=["nonexistent"],
        )
        assert r["registered"] is False
        assert "Gecersiz" in r["error"]

    def test_get_model(self):
        self.reg.register_model(
            model_id="gpt-4",
            provider="openai",
            name="GPT-4",
        )
        r = self.reg.get_model("gpt-4")
        assert r["retrieved"] is True
        assert r["model_id"] == "gpt-4"

    def test_get_model_not_found(self):
        r = self.reg.get_model("x")
        assert r["retrieved"] is False

    def test_find_by_capability(self):
        self.reg.register_model(
            model_id="m1",
            provider="p1",
            capabilities=["text_generation"],
        )
        self.reg.register_model(
            model_id="m2",
            provider="p1",
            capabilities=["vision"],
        )
        r = self.reg.find_by_capability(
            capability="text_generation",
        )
        assert r["retrieved"] is True
        assert r["count"] == 1

    def test_find_by_provider(self):
        self.reg.register_model(
            model_id="m1", provider="p1",
        )
        self.reg.register_model(
            model_id="m2", provider="p2",
        )
        r = self.reg.find_by_capability(
            provider="p1",
        )
        assert r["count"] == 1

    def test_update_status(self):
        self.reg.register_model(
            model_id="m1",
        )
        r = self.reg.update_status(
            "m1", "inactive",
        )
        assert r["updated"] is True

    def test_update_status_invalid(self):
        self.reg.register_model(
            model_id="m1",
        )
        r = self.reg.update_status(
            "m1", "bad",
        )
        assert r["updated"] is False

    def test_update_status_not_found(self):
        r = self.reg.update_status("x", "active")
        assert r["updated"] is False

    def test_increment_usage(self):
        self.reg.register_model(model_id="m1")
        self.reg.increment_usage("m1")
        m = self.reg.get_model("m1")
        assert m["usage_count"] == 1

    def test_get_pricing(self):
        self.reg.register_model(
            model_id="m1",
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.02,
        )
        r = self.reg.get_pricing("m1")
        assert r["retrieved"] is True
        assert r["input_cost_per_1k"] == 0.01

    def test_get_pricing_not_found(self):
        r = self.reg.get_pricing("x")
        assert r["retrieved"] is False

    def test_list_providers(self):
        self.reg.register_provider(name="p1")
        r = self.reg.list_providers()
        assert r["count"] == 1

    def test_get_summary(self):
        self.reg.register_model(
            model_id="m1", provider="p1",
        )
        s = self.reg.get_summary()
        assert s["total_models"] == 1
        assert "p1" in s["by_provider"]


# ============================================================
# TaskComplexityAnalyzer Testleri
# ============================================================
class TestTaskComplexityAnalyzer:
    """TaskComplexityAnalyzer testleri."""

    def setup_method(self):
        self.analyzer = TaskComplexityAnalyzer()

    def test_init(self):
        assert self.analyzer.analysis_count == 0

    def test_analyze_simple(self):
        r = self.analyzer.analyze_complexity(
            task_text="What is 2+2?",
        )
        assert r["analyzed"] is True
        assert r["complexity_level"] in (
            TaskComplexityAnalyzer.COMPLEXITY_LEVELS
        )

    def test_analyze_complex(self):
        text = (
            "Analyze and compare the trade-off between "
            "multiple optimization strategies. Evaluate "
            "the design and explain why each approach "
            "works. This is a complex multi-step task."
        )
        r = self.analyzer.analyze_complexity(
            task_text=text, context="some context",
        )
        assert r["analyzed"] is True
        assert r["complexity_score"] > 0.3

    def test_domain_detection_coding(self):
        r = self.analyzer.analyze_complexity(
            task_text="debug this function and fix the bug in the api code",
        )
        assert r["domain"] == "coding"

    def test_domain_detection_math(self):
        r = self.analyzer.analyze_complexity(
            task_text="solve the equation and calculate the formula proof",
        )
        assert r["domain"] == "math"

    def test_domain_detection_legal(self):
        r = self.analyzer.analyze_complexity(
            task_text="review the contract clause for legal compliance with regulation",
        )
        assert r["domain"] == "legal"

    def test_domain_detection_general(self):
        r = self.analyzer.analyze_complexity(
            task_text="hello world",
        )
        assert r["domain"] == "general"

    def test_token_estimation_with_hint(self):
        r = self.analyzer.analyze_complexity(
            task_text="test", max_tokens_hint=500,
        )
        assert r["estimated_tokens"] == 500

    def test_token_estimation_auto(self):
        r = self.analyzer.analyze_complexity(
            task_text="write a simple function",
        )
        assert r["estimated_tokens"] >= 256

    def test_reasoning_depth(self):
        r = self.analyzer.analyze_complexity(
            task_text="simple hello",
        )
        assert r["reasoning_depth"] in (
            "shallow", "moderate", "deep",
        )

    def test_predict_resources(self):
        r = self.analyzer.analyze_complexity(
            task_text="analyze something complex",
        )
        aid = r["analysis_id"]
        p = self.analyzer.predict_resources(aid)
        assert p["predicted"] is True
        assert "estimated_latency_ms" in p

    def test_predict_resources_not_found(self):
        p = self.analyzer.predict_resources("x")
        assert p["predicted"] is False

    def test_get_summary(self):
        self.analyzer.analyze_complexity(
            task_text="test task",
        )
        s = self.analyzer.get_summary()
        assert s["total_analyses"] == 1

    def test_complexity_levels_count(self):
        assert len(
            TaskComplexityAnalyzer.COMPLEXITY_LEVELS
        ) == 5

    def test_domains_count(self):
        assert len(
            TaskComplexityAnalyzer.DOMAINS
        ) == 10

    def test_stats_tracking(self):
        # Simple task
        self.analyzer.analyze_complexity(
            task_text="hi",
        )
        s = self.analyzer.get_summary()
        assert s["stats"]["analyses_performed"] == 1


# ============================================================
# ModelSelector Testleri
# ============================================================
class TestModelSelector:
    """ModelSelector testleri."""

    def setup_method(self):
        self.sel = ModelSelector()
        self.models = [
            {
                "model_id": "gpt-4",
                "provider": "openai",
                "capabilities": [
                    "text_generation",
                    "reasoning",
                    "code_generation",
                ],
                "input_cost_per_1k": 0.03,
                "context_window": 128000,
                "status": "active",
            },
            {
                "model_id": "claude-3",
                "provider": "anthropic",
                "capabilities": [
                    "text_generation",
                    "reasoning",
                ],
                "input_cost_per_1k": 0.015,
                "context_window": 200000,
                "status": "active",
            },
            {
                "model_id": "gpt-3.5",
                "provider": "openai",
                "capabilities": [
                    "text_generation",
                ],
                "input_cost_per_1k": 0.001,
                "context_window": 16384,
                "status": "active",
            },
        ]

    def test_init(self):
        assert self.sel.selection_count == 0

    def test_select_balanced(self):
        r = self.sel.select_model(
            available_models=self.models,
            strategy="balanced",
        )
        assert r["selected"] is True
        assert r["model_id"] in (
            "gpt-4", "claude-3", "gpt-3.5",
        )

    def test_select_lowest_cost(self):
        r = self.sel.select_model(
            available_models=self.models,
            strategy="lowest_cost",
        )
        assert r["selected"] is True
        assert r["model_id"] == "gpt-3.5"

    def test_select_best_quality(self):
        r = self.sel.select_model(
            available_models=self.models,
            strategy="best_quality",
        )
        assert r["selected"] is True
        # claude-3 has largest context
        assert r["model_id"] == "claude-3"

    def test_select_fastest(self):
        r = self.sel.select_model(
            available_models=self.models,
            strategy="fastest",
        )
        assert r["selected"] is True

    def test_select_capability_match(self):
        r = self.sel.select_model(
            available_models=self.models,
            strategy="capability_match",
        )
        assert r["selected"] is True
        assert r["model_id"] == "gpt-4"

    def test_select_with_capabilities(self):
        r = self.sel.select_model(
            available_models=self.models,
            required_capabilities=["code_generation"],
            strategy="balanced",
        )
        assert r["selected"] is True
        assert r["model_id"] == "gpt-4"

    def test_select_with_cost_filter(self):
        r = self.sel.select_model(
            available_models=self.models,
            max_cost_per_1k=0.002,
            strategy="balanced",
        )
        assert r["selected"] is True

    def test_select_with_context_filter(self):
        r = self.sel.select_model(
            available_models=self.models,
            min_context=100000,
            strategy="balanced",
        )
        assert r["selected"] is True

    def test_select_invalid_strategy(self):
        r = self.sel.select_model(
            available_models=self.models,
            strategy="invalid",
        )
        assert r["selected"] is False

    def test_select_empty_models(self):
        r = self.sel.select_model(
            available_models=[],
        )
        assert r["selected"] is False

    def test_fallback_selection(self):
        # All filtered out -> fallback to first
        r = self.sel.select_model(
            available_models=self.models,
            min_context=999999,
            strategy="balanced",
        )
        assert r["selected"] is True

    def test_set_preference(self):
        r = self.sel.set_preference(
            domain="coding",
            preferred_model="gpt-4",
            strategy="best_quality",
        )
        assert r["set"] is True

    def test_add_constraint(self):
        r = self.sel.add_constraint(
            name="max_cost",
            constraint_type="cost",
            value=0.05,
        )
        assert r["added"] is True

    def test_get_summary(self):
        self.sel.select_model(
            available_models=self.models,
        )
        s = self.sel.get_summary()
        assert s["total_selections"] == 1


# ============================================================
# FallbackRouter Testleri
# ============================================================
class TestFallbackRouter:
    """FallbackRouter testleri."""

    def setup_method(self):
        self.router = FallbackRouter(
            circuit_threshold=3,
        )

    def test_init(self):
        assert self.router.open_circuits == 0

    def test_configure_route(self):
        r = self.router.configure_route(
            primary_model="gpt-4",
            fallback_chain=["claude-3", "gpt-3.5"],
        )
        assert r["configured"] is True
        assert r["chain_length"] == 2

    def test_route_primary(self):
        self.router.configure_route(
            primary_model="gpt-4",
            fallback_chain=["claude-3"],
        )
        r = self.router.route_request(
            primary_model="gpt-4",
        )
        assert r["routed"] is True
        assert r["routed_to"] == "gpt-4"
        assert r["is_fallback"] is False

    def test_route_fallback(self):
        self.router.configure_route(
            primary_model="gpt-4",
            fallback_chain=["claude-3"],
        )
        r = self.router.route_request(
            primary_model="gpt-4",
            simulate_failure=True,
        )
        assert r["routed"] is True
        assert r["routed_to"] == "claude-3"
        assert r["is_fallback"] is True

    def test_circuit_breaker_opens(self):
        self.router.configure_route(
            primary_model="m1",
            fallback_chain=["m2"],
        )
        # Trigger failures to open circuit
        for _ in range(3):
            self.router.route_request(
                primary_model="m1",
                simulate_failure=True,
            )
        status = self.router.get_circuit_status("m1")
        assert status["state"] == "open"

    def test_reset_circuit(self):
        self.router.configure_route(
            primary_model="m1",
        )
        self.router._record_failure("m1")
        self.router._record_failure("m1")
        self.router._record_failure("m1")
        r = self.router.reset_circuit("m1")
        assert r["reset"] is True
        assert r["state"] == "closed"

    def test_half_open_circuit(self):
        self.router.configure_route(
            primary_model="m1",
        )
        r = self.router.half_open_circuit("m1")
        assert r["updated"] is True
        assert r["state"] == "half_open"

    def test_half_open_recovery(self):
        self.router.configure_route(
            primary_model="m1",
        )
        self.router.half_open_circuit("m1")
        self.router._record_success("m1")
        status = self.router.get_circuit_status("m1")
        assert status["state"] == "closed"

    def test_get_circuit_status_not_found(self):
        r = self.router.get_circuit_status("x")
        assert r["retrieved"] is False

    def test_reset_not_found(self):
        r = self.router.reset_circuit("x")
        assert r["reset"] is False

    def test_all_fail(self):
        self.router.configure_route(
            primary_model="m1",
            fallback_chain=[],
        )
        r = self.router.route_request(
            primary_model="m1",
            simulate_failure=True,
        )
        assert r["routed"] is False

    def test_get_summary(self):
        s = self.router.get_summary()
        assert s["retrieved"] is True
        assert "total_routes" in s

    def test_circuit_states(self):
        assert len(FallbackRouter.CIRCUIT_STATES) == 3


# ============================================================
# CostPerTokenTracker Testleri
# ============================================================
class TestCostPerTokenTracker:
    """CostPerTokenTracker testleri."""

    def setup_method(self):
        self.tracker = CostPerTokenTracker()

    def test_init(self):
        assert self.tracker.total_cost == 0.0

    def test_record_usage(self):
        r = self.tracker.record_usage(
            model_id="gpt-4",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
        )
        assert r["recorded"] is True
        assert r["total_cost"] == 0.06  # 0.03 + 0.03

    def test_total_cost_accumulates(self):
        self.tracker.record_usage(
            input_tokens=1000,
            input_cost_per_1k=0.01,
        )
        self.tracker.record_usage(
            input_tokens=1000,
            input_cost_per_1k=0.01,
        )
        assert self.tracker.total_cost == 0.02

    def test_set_budget(self):
        r = self.tracker.set_budget(
            name="monthly",
            provider="openai",
            daily_limit=10.0,
            monthly_limit=100.0,
        )
        assert r["set"] is True

    def test_budget_daily_alert(self):
        self.tracker.set_budget(
            name="test",
            daily_limit=0.01,
        )
        self.tracker.record_usage(
            input_tokens=1000,
            input_cost_per_1k=0.03,
        )
        status = self.tracker.get_budget_status("test")
        assert len(status["alerts"]) > 0

    def test_budget_monthly_alert(self):
        self.tracker.set_budget(
            name="test",
            monthly_limit=0.01,
        )
        self.tracker.record_usage(
            input_tokens=1000,
            input_cost_per_1k=0.03,
        )
        status = self.tracker.get_budget_status("test")
        alerts = [
            a for a in status["alerts"]
            if a["type"] == "monthly_exceeded"
        ]
        assert len(alerts) > 0

    def test_get_cost_by_model(self):
        self.tracker.record_usage(
            model_id="m1",
            input_tokens=100,
            input_cost_per_1k=0.01,
        )
        r = self.tracker.get_cost_by_model("m1")
        assert r["retrieved"] is True
        assert r["usage_count"] == 1

    def test_get_cost_by_provider(self):
        self.tracker.record_usage(
            provider="openai",
            input_tokens=100,
            input_cost_per_1k=0.01,
        )
        r = self.tracker.get_cost_by_provider("openai")
        assert r["retrieved"] is True

    def test_compare_providers(self):
        self.tracker.record_usage(
            provider="openai",
            input_tokens=1000,
            input_cost_per_1k=0.03,
        )
        self.tracker.record_usage(
            provider="anthropic",
            input_tokens=1000,
            input_cost_per_1k=0.015,
        )
        r = self.tracker.compare_providers()
        assert r["retrieved"] is True
        assert r["cheapest"] == "anthropic"

    def test_get_budget_status_not_found(self):
        r = self.tracker.get_budget_status("x")
        assert r["retrieved"] is False

    def test_get_summary(self):
        s = self.tracker.get_summary()
        assert s["retrieved"] is True
        assert "total_records" in s


# ============================================================
# LatencyOptimizer Testleri
# ============================================================
class TestLatencyOptimizer:
    """LatencyOptimizer testleri."""

    def setup_method(self):
        self.opt = LatencyOptimizer(
            default_timeout_ms=5000,
        )

    def test_init(self):
        assert self.opt.cache_hit_rate == 0.0

    def test_record_latency(self):
        r = self.opt.record_latency(
            model_id="gpt-4",
            provider="openai",
            latency_ms=150.0,
        )
        assert r["recorded"] is True

    def test_timeout_detection(self):
        self.opt.record_latency(
            model_id="m1",
            latency_ms=6000.0,
        )
        s = self.opt.get_summary()
        assert s["stats"]["timeouts_occurred"] == 1

    def test_get_fastest_model(self):
        for _ in range(5):
            self.opt.record_latency(
                model_id="fast", latency_ms=100,
            )
            self.opt.record_latency(
                model_id="slow", latency_ms=500,
            )
        r = self.opt.get_fastest_model()
        assert r["found"] is True
        assert r["fastest"] == "fast"

    def test_get_fastest_no_data(self):
        r = self.opt.get_fastest_model()
        assert r["found"] is False

    def test_get_fastest_min_samples(self):
        self.opt.record_latency(
            model_id="m1", latency_ms=100,
        )
        r = self.opt.get_fastest_model(
            min_samples=5,
        )
        assert r["found"] is False

    def test_cache_response(self):
        r = self.opt.cache_response(
            cache_key="test_q",
            response="test_a",
            model_id="gpt-4",
        )
        assert r["cached"] is True

    def test_cache_invalid_strategy(self):
        r = self.opt.cache_response(
            cache_key="k",
            strategy="invalid",
        )
        assert r["cached"] is False

    def test_lookup_cache_hit(self):
        self.opt.cache_response(
            cache_key="k1",
            response="answer",
        )
        r = self.opt.lookup_cache("k1")
        assert r["hit"] is True
        assert r["response"] == "answer"

    def test_lookup_cache_miss(self):
        r = self.opt.lookup_cache("x")
        assert r["hit"] is False

    def test_cache_hit_rate(self):
        self.opt.cache_response(
            cache_key="k1", response="a",
        )
        self.opt.lookup_cache("k1")  # hit
        self.opt.lookup_cache("x")   # miss
        assert self.opt.cache_hit_rate == 0.5

    def test_set_timeout(self):
        r = self.opt.set_timeout(
            model_id="m1", timeout_ms=10000,
        )
        assert r["set"] is True
        assert r["timeout_ms"] == 10000

    def test_set_timeout_default(self):
        r = self.opt.set_timeout(
            model_id="m1",
        )
        assert r["timeout_ms"] == 5000

    def test_get_latency_stats(self):
        for v in [100, 200, 300, 400, 500]:
            self.opt.record_latency(
                model_id="m1", latency_ms=v,
            )
        r = self.opt.get_latency_stats("m1")
        assert r["retrieved"] is True
        assert r["avg_latency_ms"] == 300.0
        assert r["min_latency_ms"] == 100.0
        assert r["max_latency_ms"] == 500.0

    def test_get_latency_stats_no_data(self):
        r = self.opt.get_latency_stats("x")
        assert r["retrieved"] is False

    def test_optimize_routing(self):
        for _ in range(5):
            self.opt.record_latency(
                model_id="m1",
                latency_ms=15000,
            )
        r = self.opt.optimize_routing(
            task_latency_budget_ms=5000,
        )
        assert r["optimized"] is True
        assert len(r["recommendations"]) > 0

    def test_get_summary(self):
        s = self.opt.get_summary()
        assert s["retrieved"] is True
        assert "cache_entries" in s


# ============================================================
# ModelPerformanceComparator Testleri
# ============================================================
class TestModelPerformanceComparator:
    """ModelPerformanceComparator testleri."""

    def setup_method(self):
        self.comp = ModelPerformanceComparator()

    def test_init(self):
        assert self.comp.evaluation_count == 0

    def test_evaluate_response(self):
        r = self.comp.evaluate_response(
            model_id="gpt-4",
            task_domain="coding",
            overall_score=0.85,
        )
        assert r["evaluated"] is True
        assert r["overall_score"] == 0.85

    def test_evaluate_with_dimensions(self):
        r = self.comp.evaluate_response(
            model_id="m1",
            scores={
                "accuracy": 0.9,
                "relevance": 0.8,
            },
        )
        assert r["evaluated"] is True
        assert r["overall_score"] == 0.85

    def test_score_clamping(self):
        r = self.comp.evaluate_response(
            model_id="m1",
            overall_score=1.5,
        )
        assert r["overall_score"] == 1.0

    def test_create_ab_test(self):
        r = self.comp.create_ab_test(
            name="gpt4-vs-claude",
            model_a="gpt-4",
            model_b="claude-3",
        )
        assert r["created"] is True

    def test_record_ab_result(self):
        c = self.comp.create_ab_test(
            name="test",
            model_a="a",
            model_b="b",
        )
        tid = c["test_id"]
        r = self.comp.record_ab_result(
            test_id=tid, variant="a", score=0.9,
        )
        assert r["recorded"] is True

    def test_record_ab_invalid_variant(self):
        c = self.comp.create_ab_test(
            name="t", model_a="a", model_b="b",
        )
        r = self.comp.record_ab_result(
            test_id=c["test_id"],
            variant="c",
        )
        assert r["recorded"] is False

    def test_record_ab_not_found(self):
        r = self.comp.record_ab_result(
            test_id="x",
        )
        assert r["recorded"] is False

    def test_ab_completion(self):
        c = self.comp.create_ab_test(
            name="t", model_a="a", model_b="b",
            sample_size=2,
        )
        tid = c["test_id"]
        self.comp.record_ab_result(
            test_id=tid, variant="a", score=0.9,
        )
        self.comp.record_ab_result(
            test_id=tid, variant="b", score=0.7,
        )
        assert (
            self.comp._ab_tests[tid]["status"]
            == "completed"
        )

    def test_get_ab_winner(self):
        c = self.comp.create_ab_test(
            name="t", model_a="a", model_b="b",
        )
        tid = c["test_id"]
        self.comp.record_ab_result(
            test_id=tid, variant="a",
            score=0.9, latency_ms=100,
        )
        self.comp.record_ab_result(
            test_id=tid, variant="b",
            score=0.7, latency_ms=200,
        )
        r = self.comp.get_ab_winner(tid)
        assert r["determined"] is True
        assert r["winner"] == "a"
        assert r["winner_model"] == "a"

    def test_get_ab_winner_not_found(self):
        r = self.comp.get_ab_winner("x")
        assert r["determined"] is False

    def test_get_ab_winner_no_data(self):
        c = self.comp.create_ab_test(
            name="t", model_a="a", model_b="b",
        )
        r = self.comp.get_ab_winner(
            c["test_id"],
        )
        assert r["determined"] is False

    def test_run_benchmark(self):
        self.comp.evaluate_response(
            model_id="m1", overall_score=0.9,
        )
        self.comp.evaluate_response(
            model_id="m2", overall_score=0.7,
        )
        r = self.comp.run_benchmark(
            name="test",
            model_ids=["m1", "m2"],
        )
        assert r["completed"] is True
        assert r["ranking"][0] == "m1"

    def test_recommend_model(self):
        self.comp.evaluate_response(
            model_id="m1",
            task_domain="coding",
            overall_score=0.9,
        )
        self.comp.evaluate_response(
            model_id="m2",
            task_domain="coding",
            overall_score=0.7,
        )
        r = self.comp.recommend_model(
            task_domain="coding",
        )
        assert r["found"] is True
        assert r["recommended"] == "m1"

    def test_recommend_with_min_score(self):
        self.comp.evaluate_response(
            model_id="m1", overall_score=0.3,
        )
        r = self.comp.recommend_model(
            min_score=0.5,
        )
        assert r["found"] is False

    def test_get_summary(self):
        s = self.comp.get_summary()
        assert s["retrieved"] is True


# ============================================================
# ProviderHealthMonitor Testleri
# ============================================================
class TestProviderHealthMonitor:
    """ProviderHealthMonitor testleri."""

    def setup_method(self):
        self.mon = ProviderHealthMonitor()

    def test_init(self):
        assert self.mon.healthy_count == 0

    def test_register_provider(self):
        r = self.mon.register_provider(
            provider_id="openai",
            name="OpenAI",
        )
        assert r["registered"] is True

    def test_health_check_healthy(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        r = self.mon.perform_health_check(
            provider_id="p1",
            response_time_ms=100,
            is_available=True,
        )
        assert r["checked"] is True
        assert r["health_state"] == "healthy"

    def test_health_check_degraded(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        r = self.mon.perform_health_check(
            provider_id="p1",
            response_time_ms=6000,
            is_available=True,
        )
        assert r["health_state"] == "degraded"

    def test_health_check_unhealthy(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        r = self.mon.perform_health_check(
            provider_id="p1",
            is_available=False,
            error_message="Connection refused",
        )
        assert r["health_state"] == "unhealthy"

    def test_health_check_not_found(self):
        r = self.mon.perform_health_check(
            provider_id="x",
        )
        assert r["checked"] is False

    def test_incident_on_state_change(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        # First become healthy
        self.mon.perform_health_check(
            provider_id="p1",
            response_time_ms=100,
            is_available=True,
        )
        # Then unhealthy
        self.mon.perform_health_check(
            provider_id="p1",
            is_available=False,
        )
        assert len(self.mon._incidents) == 1

    def test_record_request(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        r = self.mon.record_request(
            provider_id="p1",
            tokens_used=100,
        )
        assert r["recorded"] is True

    def test_record_request_error(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        self.mon.record_request(
            provider_id="p1", success=False,
        )
        p = self.mon._providers["p1"]
        assert p["error_rate"] > 0

    def test_record_request_not_found(self):
        r = self.mon.record_request(
            provider_id="x",
        )
        assert r["recorded"] is False

    def test_rate_limit_detection(self):
        self.mon.register_provider(
            provider_id="p1",
            name="P1",
            rate_limit_rpm=2,
        )
        self.mon.record_request(
            provider_id="p1",
        )
        r = self.mon.record_request(
            provider_id="p1",
        )
        assert r["rate_limited"] is True

    def test_reset_rate_counters(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        self.mon.record_request(
            provider_id="p1",
        )
        r = self.mon.reset_rate_counters("p1")
        assert r["reset"] is True

    def test_reset_rate_not_found(self):
        r = self.mon.reset_rate_counters("x")
        assert r["reset"] is False

    def test_get_uptime(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        self.mon.perform_health_check(
            provider_id="p1",
            is_available=True,
            response_time_ms=100,
        )
        r = self.mon.get_uptime("p1")
        assert r["retrieved"] is True
        assert r["uptime_percent"] == 100.0

    def test_get_uptime_not_found(self):
        r = self.mon.get_uptime("x")
        assert r["retrieved"] is False

    def test_get_error_rates(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        r = self.mon.get_error_rates()
        assert r["retrieved"] is True
        assert len(r["error_rates"]) == 1

    def test_get_rate_limit_status(self):
        self.mon.register_provider(
            provider_id="p1",
            name="P1",
            rate_limit_rpm=100,
        )
        r = self.mon.get_rate_limit_status("p1")
        assert r["retrieved"] is True
        assert r["rpm_limit"] == 100

    def test_get_rate_limit_not_found(self):
        r = self.mon.get_rate_limit_status("x")
        assert r["retrieved"] is False

    def test_get_dashboard(self):
        self.mon.register_provider(
            provider_id="p1", name="P1",
        )
        r = self.mon.get_dashboard()
        assert r["retrieved"] is True
        assert len(r["providers"]) == 1

    def test_get_summary(self):
        s = self.mon.get_summary()
        assert s["retrieved"] is True


# ============================================================
# LLMRouterOrchestrator Testleri
# ============================================================
class TestLLMRouterOrchestrator:
    """LLMRouterOrchestrator testleri."""

    def setup_method(self):
        self.orch = LLMRouterOrchestrator(
            default_provider="openai",
            cost_optimization=True,
            auto_fallback=True,
            latency_threshold_ms=5000,
        )
        # Setup provider and models
        self.orch.setup_provider(
            provider_id="openai",
            name="OpenAI",
            models=[
                {
                    "model_id": "gpt-4",
                    "name": "GPT-4",
                    "capabilities": [
                        "text_generation",
                        "reasoning",
                    ],
                    "input_cost_per_1k": 0.03,
                    "output_cost_per_1k": 0.06,
                    "context_window": 128000,
                },
                {
                    "model_id": "gpt-3.5",
                    "name": "GPT-3.5",
                    "capabilities": [
                        "text_generation",
                    ],
                    "input_cost_per_1k": 0.001,
                    "output_cost_per_1k": 0.002,
                    "context_window": 16384,
                },
            ],
        )

    def test_init(self):
        s = self.orch.get_summary()
        assert s["retrieved"] is True

    def test_setup_provider(self):
        r = self.orch.setup_provider(
            provider_id="anthropic",
            name="Anthropic",
            models=[{
                "model_id": "claude-3",
                "name": "Claude 3",
            }],
        )
        assert r["setup"] is True
        assert r["models_registered"] == 1

    def test_route_task(self):
        r = self.orch.route_task(
            task_text="Write a function to sort a list",
        )
        assert r["routed"] is True
        assert "model_id" in r
        assert "complexity_score" in r

    def test_route_task_with_provider(self):
        r = self.orch.route_task(
            task_text="Explain quantum physics",
            preferred_provider="openai",
        )
        assert r["routed"] is True

    def test_route_task_simple_cost_opt(self):
        r = self.orch.route_task(
            task_text="hi",
            strategy="balanced",
        )
        assert r["routed"] is True
        # Simple task -> lowest_cost
        assert r["strategy"] == "lowest_cost"

    def test_route_no_models(self):
        orch = LLMRouterOrchestrator()
        r = orch.route_task(
            task_text="test",
        )
        assert r["routed"] is False

    def test_record_completion(self):
        r = self.orch.record_completion(
            model_id="gpt-4",
            provider="openai",
            input_tokens=500,
            output_tokens=200,
            latency_ms=1500,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            quality_score=0.9,
            task_domain="coding",
        )
        assert r["recorded"] is True
        assert r["total_cost"] > 0

    def test_record_completion_no_quality(self):
        r = self.orch.record_completion(
            model_id="gpt-4",
            provider="openai",
            input_tokens=100,
            latency_ms=500,
        )
        assert r["recorded"] is True

    def test_get_analytics(self):
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "cost" in r
        assert "latency" in r
        assert "performance" in r
        assert "health" in r

    def test_get_summary(self):
        s = self.orch.get_summary()
        assert s["retrieved"] is True
        assert s["total_models"] == 2
        assert s["auto_fallback"] is True

    def test_full_pipeline(self):
        # Route a task
        route = self.orch.route_task(
            task_text=(
                "Analyze and compare the performance "
                "of different sorting algorithms"
            ),
        )
        assert route["routed"] is True

        # Record completion
        comp = self.orch.record_completion(
            model_id=route["model_id"],
            provider="openai",
            input_tokens=200,
            output_tokens=500,
            latency_ms=2000,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06,
            quality_score=0.85,
        )
        assert comp["recorded"] is True

        # Check analytics
        analytics = self.orch.get_analytics()
        assert analytics["retrieved"] is True


# ============================================================
# LLMRouter Models Testleri
# ============================================================
class TestLLMRouterModels:
    """LLMRouter model testleri."""

    def test_model_status_enum(self):
        from app.models.llmrouter_models import ModelStatus
        assert ModelStatus.ACTIVE == "active"
        assert ModelStatus.INACTIVE == "inactive"
        assert ModelStatus.DEPRECATED == "deprecated"
        assert ModelStatus.MAINTENANCE == "maintenance"

    def test_health_state_enum(self):
        from app.models.llmrouter_models import HealthState
        assert HealthState.HEALTHY == "healthy"
        assert HealthState.DEGRADED == "degraded"
        assert HealthState.UNHEALTHY == "unhealthy"
        assert HealthState.UNKNOWN == "unknown"

    def test_circuit_state_enum(self):
        from app.models.llmrouter_models import CircuitState
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"

    def test_selection_strategy_enum(self):
        from app.models.llmrouter_models import SelectionStrategy
        assert len(SelectionStrategy) == 5

    def test_complexity_level_enum(self):
        from app.models.llmrouter_models import ComplexityLevel
        assert len(ComplexityLevel) == 5

    def test_reasoning_depth_enum(self):
        from app.models.llmrouter_models import ReasoningDepth
        assert len(ReasoningDepth) == 3

    def test_cache_strategy_enum(self):
        from app.models.llmrouter_models import CacheStrategy
        assert len(CacheStrategy) == 4

    def test_capability_enum(self):
        from app.models.llmrouter_models import ModelCapability
        assert len(ModelCapability) == 10

    def test_provider_record(self):
        from app.models.llmrouter_models import ProviderRecord
        p = ProviderRecord(
            provider_id="openai",
            name="OpenAI",
        )
        assert p.provider_id == "openai"

    def test_model_record(self):
        from app.models.llmrouter_models import ModelRecord
        m = ModelRecord(
            model_id="gpt-4",
            provider="openai",
        )
        assert m.model_id == "gpt-4"
        assert m.status == "active"

    def test_complexity_analysis(self):
        from app.models.llmrouter_models import ComplexityAnalysis
        c = ComplexityAnalysis(
            analysis_id="ca_1",
            complexity_score=0.7,
        )
        assert c.complexity_score == 0.7

    def test_model_selection(self):
        from app.models.llmrouter_models import ModelSelection
        s = ModelSelection(
            selection_id="sl_1",
            model_id="gpt-4",
        )
        assert s.model_id == "gpt-4"

    def test_route_result(self):
        from app.models.llmrouter_models import RouteResult
        r = RouteResult(
            request_id="rt_1",
            routed_to="gpt-4",
        )
        assert r.routed_to == "gpt-4"

    def test_usage_record(self):
        from app.models.llmrouter_models import UsageRecord
        u = UsageRecord(
            input_tokens=100,
            total_cost=0.003,
        )
        assert u.total_cost == 0.003

    def test_latency_record(self):
        from app.models.llmrouter_models import LatencyRecord
        l = LatencyRecord(
            latency_ms=150.0,
        )
        assert l.latency_ms == 150.0

    def test_performance_evaluation(self):
        from app.models.llmrouter_models import PerformanceEvaluation
        p = PerformanceEvaluation(
            overall_score=0.85,
        )
        assert p.overall_score == 0.85

    def test_ab_test_record(self):
        from app.models.llmrouter_models import ABTestRecord
        a = ABTestRecord(
            name="test",
            model_a="a",
            model_b="b",
        )
        assert a.status == "active"

    def test_health_check_record(self):
        from app.models.llmrouter_models import HealthCheckRecord
        h = HealthCheckRecord(
            provider_id="p1",
            is_available=True,
        )
        assert h.is_available is True

    def test_llmrouter_summary(self):
        from app.models.llmrouter_models import LLMRouterSummary
        s = LLMRouterSummary(
            total_models=5,
            total_cost=1.5,
        )
        assert s.total_models == 5


# ============================================================
# Config Testleri
# ============================================================
class TestLLMRouterConfig:
    """LLMRouter config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.llmrouter_enabled is True
        assert s.default_provider == "anthropic"
        assert s.cost_optimization is True
        assert s.auto_fallback is True
        assert s.latency_threshold_ms == 5000
