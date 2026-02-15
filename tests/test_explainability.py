"""ATLAS Decision Explainability Layer testleri."""

import unittest

from app.core.explainability.decision_recorder import (
    DecisionRecorder,
)
from app.core.explainability.reasoning_tracer import (
    ReasoningTracer,
)
from app.core.explainability.factor_analyzer import (
    FactorAnalyzer,
)
from app.core.explainability.natural_language_explainer import (
    NaturalLanguageExplainer,
)
from app.core.explainability.visual_explainer import (
    VisualExplainer,
)
from app.core.explainability.counterfactual_generator import (
    CounterfactualGenerator,
)
from app.core.explainability.audit_formatter import (
    AuditFormatter,
)
from app.core.explainability.explanation_cache import (
    ExplanationCache,
)
from app.core.explainability.explainability_orchestrator import (
    ExplainabilityOrchestrator,
)


# ==================== Models ====================

class TestExplainabilityModels(unittest.TestCase):
    """Explainability model testleri."""

    def test_explanation_depth_enum(self):
        from app.models.explainability_models import (
            ExplanationDepth,
        )
        self.assertEqual(
            ExplanationDepth.BRIEF, "brief",
        )
        self.assertEqual(
            ExplanationDepth.STANDARD,
            "standard",
        )
        self.assertEqual(
            ExplanationDepth.DETAILED,
            "detailed",
        )
        self.assertEqual(
            ExplanationDepth.TECHNICAL,
            "technical",
        )
        self.assertEqual(
            ExplanationDepth.FULL, "full",
        )

    def test_explanation_audience_enum(self):
        from app.models.explainability_models import (
            ExplanationAudience,
        )
        self.assertEqual(
            ExplanationAudience.TECHNICAL,
            "technical",
        )
        self.assertEqual(
            ExplanationAudience.EXECUTIVE,
            "executive",
        )
        self.assertEqual(
            ExplanationAudience.LEGAL,
            "legal",
        )
        self.assertEqual(
            ExplanationAudience.END_USER,
            "end_user",
        )
        self.assertEqual(
            ExplanationAudience.AUDITOR,
            "auditor",
        )

    def test_reasoning_type_enum(self):
        from app.models.explainability_models import (
            ReasoningType,
        )
        self.assertEqual(
            ReasoningType.DEDUCTIVE,
            "deductive",
        )
        self.assertEqual(
            ReasoningType.INDUCTIVE,
            "inductive",
        )
        self.assertEqual(
            ReasoningType.PROBABILISTIC,
            "probabilistic",
        )

    def test_factor_influence_enum(self):
        from app.models.explainability_models import (
            FactorInfluence,
        )
        self.assertEqual(
            FactorInfluence.POSITIVE,
            "positive",
        )
        self.assertEqual(
            FactorInfluence.NEGATIVE,
            "negative",
        )
        self.assertEqual(
            FactorInfluence.CRITICAL,
            "critical",
        )

    def test_audit_format_enum(self):
        from app.models.explainability_models import (
            AuditFormat,
        )
        self.assertEqual(
            AuditFormat.COMPLIANCE,
            "compliance",
        )
        self.assertEqual(
            AuditFormat.LEGAL, "legal",
        )
        self.assertEqual(
            AuditFormat.CUSTOM, "custom",
        )

    def test_cache_strategy_enum(self):
        from app.models.explainability_models import (
            CacheStrategy,
        )
        self.assertEqual(
            CacheStrategy.ALWAYS, "always",
        )
        self.assertEqual(
            CacheStrategy.ON_DEMAND,
            "on_demand",
        )
        self.assertEqual(
            CacheStrategy.TTL, "ttl",
        )

    def test_explanation_record(self):
        from app.models.explainability_models import (
            ExplanationRecord,
        )
        r = ExplanationRecord(
            decision_id="d1",
            summary="Test summary",
        )
        self.assertEqual(r.decision_id, "d1")
        self.assertEqual(
            r.summary, "Test summary",
        )
        self.assertTrue(len(r.explanation_id) > 0)

    def test_reasoning_step(self):
        from app.models.explainability_models import (
            ReasoningStep,
        )
        s = ReasoningStep(
            decision_id="d1",
            step_number=1,
            description="Step 1",
        )
        self.assertEqual(s.decision_id, "d1")
        self.assertEqual(s.step_number, 1)

    def test_factor_record(self):
        from app.models.explainability_models import (
            FactorRecord,
        )
        f = FactorRecord(
            name="cost",
            weight=0.5,
        )
        self.assertEqual(f.name, "cost")
        self.assertEqual(f.weight, 0.5)

    def test_explainability_snapshot(self):
        from app.models.explainability_models import (
            ExplainabilitySnapshot,
        )
        s = ExplainabilitySnapshot(
            total_explanations=10,
            decisions_explained=5,
        )
        self.assertEqual(
            s.total_explanations, 10,
        )
        self.assertEqual(
            s.decisions_explained, 5,
        )


# ==================== DecisionRecorder ====================

class TestDecisionRecorder(unittest.TestCase):
    """DecisionRecorder testleri."""

    def setUp(self):
        self.rec = DecisionRecorder()

    def test_record_decision(self):
        r = self.rec.record_decision(
            "d1", decision_type="api_call",
        )
        self.assertTrue(r["recorded"])
        self.assertEqual(
            r["decision_id"], "d1",
        )

    def test_capture_context(self):
        self.rec.record_decision("d1")
        r = self.rec.capture_context(
            "d1", {"env": "prod", "user": "admin"},
        )
        self.assertTrue(r["context_captured"])
        self.assertEqual(r["fields"], 2)

    def test_capture_context_not_found(self):
        r = self.rec.capture_context(
            "x", {"a": 1},
        )
        self.assertIn("error", r)

    def test_log_inputs(self):
        self.rec.record_decision("d1")
        r = self.rec.log_inputs(
            "d1", {"param1": 42, "param2": "x"},
        )
        self.assertTrue(r["inputs_logged"])
        self.assertEqual(r["input_count"], 2)

    def test_log_inputs_not_found(self):
        r = self.rec.log_inputs(
            "x", {"a": 1},
        )
        self.assertIn("error", r)

    def test_log_alternatives(self):
        self.rec.record_decision("d1")
        alts = [
            {"name": "A", "score": 0.8},
            {"name": "B", "score": 0.6},
        ]
        r = self.rec.log_alternatives(
            "d1", alts,
        )
        self.assertTrue(
            r["alternatives_logged"],
        )
        self.assertEqual(r["count"], 2)

    def test_log_alternatives_not_found(self):
        r = self.rec.log_alternatives(
            "x", [],
        )
        self.assertIn("error", r)

    def test_log_factors(self):
        self.rec.record_decision("d1")
        factors = [
            {"name": "cost", "weight": 0.5},
            {"name": "speed", "weight": 0.3},
        ]
        r = self.rec.log_factors("d1", factors)
        self.assertTrue(r["factors_logged"])
        self.assertEqual(r["count"], 2)

    def test_log_factors_not_found(self):
        r = self.rec.log_factors("x", [])
        self.assertIn("error", r)

    def test_record_outcome(self):
        self.rec.record_decision("d1")
        r = self.rec.record_outcome(
            "d1", "approved",
            confidence=0.9,
            rationale="Low risk",
        )
        self.assertTrue(r["outcome_recorded"])
        self.assertEqual(r["confidence"], 0.9)

    def test_record_outcome_not_found(self):
        r = self.rec.record_outcome(
            "x", "ok",
        )
        self.assertIn("error", r)

    def test_get_decision(self):
        self.rec.record_decision(
            "d1", description="Test",
        )
        self.rec.capture_context(
            "d1", {"env": "dev"},
        )
        d = self.rec.get_decision("d1")
        self.assertEqual(
            d["decision_id"], "d1",
        )
        self.assertIn("context", d)

    def test_get_decision_not_found(self):
        d = self.rec.get_decision("x")
        self.assertIn("error", d)

    def test_get_decisions(self):
        self.rec.record_decision(
            "d1", system="api",
        )
        self.rec.record_decision(
            "d2", system="db",
        )
        self.rec.record_decision(
            "d3", system="api",
        )
        all_d = self.rec.get_decisions()
        self.assertEqual(len(all_d), 3)

        api_d = self.rec.get_decisions(
            system="api",
        )
        self.assertEqual(len(api_d), 2)

    def test_decision_count(self):
        self.assertEqual(
            self.rec.decision_count, 0,
        )
        self.rec.record_decision("d1")
        self.assertEqual(
            self.rec.decision_count, 1,
        )

    def test_recorded_count(self):
        self.rec.record_decision("d1")
        self.rec.record_decision("d2")
        self.assertEqual(
            self.rec.recorded_count, 2,
        )


# ==================== ReasoningTracer ====================

class TestReasoningTracer(unittest.TestCase):
    """ReasoningTracer testleri."""

    def setUp(self):
        self.tracer = ReasoningTracer()

    def test_start_trace(self):
        r = self.tracer.start_trace(
            "d1", reasoning_type="deductive",
        )
        self.assertTrue(r["trace_started"])

    def test_add_step(self):
        self.tracer.start_trace("d1")
        r = self.tracer.add_step(
            "d1", "analysis",
            "Analyze inputs",
            output="valid",
        )
        self.assertTrue(r["added"])
        self.assertEqual(r["step_number"], 1)

    def test_add_step_not_found(self):
        r = self.tracer.add_step(
            "x", "test", "desc",
        )
        self.assertIn("error", r)

    def test_add_multiple_steps(self):
        self.tracer.start_trace("d1")
        self.tracer.add_step(
            "d1", "step1", "First",
        )
        r = self.tracer.add_step(
            "d1", "step2", "Second",
        )
        self.assertEqual(r["step_number"], 2)

    def test_add_inference(self):
        self.tracer.start_trace("d1")
        r = self.tracer.add_inference(
            "d1",
            premise="If A then B",
            conclusion="B is true",
            rule="modus_ponens",
        )
        self.assertTrue(r["added"])

    def test_add_rule_application(self):
        self.tracer.start_trace("d1")
        r = self.tracer.add_rule_application(
            "d1",
            rule_name="threshold_check",
            conditions={"value": 85},
            result="above_threshold",
        )
        self.assertTrue(r["added"])

    def test_add_model_output(self):
        self.tracer.start_trace("d1")
        r = self.tracer.add_model_output(
            "d1",
            model_name="classifier",
            input_data={"features": [1, 2]},
            output="positive",
            confidence=0.92,
        )
        self.assertTrue(r["added"])

    def test_complete_trace(self):
        self.tracer.start_trace("d1")
        self.tracer.add_step(
            "d1", "s1", "Step 1",
        )
        r = self.tracer.complete_trace(
            "d1", conclusion="Decision made",
        )
        self.assertTrue(r["completed"])
        self.assertEqual(r["steps"], 1)
        self.assertEqual(
            r["conclusion"], "Decision made",
        )

    def test_complete_trace_not_found(self):
        r = self.tracer.complete_trace("x")
        self.assertIn("error", r)

    def test_get_trace(self):
        self.tracer.start_trace("d1")
        self.tracer.add_step(
            "d1", "s1", "Step 1",
        )
        self.tracer.add_step(
            "d1", "s2", "Step 2",
        )
        t = self.tracer.get_trace("d1")
        self.assertEqual(
            t["decision_id"], "d1",
        )
        self.assertEqual(t["step_count"], 2)

    def test_get_trace_not_found(self):
        t = self.tracer.get_trace("x")
        self.assertIn("error", t)

    def test_get_logic_chain(self):
        self.tracer.start_trace("d1")
        self.tracer.add_step(
            "d1", "s1", "Analyze data",
        )
        self.tracer.add_step(
            "d1", "s2", "Apply rule",
        )
        self.tracer.add_step(
            "d1", "s3", "Make decision",
        )
        chain = self.tracer.get_logic_chain(
            "d1",
        )
        self.assertEqual(len(chain), 3)
        self.assertEqual(
            chain[0], "Analyze data",
        )

    def test_trace_count(self):
        self.tracer.start_trace("d1")
        self.tracer.start_trace("d2")
        self.assertEqual(
            self.tracer.trace_count, 2,
        )

    def test_total_steps(self):
        self.tracer.start_trace("d1")
        self.tracer.add_step(
            "d1", "s1", "Step 1",
        )
        self.tracer.add_step(
            "d1", "s2", "Step 2",
        )
        self.assertEqual(
            self.tracer.total_steps, 2,
        )


# ==================== FactorAnalyzer ====================

class TestFactorAnalyzer(unittest.TestCase):
    """FactorAnalyzer testleri."""

    def setUp(self):
        self.analyzer = FactorAnalyzer()
        self.factors = [
            {"name": "cost", "value": 0.8,
             "weight": 0.5},
            {"name": "speed", "value": 0.6,
             "weight": 0.3},
            {"name": "quality", "value": 0.9,
             "weight": 0.2},
        ]

    def test_analyze_factors(self):
        r = self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        self.assertEqual(
            r["decision_id"], "d1",
        )
        self.assertEqual(len(r["factors"]), 3)
        self.assertIn("key_factors", r)

    def test_analyze_factors_empty(self):
        r = self.analyzer.analyze_factors(
            "d1", [],
        )
        self.assertEqual(
            len(r["factors"]), 0,
        )

    def test_factor_contributions(self):
        r = self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        for f in r["factors"]:
            self.assertIn("contribution", f)
            self.assertIn("weight_pct", f)
            self.assertIn("influence", f)

    def test_get_key_factors(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        kf = self.analyzer.get_key_factors(
            "d1", top_n=2,
        )
        self.assertLessEqual(len(kf), 2)

    def test_get_key_factors_empty(self):
        kf = self.analyzer.get_key_factors(
            "x",
        )
        self.assertEqual(len(kf), 0)

    def test_calculate_weights(self):
        r = self.analyzer.calculate_weights(
            self.factors,
        )
        self.assertIn("weights", r)
        self.assertEqual(
            r["factor_count"], 3,
        )
        total_pct = sum(
            r["weights"].values(),
        )
        self.assertAlmostEqual(
            total_pct, 100.0, places=0,
        )

    def test_contribution_analysis(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        r = self.analyzer.contribution_analysis(
            "d1",
        )
        self.assertIn("contributions", r)
        self.assertEqual(
            r["factor_count"], 3,
        )

    def test_contribution_analysis_empty(self):
        r = self.analyzer.contribution_analysis(
            "x",
        )
        self.assertEqual(
            len(r["contributions"]), 0,
        )

    def test_sensitivity_analysis(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        r = self.analyzer.sensitivity_analysis(
            "d1", "cost",
        )
        self.assertEqual(
            r["factor"], "cost",
        )
        self.assertIn("sensitivity", r)
        self.assertIn("is_sensitive", r)

    def test_sensitivity_custom_variations(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        r = self.analyzer.sensitivity_analysis(
            "d1", "cost",
            variations=[-0.1, 0.0, 0.1],
        )
        self.assertEqual(
            len(r["sensitivity"]), 3,
        )

    def test_sensitivity_not_found(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        r = self.analyzer.sensitivity_analysis(
            "d1", "nonexistent",
        )
        self.assertIn("error", r)

    def test_counterfactual_factors(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        r = self.analyzer.counterfactual_factors(
            "d1",
        )
        self.assertIn("changes_needed", r)

    def test_counterfactual_empty(self):
        r = self.analyzer.counterfactual_factors(
            "x",
        )
        self.assertEqual(
            len(r["changes_needed"]), 0,
        )

    def test_analysis_count(self):
        self.analyzer.analyze_factors(
            "d1", self.factors,
        )
        self.assertEqual(
            self.analyzer.analysis_count, 1,
        )


# ==================== NaturalLanguageExplainer ====================

class TestNaturalLanguageExplainer(
    unittest.TestCase,
):
    """NaturalLanguageExplainer testleri."""

    def setUp(self):
        self.explainer = (
            NaturalLanguageExplainer()
        )

    def test_explain_decision_en(self):
        r = self.explainer.explain_decision(
            "d1", "Deploy",
            "all checks passed",
        )
        self.assertIn("Deploy", r["text"])
        self.assertIn("all checks", r["text"])
        self.assertEqual(r["language"], "en")

    def test_explain_decision_tr(self):
        r = self.explainer.explain_decision(
            "d1", "Deploy",
            "tum kontroller gecti",
            language="tr",
        )
        self.assertEqual(r["language"], "tr")
        self.assertIn("Deploy", r["text"])

    def test_explain_factors(self):
        factors = [
            {"name": "cost",
             "weight_pct": 50.0},
            {"name": "speed",
             "weight_pct": 30.0},
        ]
        r = self.explainer.explain_factors(
            "d1", factors,
        )
        self.assertEqual(r["type"], "factors")
        self.assertEqual(len(r["texts"]), 2)

    def test_explain_alternative(self):
        r = self.explainer.explain_alternative(
            "d1", "Option B",
            "higher cost",
        )
        self.assertIn(
            "Option B", r["text"],
        )

    def test_explain_outcome(self):
        r = self.explainer.explain_outcome(
            "d1", "approved", 95.0,
        )
        self.assertIn("approved", r["text"])
        self.assertIn("95", r["text"])

    def test_explain_outcome_tr(self):
        r = self.explainer.explain_outcome(
            "d1", "onaylandi", 90.0,
            language="tr",
        )
        self.assertEqual(r["language"], "tr")

    def test_add_template(self):
        r = self.explainer.add_template(
            "custom", "en",
            "Custom: {decision}",
        )
        self.assertTrue(r["added"])

    def test_generate_summary(self):
        data = {
            "description": "Deploy v2",
            "factors": [
                {"name": "cost"},
                {"name": "risk"},
            ],
            "outcome": {
                "result": "approved",
                "confidence": 95,
            },
        }
        r = self.explainer.generate_summary(
            "d1", data,
        )
        self.assertEqual(r["type"], "summary")
        self.assertTrue(len(r["text"]) > 0)

    def test_generate_summary_executive(self):
        data = {
            "description": "Budget decision",
            "factors": [{"name": "cost"}],
            "outcome": {
                "result": "ok",
                "confidence": 80,
            },
        }
        r = self.explainer.generate_summary(
            "d1", data,
            audience="executive",
        )
        self.assertEqual(
            r["audience"], "executive",
        )

    def test_generate_summary_end_user(self):
        data = {
            "description": "Simple action",
        }
        r = self.explainer.generate_summary(
            "d1", data,
            audience="end_user",
        )
        self.assertEqual(
            r["audience"], "end_user",
        )

    def test_generate_summary_tr(self):
        data = {
            "description": "Karar",
            "factors": [{"name": "maliyet"}],
            "outcome": {
                "result": "onaylandi",
                "confidence": 90,
            },
        }
        r = self.explainer.generate_summary(
            "d1", data, language="tr",
        )
        self.assertEqual(r["language"], "tr")

    def test_get_explanations(self):
        self.explainer.explain_decision(
            "d1", "Test", "reason",
        )
        self.explainer.explain_decision(
            "d2", "Test2", "reason2",
        )
        exps = self.explainer.get_explanations()
        self.assertEqual(len(exps), 2)

    def test_get_explanations_filtered(self):
        self.explainer.explain_decision(
            "d1", "Test", "reason",
        )
        self.explainer.explain_decision(
            "d2", "Test2", "reason2",
        )
        exps = self.explainer.get_explanations(
            decision_id="d1",
        )
        self.assertEqual(len(exps), 1)

    def test_explanation_count(self):
        self.explainer.explain_decision(
            "d1", "T", "r",
        )
        self.assertEqual(
            self.explainer.explanation_count, 1,
        )

    def test_supported_languages(self):
        langs = (
            self.explainer.supported_languages
        )
        self.assertIn("en", langs)
        self.assertIn("tr", langs)


# ==================== VisualExplainer ====================

class TestVisualExplainer(unittest.TestCase):
    """VisualExplainer testleri."""

    def setUp(self):
        self.visual = VisualExplainer()

    def test_generate_decision_tree(self):
        steps = [
            {"description": "Start",
             "step_type": "start"},
            {"description": "Check",
             "step_type": "check",
             "output": "ok"},
            {"description": "End",
             "step_type": "end"},
        ]
        r = self.visual.generate_decision_tree(
            "d1", steps,
        )
        self.assertEqual(
            r["type"], "decision_tree",
        )
        self.assertEqual(
            r["node_count"], 3,
        )
        self.assertEqual(len(r["edges"]), 2)

    def test_generate_factor_chart(self):
        factors = [
            {"name": "cost",
             "contribution": 0.5,
             "weight": 0.5},
            {"name": "risk",
             "contribution": -0.3,
             "weight": 0.3},
        ]
        r = self.visual.generate_factor_chart(
            "d1", factors,
        )
        self.assertEqual(
            r["type"], "factor_chart",
        )
        self.assertEqual(r["bar_count"], 2)

    def test_factor_chart_colors(self):
        factors = [
            {"name": "pos",
             "contribution": 0.5},
            {"name": "neg",
             "contribution": -0.3},
        ]
        r = self.visual.generate_factor_chart(
            "d1", factors,
        )
        colors = [b["color"] for b in r["bars"]]
        self.assertIn("green", colors)
        self.assertIn("red", colors)

    def test_generate_timeline(self):
        events = [
            {"description": "Started",
             "timestamp": 100.0,
             "type": "start"},
            {"description": "Completed",
             "timestamp": 105.0,
             "type": "end"},
        ]
        r = self.visual.generate_timeline(
            "d1", events,
        )
        self.assertEqual(
            r["type"], "timeline",
        )
        self.assertEqual(
            r["event_count"], 2,
        )
        self.assertEqual(
            r["duration_seconds"], 5.0,
        )

    def test_timeline_single_event(self):
        r = self.visual.generate_timeline(
            "d1",
            [{"description": "E1",
              "timestamp": 100}],
        )
        self.assertEqual(
            r["duration_seconds"], 0.0,
        )

    def test_generate_comparison(self):
        alts = [
            {"name": "A", "cost": 10,
             "speed": 5},
            {"name": "B", "cost": 15,
             "speed": 8},
        ]
        r = self.visual.generate_comparison(
            "d1", alts,
        )
        self.assertEqual(
            r["type"], "comparison",
        )
        self.assertEqual(r["count"], 2)
        self.assertIn("cost", r["criteria"])

    def test_comparison_custom_criteria(self):
        alts = [
            {"name": "A", "cost": 10,
             "speed": 5},
        ]
        r = self.visual.generate_comparison(
            "d1", alts,
            criteria=["cost"],
        )
        self.assertEqual(
            r["criteria"], ["cost"],
        )

    def test_generate_impact_map(self):
        impacts = [
            {"area": "budget",
             "magnitude": 0.5,
             "direction": "negative"},
            {"area": "quality",
             "magnitude": 0.8,
             "direction": "positive"},
        ]
        r = self.visual.generate_impact_map(
            "d1", impacts,
        )
        self.assertEqual(
            r["type"], "impact_map",
        )
        self.assertEqual(
            r["node_count"], 2,
        )

    def test_get_visuals(self):
        self.visual.generate_factor_chart(
            "d1", [{"name": "a",
                     "contribution": 0.5}],
        )
        self.visual.generate_timeline(
            "d2", [{"description": "e",
                     "timestamp": 1}],
        )
        all_v = self.visual.get_visuals()
        self.assertEqual(len(all_v), 2)

    def test_get_visuals_filtered(self):
        self.visual.generate_factor_chart(
            "d1", [{"name": "a",
                     "contribution": 0.5}],
        )
        self.visual.generate_timeline(
            "d1", [{"description": "e",
                     "timestamp": 1}],
        )
        v = self.visual.get_visuals(
            visual_type="timeline",
        )
        self.assertEqual(len(v), 1)

    def test_visual_count(self):
        self.visual.generate_factor_chart(
            "d1", [],
        )
        self.assertEqual(
            self.visual.visual_count, 1,
        )


# ==================== CounterfactualGenerator ====================

class TestCounterfactualGenerator(
    unittest.TestCase,
):
    """CounterfactualGenerator testleri."""

    def setUp(self):
        self.gen = CounterfactualGenerator()
        self.factors = [
            {"name": "cost", "value": 0.8,
             "weight": 0.5},
            {"name": "speed", "value": 0.6,
             "weight": 0.3},
            {"name": "quality", "value": 0.9,
             "weight": 0.2},
        ]

    def test_generate_what_if(self):
        r = self.gen.generate_what_if(
            "d1", "cost", 0.8, 0.3,
            self.factors,
        )
        self.assertEqual(
            r["type"], "what_if",
        )
        self.assertEqual(r["factor"], "cost")
        self.assertIn("outcome_change", r)

    def test_what_if_better(self):
        r = self.gen.generate_what_if(
            "d1", "cost", 0.8, 1.5,
            self.factors,
        )
        self.assertEqual(
            r["outcome_change"], "better",
        )

    def test_what_if_worse(self):
        r = self.gen.generate_what_if(
            "d1", "cost", 0.8, 0.1,
            self.factors,
        )
        self.assertEqual(
            r["outcome_change"], "worse",
        )

    def test_what_if_same(self):
        r = self.gen.generate_what_if(
            "d1", "cost", 0.8, 0.8,
            self.factors,
        )
        self.assertEqual(
            r["outcome_change"], "same",
        )

    def test_find_minimal_change(self):
        r = self.gen.find_minimal_change(
            "d1", self.factors,
        )
        self.assertIn("changes", r)
        self.assertIn("minimal_change", r)
        self.assertTrue(len(r["changes"]) > 0)

    def test_find_minimal_change_empty(self):
        r = self.gen.find_minimal_change(
            "d1", [],
        )
        self.assertEqual(
            len(r["changes"]), 0,
        )

    def test_generate_alternatives(self):
        r = self.gen.generate_alternatives(
            "d1", self.factors,
            num_alternatives=3,
        )
        self.assertEqual(r["count"], 3)
        for alt in r["alternatives"]:
            self.assertIn("score", alt)

    def test_sensitivity_bounds(self):
        r = self.gen.sensitivity_bounds(
            "d1", "cost", self.factors,
        )
        self.assertEqual(r["factor"], "cost")
        self.assertIn("lower_bound", r)
        self.assertIn("upper_bound", r)
        self.assertIn("sensitivity", r)

    def test_sensitivity_bounds_not_found(self):
        r = self.gen.sensitivity_bounds(
            "d1", "nonexistent",
            self.factors,
        )
        self.assertIn("error", r)

    def test_sensitivity_bounds_zero(self):
        factors = [
            {"name": "x", "value": 0.0,
             "weight": 1.0},
        ]
        r = self.gen.sensitivity_bounds(
            "d1", "x", factors,
        )
        self.assertEqual(
            r["lower_bound"], -1.0,
        )
        self.assertEqual(
            r["upper_bound"], 1.0,
        )

    def test_actionable_insights(self):
        r = self.gen.actionable_insights(
            "d1", self.factors,
        )
        self.assertEqual(r["target"], "improve")
        self.assertTrue(len(r["insights"]) > 0)

    def test_actionable_insights_maintain(self):
        r = self.gen.actionable_insights(
            "d1", self.factors,
            target="maintain",
        )
        self.assertEqual(
            r["target"], "maintain",
        )
        for i in r["insights"]:
            self.assertEqual(
                i["action"], "monitor",
            )

    def test_get_counterfactuals(self):
        self.gen.generate_what_if(
            "d1", "cost", 0.8, 0.5,
            self.factors,
        )
        cfs = self.gen.get_counterfactuals(
            "d1",
        )
        self.assertEqual(len(cfs), 1)

    def test_get_counterfactuals_empty(self):
        cfs = self.gen.get_counterfactuals(
            "x",
        )
        self.assertEqual(len(cfs), 0)

    def test_generated_count(self):
        self.gen.generate_what_if(
            "d1", "cost", 0.8, 0.5,
            self.factors,
        )
        self.gen.find_minimal_change(
            "d1", self.factors,
        )
        self.assertEqual(
            self.gen.generated_count, 2,
        )


# ==================== AuditFormatter ====================

class TestAuditFormatter(unittest.TestCase):
    """AuditFormatter testleri."""

    def setUp(self):
        self.fmt = AuditFormatter()
        self.decision_data = {
            "decision_type": "deploy",
            "description": "Deploy v2",
            "recorded_at": 1000.0,
            "inputs": {"version": "2.0"},
            "factors": [
                {"name": "cost",
                 "weight": 0.5,
                 "contribution": 0.3},
            ],
            "alternatives": [
                {"name": "rollback"},
            ],
            "outcome": {
                "result": "approved",
                "confidence": 95,
                "rationale": "All checks ok",
            },
        }

    def test_format_compliance(self):
        r = self.fmt.format_compliance(
            "d1", self.decision_data,
        )
        self.assertEqual(
            r["format"], "compliance",
        )
        self.assertTrue(
            r["section_count"] >= 3,
        )

    def test_format_compliance_standard(self):
        r = self.fmt.format_compliance(
            "d1", self.decision_data,
            standard="iso27001",
        )
        self.assertEqual(
            r["standard"], "iso27001",
        )

    def test_format_legal(self):
        r = self.fmt.format_legal(
            "d1", self.decision_data,
        )
        self.assertEqual(
            r["format"], "legal",
        )
        sections = [
            s["section"]
            for s in r["sections"]
        ]
        self.assertIn("Matter", sections)
        self.assertIn("Rationale", sections)
        self.assertIn("Conclusion", sections)

    def test_format_legal_jurisdiction(self):
        r = self.fmt.format_legal(
            "d1", self.decision_data,
            jurisdiction="eu",
        )
        self.assertEqual(
            r["jurisdiction"], "eu",
        )

    def test_format_technical(self):
        r = self.fmt.format_technical(
            "d1", self.decision_data,
        )
        self.assertEqual(
            r["format"], "technical",
        )

    def test_format_technical_with_trace(self):
        trace = {
            "steps": [
                {"description": "Step 1"},
            ],
        }
        r = self.fmt.format_technical(
            "d1", self.decision_data,
            trace=trace,
        )
        sections = [
            s["section"]
            for s in r["sections"]
        ]
        self.assertIn(
            "Reasoning Trace", sections,
        )

    def test_format_executive(self):
        r = self.fmt.format_executive(
            "d1", self.decision_data,
        )
        self.assertEqual(
            r["format"], "executive",
        )
        self.assertEqual(
            r["decision"], "approved",
        )
        self.assertEqual(
            r["confidence"], 95,
        )
        self.assertIn("key_factors", r)

    def test_add_template(self):
        r = self.fmt.add_template(
            "custom1",
            ["Overview", "Details"],
        )
        self.assertTrue(r["added"])
        self.assertEqual(r["sections"], 2)

    def test_format_custom(self):
        self.fmt.add_template(
            "my_template",
            ["Inputs", "Outcome"],
        )
        r = self.fmt.format_custom(
            "d1", self.decision_data,
            "my_template",
        )
        self.assertEqual(
            r["format"], "custom",
        )
        self.assertEqual(
            r["section_count"], 2,
        )

    def test_format_custom_not_found(self):
        r = self.fmt.format_custom(
            "d1", {}, "nonexistent",
        )
        self.assertIn("error", r)

    def test_get_formatted(self):
        self.fmt.format_compliance(
            "d1", self.decision_data,
        )
        self.fmt.format_legal(
            "d2", self.decision_data,
        )
        all_f = self.fmt.get_formatted()
        self.assertEqual(len(all_f), 2)

    def test_get_formatted_filtered(self):
        self.fmt.format_compliance(
            "d1", self.decision_data,
        )
        self.fmt.format_legal(
            "d2", self.decision_data,
        )
        f = self.fmt.get_formatted(
            format_type="legal",
        )
        self.assertEqual(len(f), 1)

    def test_format_count(self):
        self.fmt.format_executive(
            "d1", self.decision_data,
        )
        self.assertEqual(
            self.fmt.format_count, 1,
        )


# ==================== ExplanationCache ====================

class TestExplanationCache(unittest.TestCase):
    """ExplanationCache testleri."""

    def setUp(self):
        self.cache = ExplanationCache(
            default_ttl=3600,
            max_size=100,
        )

    def test_set_and_get(self):
        self.cache.set(
            "k1", {"text": "explanation"},
        )
        r = self.cache.get("k1")
        self.assertIsNotNone(r)
        self.assertEqual(
            r["text"], "explanation",
        )

    def test_get_miss(self):
        r = self.cache.get("nonexistent")
        self.assertIsNone(r)

    def test_invalidate(self):
        self.cache.set(
            "k1", {"text": "test"},
        )
        r = self.cache.invalidate("k1")
        self.assertTrue(r["invalidated"])
        self.assertIsNone(
            self.cache.get("k1"),
        )

    def test_invalidate_not_found(self):
        r = self.cache.invalidate("x")
        self.assertFalse(r["invalidated"])

    def test_invalidate_pattern(self):
        self.cache.set(
            "explain_d1_basic", {"a": 1},
        )
        self.cache.set(
            "explain_d1_detail", {"a": 2},
        )
        self.cache.set(
            "explain_d2_basic", {"a": 3},
        )
        r = self.cache.invalidate_pattern(
            "d1",
        )
        self.assertEqual(r["invalidated"], 2)

    def test_update(self):
        self.cache.set(
            "k1", {"text": "old"},
        )
        r = self.cache.update(
            "k1", {"text": "new"},
        )
        self.assertTrue(r["updated"])
        data = self.cache.get("k1")
        self.assertEqual(data["text"], "new")

    def test_update_not_found(self):
        r = self.cache.update(
            "x", {"a": 1},
        )
        self.assertFalse(r["updated"])

    def test_register_pattern(self):
        r = self.cache.register_pattern(
            "decision",
            "explain_{id}_{depth}",
        )
        self.assertTrue(r["registered"])

    def test_get_by_pattern(self):
        self.cache.register_pattern(
            "decision",
            "explain_{id}_{depth}",
        )
        self.cache.set(
            "explain_d1_basic",
            {"text": "cached"},
        )
        r = self.cache.get_by_pattern(
            "decision",
            id="d1",
            depth="basic",
        )
        self.assertIsNotNone(r)
        self.assertEqual(r["text"], "cached")

    def test_get_by_pattern_miss(self):
        r = self.cache.get_by_pattern(
            "nonexistent",
        )
        self.assertIsNone(r)

    def test_eviction(self):
        small_cache = ExplanationCache(
            max_size=2,
        )
        small_cache.set("k1", {"a": 1})
        small_cache.set("k2", {"a": 2})
        small_cache.set("k3", {"a": 3})
        self.assertEqual(small_cache.size, 2)

    def test_clear(self):
        self.cache.set("k1", {"a": 1})
        self.cache.set("k2", {"a": 2})
        r = self.cache.clear()
        self.assertEqual(r["cleared"], 2)
        self.assertEqual(self.cache.size, 0)

    def test_get_stats(self):
        self.cache.set("k1", {"a": 1})
        self.cache.get("k1")
        self.cache.get("miss")
        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(
            stats["hit_rate"], 50.0,
        )

    def test_size(self):
        self.assertEqual(self.cache.size, 0)
        self.cache.set("k1", {"a": 1})
        self.assertEqual(self.cache.size, 1)

    def test_hit_rate_empty(self):
        self.assertEqual(
            self.cache.hit_rate, 0.0,
        )

    def test_hit_rate(self):
        self.cache.set("k1", {"a": 1})
        self.cache.get("k1")
        self.cache.get("k1")
        self.cache.get("miss")
        self.assertGreater(
            self.cache.hit_rate, 0,
        )

    def test_ttl_custom(self):
        self.cache.set(
            "k1", {"a": 1}, ttl=10,
        )
        r = self.cache.get("k1")
        self.assertIsNotNone(r)


# ==================== ExplainabilityOrchestrator ====================

class TestExplainabilityOrchestrator(
    unittest.TestCase,
):
    """ExplainabilityOrchestrator testleri."""

    def setUp(self):
        self.orch = (
            ExplainabilityOrchestrator()
        )
        self.decision_data = {
            "decision_type": "deploy",
            "description": "Deploy v2",
            "system": "api",
            "inputs": {"version": "2.0"},
            "factors": [
                {"name": "cost",
                 "value": 0.8,
                 "weight": 0.5},
                {"name": "risk",
                 "value": 0.2,
                 "weight": 0.3},
            ],
            "outcome": {
                "result": "approved",
                "confidence": 95,
                "rationale": "Low risk",
            },
        }

    def test_init(self):
        self.assertIsNotNone(
            self.orch.recorder,
        )
        self.assertIsNotNone(
            self.orch.tracer,
        )
        self.assertIsNotNone(
            self.orch.factor_analyzer,
        )
        self.assertIsNotNone(
            self.orch.nl_explainer,
        )
        self.assertIsNotNone(
            self.orch.visual,
        )
        self.assertIsNotNone(
            self.orch.counterfactual,
        )
        self.assertIsNotNone(
            self.orch.formatter,
        )
        self.assertIsNotNone(
            self.orch.cache,
        )

    def test_explain_decision(self):
        r = self.orch.explain_decision(
            "d1", self.decision_data,
        )
        self.assertEqual(
            r["decision_id"], "d1",
        )
        self.assertIn("explanation", r)
        self.assertIn("factors", r)

    def test_explain_decision_detailed(self):
        r = self.orch.explain_decision(
            "d1", self.decision_data,
            depth="detailed",
        )
        self.assertIn("counterfactual", r)

    def test_explain_decision_cached(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        r = self.orch.explain_decision(
            "d1", self.decision_data,
        )
        self.assertIn("explanation", r)

    def test_explain_no_cache(self):
        orch = ExplainabilityOrchestrator(
            cache_enabled=False,
        )
        r = orch.explain_decision(
            "d1", self.decision_data,
        )
        self.assertIn("explanation", r)

    def test_explain_no_counterfactuals(self):
        orch = ExplainabilityOrchestrator(
            include_counterfactuals=False,
        )
        r = orch.explain_decision(
            "d1", self.decision_data,
            depth="detailed",
        )
        self.assertNotIn(
            "counterfactual", r,
        )

    def test_explain_no_factors(self):
        data = {
            "description": "Simple",
            "outcome": {
                "result": "ok",
                "confidence": 90,
            },
        }
        r = self.orch.explain_decision(
            "d1", data,
        )
        self.assertEqual(
            r["factors"], {},
        )

    def test_get_reasoning_trace(self):
        t = self.orch.get_reasoning_trace(
            "d1",
        )
        self.assertIn("error", t)

    def test_get_audit_report(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        r = self.orch.get_audit_report("d1")
        self.assertEqual(
            r["format"], "compliance",
        )

    def test_get_audit_report_legal(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        r = self.orch.get_audit_report(
            "d1", format_type="legal",
        )
        self.assertEqual(
            r["format"], "legal",
        )

    def test_get_audit_report_executive(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        r = self.orch.get_audit_report(
            "d1", format_type="executive",
        )
        self.assertEqual(
            r["format"], "executive",
        )

    def test_get_audit_report_technical(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        r = self.orch.get_audit_report(
            "d1", format_type="technical",
        )
        self.assertEqual(
            r["format"], "technical",
        )

    def test_get_audit_report_not_found(self):
        r = self.orch.get_audit_report("x")
        self.assertIn("error", r)

    def test_get_status(self):
        s = self.orch.get_status()
        self.assertIn(
            "decisions_recorded", s,
        )
        self.assertIn("traces", s)
        self.assertIn("cache_size", s)

    def test_get_status_after_work(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        s = self.orch.get_status()
        self.assertEqual(
            s["decisions_recorded"], 1,
        )

    def test_get_analytics(self):
        a = self.orch.get_analytics()
        self.assertIn(
            "total_explanations", a,
        )
        self.assertIn("cache_stats", a)

    def test_explanations_generated(self):
        self.orch.explain_decision(
            "d1", self.decision_data,
        )
        self.assertEqual(
            self.orch.explanations_generated,
            1,
        )

    def test_full_pipeline(self):
        # Record + Explain
        self.orch.explain_decision(
            "d1", self.decision_data,
            depth="detailed",
        )

        # Audit
        audit = self.orch.get_audit_report(
            "d1",
        )
        self.assertIn("sections", audit)

        # Status
        status = self.orch.get_status()
        self.assertGreater(
            status["decisions_recorded"], 0,
        )

        # Analytics
        analytics = self.orch.get_analytics()
        self.assertGreater(
            analytics["total_explanations"], 0,
        )


# ==================== Init & Config ====================

class TestExplainabilityInit(unittest.TestCase):
    """Explainability __init__ testleri."""

    def test_imports(self):
        from app.core.explainability import (
            AuditFormatter,
            CounterfactualGenerator,
            DecisionRecorder,
            ExplanationCache,
            ExplainabilityOrchestrator,
            FactorAnalyzer,
            NaturalLanguageExplainer,
            ReasoningTracer,
            VisualExplainer,
        )
        self.assertIsNotNone(AuditFormatter)
        self.assertIsNotNone(
            CounterfactualGenerator,
        )
        self.assertIsNotNone(DecisionRecorder)
        self.assertIsNotNone(ExplanationCache)
        self.assertIsNotNone(
            ExplainabilityOrchestrator,
        )
        self.assertIsNotNone(FactorAnalyzer)
        self.assertIsNotNone(
            NaturalLanguageExplainer,
        )
        self.assertIsNotNone(ReasoningTracer)
        self.assertIsNotNone(VisualExplainer)

    def test_instantiate_all(self):
        from app.core.explainability import (
            AuditFormatter,
            CounterfactualGenerator,
            DecisionRecorder,
            ExplanationCache,
            ExplainabilityOrchestrator,
            FactorAnalyzer,
            NaturalLanguageExplainer,
            ReasoningTracer,
            VisualExplainer,
        )
        instances = [
            AuditFormatter(),
            CounterfactualGenerator(),
            DecisionRecorder(),
            ExplanationCache(),
            ExplainabilityOrchestrator(),
            FactorAnalyzer(),
            NaturalLanguageExplainer(),
            ReasoningTracer(),
            VisualExplainer(),
        ]
        for inst in instances:
            self.assertIsNotNone(inst)


class TestExplainabilityConfig(
    unittest.TestCase,
):
    """Explainability config testleri."""

    def test_config_defaults(self):
        from app.config import settings

        self.assertTrue(
            settings.explainability_enabled,
        )
        self.assertEqual(
            settings.default_explanation_depth,
            "standard",
        )
        self.assertTrue(
            settings.cache_explanations,
        )
        self.assertTrue(
            settings.include_counterfactuals,
        )
        self.assertEqual(
            settings.explanation_language,
            "en",
        )


if __name__ == "__main__":
    unittest.main()
