"""ATLAS Task Memory & Command Learning testleri.

Görev hafızası: komut öğrenme, tercih takibi,
şablon oluşturma, kişiselleştirme testleri.
"""

import pytest

from app.core.taskmem.command_pattern_learner import (
    CommandPatternLearner,
)
from app.core.taskmem.command_predictor import (
    CommandPredictor,
)
from app.core.taskmem.execution_memory import (
    ExecutionMemory,
)
from app.core.taskmem.feedback_integrator import (
    TaskFeedbackIntegrator,
)
from app.core.taskmem.personalization_engine import (
    PersonalizationEngine,
)
from app.core.taskmem.preference_tracker import (
    TaskPreferenceTracker,
)
from app.core.taskmem.quality_improver import (
    QualityImprover,
)
from app.core.taskmem.task_template_builder import (
    TaskTemplateBuilder,
)
from app.core.taskmem.taskmem_orchestrator import (
    TaskMemOrchestrator,
)
from app.models.taskmem_models import (
    FeedbackRecord,
    FeedbackType,
    PatternRecord,
    PatternType,
    PersonalizationMode,
    PredictionConfidence,
    QualityLevel,
    TaskMemSnapshot,
    TemplateRecord,
    TemplateStatus,
)


# ==================== Models ====================


class TestPatternType:
    """PatternType enum testleri."""

    def test_values(self):
        assert PatternType.COMMAND == "command"
        assert PatternType.SEQUENCE == "sequence"
        assert PatternType.SHORTCUT == "shortcut"
        assert PatternType.ALIAS == "alias"
        assert PatternType.WORKFLOW == "workflow"
        assert PatternType.HABIT == "habit"

    def test_member_count(self):
        assert len(PatternType) == 6


class TestFeedbackType:
    """FeedbackType enum testleri."""

    def test_values(self):
        assert FeedbackType.EXPLICIT == "explicit"
        assert FeedbackType.IMPLICIT == "implicit"
        assert FeedbackType.CORRECTION == "correction"
        assert FeedbackType.RATING == "rating"
        assert FeedbackType.SUGGESTION == "suggestion"
        assert FeedbackType.COMPLAINT == "complaint"

    def test_member_count(self):
        assert len(FeedbackType) == 6


class TestQualityLevel:
    """QualityLevel enum testleri."""

    def test_values(self):
        assert QualityLevel.EXCELLENT == "excellent"
        assert QualityLevel.GOOD == "good"
        assert QualityLevel.AVERAGE == "average"
        assert QualityLevel.POOR == "poor"
        assert QualityLevel.FAILING == "failing"
        assert QualityLevel.UNKNOWN == "unknown"

    def test_member_count(self):
        assert len(QualityLevel) == 6


class TestPersonalizationMode:
    """PersonalizationMode enum testleri."""

    def test_values(self):
        assert (
            PersonalizationMode.AGGRESSIVE
            == "aggressive"
        )
        assert (
            PersonalizationMode.MODERATE
            == "moderate"
        )
        assert (
            PersonalizationMode.CONSERVATIVE
            == "conservative"
        )
        assert (
            PersonalizationMode.MINIMAL
            == "minimal"
        )
        assert PersonalizationMode.OFF == "off"
        assert PersonalizationMode.AUTO == "auto"

    def test_member_count(self):
        assert len(PersonalizationMode) == 6


class TestTemplateStatus:
    """TemplateStatus enum testleri."""

    def test_values(self):
        assert TemplateStatus.DRAFT == "draft"
        assert TemplateStatus.ACTIVE == "active"
        assert TemplateStatus.ARCHIVED == "archived"
        assert (
            TemplateStatus.DEPRECATED
            == "deprecated"
        )
        assert TemplateStatus.TESTING == "testing"
        assert TemplateStatus.APPROVED == "approved"

    def test_member_count(self):
        assert len(TemplateStatus) == 6


class TestPredictionConfidence:
    """PredictionConfidence enum testleri."""

    def test_values(self):
        assert (
            PredictionConfidence.VERY_HIGH
            == "very_high"
        )
        assert PredictionConfidence.HIGH == "high"
        assert (
            PredictionConfidence.MEDIUM == "medium"
        )
        assert PredictionConfidence.LOW == "low"
        assert (
            PredictionConfidence.VERY_LOW
            == "very_low"
        )
        assert (
            PredictionConfidence.UNCERTAIN
            == "uncertain"
        )

    def test_member_count(self):
        assert len(PredictionConfidence) == 6


class TestPatternRecord:
    """PatternRecord model testleri."""

    def test_defaults(self):
        r = PatternRecord()
        assert len(r.pattern_id) == 8
        assert r.pattern_type == PatternType.COMMAND
        assert r.name == ""
        assert r.frequency == 0
        assert r.confidence == 0.0
        assert r.created_at is not None
        assert r.metadata == {}

    def test_custom(self):
        r = PatternRecord(
            name="deploy",
            pattern_type=PatternType.WORKFLOW,
            frequency=10,
            confidence=0.85,
            metadata={"source": "auto"},
        )
        assert r.name == "deploy"
        assert r.pattern_type == PatternType.WORKFLOW
        assert r.frequency == 10
        assert r.confidence == 0.85
        assert r.metadata["source"] == "auto"

    def test_unique_ids(self):
        r1 = PatternRecord()
        r2 = PatternRecord()
        assert r1.pattern_id != r2.pattern_id


class TestFeedbackRecord:
    """FeedbackRecord model testleri."""

    def test_defaults(self):
        r = FeedbackRecord()
        assert len(r.feedback_id) == 8
        assert (
            r.feedback_type
            == FeedbackType.EXPLICIT
        )
        assert r.score == 0.0
        assert r.message == ""
        assert r.created_at is not None

    def test_custom(self):
        r = FeedbackRecord(
            feedback_type=FeedbackType.CORRECTION,
            score=4.5,
            message="Great work",
        )
        assert (
            r.feedback_type
            == FeedbackType.CORRECTION
        )
        assert r.score == 4.5
        assert r.message == "Great work"


class TestTemplateRecord:
    """TemplateRecord model testleri."""

    def test_defaults(self):
        r = TemplateRecord()
        assert len(r.template_id) == 8
        assert r.name == ""
        assert r.status == TemplateStatus.DRAFT
        assert r.version == 1
        assert r.usage_count == 0
        assert r.created_at is not None

    def test_custom(self):
        r = TemplateRecord(
            name="deploy_template",
            status=TemplateStatus.ACTIVE,
            version=3,
            usage_count=15,
        )
        assert r.name == "deploy_template"
        assert r.status == TemplateStatus.ACTIVE
        assert r.version == 3
        assert r.usage_count == 15


class TestTaskMemSnapshot:
    """TaskMemSnapshot model testleri."""

    def test_defaults(self):
        s = TaskMemSnapshot()
        assert s.patterns_learned == 0
        assert s.templates_created == 0
        assert s.feedbacks_received == 0
        assert s.predictions_made == 0
        assert s.quality_score == 0.0
        assert s.timestamp is not None

    def test_custom(self):
        s = TaskMemSnapshot(
            patterns_learned=50,
            templates_created=10,
            feedbacks_received=100,
            predictions_made=200,
            quality_score=4.2,
        )
        assert s.patterns_learned == 50
        assert s.templates_created == 10
        assert s.quality_score == 4.2


# =========== CommandPatternLearner ===========


class TestCommandPatternLearnerInit:
    """CommandPatternLearner başlatma testleri."""

    def test_default_init(self):
        cpl = CommandPatternLearner()
        assert cpl.pattern_count == 0
        assert cpl.command_count == 0
        assert cpl.alias_count == 0

    def test_custom_frequency(self):
        cpl = CommandPatternLearner(
            min_frequency=5,
        )
        assert cpl._min_frequency == 5


class TestCommandPatternLearnerRecord:
    """Komut kaydetme testleri."""

    def test_record_command(self):
        cpl = CommandPatternLearner()
        r = cpl.record_command("git status")
        assert r["recorded"] is True
        assert r["command"] == "git status"
        assert "command_id" in r
        assert cpl.command_count == 1

    def test_record_with_context(self):
        cpl = CommandPatternLearner()
        r = cpl.record_command(
            "deploy", context="production",
        )
        assert r["recorded"] is True

    def test_record_with_params(self):
        cpl = CommandPatternLearner()
        r = cpl.record_command(
            "build",
            params={"target": "release"},
        )
        assert r["recorded"] is True

    def test_multiple_records(self):
        cpl = CommandPatternLearner()
        for i in range(5):
            cpl.record_command(f"cmd_{i}")
        assert cpl.command_count == 5


class TestCommandPatternLearnerPatterns:
    """Örüntü çıkarma testleri."""

    def test_extract_no_patterns(self):
        cpl = CommandPatternLearner()
        cpl.record_command("git status")
        cpl.record_command("git diff")
        r = cpl.extract_patterns()
        assert r["patterns_found"] == 0

    def test_extract_with_patterns(self):
        cpl = CommandPatternLearner()
        for _ in range(5):
            cpl.record_command("git status")
        r = cpl.extract_patterns()
        assert r["patterns_found"] >= 1
        assert cpl.pattern_count >= 1

    def test_analyze_frequency(self):
        cpl = CommandPatternLearner()
        for _ in range(3):
            cpl.record_command("git status")
        for _ in range(2):
            cpl.record_command("git diff")
        r = cpl.analyze_frequency()
        assert r["unique_commands"] == 2
        assert r["total_commands"] == 5
        assert r["most_used"] == "git status"

    def test_analyze_empty(self):
        cpl = CommandPatternLearner()
        r = cpl.analyze_frequency()
        assert r["unique_commands"] == 0
        assert r["most_used"] is None


class TestCommandPatternLearnerSequences:
    """Sekans öğrenme testleri."""

    def test_learn_sequences_insufficient(self):
        cpl = CommandPatternLearner()
        cpl.record_command("a")
        r = cpl.learn_sequences()
        assert r["count"] == 0

    def test_learn_sequences(self):
        cpl = CommandPatternLearner()
        for _ in range(3):
            cpl.record_command("build")
            cpl.record_command("test")
            cpl.record_command("deploy")
        r = cpl.learn_sequences()
        assert r["count"] >= 1

    def test_detect_shortcuts(self):
        cpl = CommandPatternLearner(
            min_frequency=2,
        )
        for _ in range(3):
            cpl.record_command("git status")
        r = cpl.detect_shortcuts()
        assert isinstance(r["shortcuts"], list)

    def test_shortcuts_single_word(self):
        cpl = CommandPatternLearner(
            min_frequency=2,
        )
        for _ in range(3):
            cpl.record_command("deploy")
        r = cpl.detect_shortcuts()
        # Tek kelime kısayol önermez
        assert r["count"] == 0


class TestCommandPatternLearnerAliases:
    """Takma ad testleri."""

    def test_create_alias(self):
        cpl = CommandPatternLearner()
        r = cpl.create_alias(
            "gs", "git status",
        )
        assert r["created"] is True
        assert r["alias"] == "gs"
        assert cpl.alias_count == 1

    def test_resolve_alias(self):
        cpl = CommandPatternLearner()
        cpl.create_alias("gs", "git status")
        r = cpl.resolve_alias("gs")
        assert r["resolved"] is True
        assert r["command"] == "git status"

    def test_resolve_unknown_alias(self):
        cpl = CommandPatternLearner()
        r = cpl.resolve_alias("unknown")
        assert "error" in r

    def test_get_patterns_by_type(self):
        cpl = CommandPatternLearner()
        for _ in range(5):
            cpl.record_command("test")
        cpl.extract_patterns()
        r = cpl.get_patterns("command")
        assert isinstance(r, list)


# =========== TaskPreferenceTracker ===========


class TestPreferenceTrackerInit:
    """TaskPreferenceTracker başlatma testleri."""

    def test_default_init(self):
        pt = TaskPreferenceTracker()
        assert pt.preference_count > 0
        assert pt.category_count == 0

    def test_default_preferences(self):
        pt = TaskPreferenceTracker()
        prefs = pt.get_all_preferences()
        assert prefs["format"] == "markdown"
        assert prefs["detail_level"] == "medium"
        assert prefs["language"] == "tr"


class TestPreferenceTrackerSet:
    """Tercih ayarlama testleri."""

    def test_set_preference(self):
        pt = TaskPreferenceTracker()
        r = pt.set_preference(
            "format", "json",
        )
        assert r["set"] is True
        assert r["value"] == "json"
        assert r["old_value"] == "markdown"

    def test_set_category_preference(self):
        pt = TaskPreferenceTracker()
        r = pt.set_preference(
            "format", "html",
            category="report",
        )
        assert r["set"] is True
        assert r["category"] == "report"
        assert pt.category_count == 1

    def test_get_preference(self):
        pt = TaskPreferenceTracker()
        v = pt.get_preference("format")
        assert v == "markdown"

    def test_get_category_preference(self):
        pt = TaskPreferenceTracker()
        pt.set_preference(
            "format", "html",
            category="report",
        )
        v = pt.get_preference(
            "format", category="report",
        )
        assert v == "html"

    def test_get_nonexistent(self):
        pt = TaskPreferenceTracker()
        v = pt.get_preference("nonexistent")
        assert v is None


class TestPreferenceTrackerApply:
    """Tercih uygulama testleri."""

    def test_apply_preferences(self):
        pt = TaskPreferenceTracker()
        r = pt.apply_preferences("analysis")
        assert r["applied"] is True
        assert "preferences" in r
        assert r["task_type"] == "analysis"

    def test_apply_with_category_override(self):
        pt = TaskPreferenceTracker()
        pt.set_preference(
            "detail_level", "high",
            category="analysis",
        )
        r = pt.apply_preferences("analysis")
        assert (
            r["preferences"]["detail_level"]
            == "high"
        )

    def test_learn_from_usage(self):
        pt = TaskPreferenceTracker()
        r = pt.learn_from_usage(
            "format", "json",
        )
        assert r["learned"] is True
        assert r["differs"] is True
        assert r["current"] == "markdown"

    def test_learn_same_value(self):
        pt = TaskPreferenceTracker()
        r = pt.learn_from_usage(
            "format", "markdown",
        )
        assert r["differs"] is False

    def test_get_history(self):
        pt = TaskPreferenceTracker()
        pt.set_preference("format", "json")
        pt.set_preference("format", "html")
        h = pt.get_history(key="format")
        assert len(h) == 2

    def test_get_all_history(self):
        pt = TaskPreferenceTracker()
        pt.set_preference("format", "json")
        pt.set_preference(
            "detail_level", "high",
        )
        h = pt.get_history()
        assert len(h) == 2


# =========== TaskFeedbackIntegrator ===========


class TestFeedbackIntegratorInit:
    """TaskFeedbackIntegrator başlatma."""

    def test_default_init(self):
        fi = TaskFeedbackIntegrator()
        assert fi.feedback_count == 0
        assert fi.correction_count == 0


class TestFeedbackIntegratorExplicit:
    """Açık geri bildirim testleri."""

    def test_record_explicit(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_explicit(
            "task_1", rating=4.5,
        )
        assert r["recorded"] is True
        assert r["rating"] == 4.5
        assert fi.feedback_count == 1

    def test_rating_clamped(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_explicit(
            "task_1", rating=10.0,
        )
        assert r["rating"] == 5.0

    def test_rating_clamped_low(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_explicit(
            "task_1", rating=-1.0,
        )
        assert r["rating"] == 0.0

    def test_with_comment(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_explicit(
            "task_1",
            rating=4.0,
            comment="Good work",
        )
        assert r["recorded"] is True


class TestFeedbackIntegratorImplicit:
    """Örtük sinyal testleri."""

    def test_record_implicit_accepted(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_implicit(
            "task_1", "accepted",
        )
        assert r["recorded"] is True
        assert r["inferred_score"] == 4.0

    def test_record_implicit_rejected(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_implicit(
            "task_1", "rejected",
        )
        assert r["inferred_score"] == 1.0

    def test_record_implicit_quick_approve(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_implicit(
            "task_1", "quick_approve",
        )
        assert r["inferred_score"] == 5.0

    def test_record_implicit_unknown_signal(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_implicit(
            "task_1", "unknown_signal",
        )
        assert r["inferred_score"] == 3.0


class TestFeedbackIntegratorCorrection:
    """Düzeltme testleri."""

    def test_record_correction(self):
        fi = TaskFeedbackIntegrator()
        r = fi.record_correction(
            "task_1",
            original="colour",
            corrected="color",
            field="spelling",
        )
        assert r["recorded"] is True
        assert fi.correction_count == 1


class TestFeedbackIntegratorSatisfaction:
    """Memnuniyet testleri."""

    def test_satisfaction_empty(self):
        fi = TaskFeedbackIntegrator()
        r = fi.get_satisfaction_score()
        assert r["score"] == 0.0
        assert r["count"] == 0
        assert r["trend"] == "insufficient_data"

    def test_satisfaction_with_data(self):
        fi = TaskFeedbackIntegrator()
        fi.record_explicit("t1", 4.0)
        fi.record_explicit("t2", 5.0)
        r = fi.get_satisfaction_score()
        assert r["score"] == 4.5
        assert r["count"] == 2

    def test_satisfaction_trend(self):
        fi = TaskFeedbackIntegrator()
        # 10 eski düşük puan
        for i in range(10):
            fi.record_explicit(
                f"old_{i}", 2.0,
            )
        # 5 yeni yüksek puan
        for i in range(5):
            fi.record_explicit(
                f"new_{i}", 5.0,
            )
        r = fi.get_satisfaction_score()
        assert r["trend"] == "improving"


class TestFeedbackIntegratorImprovements:
    """İyileştirme eşleme testleri."""

    def test_map_improvements_empty(self):
        fi = TaskFeedbackIntegrator()
        r = fi.map_improvements()
        assert r["count"] == 0

    def test_map_from_corrections(self):
        fi = TaskFeedbackIntegrator()
        for i in range(3):
            fi.record_correction(
                f"t_{i}",
                original="a",
                corrected="b",
                field="format",
            )
        r = fi.map_improvements()
        assert r["count"] >= 1

    def test_map_from_low_ratings(self):
        fi = TaskFeedbackIntegrator()
        for i in range(3):
            fi.record_explicit(
                f"t_{i}",
                rating=1.5,
                category="speed",
            )
        r = fi.map_improvements()
        assert r["count"] >= 1

    def test_get_feedbacks(self):
        fi = TaskFeedbackIntegrator()
        fi.record_explicit("t1", 4.0)
        fi.record_explicit("t2", 3.0)
        r = fi.get_feedbacks(task_id="t1")
        assert len(r) == 1

    def test_get_feedbacks_by_type(self):
        fi = TaskFeedbackIntegrator()
        fi.record_explicit("t1", 4.0)
        fi.record_implicit("t2", "accepted")
        r = fi.get_feedbacks(
            feedback_type="explicit",
        )
        assert len(r) == 1


# =========== TaskTemplateBuilder ===========


class TestTemplateBuilderInit:
    """TaskTemplateBuilder başlatma testleri."""

    def test_default_init(self):
        tb = TaskTemplateBuilder()
        assert tb.template_count == 0
        assert tb.usage_count == 0


class TestTemplateBuilderCreate:
    """Şablon oluşturma testleri."""

    def test_create_template(self):
        tb = TaskTemplateBuilder()
        r = tb.create_template(
            name="deploy",
            pattern="deploy {env} {version}",
        )
        assert r["created"] is True
        assert r["name"] == "deploy"
        assert "env" in r["variables"]
        assert "version" in r["variables"]
        assert tb.template_count == 1

    def test_create_with_explicit_vars(self):
        tb = TaskTemplateBuilder()
        r = tb.create_template(
            name="test",
            pattern="run tests",
            variables=["target"],
        )
        assert r["variables"] == ["target"]

    def test_create_no_variables(self):
        tb = TaskTemplateBuilder()
        r = tb.create_template(
            name="simple",
            pattern="run all tests",
        )
        assert r["variables"] == []


class TestTemplateBuilderExtract:
    """Şablon çıkarma testleri."""

    def test_extract_no_examples(self):
        tb = TaskTemplateBuilder()
        r = tb.extract_template([])
        assert "error" in r

    def test_extract_single_example(self):
        tb = TaskTemplateBuilder()
        r = tb.extract_template(
            ["deploy production v1"],
        )
        assert r["created"] is True

    def test_extract_multiple_examples(self):
        tb = TaskTemplateBuilder()
        r = tb.extract_template(
            [
                "deploy production v1",
                "deploy staging v2",
                "deploy testing v3",
            ],
            name="deploy_tmpl",
        )
        assert r["created"] is True
        assert r["name"] == "deploy_tmpl"
        # "deploy" ortak, geri kalanı değişken
        assert len(r["variables"]) >= 1


class TestTemplateBuilderApply:
    """Şablon uygulama testleri."""

    def test_apply_template(self):
        tb = TaskTemplateBuilder()
        cr = tb.create_template(
            name="deploy",
            pattern="deploy {env} {ver}",
        )
        tid = cr["template_id"]
        r = tb.apply_template(
            tid,
            {"env": "prod", "ver": "v2"},
        )
        assert r["applied"] is True
        assert r["result"] == "deploy prod v2"
        assert tb.usage_count == 1

    def test_apply_nonexistent(self):
        tb = TaskTemplateBuilder()
        r = tb.apply_template(
            "invalid", {},
        )
        assert "error" in r

    def test_update_version(self):
        tb = TaskTemplateBuilder()
        cr = tb.create_template(
            name="test",
            pattern="run {suite}",
        )
        tid = cr["template_id"]
        r = tb.update_version(
            tid, "execute {suite} {mode}",
        )
        assert r["updated"] is True
        assert r["version"] == 2

    def test_update_nonexistent(self):
        tb = TaskTemplateBuilder()
        r = tb.update_version(
            "invalid", "pattern",
        )
        assert "error" in r

    def test_get_template(self):
        tb = TaskTemplateBuilder()
        cr = tb.create_template(
            name="test",
            pattern="run {suite}",
        )
        tid = cr["template_id"]
        t = tb.get_template(tid)
        assert t["name"] == "test"

    def test_get_nonexistent(self):
        tb = TaskTemplateBuilder()
        t = tb.get_template("invalid")
        assert "error" in t

    def test_get_templates_by_category(self):
        tb = TaskTemplateBuilder()
        tb.create_template(
            name="a",
            pattern="p",
            category="deploy",
        )
        tb.create_template(
            name="b",
            pattern="q",
            category="test",
        )
        r = tb.get_templates(category="deploy")
        assert len(r) == 1


# =========== QualityImprover ===========


class TestQualityImproverInit:
    """QualityImprover başlatma testleri."""

    def test_default_init(self):
        qi = QualityImprover()
        assert qi.score_count == 0
        assert qi.practice_count == 0

    def test_criteria_defined(self):
        assert "completeness" in (
            QualityImprover.QUALITY_CRITERIA
        )
        assert "accuracy" in (
            QualityImprover.QUALITY_CRITERIA
        )
        total = sum(
            QualityImprover
            .QUALITY_CRITERIA.values(),
        )
        assert abs(total - 1.0) < 0.01


class TestQualityImproverScore:
    """Kalite puanlama testleri."""

    def test_score_quality(self):
        qi = QualityImprover()
        r = qi.score_quality(
            "task_1",
            {
                "completeness": 4.5,
                "accuracy": 4.0,
                "clarity": 3.5,
                "timeliness": 4.0,
                "relevance": 4.0,
            },
        )
        assert r["scored"] is True
        assert r["overall"] > 0
        assert r["level"] in (
            "excellent", "good",
            "average", "poor",
        )
        assert qi.score_count == 1

    def test_score_excellent(self):
        qi = QualityImprover()
        r = qi.score_quality(
            "t1",
            {
                "completeness": 5.0,
                "accuracy": 5.0,
                "clarity": 5.0,
                "timeliness": 5.0,
                "relevance": 5.0,
            },
        )
        assert r["level"] == "excellent"

    def test_score_poor(self):
        qi = QualityImprover()
        r = qi.score_quality(
            "t1",
            {
                "completeness": 1.0,
                "accuracy": 1.0,
                "clarity": 1.0,
                "timeliness": 1.0,
                "relevance": 1.0,
            },
        )
        assert r["level"] == "poor"


class TestQualityImproverSuggestions:
    """İyileştirme önerisi testleri."""

    def test_suggest_improvements(self):
        qi = QualityImprover()
        r = qi.suggest_improvements(
            "task_1",
            {
                "completeness": 2.0,
                "accuracy": 4.5,
                "clarity": 1.5,
            },
        )
        assert r["count"] >= 2
        # Impact sıralaması
        if r["count"] >= 2:
            assert (
                r["suggestions"][0]["impact"]
                >= r["suggestions"][1]["impact"]
            )

    def test_no_suggestions_needed(self):
        qi = QualityImprover()
        r = qi.suggest_improvements(
            "task_1",
            {
                "completeness": 4.5,
                "accuracy": 4.0,
                "clarity": 3.5,
                "timeliness": 4.0,
                "relevance": 4.0,
            },
        )
        assert r["count"] == 0


class TestQualityImproverEnhance:
    """Otomatik geliştirme testleri."""

    def test_auto_enhance_structure(self):
        qi = QualityImprover()
        r = qi.auto_enhance("Some content")
        assert "enhanced_content" in r
        assert r["enhanced_content"].startswith(
            "#",
        )

    def test_auto_enhance_already_structured(self):
        qi = QualityImprover()
        r = qi.auto_enhance("# Title\nContent")
        assert r["enhanced"] is False

    def test_auto_enhance_long_content(self):
        qi = QualityImprover()
        long = "x" * 600
        r = qi.auto_enhance(long)
        assert r["enhanced"] is True

    def test_custom_enhancements(self):
        qi = QualityImprover()
        r = qi.auto_enhance(
            "test",
            enhancements=["add_structure"],
        )
        assert "enhanced_content" in r


class TestQualityImproverAB:
    """A/B test testleri."""

    def test_run_ab_test(self):
        qi = QualityImprover()
        r = qi.run_ab_test(
            {"overall": 4.5},
            {"overall": 3.5},
        )
        assert r["winner"] == "A"
        assert r["improvement"] == 1.0

    def test_ab_test_tie(self):
        qi = QualityImprover()
        r = qi.run_ab_test(
            {"overall": 4.0},
            {"overall": 4.0},
        )
        assert r["winner"] == "tie"

    def test_ab_test_b_wins(self):
        qi = QualityImprover()
        r = qi.run_ab_test(
            {"overall": 2.0},
            {"overall": 4.0},
        )
        assert r["winner"] == "B"


class TestQualityImproverPractices:
    """En iyi uygulama testleri."""

    def test_learn_practice(self):
        qi = QualityImprover()
        r = qi.learn_best_practice(
            "Always test",
            category="testing",
        )
        assert r["learned"] is True
        assert qi.practice_count == 1

    def test_quality_trend_no_data(self):
        qi = QualityImprover()
        r = qi.get_quality_trend()
        assert r["trend"] == "no_data"

    def test_quality_trend_insufficient(self):
        qi = QualityImprover()
        qi.score_quality(
            "t1",
            {"completeness": 4.0},
        )
        r = qi.get_quality_trend()
        assert r["trend"] == "insufficient_data"


# =========== CommandPredictor ===========


class TestCommandPredictorInit:
    """CommandPredictor başlatma testleri."""

    def test_default_init(self):
        cp = CommandPredictor()
        assert cp.prediction_count == 0
        assert cp.accuracy == 0.0


class TestCommandPredictorObserve:
    """Gözlem testleri."""

    def test_observe(self):
        cp = CommandPredictor()
        r = cp.observe("git status")
        assert r["observed"] is True
        assert r["command"] == "git status"

    def test_observe_with_context(self):
        cp = CommandPredictor()
        r = cp.observe(
            "deploy", context="prod",
        )
        assert r["observed"] is True

    def test_observe_builds_transitions(self):
        cp = CommandPredictor()
        cp.observe("build")
        cp.observe("test")
        assert "build" in cp._transitions
        assert "test" in cp._transitions["build"]


class TestCommandPredictorPredict:
    """Tahmin testleri."""

    def test_predict_no_data(self):
        cp = CommandPredictor()
        r = cp.predict_next("unknown")
        assert r["predictions"] == []
        assert r["confidence"] == 0.0

    def test_predict_with_data(self):
        cp = CommandPredictor()
        cp.observe("build")
        cp.observe("test")
        cp.observe("build")
        cp.observe("test")
        r = cp.predict_next("build")
        assert len(r["predictions"]) >= 1
        assert (
            r["predictions"][0]["command"]
            == "test"
        )

    def test_predict_multiple(self):
        cp = CommandPredictor()
        cp.observe("build")
        cp.observe("test")
        cp.observe("build")
        cp.observe("deploy")
        r = cp.predict_next("build")
        assert len(r["predictions"]) >= 1


class TestCommandPredictorContext:
    """Bağlam önerisi testleri."""

    def test_suggest_by_context(self):
        cp = CommandPredictor()
        cp.observe("deploy", context="prod")
        cp.observe("restart", context="prod")
        r = cp.suggest_by_context("prod")
        assert r["count"] >= 1

    def test_suggest_empty_context(self):
        cp = CommandPredictor()
        r = cp.suggest_by_context("none")
        assert r["count"] == 0


class TestCommandPredictorTime:
    """Zaman kalıbı testleri."""

    def test_get_time_patterns(self):
        cp = CommandPredictor()
        cp.observe("standup", hour=9)
        cp.observe("standup", hour=9)
        r = cp.get_time_patterns(9)
        assert r["total"] >= 2
        assert "standup" in r["commands"]

    def test_time_patterns_empty(self):
        cp = CommandPredictor()
        r = cp.get_time_patterns(3)
        assert r["total"] == 0


class TestCommandPredictorWorkflow:
    """İş akışı testleri."""

    def test_define_workflow(self):
        cp = CommandPredictor()
        r = cp.define_workflow(
            "deploy_flow",
            ["build", "test", "deploy"],
        )
        assert r["defined"] is True
        assert r["steps"] == 3

    def test_predict_workflow(self):
        cp = CommandPredictor()
        cp.define_workflow(
            "deploy_flow",
            ["build", "test", "deploy"],
        )
        r = cp.predict_workflow("build")
        assert r["count"] >= 1
        wf = r["workflows"][0]
        assert wf["next_steps"] == [
            "test", "deploy",
        ]

    def test_predict_workflow_no_match(self):
        cp = CommandPredictor()
        r = cp.predict_workflow("unknown")
        assert r["count"] == 0


class TestCommandPredictorVerify:
    """Doğrulama testleri."""

    def test_verify_correct(self):
        cp = CommandPredictor()
        cp._stats["predictions_made"] = 1
        r = cp.verify_prediction(
            "test", "test",
        )
        assert r["correct"] is True

    def test_verify_incorrect(self):
        cp = CommandPredictor()
        cp._stats["predictions_made"] = 1
        r = cp.verify_prediction(
            "test", "deploy",
        )
        assert r["correct"] is False


# =========== ExecutionMemory ===========


class TestExecutionMemoryInit:
    """ExecutionMemory başlatma testleri."""

    def test_default_init(self):
        em = ExecutionMemory()
        assert em.execution_count == 0
        assert em.success_rate == 0.0


class TestExecutionMemoryRecord:
    """Yürütme kaydetme testleri."""

    def test_record_success(self):
        em = ExecutionMemory()
        r = em.record_execution(
            "task_1", "build",
            success=True,
            duration_ms=150.0,
        )
        assert r["recorded"] is True
        assert r["success"] is True
        assert em.execution_count == 1

    def test_record_failure(self):
        em = ExecutionMemory()
        em.record_execution(
            "task_1", "build",
            success=False,
            error="compile error",
        )
        assert em.success_rate == 0.0

    def test_success_rate(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "a", success=True,
        )
        em.record_execution(
            "t2", "b", success=True,
        )
        em.record_execution(
            "t3", "c", success=False,
        )
        assert em.success_rate == pytest.approx(
            0.667, abs=0.001,
        )


class TestExecutionMemoryAnalysis:
    """Yürütme analizi testleri."""

    def test_get_success_rate_all(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "build",
            success=True,
        )
        em.record_execution(
            "t2", "build",
            success=False,
        )
        r = em.get_success_rate()
        assert r["rate"] == 0.5
        assert r["total"] == 2

    def test_get_success_rate_by_command(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "build", success=True,
        )
        em.record_execution(
            "t2", "test", success=False,
        )
        r = em.get_success_rate(
            command="build",
        )
        assert r["rate"] == 1.0
        assert r["total"] == 1

    def test_get_success_rate_empty(self):
        em = ExecutionMemory()
        r = em.get_success_rate()
        assert r["rate"] == 0.0
        assert r["total"] == 0

    def test_get_duration_patterns(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "build",
            success=True,
            duration_ms=100.0,
        )
        em.record_execution(
            "t2", "build",
            success=True,
            duration_ms=200.0,
        )
        r = em.get_duration_patterns(
            command="build",
        )
        assert r["avg_ms"] == 150.0
        assert r["min_ms"] == 100.0
        assert r["max_ms"] == 200.0
        assert r["count"] == 2

    def test_duration_patterns_empty(self):
        em = ExecutionMemory()
        r = em.get_duration_patterns()
        assert r["avg_ms"] == 0.0
        assert r["count"] == 0

    def test_get_resource_usage(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "build",
            success=True,
            resource_usage={
                "cpu": 80.0,
                "memory": 512.0,
            },
        )
        em.record_execution(
            "t2", "build",
            success=True,
            resource_usage={
                "cpu": 60.0,
                "memory": 256.0,
            },
        )
        r = em.get_resource_usage(
            command="build",
        )
        assert r["count"] == 2
        assert r["avg_resources"]["cpu"] == 70.0

    def test_resource_usage_empty(self):
        em = ExecutionMemory()
        r = em.get_resource_usage()
        assert r["count"] == 0


class TestExecutionMemoryHints:
    """Optimizasyon ipuçları testleri."""

    def test_generate_hints_empty(self):
        em = ExecutionMemory()
        r = em.generate_hints()
        assert r["count"] == 0

    def test_hint_slow_command(self):
        em = ExecutionMemory()
        for i in range(3):
            em.record_execution(
                f"t_{i}", "heavy_build",
                success=True,
                duration_ms=6000.0,
            )
        r = em.generate_hints()
        slow = [
            h for h in r["hints"]
            if h["type"] == "slow_command"
        ]
        assert len(slow) >= 1

    def test_hint_high_failure(self):
        em = ExecutionMemory()
        for i in range(4):
            em.record_execution(
                f"t_{i}", "flaky_cmd",
                success=False,
            )
        r = em.generate_hints()
        fail = [
            h for h in r["hints"]
            if h["type"] == "high_failure"
        ]
        assert len(fail) >= 1

    def test_get_history(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "build", success=True,
        )
        em.record_execution(
            "t2", "test", success=False,
        )
        h = em.get_history(task_id="t1")
        assert len(h) == 1

    def test_get_history_by_success(self):
        em = ExecutionMemory()
        em.record_execution(
            "t1", "a", success=True,
        )
        em.record_execution(
            "t2", "b", success=False,
        )
        h = em.get_history(success=True)
        assert len(h) == 1

    def test_get_history_limit(self):
        em = ExecutionMemory()
        for i in range(30):
            em.record_execution(
                f"t_{i}", "cmd",
                success=True,
            )
        h = em.get_history(limit=10)
        assert len(h) == 10


# ========= PersonalizationEngine =========


class TestPersonalizationInit:
    """PersonalizationEngine başlatma."""

    def test_default_init(self):
        pe = PersonalizationEngine()
        assert pe.adaptation_count == 0
        assert pe.learning_count == 0

    def test_custom_level(self):
        pe = PersonalizationEngine(
            level="aggressive",
        )
        assert pe._level == "aggressive"


class TestPersonalizationProfile:
    """Profil testleri."""

    def test_get_profile(self):
        pe = PersonalizationEngine()
        p = pe.get_profile()
        assert p["expertise"] == "intermediate"
        assert (
            p["communication_style"]
            == "professional"
        )

    def test_update_profile(self):
        pe = PersonalizationEngine()
        r = pe.update_profile(
            expertise="expert",
        )
        assert r["updated"] is True
        assert r["count"] == 1
        p = pe.get_profile()
        assert p["expertise"] == "expert"

    def test_update_invalid_field(self):
        pe = PersonalizationEngine()
        r = pe.update_profile(invalid="x")
        assert r["count"] == 0
        assert r["updated"] is False


class TestPersonalizationAdapt:
    """Adaptasyon testleri."""

    def test_adapt_response(self):
        pe = PersonalizationEngine()
        r = pe.adapt_response(
            "Hello world",
        )
        assert r["adapted"] is True
        assert "adapted_content" in r
        assert pe.adaptation_count == 1

    def test_adapt_brief(self):
        pe = PersonalizationEngine()
        pe.update_profile(
            detail_preference="brief",
        )
        long_content = "\n".join(
            [f"Line {i}" for i in range(10)],
        )
        r = pe.adapt_response(long_content)
        assert "brevity" in r["adaptations"]

    def test_adapt_casual(self):
        pe = PersonalizationEngine()
        pe.update_profile(
            communication_style="casual",
        )
        r = pe.adapt_response(
            "Dear User, welcome",
        )
        assert "casual_tone" in r["adaptations"]
        assert (
            "Hi" in r["adapted_content"]
        )

    def test_adapt_detailed(self):
        pe = PersonalizationEngine()
        pe.update_profile(
            detail_preference="detailed",
        )
        r = pe.adapt_response("Content")
        assert (
            "keep_detailed" in r["adaptations"]
        )


class TestPersonalizationPreferences:
    """Tercih uygulama testleri."""

    def test_apply_preferences(self):
        pe = PersonalizationEngine()
        r = pe.apply_preferences(
            {"timeout": 30},
        )
        assert r["personalized"] is True
        assert (
            r["config"]["detail_level"]
            == "medium"
        )
        assert (
            r["config"]["style"]
            == "professional"
        )

    def test_apply_preserves_existing(self):
        pe = PersonalizationEngine()
        r = pe.apply_preferences(
            {
                "timeout": 30,
                "detail_level": "high",
            },
        )
        assert r["config"]["detail_level"] == "high"
        assert r["config"]["timeout"] == 30


class TestPersonalizationContext:
    """Bağlam adaptasyonu testleri."""

    def test_adapt_to_context_high(self):
        pe = PersonalizationEngine()
        r = pe.adapt_to_context(
            "emergency", urgency="high",
        )
        assert r["adapted"] is True
        assert (
            r["recommendations"]["detail"]
            == "brief"
        )

    def test_adapt_to_context_low(self):
        pe = PersonalizationEngine()
        r = pe.adapt_to_context(
            "routine", urgency="low",
        )
        assert r["adapted"] is True
        assert (
            r["recommendations"]["format"]
            == "structured"
        )

    def test_adapt_to_context_normal(self):
        pe = PersonalizationEngine()
        r = pe.adapt_to_context("normal")
        assert (
            r["recommendations"]["detail"]
            == "medium"
        )


class TestPersonalizationLearn:
    """Öğrenme testleri."""

    def test_learn(self):
        pe = PersonalizationEngine()
        r = pe.learn(
            "User prefers tables",
            category="format",
            confidence=0.8,
        )
        assert r["learned"] is True
        assert pe.learning_count == 1

    def test_learning_summary(self):
        pe = PersonalizationEngine()
        pe.learn("obs1", category="format")
        pe.learn("obs2", category="format")
        pe.learn("obs3", category="speed")
        r = pe.get_learning_summary()
        assert r["total_learnings"] == 3
        assert r["by_category"]["format"] == 2
        assert r["by_category"]["speed"] == 1


# ========= TaskMemOrchestrator =========


class TestOrchestratorInit:
    """TaskMemOrchestrator başlatma."""

    def test_default_init(self):
        o = TaskMemOrchestrator()
        assert o.task_count == 0

    def test_custom_init(self):
        o = TaskMemOrchestrator(
            learning_rate=0.5,
            personalization_level="aggressive",
        )
        assert o._learning_rate == 0.5


class TestOrchestratorProcessTask:
    """Görev işleme testleri."""

    def test_process_task(self):
        o = TaskMemOrchestrator()
        r = o.process_task(
            task_id="t1",
            command="build",
            context="ci",
            success=True,
            duration_ms=100.0,
        )
        assert r["processed"] is True
        assert r["task_id"] == "t1"
        assert r["success"] is True
        assert o.task_count == 1

    def test_process_multiple(self):
        o = TaskMemOrchestrator()
        for i in range(5):
            o.process_task(
                task_id=f"t_{i}",
                command="test",
            )
        assert o.task_count == 5

    def test_process_with_prediction(self):
        o = TaskMemOrchestrator()
        o.process_task(
            "t1", "build", context="ci",
        )
        o.process_task(
            "t2", "test", context="ci",
        )
        r = o.process_task(
            "t3", "build", context="ci",
        )
        assert "next_prediction" in r


class TestOrchestratorFeedback:
    """Geri bildirim öğrenme testleri."""

    def test_learn_from_feedback_high(self):
        o = TaskMemOrchestrator()
        r = o.learn_from_feedback(
            "t1", rating=4.5,
        )
        assert r["learned"] is True
        assert r["rating"] == 4.5

    def test_learn_from_feedback_low(self):
        o = TaskMemOrchestrator()
        r = o.learn_from_feedback(
            "t1",
            rating=1.5,
            comment="Too slow",
        )
        assert r["learned"] is True

    def test_learn_neutral(self):
        o = TaskMemOrchestrator()
        r = o.learn_from_feedback(
            "t1", rating=3.0,
        )
        assert r["learned"] is True


class TestOrchestratorPersonalize:
    """Kişiselleştirme testleri."""

    def test_personalize_output(self):
        o = TaskMemOrchestrator()
        r = o.personalize_output(
            content="Test content",
            task_type="report",
        )
        assert r["personalized"] is True
        assert "personalized_content" in r

    def test_personalize_with_context(self):
        o = TaskMemOrchestrator()
        r = o.personalize_output(
            content="Data",
            task_type="analysis",
            context="urgent",
        )
        assert r["personalized"] is True


class TestOrchestratorAnalytics:
    """Analitik testleri."""

    def test_get_analytics(self):
        o = TaskMemOrchestrator()
        o.process_task("t1", "build")
        a = o.get_analytics()
        assert a["tasks_processed"] == 1
        assert "patterns_learned" in a
        assert "commands_recorded" in a
        assert "predictions_made" in a
        assert "prediction_accuracy" in a
        assert "executions_recorded" in a
        assert "success_rate" in a
        assert "feedbacks_received" in a
        assert "templates_created" in a
        assert "quality_scores" in a
        assert "adaptations" in a

    def test_get_status(self):
        o = TaskMemOrchestrator()
        s = o.get_status()
        assert "tasks_processed" in s
        assert "patterns" in s
        assert "templates" in s
        assert "satisfaction" in s
        assert "prediction_accuracy" in s


class TestOrchestratorIntegration:
    """Entegrasyon testleri."""

    def test_full_pipeline(self):
        o = TaskMemOrchestrator()

        # 1. Görevler işle
        for i in range(5):
            o.process_task(
                f"t_{i}", "build",
                success=True,
                duration_ms=100.0,
            )

        # 2. Geri bildirim
        o.learn_from_feedback("t_0", 4.5)
        o.learn_from_feedback("t_1", 3.0)

        # 3. Kişiselleştir
        r = o.personalize_output(
            "Report content",
            task_type="report",
        )
        assert r["personalized"] is True

        # 4. Analitik kontrol
        a = o.get_analytics()
        assert a["tasks_processed"] == 5
        assert a["learnings_applied"] == 2
        assert a["improvements_made"] == 1

    def test_repeated_commands_generate_patterns(
        self,
    ):
        o = TaskMemOrchestrator()
        for i in range(10):
            o.process_task(
                f"t_{i}", "deploy",
                success=True,
            )

        a = o.get_analytics()
        assert a["patterns_learned"] >= 1

    def test_status_after_feedback(self):
        o = TaskMemOrchestrator()
        o.learn_from_feedback("t1", 4.0)
        o.learn_from_feedback("t2", 5.0)
        s = o.get_status()
        assert s["satisfaction"] > 0


# =========== Config ===========


class TestTaskMemConfig:
    """Task memory config testleri."""

    def test_config_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.taskmem_enabled is True
        assert s.learning_rate == 0.1
        assert s.template_auto_create is True
        assert s.prediction_enabled is True
        assert (
            s.personalization_level == "moderate"
        )


# =========== Imports ===========


class TestTaskMemImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.taskmem import (
            CommandPatternLearner,
            CommandPredictor,
            ExecutionMemory,
            PersonalizationEngine,
            QualityImprover,
            TaskFeedbackIntegrator,
            TaskMemOrchestrator,
            TaskPreferenceTracker,
            TaskTemplateBuilder,
        )

        assert CommandPatternLearner is not None
        assert CommandPredictor is not None
        assert ExecutionMemory is not None
        assert PersonalizationEngine is not None
        assert QualityImprover is not None
        assert TaskFeedbackIntegrator is not None
        assert TaskMemOrchestrator is not None
        assert TaskPreferenceTracker is not None
        assert TaskTemplateBuilder is not None

    def test_import_models(self):
        from app.models.taskmem_models import (
            FeedbackRecord,
            FeedbackType,
            PatternRecord,
            PatternType,
            PersonalizationMode,
            PredictionConfidence,
            QualityLevel,
            TaskMemSnapshot,
            TemplateRecord,
            TemplateStatus,
        )

        assert PatternType is not None
        assert FeedbackType is not None
        assert QualityLevel is not None
        assert PersonalizationMode is not None
        assert TemplateStatus is not None
        assert PredictionConfidence is not None
        assert PatternRecord is not None
        assert FeedbackRecord is not None
        assert TemplateRecord is not None
        assert TaskMemSnapshot is not None
