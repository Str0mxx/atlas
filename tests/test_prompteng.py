"""
Prompt Engineering & Optimization testleri.
"""

import pytest

from app.core.prompteng.ab_prompt_tester import (
    ABPromptTester,
)
from app.core.prompteng.chain_of_thought_builder import (
    ChainOfThoughtBuilder,
)
from app.core.prompteng.context_window_manager import (
    ContextWindowManager,
)
from app.core.prompteng.few_shot_selector import (
    FewShotSelector,
)
from app.core.prompteng.prompt_optimizer import (
    PromptOptimizer,
)
from app.core.prompteng.prompt_performance_tracker import (
    PromptPerformanceTracker,
)
from app.core.prompteng.prompt_template_library import (
    PromptTemplateLibrary,
)
from app.core.prompteng.prompt_version_control import (
    PromptVersionControl,
)
from app.core.prompteng.prompteng_orchestrator import (
    PromptEngOrchestrator,
)


# ===================== PromptTemplateLibrary =====================


class TestPromptTemplateLibrary:
    """PromptTemplateLibrary testleri."""

    def setup_method(self) -> None:
        self.lib = PromptTemplateLibrary()

    def test_init(self) -> None:
        assert self.lib.template_count == 0

    def test_create_category(self) -> None:
        r = self.lib.create_category(
            name="coding",
            description="Kodlama sablonlari",
        )
        assert r["created"] is True
        assert r["name"] == "coding"

    def test_create_template(self) -> None:
        r = self.lib.create_template(
            name="test",
            content="Hello {{name}}",
            category="general",
        )
        assert r["created"] is True
        assert "name" in r["variables"]
        assert self.lib.template_count == 1

    def test_create_template_multi_vars(self) -> None:
        r = self.lib.create_template(
            name="multi",
            content="{{greeting}} {{name}}, age {{age}}",
        )
        assert r["created"] is True
        assert len(r["variables"]) == 3

    def test_render_template(self) -> None:
        t = self.lib.create_template(
            name="greet",
            content="Hello {{name}}!",
        )
        r = self.lib.render_template(
            template_id=t["template_id"],
            variables={"name": "World"},
        )
        assert r["rendered"] is True
        assert "World" in r["content"]

    def test_render_missing_template(self) -> None:
        r = self.lib.render_template(
            template_id="bad"
        )
        assert r["rendered"] is False

    def test_get_template(self) -> None:
        t = self.lib.create_template(
            name="t1",
            content="test",
        )
        r = self.lib.get_template(
            template_id=t["template_id"]
        )
        assert r["retrieved"] is True

    def test_get_missing_template(self) -> None:
        r = self.lib.get_template(
            template_id="bad"
        )
        assert r["retrieved"] is False

    def test_update_template(self) -> None:
        t = self.lib.create_template(
            name="u1",
            content="v1",
        )
        r = self.lib.update_template(
            template_id=t["template_id"],
            content="v2 {{x}}",
        )
        assert r["updated"] is True
        assert r["version"] == 2

    def test_update_missing_template(self) -> None:
        r = self.lib.update_template(
            template_id="bad",
            content="x",
        )
        assert r["updated"] is False

    def test_search_templates(self) -> None:
        self.lib.create_template(
            name="code helper",
            content="code prompt",
            category="coding",
            tags=["python"],
        )
        r = self.lib.search_templates(
            query="code"
        )
        assert r["found"] is True
        assert r["count"] >= 1

    def test_search_by_category(self) -> None:
        self.lib.create_template(
            name="c1",
            content="ct",
            category="writing",
        )
        r = self.lib.search_templates(
            category="writing"
        )
        assert r["found"] is True

    def test_search_by_tags(self) -> None:
        self.lib.create_template(
            name="t1",
            content="tc",
            tags=["sql", "db"],
        )
        r = self.lib.search_templates(
            tags=["sql"]
        )
        assert r["found"] is True

    def test_list_by_category(self) -> None:
        self.lib.create_template(
            name="lc",
            content="x",
            category="testing",
        )
        r = self.lib.list_by_category(
            category="testing"
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_template_inheritance(self) -> None:
        parent = self.lib.create_template(
            name="parent",
            content="Base: {{base_var}}",
        )
        child = self.lib.create_template(
            name="child",
            content="Child: {{child_var}}",
            parent_template=parent["template_id"],
        )
        assert child["created"] is True
        assert "base_var" in child["variables"]
        assert "child_var" in child["variables"]

    def test_get_summary(self) -> None:
        r = self.lib.get_summary()
        assert r["retrieved"] is True


# ===================== PromptOptimizer =====================


class TestPromptOptimizer:
    """PromptOptimizer testleri."""

    def setup_method(self) -> None:
        self.opt = PromptOptimizer()

    def test_init(self) -> None:
        assert self.opt.optimization_count == 0

    def test_optimize_basic(self) -> None:
        r = self.opt.optimize(
            prompt="This is a  test prompt"
        )
        assert r["optimized"] is True

    def test_optimize_removes_spaces(self) -> None:
        r = self.opt.optimize(
            prompt="Hello   world   test",
            optimization_types=["length_reduction"],
        )
        assert r["optimized"] is True
        assert "  " not in r["optimized_prompt"]

    def test_optimize_removes_redundancy(self) -> None:
        r = self.opt.optimize(
            prompt="Do this. Do this. Do that.",
            optimization_types=["redundancy_removal"],
        )
        assert r["optimized"] is True

    def test_optimize_clarity(self) -> None:
        r = self.opt.optimize(
            prompt="kind of do this task",
            optimization_types=["clarity_improvement"],
        )
        assert r["optimized"] is True
        assert "kind of" not in r["optimized_prompt"]

    def test_optimize_token_target(self) -> None:
        long_text = " ".join(
            [f"word{i}" for i in range(100)]
        )
        r = self.opt.optimize(
            prompt=long_text,
            target_tokens=20,
            optimization_types=["token_optimization"],
        )
        assert r["optimized"] is True
        assert r["optimized_words"] < 100

    def test_optimize_structure(self) -> None:
        r = self.opt.optimize(
            prompt="some text",
            optimization_types=["structure_enhancement"],
        )
        assert r["optimized"] is True

    def test_optimize_all_types(self) -> None:
        r = self.opt.optimize(
            prompt="kind of  do  this task. Do this task."
        )
        assert r["optimized"] is True
        assert len(r["applied"]) >= 1

    def test_add_rule(self) -> None:
        r = self.opt.add_rule(
            name="test_rule",
            rule_type="replace",
            pattern="foo",
            replacement="bar",
        )
        assert r["added"] is True

    def test_analyze_prompt(self) -> None:
        r = self.opt.analyze_prompt(
            prompt="This is a test prompt for analysis."
        )
        assert r["analyzed"] is True
        assert r["word_count"] > 0
        assert r["quality_score"] > 0

    def test_analyze_empty(self) -> None:
        r = self.opt.analyze_prompt(prompt="  ")
        assert r["analyzed"] is True
        assert r["quality_score"] == 0.0

    def test_analyze_short(self) -> None:
        r = self.opt.analyze_prompt(prompt="Hi")
        assert r["analyzed"] is True
        assert "too_short" in r["issues"]

    def test_get_summary(self) -> None:
        self.opt.optimize(prompt="test")
        r = self.opt.get_summary()
        assert r["retrieved"] is True
        assert r["total_optimizations"] >= 1


# ===================== PromptVersionControl =====================


class TestPromptVersionControl:
    """PromptVersionControl testleri."""

    def setup_method(self) -> None:
        self.vc = PromptVersionControl()

    def test_init(self) -> None:
        assert self.vc.prompt_count == 0

    def test_track_prompt(self) -> None:
        r = self.vc.track_prompt(
            name="test",
            content="v1 content",
            author="user",
        )
        assert r["tracked"] is True
        assert r["version"] == 1
        assert self.vc.prompt_count == 1

    def test_commit(self) -> None:
        t = self.vc.track_prompt(
            name="t1",
            content="v1",
        )
        r = self.vc.commit(
            prompt_id=t["prompt_id"],
            content="v2",
            message="Update",
            author="user",
        )
        assert r["committed"] is True
        assert r["version"] == 2

    def test_commit_missing(self) -> None:
        r = self.vc.commit(
            prompt_id="bad",
            content="x",
        )
        assert r["committed"] is False

    def test_get_history(self) -> None:
        t = self.vc.track_prompt(
            name="h1",
            content="v1",
        )
        self.vc.commit(
            prompt_id=t["prompt_id"],
            content="v2",
            message="Change",
        )
        r = self.vc.get_history(
            prompt_id=t["prompt_id"]
        )
        assert r["retrieved"] is True
        assert r["total_versions"] == 2

    def test_get_history_missing(self) -> None:
        r = self.vc.get_history(prompt_id="bad")
        assert r["retrieved"] is False

    def test_diff(self) -> None:
        t = self.vc.track_prompt(
            name="d1",
            content="hello world",
        )
        self.vc.commit(
            prompt_id=t["prompt_id"],
            content="hello universe",
        )
        r = self.vc.diff(
            prompt_id=t["prompt_id"],
            version_a=1,
            version_b=2,
        )
        assert r["diffed"] is True
        assert r["changed"] is True

    def test_diff_missing_version(self) -> None:
        t = self.vc.track_prompt(
            name="dm",
            content="x",
        )
        r = self.vc.diff(
            prompt_id=t["prompt_id"],
            version_a=1,
            version_b=99,
        )
        assert r["diffed"] is False

    def test_diff_missing_prompt(self) -> None:
        r = self.vc.diff(
            prompt_id="bad",
            version_a=1,
            version_b=2,
        )
        assert r["diffed"] is False

    def test_rollback(self) -> None:
        t = self.vc.track_prompt(
            name="rb",
            content="original",
        )
        self.vc.commit(
            prompt_id=t["prompt_id"],
            content="changed",
        )
        r = self.vc.rollback(
            prompt_id=t["prompt_id"],
            target_version=1,
        )
        assert r["rolled_back"] is True
        assert r["new_version"] == 3

    def test_rollback_missing(self) -> None:
        r = self.vc.rollback(
            prompt_id="bad",
            target_version=1,
        )
        assert r["rolled_back"] is False

    def test_rollback_missing_version(self) -> None:
        t = self.vc.track_prompt(
            name="rbm",
            content="x",
        )
        r = self.vc.rollback(
            prompt_id=t["prompt_id"],
            target_version=99,
        )
        assert r["rolled_back"] is False

    def test_create_branch(self) -> None:
        t = self.vc.track_prompt(
            name="br",
            content="main content",
        )
        r = self.vc.create_branch(
            prompt_id=t["prompt_id"],
            branch_name="experiment",
        )
        assert r["created"] is True

    def test_create_branch_from_version(self) -> None:
        t = self.vc.track_prompt(
            name="bv",
            content="v1",
        )
        self.vc.commit(
            prompt_id=t["prompt_id"],
            content="v2",
        )
        r = self.vc.create_branch(
            prompt_id=t["prompt_id"],
            branch_name="fix",
            from_version=1,
        )
        assert r["created"] is True
        assert r["from_version"] == 1

    def test_create_branch_missing(self) -> None:
        r = self.vc.create_branch(
            prompt_id="bad",
            branch_name="x",
        )
        assert r["created"] is False

    def test_get_summary(self) -> None:
        r = self.vc.get_summary()
        assert r["retrieved"] is True


# ===================== ABPromptTester =====================


class TestABPromptTester:
    """ABPromptTester testleri."""

    def setup_method(self) -> None:
        self.ab = ABPromptTester()

    def test_init(self) -> None:
        assert self.ab.test_count == 0

    def test_create_test(self) -> None:
        r = self.ab.create_test(
            name="test1",
            prompt_a="Prompt A",
            prompt_b="Prompt B",
        )
        assert r["created"] is True
        assert r["status"] == "running"

    def test_record_result(self) -> None:
        t = self.ab.create_test(
            name="t1",
            prompt_a="A",
            prompt_b="B",
            sample_size=10,
        )
        r = self.ab.record_result(
            test_id=t["test_id"],
            variant="a",
            score=0.8,
        )
        assert r["recorded"] is True

    def test_record_invalid_variant(self) -> None:
        t = self.ab.create_test(
            name="iv",
            prompt_a="A",
            prompt_b="B",
        )
        r = self.ab.record_result(
            test_id=t["test_id"],
            variant="c",
        )
        assert r["recorded"] is False

    def test_record_missing_test(self) -> None:
        r = self.ab.record_result(
            test_id="bad",
            variant="a",
        )
        assert r["recorded"] is False

    def test_auto_completion(self) -> None:
        t = self.ab.create_test(
            name="ac",
            prompt_a="A",
            prompt_b="B",
            sample_size=6,
        )
        tid = t["test_id"]
        for i in range(3):
            self.ab.record_result(
                test_id=tid,
                variant="a",
                score=0.9,
            )
        for i in range(3):
            self.ab.record_result(
                test_id=tid,
                variant="b",
                score=0.3,
            )
        r = self.ab.get_test_results(
            test_id=tid
        )
        assert r["status"] == "completed"

    def test_get_test_results(self) -> None:
        t = self.ab.create_test(
            name="tr",
            prompt_a="A",
            prompt_b="B",
        )
        self.ab.record_result(
            test_id=t["test_id"],
            variant="a",
            score=0.7,
        )
        r = self.ab.get_test_results(
            test_id=t["test_id"]
        )
        assert r["retrieved"] is True
        assert r["variant_a"]["count"] == 1

    def test_get_results_missing(self) -> None:
        r = self.ab.get_test_results(
            test_id="bad"
        )
        assert r["retrieved"] is False

    def test_promote_winner(self) -> None:
        t = self.ab.create_test(
            name="pw",
            prompt_a="Good prompt",
            prompt_b="Bad prompt",
            sample_size=6,
        )
        tid = t["test_id"]
        for _ in range(3):
            self.ab.record_result(
                test_id=tid,
                variant="a",
                score=0.95,
            )
            self.ab.record_result(
                test_id=tid,
                variant="b",
                score=0.2,
            )
        r = self.ab.promote_winner(
            test_id=tid
        )
        assert r["promoted"] is True

    def test_promote_no_winner(self) -> None:
        t = self.ab.create_test(
            name="nw",
            prompt_a="A",
            prompt_b="B",
        )
        r = self.ab.promote_winner(
            test_id=t["test_id"]
        )
        assert r["promoted"] is False

    def test_promote_missing(self) -> None:
        r = self.ab.promote_winner(
            test_id="bad"
        )
        assert r["promoted"] is False

    def test_extract_learning(self) -> None:
        t = self.ab.create_test(
            name="el",
            prompt_a="A",
            prompt_b="B",
            sample_size=4,
        )
        tid = t["test_id"]
        for _ in range(2):
            self.ab.record_result(
                test_id=tid,
                variant="a",
                score=0.9,
            )
            self.ab.record_result(
                test_id=tid,
                variant="b",
                score=0.3,
            )
        r = self.ab.extract_learning(
            test_id=tid
        )
        assert r["extracted"] is True
        assert r["score_diff"] > 0

    def test_extract_missing(self) -> None:
        r = self.ab.extract_learning(
            test_id="bad"
        )
        assert r["extracted"] is False

    def test_record_completed_test(self) -> None:
        t = self.ab.create_test(
            name="ct",
            prompt_a="A",
            prompt_b="B",
            sample_size=4,
        )
        tid = t["test_id"]
        for _ in range(2):
            self.ab.record_result(
                test_id=tid,
                variant="a",
                score=0.9,
            )
            self.ab.record_result(
                test_id=tid,
                variant="b",
                score=0.1,
            )
        r = self.ab.record_result(
            test_id=tid,
            variant="a",
            score=0.5,
        )
        assert r["recorded"] is False

    def test_get_summary(self) -> None:
        r = self.ab.get_summary()
        assert r["retrieved"] is True


# ===================== ContextWindowManager =====================


class TestContextWindowManager:
    """ContextWindowManager testleri."""

    def setup_method(self) -> None:
        self.cwm = ContextWindowManager()

    def test_init(self) -> None:
        assert self.cwm.window_count == 0

    def test_count_tokens(self) -> None:
        r = self.cwm.count_tokens(
            text="Hello world test"
        )
        assert r["counted"] is True
        assert r["word_count"] == 3
        assert r["estimated_tokens"] > 0

    def test_create_window(self) -> None:
        r = self.cwm.create_window(
            name="test",
            max_tokens=4096,
            system_prompt="You are helpful.",
            reserved_output=500,
        )
        assert r["created"] is True
        assert r["available_tokens"] > 0

    def test_add_segment(self) -> None:
        w = self.cwm.create_window(
            name="seg",
            max_tokens=4096,
        )
        r = self.cwm.add_segment(
            window_id=w["window_id"],
            content="Test segment content",
            priority="high",
        )
        assert r["added"] is True
        assert r["tokens"] > 0

    def test_add_segment_missing(self) -> None:
        r = self.cwm.add_segment(
            window_id="bad",
            content="x",
        )
        assert r["added"] is False

    def test_fit_context_no_overflow(self) -> None:
        w = self.cwm.create_window(
            name="fit",
            max_tokens=4096,
        )
        self.cwm.add_segment(
            window_id=w["window_id"],
            content="short",
        )
        r = self.cwm.fit_context(
            window_id=w["window_id"]
        )
        assert r["fitted"] is True
        assert r["truncated"] is False

    def test_fit_context_with_overflow(self) -> None:
        w = self.cwm.create_window(
            name="overflow",
            max_tokens=20,
            reserved_output=5,
        )
        self.cwm.add_segment(
            window_id=w["window_id"],
            content=" ".join(["word"] * 50),
            priority="low",
        )
        self.cwm.add_segment(
            window_id=w["window_id"],
            content="critical data",
            priority="critical",
        )
        r = self.cwm.fit_context(
            window_id=w["window_id"]
        )
        assert r["fitted"] is True

    def test_fit_context_missing(self) -> None:
        r = self.cwm.fit_context(
            window_id="bad"
        )
        assert r["fitted"] is False

    def test_chunk_fixed(self) -> None:
        text = " ".join(
            [f"w{i}" for i in range(100)]
        )
        r = self.cwm.chunk_text(
            text=text,
            chunk_size=20,
            strategy="fixed_size",
        )
        assert r["chunked"] is True
        assert r["total_chunks"] >= 5

    def test_chunk_sentence(self) -> None:
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        r = self.cwm.chunk_text(
            text=text,
            chunk_size=3,
            strategy="sentence_boundary",
        )
        assert r["chunked"] is True

    def test_chunk_paragraph(self) -> None:
        text = "Para one.\n\nPara two.\n\nPara three."
        r = self.cwm.chunk_text(
            text=text,
            chunk_size=3,
            strategy="paragraph_boundary",
        )
        assert r["chunked"] is True

    def test_chunk_overlap(self) -> None:
        text = " ".join(
            [f"w{i}" for i in range(50)]
        )
        r = self.cwm.chunk_text(
            text=text,
            chunk_size=20,
            strategy="overlap_sliding",
            overlap=5,
        )
        assert r["chunked"] is True
        assert r["total_chunks"] >= 3

    def test_get_chunks(self) -> None:
        text = "word " * 20
        c = self.cwm.chunk_text(
            text=text,
            chunk_size=5,
        )
        r = self.cwm.get_chunks(
            chunk_id=c["chunk_id"]
        )
        assert r["retrieved"] is True
        assert r["total"] > 0

    def test_get_chunks_missing(self) -> None:
        r = self.cwm.get_chunks(
            chunk_id="bad"
        )
        assert r["retrieved"] is False

    def test_handle_overflow_no_overflow(self) -> None:
        r = self.cwm.handle_overflow(
            text="short text",
            max_tokens=100,
        )
        assert r["handled"] is True
        assert r["overflow"] is False

    def test_handle_overflow_truncate_end(self) -> None:
        text = " ".join(
            [f"w{i}" for i in range(100)]
        )
        r = self.cwm.handle_overflow(
            text=text,
            max_tokens=10,
            strategy="truncate_end",
        )
        assert r["handled"] is True
        assert r["overflow"] is True

    def test_handle_overflow_truncate_start(self) -> None:
        text = " ".join(
            [f"w{i}" for i in range(100)]
        )
        r = self.cwm.handle_overflow(
            text=text,
            max_tokens=10,
            strategy="truncate_start",
        )
        assert r["handled"] is True
        assert r["overflow"] is True

    def test_handle_overflow_truncate_middle(self) -> None:
        text = " ".join(
            [f"w{i}" for i in range(100)]
        )
        r = self.cwm.handle_overflow(
            text=text,
            max_tokens=10,
            strategy="truncate_middle",
        )
        assert r["handled"] is True
        assert "..." in r["text"]

    def test_get_window_status(self) -> None:
        w = self.cwm.create_window(
            name="st"
        )
        r = self.cwm.get_window_status(
            window_id=w["window_id"]
        )
        assert r["retrieved"] is True

    def test_get_window_status_missing(self) -> None:
        r = self.cwm.get_window_status(
            window_id="bad"
        )
        assert r["retrieved"] is False

    def test_get_summary(self) -> None:
        r = self.cwm.get_summary()
        assert r["retrieved"] is True


# ===================== ChainOfThoughtBuilder =====================


class TestChainOfThoughtBuilder:
    """ChainOfThoughtBuilder testleri."""

    def setup_method(self) -> None:
        self.cot = ChainOfThoughtBuilder()

    def test_init(self) -> None:
        assert self.cot.chain_count == 0

    def test_build_standard(self) -> None:
        r = self.cot.build_cot(
            task="What is 2+2?",
            cot_type="standard",
        )
        assert r["built"] is True
        assert "step by step" in r["prompt"].lower()

    def test_build_zero_shot(self) -> None:
        r = self.cot.build_cot(
            task="Explain gravity",
            cot_type="zero_shot",
        )
        assert r["built"] is True

    def test_build_few_shot(self) -> None:
        r = self.cot.build_cot(
            task="What is 5+3?",
            cot_type="few_shot",
            examples=[
                {
                    "question": "2+2?",
                    "reasoning": "2 plus 2",
                    "answer": "4",
                }
            ],
        )
        assert r["built"] is True
        assert "2+2?" in r["prompt"]

    def test_build_self_consistency(self) -> None:
        r = self.cot.build_cot(
            task="Complex problem",
            cot_type="self_consistency",
            num_steps=3,
        )
        assert r["built"] is True
        assert "Path 1" in r["prompt"]

    def test_build_tree_of_thought(self) -> None:
        r = self.cot.build_cot(
            task="Strategic decision",
            cot_type="tree_of_thought",
            num_steps=3,
        )
        assert r["built"] is True
        assert "Branch 1" in r["prompt"]

    def test_build_reflection(self) -> None:
        r = self.cot.build_cot(
            task="Analyze this",
            cot_type="reflection",
        )
        assert r["built"] is True
        assert "reconsider" in r["prompt"].lower()

    def test_build_step_by_step(self) -> None:
        r = self.cot.build_cot(
            task="Build a house",
            cot_type="step_by_step",
            num_steps=5,
        )
        assert r["built"] is True
        assert "Step 1" in r["prompt"]

    def test_build_unknown_type(self) -> None:
        r = self.cot.build_cot(
            task="test",
            cot_type="unknown",
        )
        assert r["built"] is True

    def test_add_template(self) -> None:
        r = self.cot.add_template(
            name="custom",
            prefix="Think first:",
            suffix="Answer:",
        )
        assert r["added"] is True

    def test_enhance_with_reflection(self) -> None:
        r = self.cot.enhance_with_reflection(
            prompt="Solve this problem"
        )
        assert r["enhanced"] is True
        assert "assumptions" in r["enhanced_prompt"].lower()

    def test_get_chain(self) -> None:
        c = self.cot.build_cot(
            task="test",
        )
        r = self.cot.get_chain(
            chain_id=c["chain_id"]
        )
        assert r["retrieved"] is True

    def test_get_chain_missing(self) -> None:
        r = self.cot.get_chain(
            chain_id="bad"
        )
        assert r["retrieved"] is False

    def test_get_summary(self) -> None:
        self.cot.build_cot(task="t1")
        r = self.cot.get_summary()
        assert r["retrieved"] is True
        assert r["total_chains"] >= 1


# ===================== FewShotSelector =====================


class TestFewShotSelector:
    """FewShotSelector testleri."""

    def setup_method(self) -> None:
        self.fs = FewShotSelector()

    def test_init(self) -> None:
        assert self.fs.example_count == 0

    def test_add_example(self) -> None:
        r = self.fs.add_example(
            input_text="What is AI?",
            output_text="AI is artificial intelligence.",
            domain="tech",
        )
        assert r["added"] is True
        assert self.fs.example_count == 1

    def test_select_similar(self) -> None:
        self.fs.add_example(
            input_text="Python programming language",
            output_text="Python is versatile",
            domain="coding",
        )
        self.fs.add_example(
            input_text="Cooking recipes pasta",
            output_text="Boil pasta",
            domain="cooking",
        )
        r = self.fs.select_examples(
            query="Python code",
            strategy="similarity",
        )
        assert r["selected"] is True

    def test_select_diverse(self) -> None:
        for d in ["a", "b", "c"]:
            self.fs.add_example(
                input_text=f"example {d}",
                output_text=f"output {d}",
                domain=d,
            )
        r = self.fs.select_examples(
            query="test",
            k=3,
            strategy="diversity",
        )
        assert r["selected"] is True
        assert r["count"] == 3

    def test_select_by_performance(self) -> None:
        self.fs.add_example(
            input_text="good",
            output_text="result",
            quality_score=0.9,
        )
        self.fs.add_example(
            input_text="bad",
            output_text="result",
            quality_score=0.1,
        )
        r = self.fs.select_examples(
            query="test",
            strategy="performance",
            k=1,
        )
        assert r["selected"] is True
        assert r["count"] == 1

    def test_select_balanced(self) -> None:
        self.fs.add_example(
            input_text="test query",
            output_text="answer",
            quality_score=0.8,
        )
        r = self.fs.select_examples(
            query="test query",
            strategy="balanced",
        )
        assert r["selected"] is True

    def test_select_with_domain_filter(self) -> None:
        self.fs.add_example(
            input_text="x",
            output_text="y",
            domain="math",
        )
        self.fs.add_example(
            input_text="a",
            output_text="b",
            domain="science",
        )
        r = self.fs.select_examples(
            query="test",
            domain="math",
        )
        assert r["selected"] is True
        for ex in r["examples"]:
            assert ex["domain"] == "math"

    def test_select_with_exclude(self) -> None:
        e1 = self.fs.add_example(
            input_text="x",
            output_text="y",
        )
        self.fs.add_example(
            input_text="a",
            output_text="b",
        )
        r = self.fs.select_examples(
            query="test",
            exclude_ids=[e1["example_id"]],
        )
        assert r["selected"] is True

    def test_select_empty(self) -> None:
        r = self.fs.select_examples(
            query="test",
            domain="nonexistent",
        )
        assert r["selected"] is True
        assert r["count"] == 0

    def test_format_qa(self) -> None:
        examples = [
            {"input": "Q1", "output": "A1"}
        ]
        r = self.fs.format_few_shot(
            examples=examples,
            task="Q2",
            format_type="qa",
        )
        assert r["formatted"] is True
        assert "Q: Q1" in r["prompt"]

    def test_format_instruction(self) -> None:
        examples = [
            {"input": "I1", "output": "O1"}
        ]
        r = self.fs.format_few_shot(
            examples=examples,
            task="I2",
            format_type="instruction",
        )
        assert r["formatted"] is True
        assert "Input:" in r["prompt"]

    def test_format_conversation(self) -> None:
        examples = [
            {"input": "Hi", "output": "Hello"}
        ]
        r = self.fs.format_few_shot(
            examples=examples,
            task="Bye",
            format_type="conversation",
        )
        assert r["formatted"] is True
        assert "User:" in r["prompt"]

    def test_format_default(self) -> None:
        examples = [
            {"input": "x", "output": "y"}
        ]
        r = self.fs.format_few_shot(
            examples=examples,
            task="z",
            format_type="plain",
        )
        assert r["formatted"] is True
        assert "->" in r["prompt"]

    def test_record_performance(self) -> None:
        e = self.fs.add_example(
            input_text="x",
            output_text="y",
        )
        r = self.fs.record_performance(
            example_id=e["example_id"],
            success=True,
            quality_score=0.9,
        )
        assert r["recorded"] is True
        assert r["success_rate"] == 1.0

    def test_record_performance_missing(self) -> None:
        r = self.fs.record_performance(
            example_id="bad"
        )
        assert r["recorded"] is False

    def test_get_summary(self) -> None:
        r = self.fs.get_summary()
        assert r["retrieved"] is True


# ===================== PromptPerformanceTracker =====================


class TestPromptPerformanceTracker:
    """PromptPerformanceTracker testleri."""

    def setup_method(self) -> None:
        self.pt = PromptPerformanceTracker()

    def test_init(self) -> None:
        assert self.pt.record_count == 0

    def test_register_prompt(self) -> None:
        r = self.pt.register_prompt(
            name="test",
            prompt_text="Hello {{name}}",
            model="claude",
        )
        assert r["registered"] is True

    def test_record_execution(self) -> None:
        p = self.pt.register_prompt(
            name="exec",
        )
        r = self.pt.record_execution(
            prompt_id=p["prompt_id"],
            success=True,
            quality_score=0.8,
            latency_ms=150.0,
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
        )
        assert r["recorded"] is True
        assert r["total_calls"] == 1

    def test_record_missing(self) -> None:
        r = self.pt.record_execution(
            prompt_id="bad"
        )
        assert r["recorded"] is False

    def test_get_metrics(self) -> None:
        p = self.pt.register_prompt(
            name="met",
        )
        pid = p["prompt_id"]
        self.pt.record_execution(
            prompt_id=pid,
            success=True,
            quality_score=0.9,
            latency_ms=100.0,
            cost=0.001,
            input_tokens=50,
            output_tokens=30,
        )
        self.pt.record_execution(
            prompt_id=pid,
            success=True,
            quality_score=0.7,
            latency_ms=200.0,
            cost=0.002,
            input_tokens=60,
            output_tokens=40,
        )
        r = self.pt.get_metrics(
            prompt_id=pid
        )
        assert r["retrieved"] is True
        assert r["total_calls"] == 2
        assert r["success_rate"] == 1.0
        assert r["avg_quality"] == 0.8

    def test_get_metrics_empty(self) -> None:
        p = self.pt.register_prompt(
            name="empty",
        )
        r = self.pt.get_metrics(
            prompt_id=p["prompt_id"]
        )
        assert r["retrieved"] is True
        assert r["total_calls"] == 0

    def test_get_metrics_missing(self) -> None:
        r = self.pt.get_metrics(
            prompt_id="bad"
        )
        assert r["retrieved"] is False

    def test_get_trend(self) -> None:
        p = self.pt.register_prompt(
            name="tr",
        )
        pid = p["prompt_id"]
        for i in range(10):
            self.pt.record_execution(
                prompt_id=pid,
                success=True,
                quality_score=0.5 + i * 0.05,
                latency_ms=100.0,
            )
        r = self.pt.get_trend(
            prompt_id=pid
        )
        assert r["retrieved"] is True
        assert r["quality_trend"] in (
            "improving",
            "stable",
            "declining",
        )

    def test_get_trend_insufficient(self) -> None:
        p = self.pt.register_prompt(
            name="ti",
        )
        r = self.pt.get_trend(
            prompt_id=p["prompt_id"]
        )
        assert r["retrieved"] is True
        assert r["trend"] == "insufficient"

    def test_get_trend_missing(self) -> None:
        r = self.pt.get_trend(
            prompt_id="bad"
        )
        assert r["retrieved"] is False

    def test_compare_prompts(self) -> None:
        p1 = self.pt.register_prompt(
            name="c1",
        )
        p2 = self.pt.register_prompt(
            name="c2",
        )
        self.pt.record_execution(
            prompt_id=p1["prompt_id"],
            quality_score=0.9,
            cost=0.001,
        )
        self.pt.record_execution(
            prompt_id=p2["prompt_id"],
            quality_score=0.7,
            cost=0.0005,
        )
        r = self.pt.compare_prompts(
            prompt_ids=[
                p1["prompt_id"],
                p2["prompt_id"],
            ]
        )
        assert r["compared"] is True
        assert r["count"] == 2

    def test_compare_empty(self) -> None:
        r = self.pt.compare_prompts(
            prompt_ids=[]
        )
        assert r["compared"] is True

    def test_get_alerts(self) -> None:
        p = self.pt.register_prompt(
            name="al",
        )
        pid = p["prompt_id"]
        for _ in range(6):
            self.pt.record_execution(
                prompt_id=pid,
                success=False,
                quality_score=0.2,
            )
        r = self.pt.get_alerts(
            success_threshold=0.8,
            quality_threshold=0.5,
        )
        assert r["retrieved"] is True
        assert r["count"] >= 1

    def test_get_alerts_no_issues(self) -> None:
        p = self.pt.register_prompt(
            name="ok",
        )
        pid = p["prompt_id"]
        for _ in range(6):
            self.pt.record_execution(
                prompt_id=pid,
                success=True,
                quality_score=0.9,
            )
        r = self.pt.get_alerts()
        assert r["retrieved"] is True

    def test_get_summary(self) -> None:
        r = self.pt.get_summary()
        assert r["retrieved"] is True


# ===================== PromptEngOrchestrator =====================


class TestPromptEngOrchestrator:
    """PromptEngOrchestrator testleri."""

    def setup_method(self) -> None:
        self.orch = PromptEngOrchestrator()

    def test_init(self) -> None:
        s = self.orch.get_summary()
        assert s["retrieved"] is True

    def test_create_prompt(self) -> None:
        r = self.orch.create_prompt(
            name="test",
            content="Hello {{name}}",
            category="general",
            domain="tech",
        )
        assert r["created"] is True
        assert r["template_id"] is not None

    def test_create_prompt_with_optimize(self) -> None:
        r = self.orch.create_prompt(
            name="opt",
            content="kind of  do  this task",
            auto_optimize=True,
        )
        assert r["created"] is True
        assert r["optimized"] is True

    def test_create_prompt_no_optimize(self) -> None:
        r = self.orch.create_prompt(
            name="noopt",
            content="simple prompt",
            auto_optimize=False,
        )
        assert r["created"] is True

    def test_enhance_prompt_basic(self) -> None:
        r = self.orch.enhance_prompt(
            prompt="Test task"
        )
        assert r["enhanced"] is True

    def test_enhance_with_cot(self) -> None:
        r = self.orch.enhance_prompt(
            prompt="Solve this",
            cot_type="standard",
        )
        assert r["enhanced"] is True
        assert "cot" in r["applied"]

    def test_enhance_with_few_shot(self) -> None:
        self.orch.few_shot.add_example(
            input_text="coding task",
            output_text="code solution",
            domain="coding",
        )
        r = self.orch.enhance_prompt(
            prompt="coding task",
            few_shot_domain="coding",
            few_shot_k=1,
        )
        assert r["enhanced"] is True

    def test_enhance_with_token_limit(self) -> None:
        long_text = " ".join(
            ["word"] * 1000
        )
        r = self.orch.enhance_prompt(
            prompt=long_text,
            max_tokens=50,
        )
        assert r["enhanced"] is True

    def test_test_prompt(self) -> None:
        r = self.orch.test_prompt(
            name="ab test",
            prompt_a="Variant A",
            prompt_b="Variant B",
        )
        assert r["started"] is True

    def test_test_prompt_disabled(self) -> None:
        orch = PromptEngOrchestrator(
            ab_testing=False
        )
        r = orch.test_prompt(
            name="disabled",
            prompt_a="A",
            prompt_b="B",
        )
        assert r["started"] is False

    def test_deploy_prompt(self) -> None:
        c = self.orch.create_prompt(
            name="deploy",
            content="Deploy me",
        )
        r = self.orch.deploy_prompt(
            template_id=c["template_id"],
            version_id=c.get("version_id", ""),
            message="First deploy",
        )
        assert r["deployed"] is True

    def test_deploy_missing(self) -> None:
        r = self.orch.deploy_prompt(
            template_id="bad"
        )
        assert r["deployed"] is False

    def test_record_usage(self) -> None:
        c = self.orch.create_prompt(
            name="usage",
            content="test",
        )
        r = self.orch.record_usage(
            perf_id=c["perf_id"],
            success=True,
            quality_score=0.9,
            latency_ms=100.0,
        )
        assert r["recorded"] is True

    def test_get_analytics(self) -> None:
        r = self.orch.get_analytics()
        assert r["retrieved"] is True
        assert "templates" in r
        assert "optimizer" in r

    def test_get_summary(self) -> None:
        r = self.orch.get_summary()
        assert r["retrieved"] is True
        assert "config" in r


# ===================== Models =====================


class TestPromptEngModels:
    """Prompteng model testleri."""

    def test_optimization_type_enum(self) -> None:
        from app.models.prompteng_models import (
            OptimizationType,
        )
        assert OptimizationType.LENGTH_REDUCTION == "length_reduction"
        assert len(OptimizationType) == 6

    def test_cot_type_enum(self) -> None:
        from app.models.prompteng_models import (
            CotType,
        )
        assert CotType.STANDARD == "standard"
        assert len(CotType) == 7

    def test_chunk_strategy_enum(self) -> None:
        from app.models.prompteng_models import (
            ChunkStrategy,
        )
        assert ChunkStrategy.FIXED_SIZE == "fixed_size"
        assert len(ChunkStrategy) == 5

    def test_priority_level_enum(self) -> None:
        from app.models.prompteng_models import (
            PriorityLevel,
        )
        assert PriorityLevel.CRITICAL == "critical"
        assert len(PriorityLevel) == 5

    def test_selection_strategy_enum(self) -> None:
        from app.models.prompteng_models import (
            SelectionStrategy,
        )
        assert SelectionStrategy.BALANCED == "balanced"
        assert len(SelectionStrategy) == 5

    def test_test_status_enum(self) -> None:
        from app.models.prompteng_models import (
            TestStatus,
        )
        assert TestStatus.RUNNING == "running"
        assert len(TestStatus) == 4

    def test_quality_trend_enum(self) -> None:
        from app.models.prompteng_models import (
            QualityTrend,
        )
        assert QualityTrend.IMPROVING == "improving"
        assert len(QualityTrend) == 4

    def test_prompt_template_model(self) -> None:
        from app.models.prompteng_models import (
            PromptTemplate,
        )
        t = PromptTemplate(
            template_id="t1",
            name="test",
        )
        assert t.template_id == "t1"
        assert t.version == 1

    def test_optimization_result_model(self) -> None:
        from app.models.prompteng_models import (
            OptimizationResult,
        )
        r = OptimizationResult(
            tokens_saved=10,
            optimized=True,
        )
        assert r.tokens_saved == 10

    def test_version_record_model(self) -> None:
        from app.models.prompteng_models import (
            VersionRecord,
        )
        v = VersionRecord(
            prompt_id="p1",
            version=2,
        )
        assert v.version == 2

    def test_ab_test_record_model(self) -> None:
        from app.models.prompteng_models import (
            ABTestRecord,
        )
        t = ABTestRecord(
            test_id="t1",
            sample_size=50,
        )
        assert t.sample_size == 50

    def test_ab_test_result_model(self) -> None:
        from app.models.prompteng_models import (
            ABTestResult,
        )
        r = ABTestResult(
            variant="a",
            score=0.9,
        )
        assert r.score == 0.9

    def test_context_window_model(self) -> None:
        from app.models.prompteng_models import (
            ContextWindow,
        )
        w = ContextWindow(
            max_tokens=8192
        )
        assert w.max_tokens == 8192

    def test_chunk_result_model(self) -> None:
        from app.models.prompteng_models import (
            ChunkResult,
        )
        c = ChunkResult(total_chunks=5)
        assert c.total_chunks == 5

    def test_cot_chain_model(self) -> None:
        from app.models.prompteng_models import (
            CotChain,
        )
        c = CotChain(
            cot_type="reflection"
        )
        assert c.cot_type == "reflection"

    def test_few_shot_example_model(self) -> None:
        from app.models.prompteng_models import (
            FewShotExample,
        )
        e = FewShotExample(
            quality_score=0.95
        )
        assert e.quality_score == 0.95

    def test_performance_metrics_model(self) -> None:
        from app.models.prompteng_models import (
            PerformanceMetrics,
        )
        m = PerformanceMetrics(
            success_rate=0.95
        )
        assert m.success_rate == 0.95

    def test_prompteng_summary_model(self) -> None:
        from app.models.prompteng_models import (
            PromptEngSummary,
        )
        s = PromptEngSummary(
            templates=10,
            ab_tests=5,
        )
        assert s.templates == 10


# ===================== Config =====================


class TestPromptEngConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import Settings

        s = Settings()
        assert s.prompteng_enabled is True
        assert s.auto_optimize is True
        assert s.ab_testing is True
        assert s.cot_enabled is True
        assert s.version_control is True
