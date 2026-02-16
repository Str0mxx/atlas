"""ATLAS Report & Insight Generator testleri.

ReportBuilder, ExecutiveSummary,
ComparisonMatrix, OpportunityScorer,
VisualPresenter, ActionableInsights,
TelegramFormatter, ExportManager,
ReportGenOrchestrator testleri.
"""

import pytest

from app.core.reportgen.actionable_insights import (
    ActionableInsights,
)
from app.core.reportgen.comparison_matrix import (
    ComparisonMatrix,
)
from app.core.reportgen.executive_summary import (
    ExecutiveSummary,
)
from app.core.reportgen.export_manager import (
    ExportManager,
)
from app.core.reportgen.opportunity_scorer import (
    OpportunityScorer,
)
from app.core.reportgen.report_builder import (
    ReportBuilder,
)
from app.core.reportgen.reportgen_orchestrator import (
    ReportGenOrchestrator,
)
from app.core.reportgen.telegram_formatter import (
    TelegramFormatter,
)
from app.core.reportgen.visual_presenter import (
    VisualPresenter,
)


# ── ReportBuilder ───────────────────────────


class TestReportBuilderInit:
    """ReportBuilder başlatma testleri."""

    def test_default_init(self):
        rb = ReportBuilder()
        assert rb.report_count == 0
        assert rb.template_count == 0
        assert rb.section_count == 0

    def test_empty_reports(self):
        rb = ReportBuilder()
        assert rb.get_reports() == []


class TestReportBuilderCreate:
    """ReportBuilder oluşturma testleri."""

    def test_create_report(self):
        rb = ReportBuilder()
        result = rb.create_report("Test Report")
        assert result["created"] is True
        assert result["report_id"] == "rpt_1"
        assert rb.report_count == 1

    def test_create_with_metadata(self):
        rb = ReportBuilder()
        result = rb.create_report(
            "Test", metadata={"key": "val"},
        )
        assert result["created"] is True

    def test_create_with_template(self):
        rb = ReportBuilder()
        rb.register_template(
            "basic",
            [{"title": "Intro"}, {"title": "Body"}],
        )
        result = rb.create_report(
            "Templated",
            template_id="tmpl_basic",
        )
        assert result["template_applied"] is True

    def test_create_no_template(self):
        rb = ReportBuilder()
        result = rb.create_report("Simple")
        assert result["template_applied"] is False


class TestReportBuilderSections:
    """ReportBuilder bölüm testleri."""

    def test_add_section(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        result = rb.add_section(
            rpt["report_id"],
            "Introduction",
            "Hello world",
        )
        assert result["added"] is True
        assert result["section_index"] == 0
        assert rb.section_count == 1

    def test_add_multiple_sections(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        rb.add_section(
            rpt["report_id"], "S1", "C1",
        )
        result = rb.add_section(
            rpt["report_id"], "S2", "C2",
        )
        assert result["section_index"] == 1

    def test_add_section_not_found(self):
        rb = ReportBuilder()
        result = rb.add_section(
            "invalid", "T", "C",
        )
        assert result["error"] == "report_not_found"

    def test_set_style(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        result = rb.set_style(
            rpt["report_id"],
            font="Arial", theme="dark",
        )
        assert result["updated"] is True
        assert result["style"]["font"] == "Arial"

    def test_set_style_not_found(self):
        rb = ReportBuilder()
        result = rb.set_style("invalid")
        assert "error" in result

    def test_set_dynamic_content(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        rb.add_section(
            rpt["report_id"], "S1", "C1",
        )
        result = rb.set_dynamic_content(
            rpt["report_id"], 0,
            {"chart": "bar_data"},
        )
        assert result["dynamic_set"] is True

    def test_set_dynamic_section_not_found(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        result = rb.set_dynamic_content(
            rpt["report_id"], 99, {},
        )
        assert result["error"] == "section_not_found"


class TestReportBuilderFinalize:
    """ReportBuilder sonuçlandırma testleri."""

    def test_finalize(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test Report")
        rb.add_section(
            rpt["report_id"],
            "Intro", "Hello",
        )
        result = rb.finalize(
            rpt["report_id"],
        )
        assert result["finalized"] is True
        assert result["sections"] == 1
        assert result["content_length"] > 0

    def test_finalize_not_found(self):
        rb = ReportBuilder()
        result = rb.finalize("invalid")
        assert "error" in result

    def test_register_template(self):
        rb = ReportBuilder()
        result = rb.register_template(
            "weekly",
            [{"title": "Summary"}, {"title": "Details"}],
            description="Weekly report",
        )
        assert result["registered"] is True
        assert rb.template_count == 1

    def test_get_report(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        report = rb.get_report(
            rpt["report_id"],
        )
        assert report["title"] == "Test"

    def test_get_reports_filtered(self):
        rb = ReportBuilder()
        rpt = rb.create_report("Test")
        rb.finalize(rpt["report_id"])
        ready = rb.get_reports(status="ready")
        assert len(ready) == 1


# ── ExecutiveSummary ────────────────────────


class TestExecutiveSummaryInit:
    """ExecutiveSummary başlatma testleri."""

    def test_default_init(self):
        es = ExecutiveSummary()
        assert es.summary_count == 0
        assert es.action_item_count == 0

    def test_custom_max_points(self):
        es = ExecutiveSummary(max_key_points=3)
        assert es._max_key_points == 3


class TestExecutiveSummaryExtract:
    """ExecutiveSummary çıkarma testleri."""

    def test_extract_key_points(self):
        es = ExecutiveSummary()
        result = es.extract_key_points(
            "Point one. Point two. Point three.",
        )
        assert result["count"] >= 1
        assert len(result["key_points"]) >= 1

    def test_extract_with_limit(self):
        es = ExecutiveSummary()
        result = es.extract_key_points(
            "A. B. C. D. E.",
            max_points=2,
        )
        assert result["count"] <= 2

    def test_generate_highlights(self):
        es = ExecutiveSummary()
        result = es.generate_highlights(
            {"revenue": 100, "users": 500},
        )
        assert result["count"] == 2
        assert len(result["highlights"]) == 2

    def test_create_tldr(self):
        es = ExecutiveSummary()
        result = es.create_tldr(
            "This is a long text that should be shortened to a brief summary.",
            max_chars=50,
        )
        assert len(result["tldr"]) <= 51
        assert result["truncated"] is True

    def test_create_tldr_short(self):
        es = ExecutiveSummary()
        result = es.create_tldr(
            "Short text.", max_chars=100,
        )
        assert result["truncated"] is False

    def test_rank_priorities(self):
        es = ExecutiveSummary()
        items = [
            {"name": "A", "score": 3},
            {"name": "B", "score": 7},
            {"name": "C", "score": 5},
        ]
        result = es.rank_priorities(items)
        assert result["ranked_items"][0]["name"] == "B"
        assert result["ranked_items"][0]["rank"] == 1

    def test_generate_action_items(self):
        es = ExecutiveSummary()
        insights = [
            {"recommendation": "Do X", "priority": "high"},
            {"description": "Check Y"},
        ]
        result = es.generate_action_items(
            insights,
        )
        assert result["count"] == 2
        assert es.action_item_count == 2

    def test_create_summary(self):
        es = ExecutiveSummary()
        result = es.create_summary(
            report_id="rpt_1",
            content="Important data. Revenue grew.",
            data={"revenue": 100},
            insights=[{"recommendation": "Expand"}],
        )
        assert "summary_id" in result
        assert result["tldr"] != ""
        assert es.summary_count == 1


# ── ComparisonMatrix ────────────────────────


class TestComparisonMatrixInit:
    """ComparisonMatrix başlatma testleri."""

    def test_default_init(self):
        cm = ComparisonMatrix()
        assert cm.comparison_count == 0
        assert cm.winner_count == 0


class TestComparisonMatrixCreate:
    """ComparisonMatrix oluşturma testleri."""

    def test_create_comparison(self):
        cm = ComparisonMatrix()
        result = cm.create_comparison(
            "Tools",
            ["A", "B"],
            [{"name": "price", "weight": 0.5}],
        )
        assert result["created"] is True
        assert result["items_count"] == 2
        assert cm.comparison_count == 1

    def test_set_scores(self):
        cm = ComparisonMatrix()
        cmp = cm.create_comparison(
            "Test",
            ["A", "B"],
            [{"name": "quality", "weight": 1.0}],
        )
        result = cm.set_scores(
            cmp["comparison_id"],
            {"A": {"quality": 8}, "B": {"quality": 6}},
        )
        assert result["set"] is True

    def test_set_scores_not_found(self):
        cm = ComparisonMatrix()
        result = cm.set_scores("invalid", {})
        assert "error" in result


class TestComparisonMatrixAnalyze:
    """ComparisonMatrix analiz testleri."""

    def test_calculate_weighted(self):
        cm = ComparisonMatrix()
        cmp = cm.create_comparison(
            "Test",
            ["A", "B"],
            [
                {"name": "quality", "weight": 0.6},
                {"name": "price", "weight": 0.4},
            ],
        )
        cm.set_scores(
            cmp["comparison_id"],
            {
                "A": {"quality": 8, "price": 6},
                "B": {"quality": 5, "price": 9},
            },
        )
        result = cm.calculate_weighted(
            cmp["comparison_id"],
        )
        assert result["winner"] is not None
        assert result["method"] == "weighted"
        assert cm.winner_count == 1

    def test_calculate_weighted_not_found(self):
        cm = ComparisonMatrix()
        result = cm.calculate_weighted(
            "invalid",
        )
        assert "error" in result

    def test_generate_table(self):
        cm = ComparisonMatrix()
        cmp = cm.create_comparison(
            "Test",
            ["A", "B"],
            [{"name": "speed", "weight": 1.0}],
        )
        cm.set_scores(
            cmp["comparison_id"],
            {"A": {"speed": 7}, "B": {"speed": 9}},
        )
        result = cm.generate_table(
            cmp["comparison_id"],
        )
        assert result["row_count"] == 2
        assert "headers" in result

    def test_generate_table_not_found(self):
        cm = ComparisonMatrix()
        result = cm.generate_table("invalid")
        assert "error" in result

    def test_highlight_winner(self):
        cm = ComparisonMatrix()
        cmp = cm.create_comparison(
            "Test",
            ["A", "B"],
            [{"name": "q", "weight": 1.0}],
        )
        cm.set_scores(
            cmp["comparison_id"],
            {"A": {"q": 5.0}, "B": {"q": 3.0}},
        )
        cm.calculate_weighted(
            cmp["comparison_id"],
        )
        result = cm.highlight_winner(
            cmp["comparison_id"],
        )
        assert result["highlighted"] is True
        assert result["winner"] == "A"

    def test_highlight_no_winner(self):
        cm = ComparisonMatrix()
        cmp = cm.create_comparison(
            "Test", ["A"], [{"name": "q"}],
        )
        result = cm.highlight_winner(
            cmp["comparison_id"],
        )
        assert result["winner"] is None

    def test_get_comparisons(self):
        cm = ComparisonMatrix()
        cm.create_comparison(
            "C1", ["A"], [{"name": "q"}],
        )
        cm.create_comparison(
            "C2", ["B"], [{"name": "q"}],
        )
        assert len(cm.get_comparisons()) == 2


# ── OpportunityScorer ───────────────────────


class TestOpportunityScorerInit:
    """OpportunityScorer başlatma testleri."""

    def test_default_init(self):
        os = OpportunityScorer()
        assert os.scored_count == 0
        assert os.ranking_count == 0

    def test_custom_weights(self):
        os = OpportunityScorer(
            weights={"roi": 0.5, "risk": 0.5},
        )
        assert os._weights["roi"] == 0.5


class TestOpportunityScorerScore:
    """OpportunityScorer puanlama testleri."""

    def test_score_opportunity(self):
        os = OpportunityScorer()
        result = os.score_opportunity(
            "New Product",
            roi_estimate=8,
            risk_level=3,
            feasibility=7,
            impact=9,
        )
        assert result["scored"] is True
        assert result["final_score"] > 0
        assert os.scored_count == 1

    def test_estimate_roi(self):
        os = OpportunityScorer()
        result = os.estimate_roi(
            investment=1000,
            expected_return=1500,
            timeframe_months=12,
        )
        assert result["roi_percentage"] == 50.0
        assert result["payback_months"] > 0

    def test_estimate_roi_invalid(self):
        os = OpportunityScorer()
        result = os.estimate_roi(0, 100)
        assert "error" in result

    def test_assess_risk(self):
        os = OpportunityScorer()
        factors = [
            {"name": "market", "severity": 6, "probability": 0.7},
            {"name": "tech", "severity": 3, "probability": 0.3},
        ]
        result = os.assess_risk(factors)
        assert result["risk_level"] in (
            "low", "medium", "high", "critical",
        )
        assert result["factor_count"] == 2

    def test_assess_risk_empty(self):
        os = OpportunityScorer()
        result = os.assess_risk([])
        assert result["level"] == "low"

    def test_score_feasibility(self):
        os = OpportunityScorer()
        result = os.score_feasibility(
            resources_available=8,
            technical_complexity=3,
            team_capability=7,
            time_constraint=4,
        )
        assert result["level"] in (
            "low", "medium", "high",
        )
        assert result["feasibility_score"] > 0


class TestOpportunityScorerRank:
    """OpportunityScorer sıralama testleri."""

    def test_rank_opportunities(self):
        os = OpportunityScorer()
        os.score_opportunity(
            "A", 5, 5, 5, 5,
        )
        os.score_opportunity(
            "B", 9, 2, 8, 9,
        )
        result = os.rank_opportunities()
        assert result["count"] == 2
        assert result["ranked"][0]["rank"] == 1
        assert os.ranking_count == 1

    def test_rank_empty(self):
        os = OpportunityScorer()
        result = os.rank_opportunities()
        assert result["count"] == 0
        assert result["top"] is None

    def test_get_opportunities(self):
        os = OpportunityScorer()
        os.score_opportunity(
            "A", 5, 5, 5, 5,
        )
        assert len(os.get_opportunities()) == 1


# ── VisualPresenter ─────────────────────────


class TestVisualPresenterInit:
    """VisualPresenter başlatma testleri."""

    def test_default_init(self):
        vp = VisualPresenter()
        assert vp.visual_count == 0
        assert vp.chart_count == 0


class TestVisualPresenterCharts:
    """VisualPresenter grafik testleri."""

    def test_create_chart(self):
        vp = VisualPresenter()
        result = vp.create_chart(
            "bar",
            {"labels": ["A"], "values": [1]},
            title="Test Chart",
        )
        assert result["created"] is True
        assert result["type"] == "bar"
        assert vp.chart_count == 1

    def test_create_bar_chart(self):
        vp = VisualPresenter()
        result = vp.create_bar_chart(
            ["A", "B"], [10, 20], "Sales",
        )
        assert result["type"] == "bar"

    def test_create_line_chart(self):
        vp = VisualPresenter()
        result = vp.create_line_chart(
            [1, 2, 3], [10, 20, 30], "Trend",
        )
        assert result["type"] == "line"

    def test_create_pie_chart(self):
        vp = VisualPresenter()
        result = vp.create_pie_chart(
            ["A", "B"], [60, 40], "Share",
        )
        assert result["type"] == "pie"

    def test_create_graph(self):
        vp = VisualPresenter()
        result = vp.create_graph(
            nodes=[{"id": "1"}, {"id": "2"}],
            edges=[{"from": "1", "to": "2"}],
            title="Network",
        )
        assert result["type"] == "graph"
        assert result["node_count"] == 2

    def test_create_infographic(self):
        vp = VisualPresenter()
        result = vp.create_infographic(
            sections=[
                {"title": "Key Stat", "value": "100"},
            ],
            title="Overview",
        )
        assert result["type"] == "infographic"
        assert result["section_count"] == 1

    def test_create_data_table(self):
        vp = VisualPresenter()
        result = vp.create_data_table(
            headers=["Name", "Value"],
            rows=[["A", 10], ["B", 20]],
            title="Data",
        )
        assert result["type"] == "table"
        assert result["row_count"] == 2

    def test_get_visuals_filtered(self):
        vp = VisualPresenter()
        vp.create_bar_chart(["A"], [1])
        vp.create_pie_chart(["B"], [2])
        charts = vp.get_visuals(
            visual_type="bar",
        )
        assert len(charts) == 1

    def test_multiple_visuals(self):
        vp = VisualPresenter()
        vp.create_bar_chart(["A"], [1])
        vp.create_line_chart([1], [2])
        vp.create_pie_chart(["C"], [3])
        assert vp.visual_count == 3


# ── ActionableInsights ──────────────────────


class TestActionableInsightsInit:
    """ActionableInsights başlatma testleri."""

    def test_default_init(self):
        ai = ActionableInsights()
        assert ai.insight_count == 0
        assert ai.recommendation_count == 0


class TestActionableInsightsExtract:
    """ActionableInsights çıkarma testleri."""

    def test_extract_insights(self):
        ai = ActionableInsights()
        result = ai.extract_insights(
            {"revenue": 95, "churn": 15},
            context="monthly",
        )
        assert result["count"] == 2
        assert ai.insight_count == 2

    def test_extract_high_value_opportunity(self):
        ai = ActionableInsights()
        result = ai.extract_insights(
            {"growth": 90},
        )
        assert result["insights"][0]["type"] == "opportunity"
        assert result["insights"][0]["priority"] == "high"

    def test_extract_low_value_risk(self):
        ai = ActionableInsights()
        result = ai.extract_insights(
            {"satisfaction": 10},
        )
        assert result["insights"][0]["type"] == "risk"

    def test_recommend_actions(self):
        ai = ActionableInsights()
        result = ai.extract_insights(
            {"metric": 50},
        )
        recs = ai.recommend_actions(
            result["insights"],
        )
        assert recs["count"] == 1
        assert ai.recommendation_count == 1

    def test_suggest_next_steps(self):
        ai = ActionableInsights()
        actions = [
            {"recommendation": "Do A", "priority": "high"},
            {"recommendation": "Do B", "priority": "low"},
        ]
        result = ai.suggest_next_steps(actions)
        assert result["count"] == 2
        assert result["first_step"] == "Do A"

    def test_assign_owners(self):
        ai = ActionableInsights()
        actions = [
            {"recommendation": "Task 1"},
            {"recommendation": "Task 2"},
            {"recommendation": "Task 3"},
        ]
        result = ai.assign_owners(
            actions, ["Alice", "Bob"],
        )
        assert result["count"] == 3
        assert result["assignments"][0]["owner"] == "Alice"
        assert result["assignments"][1]["owner"] == "Bob"
        assert result["assignments"][2]["owner"] == "Alice"

    def test_suggest_deadlines(self):
        ai = ActionableInsights()
        actions = [
            {"priority": "critical"},
            {"priority": "low"},
        ]
        result = ai.suggest_deadlines(
            actions, base_days=7,
        )
        assert result["count"] == 2
        critical = result["deadlines"][0]
        low = result["deadlines"][1]
        assert critical["suggested_days"] < low["suggested_days"]

    def test_get_insights_filtered(self):
        ai = ActionableInsights()
        ai.extract_insights(
            {"high_val": 95, "low_val": 10},
        )
        risks = ai.get_insights(
            insight_type="risk",
        )
        assert len(risks) >= 1


# ── TelegramFormatter ──────────────────────


class TestTelegramFormatterInit:
    """TelegramFormatter başlatma testleri."""

    def test_default_init(self):
        tf = TelegramFormatter()
        assert tf.message_count == 0
        assert tf.button_count == 0
        assert tf._use_emoji is True

    def test_no_emoji(self):
        tf = TelegramFormatter(use_emoji=False)
        assert tf._use_emoji is False


class TestTelegramFormatterFormat:
    """TelegramFormatter biçimlendirme testleri."""

    def test_format_report(self):
        tf = TelegramFormatter()
        result = tf.format_report(
            "Weekly Report",
            [{"title": "Summary", "content": "All good"}],
        )
        assert result["formatted"] is True
        assert "<b>" in result["text"]
        assert tf.message_count == 1

    def test_format_report_no_emoji(self):
        tf = TelegramFormatter(use_emoji=False)
        result = tf.format_report(
            "Report", [{"title": "S", "content": "C"}],
        )
        assert "\U0001f4ca" not in result["text"]

    def test_split_message_short(self):
        tf = TelegramFormatter()
        result = tf.split_message("Short text")
        assert result["count"] == 1
        assert result["split"] is False

    def test_split_message_long(self):
        tf = TelegramFormatter()
        long_text = "Line\n" * 1000
        result = tf.split_message(
            long_text, max_length=100,
        )
        assert result["count"] > 1
        assert result["split"] is True

    def test_add_inline_buttons(self):
        tf = TelegramFormatter()
        result = tf.add_inline_buttons(
            "msg_1",
            [
                {"text": "Yes", "callback": "yes"},
                {"text": "No", "callback": "no"},
            ],
        )
        assert result["added"] is True
        assert result["button_count"] == 2
        assert tf.button_count == 2

    def test_format_summary(self):
        tf = TelegramFormatter()
        result = tf.format_summary(
            tldr="All metrics improved.",
            highlights=["Revenue up 20%"],
            actions=["Expand marketing"],
        )
        assert "TL;DR" in result["text"]
        assert result["length"] > 0

    def test_get_messages(self):
        tf = TelegramFormatter()
        tf.format_report(
            "R1", [{"title": "S", "content": "C"}],
        )
        assert len(tf.get_messages()) == 1


# ── ExportManager ───────────────────────────


class TestExportManagerInit:
    """ExportManager başlatma testleri."""

    def test_default_init(self):
        em = ExportManager()
        assert em.export_count == 0
        assert em.email_count == 0


class TestExportManagerExport:
    """ExportManager aktarma testleri."""

    def test_export_pdf(self):
        em = ExportManager()
        result = em.export_pdf(
            "rpt_1", "content", "Report",
        )
        assert result["exported"] is True
        assert result["format"] == "pdf"
        assert result["file_path"].endswith(".pdf")

    def test_export_word(self):
        em = ExportManager()
        result = em.export_word(
            "rpt_1", "content", "Report",
        )
        assert result["format"] == "word"
        assert result["file_path"].endswith(".docx")

    def test_export_html(self):
        em = ExportManager()
        result = em.export_html(
            "rpt_1", "<h1>Report</h1>",
        )
        assert result["format"] == "html"

    def test_export_markdown(self):
        em = ExportManager()
        result = em.export_markdown(
            "rpt_1", "# Report",
        )
        assert result["format"] == "markdown"
        assert result["file_path"].endswith(".md")

    def test_export_json(self):
        em = ExportManager()
        result = em.export_json(
            "rpt_1", {"key": "value"},
        )
        assert result["format"] == "json"

    def test_multiple_exports(self):
        em = ExportManager()
        em.export_pdf("rpt_1", "c")
        em.export_html("rpt_1", "c")
        em.export_markdown("rpt_1", "c")
        assert em.export_count == 3


class TestExportManagerEmail:
    """ExportManager e-posta testleri."""

    def test_send_email(self):
        em = ExportManager()
        exp = em.export_pdf("rpt_1", "c", "R")
        result = em.send_email(
            exp["export_id"],
            to="user@example.com",
            subject="Report",
        )
        assert result["sent"] is True
        assert em.email_count == 1

    def test_send_email_not_found(self):
        em = ExportManager()
        result = em.send_email(
            "invalid", "user@x.com",
        )
        assert "error" in result

    def test_get_exports_filtered(self):
        em = ExportManager()
        em.export_pdf("rpt_1", "c")
        em.export_html("rpt_2", "c")
        pdfs = em.get_exports(fmt="pdf")
        assert len(pdfs) == 1

    def test_get_exports_by_report(self):
        em = ExportManager()
        em.export_pdf("rpt_1", "c")
        em.export_html("rpt_1", "c")
        em.export_pdf("rpt_2", "c")
        r1 = em.get_exports(report_id="rpt_1")
        assert len(r1) == 2


# ── ReportGenOrchestrator ──────────────────


class TestReportGenOrchestratorInit:
    """ReportGenOrchestrator başlatma testleri."""

    def test_default_init(self):
        rgo = ReportGenOrchestrator()
        assert rgo.report_count == 0
        assert rgo.builder is not None
        assert rgo.summary is not None
        assert rgo.insights is not None

    def test_custom_emoji(self):
        rgo = ReportGenOrchestrator(
            use_emoji=False,
        )
        assert rgo.telegram._use_emoji is False


class TestReportGenOrchestratorGenerate:
    """ReportGenOrchestrator üretim testleri."""

    def test_generate_report(self):
        rgo = ReportGenOrchestrator()
        result = rgo.generate_report(
            title="Monthly Report",
            data={"revenue": 100, "users": 50},
        )
        assert result["success"] is True
        assert result["report_id"] is not None
        assert result["insights_count"] >= 1
        assert rgo.report_count == 1

    def test_generate_no_insights(self):
        rgo = ReportGenOrchestrator()
        result = rgo.generate_report(
            title="Simple",
            data={"metric": 42},
            include_insights=False,
        )
        assert result["insights_count"] == 0

    def test_generate_no_visuals(self):
        rgo = ReportGenOrchestrator()
        result = rgo.generate_report(
            title="Text Only",
            data={"metric": 42},
            include_visuals=False,
        )
        assert result["visuals"] == []

    def test_generate_telegram_friendly(self):
        rgo = ReportGenOrchestrator()
        result = rgo.generate_report(
            title="TG Report",
            data={"score": 85},
            telegram_friendly=True,
        )
        assert result["telegram_message"] is not None

    def test_generate_no_telegram(self):
        rgo = ReportGenOrchestrator()
        result = rgo.generate_report(
            title="No TG",
            data={"x": 1},
            telegram_friendly=False,
        )
        assert result["telegram_message"] is None

    def test_generate_with_visuals(self):
        rgo = ReportGenOrchestrator()
        result = rgo.generate_report(
            title="Visual Report",
            data={"sales": 100, "costs": 50},
            include_visuals=True,
        )
        assert len(result["visuals"]) >= 1


class TestReportGenOrchestratorExport:
    """ReportGenOrchestrator aktarma testleri."""

    def test_export_report(self):
        rgo = ReportGenOrchestrator()
        gen = rgo.generate_report(
            title="Export Test",
            data={"a": 1},
        )
        result = rgo.export_report(
            gen["report_id"],
            formats=["pdf", "html"],
        )
        assert result["count"] == 2

    def test_export_not_found(self):
        rgo = ReportGenOrchestrator()
        result = rgo.export_report("invalid")
        assert "error" in result

    def test_export_default_format(self):
        rgo = ReportGenOrchestrator()
        gen = rgo.generate_report(
            title="Default", data={"x": 1},
        )
        result = rgo.export_report(
            gen["report_id"],
        )
        assert result["count"] == 1


class TestReportGenOrchestratorAnalytics:
    """ReportGenOrchestrator analitik testleri."""

    def test_get_analytics(self):
        rgo = ReportGenOrchestrator()
        rgo.generate_report(
            title="Test", data={"a": 1},
        )
        analytics = rgo.get_analytics()
        assert analytics["reports_generated"] == 1
        assert "summaries" in analytics
        assert "insights" in analytics

    def test_get_status(self):
        rgo = ReportGenOrchestrator()
        status = rgo.get_status()
        assert "reports_generated" in status
        assert "total_reports" in status
        assert "total_exports" in status

    def test_analytics_after_operations(self):
        rgo = ReportGenOrchestrator()
        rgo.generate_report(
            title="R1", data={"a": 1},
        )
        rgo.generate_report(
            title="R2", data={"b": 2},
        )
        analytics = rgo.get_analytics()
        assert analytics["reports_generated"] == 2
        assert analytics["pipelines_completed"] == 2


# ── Integration & __init__ ──────────────────


class TestReportGenImports:
    """Modül import testleri."""

    def test_import_all(self):
        from app.core.reportgen import (
            ActionableInsights,
            ComparisonMatrix,
            ExecutiveSummary,
            ExportManager,
            OpportunityScorer,
            ReportBuilder,
            ReportGenOrchestrator,
            TelegramFormatter,
            VisualPresenter,
        )
        assert ActionableInsights is not None
        assert ComparisonMatrix is not None
        assert ExecutiveSummary is not None
        assert ExportManager is not None
        assert OpportunityScorer is not None
        assert ReportBuilder is not None
        assert ReportGenOrchestrator is not None
        assert TelegramFormatter is not None
        assert VisualPresenter is not None


class TestReportGenModels:
    """Model import testleri."""

    def test_import_enums(self):
        from app.models.reportgen_models import (
            ChartType,
            InsightType,
            PriorityLevel,
            ReportFormat,
            ReportStatus,
            ScoringMethod,
        )
        assert len(ReportFormat) >= 1
        assert len(InsightType) >= 1
        assert len(ReportStatus) >= 1
        assert len(ChartType) >= 1
        assert len(PriorityLevel) >= 1
        assert len(ScoringMethod) >= 1

    def test_import_models(self):
        from app.models.reportgen_models import (
            ComparisonRecord,
            InsightRecord,
            ReportGenSnapshot,
            ReportRecord,
        )
        assert ReportRecord is not None
        assert InsightRecord is not None
        assert ComparisonRecord is not None
        assert ReportGenSnapshot is not None

    def test_model_defaults(self):
        from app.models.reportgen_models import (
            ReportRecord,
        )
        record = ReportRecord(title="Test")
        assert record.title == "Test"
        assert record.report_id is not None


class TestReportGenConfig:
    """Config testleri."""

    def test_config_settings(self):
        from app.config import settings
        assert hasattr(settings, "reportgen_enabled")
        assert hasattr(settings, "default_format")
        assert hasattr(settings, "include_visuals")
        assert hasattr(settings, "telegram_friendly")
        assert hasattr(settings, "auto_export")

    def test_config_defaults(self):
        from app.config import settings
        assert settings.reportgen_enabled is True
        assert settings.default_format == "markdown"
        assert settings.include_visuals is True
        assert settings.telegram_friendly is True
        assert settings.auto_export is False
