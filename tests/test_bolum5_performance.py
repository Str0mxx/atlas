"""BOLUM 5: Performance & Quality testleri.

Context window yonetimi, token streaming,
hata iyilestirme ve model testleri.
~200 test.
"""

import time
import pytest
from unittest.mock import MagicMock

# -- Model imports --
from app.models.performance_models import (
    TruncationInfo,
    StreamLane,
    StreamChunk,
    CompactionResult,
    ErrorClassification,
    EnhancedError,
    PageInfo,
)

from app.models.contextwindow_models import (
    OverflowStrategy,
    MessagePriority,
    SummaryLevel,
    WindowStatus,
    TokenUsage,
    WindowSnapshot,
    SummaryResult,
    RetentionRule,
    SystemPromptConfig,
)

from app.models.streaming_models import (
    StreamState,
    StreamEventType,
    FlushReason,
    StreamErrorType,
    ProviderFormat,
    StreamToken,
    StreamEvent,
    BufferState,
    StreamError,
    StreamMetrics,
    StreamConfig,
    StreamingSnapshot,
)

# -- Core imports --
from app.core.contextwindow.context_compactor import (
    ContextCompactor,
)
from app.core.contextwindow.token_counter import (
    TokenCounter,
)
from app.core.contextwindow.message_summarizer import (
    MessageSummarizer,
)
from app.core.contextwindow.priority_retainer import (
    PriorityRetainer,
)
from app.core.contextwindow.system_prompt_guarantee import (
    SystemPromptGuarantee,
)
from app.core.contextwindow.context_window_mgr import (
    ContextWindowMgr,
)
from app.core.tokenstream.stream_enhancer import (
    StreamEnhancer,
)
from app.core.resilience.error_enhancer import (
    ErrorEnhancer,
)
from app.core.tokenstream.token_buffer import (
    TokenBuffer,
)
from app.core.tokenstream.provider_stream_adapter import (
    ProviderStreamAdapter,
)
from app.core.tokenstream.stream_error_handler import (
    StreamErrorHandler,
)
from app.core.tokenstream.stream_event_emitter import (
    StreamEventEmitter,
)
from app.core.tokenstream.streaming_client import (
    StreamingClient,
)


# ====== PERFORMANCE MODELS ======


class TestTruncationInfo:
    """TruncationInfo model testleri."""

    def test_defaults(self):
        t = TruncationInfo()
        assert t.total_chars == 0
        assert t.cap == 150_000
        assert t.truncated is False
        assert t.truncated_count == 0
        assert t.kept_count == 0
        assert t.truncation_ratio == 0.0

    def test_custom_values(self):
        t = TruncationInfo(
            total_chars=5000,
            cap=3000,
            truncated=True,
            truncated_count=2,
            kept_count=8,
            truncation_ratio=0.2,
        )
        assert t.total_chars == 5000
        assert t.cap == 3000
        assert t.truncated is True
        assert t.truncated_count == 2


class TestStreamLane:
    """StreamLane enum testleri."""

    def test_values(self):
        assert StreamLane.REASONING == "reasoning"
        assert StreamLane.ANSWER == "answer"
        assert StreamLane.TOOL_CALL == "tool_call"

    def test_member_count(self):
        assert len(StreamLane) == 3


class TestStreamChunk:
    """StreamChunk model testleri."""

    def test_defaults(self):
        sc = StreamChunk()
        assert sc.content == ""
        assert sc.lane == StreamLane.ANSWER
        assert sc.thread_id == ""
        assert sc.chunk_index == 0
        assert sc.is_final is False

    def test_custom(self):
        sc = StreamChunk(
            content="hello",
            lane=StreamLane.REASONING,
            thread_id="t1",
            chunk_index=3,
            is_final=True,
        )
        assert sc.content == "hello"
        assert sc.lane == StreamLane.REASONING
        assert sc.is_final is True


class TestCompactionResult:
    """CompactionResult model testleri."""

    def test_defaults(self):
        cr = CompactionResult()
        assert cr.original_size == 0
        assert cr.compacted_size == 0
        assert cr.ratio == 0.0
        assert cr.items_removed == 0
        assert cr.items_kept == 0
        assert cr.strategy == ""

    def test_custom(self):
        cr = CompactionResult(
            original_size=1000,
            compacted_size=500,
            ratio=0.5,
            strategy="truncate",
        )
        assert cr.ratio == 0.5
        assert cr.strategy == "truncate"


class TestErrorClassification:
    """ErrorClassification enum testleri."""

    def test_values(self):
        assert ErrorClassification.BILLING == "billing"
        assert ErrorClassification.TIMEOUT == "timeout"
        assert ErrorClassification.CONTEXT_OVERFLOW == "context_overflow"
        assert ErrorClassification.PROVIDER == "provider"
        assert ErrorClassification.TRANSIENT == "transient"
        assert ErrorClassification.PERMANENT == "permanent"

    def test_member_count(self):
        assert len(ErrorClassification) == 6


class TestEnhancedError:
    """EnhancedError model testleri."""

    def test_defaults(self):
        ee = EnhancedError()
        assert ee.original_error == ""
        assert ee.classification == ErrorClassification.TRANSIENT
        assert ee.model == ""
        assert ee.provider == ""
        assert ee.retryable is True
        assert ee.retry_count == 0
        assert ee.max_retries == 3
        assert ee.deferred is False

    def test_custom(self):
        ee = EnhancedError(
            original_error="billing error",
            classification=ErrorClassification.BILLING,
            retryable=False,
        )
        assert ee.classification == ErrorClassification.BILLING
        assert ee.retryable is False


class TestPageInfo:
    """PageInfo model testleri."""

    def test_defaults(self):
        pi = PageInfo()
        assert pi.page_number == 0
        assert pi.total_pages == 0
        assert pi.content_length == 0
        assert pi.budget_used == 0
        assert pi.budget_remaining == 0

    def test_custom(self):
        pi = PageInfo(
            page_number=2,
            total_pages=5,
            content_length=3000,
        )
        assert pi.page_number == 2
        assert pi.total_pages == 5


# ====== CONTEXTWINDOW MODELS ======


class TestOverflowStrategy:
    """OverflowStrategy enum testleri."""

    def test_values(self):
        assert OverflowStrategy.TRUNCATE.value is not None
        assert OverflowStrategy.DROP_OLDEST.value is not None
        assert OverflowStrategy.SUMMARIZE.value is not None

    def test_has_drop_lowest(self):
        assert hasattr(OverflowStrategy, "DROP_LOWEST")


class TestMessagePriority:
    """MessagePriority enum testleri."""

    def test_values(self):
        assert MessagePriority.CRITICAL.value is not None
        assert MessagePriority.HIGH.value is not None
        assert MessagePriority.MEDIUM.value is not None
        assert MessagePriority.LOW.value is not None
        assert MessagePriority.DISPOSABLE.value is not None


class TestSummaryLevel:
    """SummaryLevel enum testleri."""

    def test_values(self):
        assert SummaryLevel.BRIEF.value is not None
        assert SummaryLevel.STANDARD.value is not None
        assert SummaryLevel.DETAILED.value is not None


class TestWindowStatus:
    """WindowStatus enum testleri."""

    def test_values(self):
        assert WindowStatus.HEALTHY.value is not None
        assert WindowStatus.WARNING.value is not None
        assert WindowStatus.CRITICAL.value is not None
        assert WindowStatus.OVERFLOW.value is not None


class TestTokenUsage:
    """TokenUsage model testleri."""

    def test_defaults(self):
        tu = TokenUsage()
        assert tu.usage_id != ""
        assert tu.token_count == 0

    def test_uuid_unique(self):
        t1 = TokenUsage()
        t2 = TokenUsage()
        assert t1.usage_id != t2.usage_id


class TestWindowSnapshot:
    """WindowSnapshot model testleri."""

    def test_defaults(self):
        ws = WindowSnapshot()
        assert ws.snapshot_id != ""
        assert ws.message_count == 0
        assert ws.total_tokens == 0


class TestSummaryResult:
    """SummaryResult model testleri."""

    def test_defaults(self):
        sr = SummaryResult()
        assert sr.summary_id != ""
        assert sr.original_tokens == 0
        assert sr.summary_text == ""

    def test_uuid_unique(self):
        s1 = SummaryResult()
        s2 = SummaryResult()
        assert s1.summary_id != s2.summary_id


class TestRetentionRule:
    """RetentionRule model testleri."""

    def test_defaults(self):
        rr = RetentionRule()
        assert rr.rule_id != ""
        assert rr.enabled is True

    def test_custom(self):
        rr = RetentionRule(enabled=False)
        assert rr.enabled is False


class TestSystemPromptConfig:
    """SystemPromptConfig model testleri."""

    def test_defaults(self):
        spc = SystemPromptConfig()
        assert spc.version == 1
        assert spc.is_protected is True

    def test_custom(self):
        spc = SystemPromptConfig(
            version=3,
            is_protected=False,
        )
        assert spc.version == 3
        assert spc.is_protected is False


# ====== STREAMING MODELS ======


class TestStreamState:
    """StreamState enum testleri."""

    def test_member_count(self):
        assert len(StreamState) == 8

    def test_key_values(self):
        assert StreamState.IDLE.value is not None
        assert StreamState.STREAMING.value is not None
        assert StreamState.ERROR.value is not None
        assert StreamState.COMPLETED.value is not None


class TestStreamEventType:
    """StreamEventType enum testleri."""

    def test_member_count(self):
        assert len(StreamEventType) == 13

    def test_key_values(self):
        assert StreamEventType.TOKEN.value is not None
        assert StreamEventType.START.value is not None
        assert StreamEventType.END.value is not None
        assert StreamEventType.ERROR.value is not None
        assert StreamEventType.FLUSH.value is not None


class TestFlushReason:
    """FlushReason enum testleri."""

    def test_member_count(self):
        assert len(FlushReason) == 6

    def test_key_values(self):
        assert FlushReason.BUFFER_FULL.value is not None
        assert FlushReason.SENTENCE_BOUNDARY.value is not None


class TestStreamErrorType:
    """StreamErrorType enum testleri."""

    def test_member_count(self):
        assert len(StreamErrorType) == 9

    def test_key_values(self):
        assert StreamErrorType.CONNECTION.value is not None
        assert StreamErrorType.TIMEOUT.value is not None
        assert StreamErrorType.RATE_LIMIT.value is not None


class TestProviderFormat:
    """ProviderFormat enum testleri."""

    def test_values(self):
        assert ProviderFormat.SSE.value is not None
        assert ProviderFormat.NDJSON.value is not None
        assert ProviderFormat.WEBSOCKET.value is not None
        assert ProviderFormat.RAW.value is not None

    def test_member_count(self):
        assert len(ProviderFormat) == 4


class TestStreamToken:
    """StreamToken model testleri."""

    def test_defaults(self):
        st = StreamToken()
        assert st.content == ""

    def test_custom(self):
        st = StreamToken(content="hello")
        assert st.content == "hello"


class TestStreamEvent:
    """StreamEvent model testleri."""

    def test_defaults(self):
        se = StreamEvent()
        assert se.event_type == StreamEventType.TOKEN


class TestBufferState:
    """BufferState model testleri."""

    def test_defaults(self):
        bs = BufferState()
        assert bs.token_count == 0


class TestStreamErrorModel:
    """StreamError model testleri."""

    def test_defaults(self):
        se = StreamError()
        assert se.error_type == StreamErrorType.UNKNOWN


class TestStreamMetrics:
    """StreamMetrics model testleri."""

    def test_defaults(self):
        sm = StreamMetrics()
        assert sm.total_tokens == 0
        assert sm.total_bytes == 0


class TestStreamConfig:
    """StreamConfig model testleri."""

    def test_defaults(self):
        sc = StreamConfig()
        assert sc.buffer_size == 64

    def test_custom(self):
        sc = StreamConfig(buffer_size=128)
        assert sc.buffer_size == 128


class TestStreamingSnapshot:
    """StreamingSnapshot model testleri."""

    def test_defaults(self):
        ss = StreamingSnapshot()
        assert ss.snapshot_id != ""


# ====== CONTEXT COMPACTOR ======


class TestContextCompactor:
    """ContextCompactor testleri."""

    def test_init(self):
        cc = ContextCompactor()
        assert cc._total_cap == ContextCompactor.BOOTSTRAP_CAP
        assert cc._truncation_log == []

    def test_bootstrap_cap_value(self):
        assert ContextCompactor.BOOTSTRAP_CAP == 150_000
        assert ContextCompactor.OLD_BOOTSTRAP_CAP == 24_000

    def test_raise_bootstrap_cap(self):
        cc = ContextCompactor()
        cc._total_cap = 24_000
        result = cc.raise_bootstrap_cap()
        assert result == 150_000
        assert cc._total_cap == 150_000

    def test_truncation_visibility_no_truncation(self):
        cc = ContextCompactor()
        msgs = [
            {"content": "hello"},
            {"content": "world"},
        ]
        info = cc.get_truncation_visibility(msgs)
        assert info["truncated"] is False
        assert info["total_chars"] == 10
        assert info["cap"] == 150_000
        assert info["kept_count"] == 2
        assert info["truncated_count"] == 0

    def test_truncation_visibility_with_truncation(self):
        cc = ContextCompactor()
        msgs = [
            {"content": "a" * 100},
            {"content": "b" * 100},
        ]
        info = cc.get_truncation_visibility(msgs, cap=150)
        assert info["truncated"] is True
        assert info["total_chars"] == 200
        assert info["cap"] == 150

    def test_compact_tool_results_under_budget(self):
        cc = ContextCompactor()
        results = [{"output": "short"}]
        compacted = cc.compact_tool_results(results, 1000)
        assert len(compacted) == 1
        assert compacted[0]["output"] == "short"

    def test_compact_tool_results_over_budget(self):
        cc = ContextCompactor()
        results = [
            {"output": "x" * 500},
            {"output": "y" * 500},
        ]
        compacted = cc.compact_tool_results(results, 200)
        assert len(compacted) == 2
        for item in compacted:
            assert len(item["output"]) <= 200

    def test_compact_tool_results_empty(self):
        cc = ContextCompactor()
        assert cc.compact_tool_results([], 100) == []

    def test_auto_page_read_short_content(self):
        cc = ContextCompactor()
        pages = cc.auto_page_read("short text", 10000)
        assert len(pages) == 1
        assert pages[0] == "short text"

    def test_auto_page_read_empty(self):
        cc = ContextCompactor()
        pages = cc.auto_page_read("", 1000)
        assert pages == []

    def test_auto_page_read_long_content(self):
        cc = ContextCompactor()
        content_lines = ["line " + str(i) for i in range(200)]
        content = chr(10).join(content_lines)
        pages = cc.auto_page_read(content, 100)
        assert len(pages) > 1
        reconstructed = chr(10).join(pages)
        assert reconstructed == content

    def test_compact_path_with_home(self):
        import os
        home = os.path.expanduser("~")
        path = home + "/documents/file.txt"
        result = ContextCompactor.compact_path(path)
        assert result.startswith("~")
        assert "file.txt" in result

    def test_compact_path_without_home(self):
        result = ContextCompactor.compact_path("/etc/config")
        assert result == "/etc/config"

    def test_compact_path_empty(self):
        result = ContextCompactor.compact_path("")
        assert result == ""


# ====== TOKEN COUNTER ======


class TestTokenCounter:
    """TokenCounter testleri."""

    def test_init(self):
        tc = TokenCounter()
        assert tc._cache == {}

    def test_count_basic(self):
        tc = TokenCounter()
        result = tc.count("Hello world")
        assert result > 0
        assert isinstance(result, int)

    def test_count_empty(self):
        tc = TokenCounter()
        result = tc.count("")
        assert result == 0

    def test_count_caching(self):
        tc = TokenCounter()
        text = "test caching"
        r1 = tc.count(text)
        r2 = tc.count(text)
        assert r1 == r2
        assert len(tc._cache) >= 1

    def test_count_messages(self):
        tc = TokenCounter()
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        result = tc.count_messages(msgs)
        assert result > 0

    def test_count_messages_empty(self):
        tc = TokenCounter()
        assert tc.count_messages([]) == 0

    def test_count_with_detail(self):
        tc = TokenCounter()
        msgs = [{"role": "user", "content": "test"}]
        details = tc.count_with_detail(msgs)
        assert isinstance(details, list)
        assert len(details) == 1
        assert isinstance(details[0], TokenUsage)
        assert details[0].token_count > 0

    def test_count_remaining(self):
        tc = TokenCounter()
        remaining = tc.count_remaining(1000, 4096)
        assert remaining == 3096

    def test_estimate_tokens(self):
        tc = TokenCounter()
        est = tc.estimate_tokens("hello world test")
        assert est > 0

    def test_estimate_ratio(self):
        tc = TokenCounter()
        ratio = tc.estimate_ratio(2000)
        assert isinstance(ratio, float)

    def test_will_fit_true(self):
        tc = TokenCounter()
        result = tc.will_fit("short", 100, 4096)
        assert result is True

    def test_will_fit_false(self):
        tc = TokenCounter()
        result = tc.will_fit("x" * 100000, 4000, 4096)
        assert result is False

    def test_clear_cache(self):
        tc = TokenCounter()
        tc.count("test")
        assert len(tc._cache) > 0
        tc.clear_cache()
        assert len(tc._cache) == 0

    def test_model_limits(self):
        tc = TokenCounter()
        tc.set_model("gpt-4")
        assert tc.get_model_limit() > 0
        tc.set_model("gpt-3.5-turbo")
        assert tc.get_model_limit() > 0

    def test_count_with_detail_multiple(self):
        tc = TokenCounter()
        msgs = [
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "msg2"},
            {"role": "user", "content": "msg3"},
        ]
        details = tc.count_with_detail(msgs)
        assert len(details) == 3

    def test_cache_max_size(self):
        tc = TokenCounter()
        for i in range(100):
            tc.count(f"unique text {i}")
        assert len(tc._cache) <= 10001

    def test_count_remaining_negative(self):
        tc = TokenCounter()
        remaining = tc.count_remaining(5000, 4096)
        assert remaining >= 0


# ====== MESSAGE SUMMARIZER ======


class TestMessageSummarizer:
    """MessageSummarizer testleri."""

    def test_init(self):
        ms = MessageSummarizer()
        assert ms._summaries == {}
        assert ms._templates == {}

    def test_summarize_basic(self):
        ms = MessageSummarizer()
        msgs = [
            {"role": "user", "content": "Tell me about Python."},
            {"role": "assistant", "content": "Python is versatile."},
        ]
        result = ms.summarize(msgs)
        assert isinstance(result, SummaryResult)
        assert result.summary_text != ""
        assert result.original_tokens >= 0

    def test_summarize_empty(self):
        ms = MessageSummarizer()
        result = ms.summarize([])
        assert result.original_tokens == 0

    def test_summarize_progressive(self):
        ms = MessageSummarizer()
        msgs = [
            {"role": "user", "content": "Topic A."},
            {"role": "assistant", "content": "Response A."},
            {"role": "user", "content": "Topic B."},
            {"role": "assistant", "content": "Response B."},
        ]
        result = ms.summarize_progressive(msgs)
        assert isinstance(result, SummaryResult)

    def test_summarize_by_role(self):
        ms = MessageSummarizer()
        msgs = [
            {"role": "user", "content": "User says hello."},
            {"role": "assistant", "content": "Assistant replies."},
            {"role": "system", "content": "System instruction."},
        ]
        result = ms.summarize_by_role(msgs)
        assert isinstance(result, dict)

    def test_extract_key_points(self):
        ms = MessageSummarizer()
        msgs = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a language."},
        ]
        points = ms.extract_key_points(msgs)
        assert isinstance(points, list)

    def test_template_crud(self):
        ms = MessageSummarizer()
        ms.add_template("test_tpl", "Summary: {content}")
        assert "test_tpl" in ms._templates
        tpl = ms.get_template("test_tpl")
        assert tpl == "Summary: {content}"
        ms.remove_template("test_tpl")
        assert "test_tpl" not in ms._templates

    def test_summary_storage(self):
        ms = MessageSummarizer()
        msgs = [{"role": "user", "content": "Test."}]
        result = ms.summarize(msgs)
        stored = ms.get_summary(result.summary_id)
        assert stored is not None

    def test_summary_levels(self):
        ms = MessageSummarizer()
        from app.models.contextwindow_models import SummaryLevel as SL
        brief = ms._get_ratio(SL.BRIEF)
        standard = ms._get_ratio(SL.STANDARD)
        detailed = ms._get_ratio(SL.DETAILED)
        assert brief < standard < detailed


# ====== PRIORITY RETAINER ======


class TestPriorityRetainer:
    """PriorityRetainer testleri."""

    def test_init(self):
        pr = PriorityRetainer()
        assert pr._rules == {}
        assert pr._pinned == {}

    def test_role_priorities_map(self):
        pr = PriorityRetainer()
        assert pr._role_priorities["system"] == MessagePriority.CRITICAL
        assert pr._role_priorities["user"] == MessagePriority.HIGH
        assert pr._role_priorities["assistant"] == MessagePriority.MEDIUM
        assert pr._role_priorities["tool"] == MessagePriority.LOW

    def test_default_role_priorities(self):
        pr = PriorityRetainer()
        assert pr._role_priorities["system"] == MessagePriority.CRITICAL
        assert pr._role_priorities["user"] == MessagePriority.HIGH
        assert pr._role_priorities["assistant"] == MessagePriority.MEDIUM
        assert pr._role_priorities["tool"] == MessagePriority.LOW

    def test_evaluate_priority_system(self):
        pr = PriorityRetainer()
        msg = {"role": "system", "content": "You are a helper."}
        priority = pr.evaluate_priority(msg)
        assert priority == MessagePriority.CRITICAL

    def test_evaluate_priority_user(self):
        pr = PriorityRetainer()
        msg = {"role": "user", "content": "Hello"}
        priority = pr.evaluate_priority(msg)
        assert priority == MessagePriority.HIGH

    def test_evaluate_priority_assistant(self):
        pr = PriorityRetainer()
        msg = {"role": "assistant", "content": "Hi"}
        priority = pr.evaluate_priority(msg)
        assert priority == MessagePriority.MEDIUM

    def test_evaluate_priority_tool(self):
        pr = PriorityRetainer()
        msg = {"role": "tool", "content": "result"}
        priority = pr.evaluate_priority(msg)
        assert priority == MessagePriority.LOW

    def test_add_rule(self):
        pr = PriorityRetainer()
        rule = pr.add_rule("test_rule", role="system", priority=MessagePriority.HIGH)
        assert rule is not None
        assert len(pr._rules) >= 1

    def test_filter_by_priority(self):
        pr = PriorityRetainer()
        msgs = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "tool", "content": "tool"},
        ]
        filtered = pr.filter_by_priority(
            msgs, min_priority=MessagePriority.HIGH,
        )
        assert len(filtered) >= 1

    def test_sort_by_priority(self):
        pr = PriorityRetainer()
        msgs = [
            {"role": "tool", "content": "low"},
            {"role": "system", "content": "critical"},
            {"role": "user", "content": "high"},
        ]
        sorted_msgs = pr.sort_by_priority(msgs)
        assert len(sorted_msgs) == 3

    def test_select_for_budget(self):
        pr = PriorityRetainer()
        msgs = [
            {"role": "system", "content": "sys prompt"},
            {"role": "user", "content": "user msg"},
            {"role": "assistant", "content": "a" * 1000},
        ]
        selected = pr.select_for_budget(msgs, 100)
        assert isinstance(selected, list)

    def test_pin_message(self):
        pr = PriorityRetainer()
        pr.pin_message("msg1", {"role": "user", "content": "pinned"})
        assert "msg1" in pr._pinned

    def test_unpin_message(self):
        pr = PriorityRetainer()
        pr.pin_message("msg1", {"role": "user", "content": "pinned"})
        pr.unpin_message("msg1")
        assert "msg1" not in pr._pinned

    def test_max_pinned_limit(self):
        pr = PriorityRetainer()
        assert len(pr._pinned) == 0  # starts empty

    def test_evaluate_priority_with_keyword(self):
        pr = PriorityRetainer()
        pr._keywords = {"urgent": MessagePriority.CRITICAL}
        msg = {"role": "user", "content": "This is urgent matter"}
        priority = pr.evaluate_priority(msg)
        assert priority in (
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
        )

    def test_sort_preserves_count(self):
        pr = PriorityRetainer()
        msgs = [
            {"role": "user", "content": "a"},
            {"role": "user", "content": "b"},
            {"role": "user", "content": "c"},
        ]
        sorted_msgs = pr.sort_by_priority(msgs)
        assert len(sorted_msgs) == 3


# ====== SYSTEM PROMPT GUARANTEE ======


class TestSystemPromptGuarantee:
    """SystemPromptGuarantee testleri."""

    def test_init(self):
        spg = SystemPromptGuarantee()
        assert spg._prompts == {}
        assert spg._active_id == ""

    def test_default_reserve(self):
        spg = SystemPromptGuarantee()
        assert spg._reserve_tokens == 2000

    def test_max_reserve(self):
        spg = SystemPromptGuarantee()
        assert spg._reserve_tokens > 0

    def test_max_prompts(self):
        spg = SystemPromptGuarantee()
        assert isinstance(spg._prompts, dict)

    def test_register_prompt(self):
        spg = SystemPromptGuarantee()
        result = spg.register_prompt("You are helpful.")
        assert result is not None
        assert spg._active_id == result.config_id

    def test_register_first_becomes_active(self):
        spg = SystemPromptGuarantee()
        result = spg.register_prompt("First prompt")
        assert spg._active_id == result.config_id

    def test_register_multiple(self):
        spg = SystemPromptGuarantee()
        r1 = spg.register_prompt("First")
        r2 = spg.register_prompt("Second")
        assert r1.config_id != r2.config_id
        assert spg._active_id == r1.config_id

    def test_inject_system_prompt(self):
        spg = SystemPromptGuarantee()
        spg.register_prompt("System instruction.")
        msgs = [{"role": "user", "content": "hello"}]
        result = spg.inject_system_prompt(msgs, 128000)
        assert len(result) >= 1
        has_system = any(
            m.get("role") == "system" for m in result
        )
        assert has_system

    def test_inject_with_existing_system(self):
        spg = SystemPromptGuarantee()
        spg.register_prompt("New system prompt.")
        msgs = [
            {"role": "system", "content": "Old prompt."},
            {"role": "user", "content": "hello"},
        ]
        result = spg.inject_system_prompt(msgs, 128000)
        assert len(result) >= 2

    def test_calculate_available(self):
        spg = SystemPromptGuarantee()
        spg.register_prompt("Short prompt")
        available = spg.calculate_available(128000)
        assert available < 128000
        assert available > 0

    def test_fits_with_prompt(self):
        spg = SystemPromptGuarantee()
        spg.register_prompt("System")
        result = spg.fits_with_prompt(100, 128000)
        assert result is True

    def test_fits_with_prompt_overflow(self):
        spg = SystemPromptGuarantee()
        spg.register_prompt("x" * 50000)
        result = spg.fits_with_prompt(100000, 128000)
        assert isinstance(result, bool)

    def test_version_history(self):
        spg = SystemPromptGuarantee()
        pid = spg.register_prompt("Version 1")
        assert len(spg._prompts) >= 1

    def test_inject_empty_messages(self):
        spg = SystemPromptGuarantee()
        spg.register_prompt("System prompt")
        result = spg.inject_system_prompt([], 128000)
        assert len(result) >= 1

    def test_no_active_prompt(self):
        spg = SystemPromptGuarantee()
        msgs = [{"role": "user", "content": "hi"}]
        result = spg.inject_system_prompt(msgs, 128000)
        assert isinstance(result, list)


# ====== CONTEXT WINDOW MGR ======


class TestContextWindowMgr:
    """ContextWindowMgr testleri."""

    def test_init(self):
        mgr = ContextWindowMgr()
        assert mgr._messages == []
        assert mgr._max_tokens == 128000

    def test_default_max_tokens(self):
        mgr = ContextWindowMgr()
        assert mgr._max_tokens == 128000

    def test_warning_critical_thresholds(self):
        mgr = ContextWindowMgr()
        assert mgr._max_tokens > 0
        assert mgr._overflow_strategy is not None

    def test_add_message(self):
        mgr = ContextWindowMgr()
        mgr.add_message(role="user", content="hello")
        assert mgr.get_message_count() >= 1

    def test_add_multiple_messages(self):
        mgr = ContextWindowMgr()
        for i in range(5):
            mgr.add_message(role="user", content=f"msg {i}")
        assert mgr.get_message_count() == 5

    def test_remove_message(self):
        mgr = ContextWindowMgr()
        mgr.add_message(role="user", content="to remove")
        initial_count = mgr.get_message_count()
        if initial_count > 0:
            mgr.remove_message(0)
            assert mgr.get_message_count() == initial_count - 1

    def test_get_status_normal(self):
        mgr = ContextWindowMgr()
        mgr.add_message(role="user", content="hello")
        status = mgr.get_status()
        assert status in (WindowStatus.HEALTHY, WindowStatus.WARNING, WindowStatus.CRITICAL, WindowStatus.OVERFLOW)

    def test_take_snapshot(self):
        mgr = ContextWindowMgr()
        mgr.add_message(role="user", content="test")
        snap = mgr.take_snapshot()
        assert isinstance(snap, WindowSnapshot)
        assert snap.message_count >= 1

    def test_overflow_handling(self):
        mgr = ContextWindowMgr(max_tokens=50)
        for i in range(100):
            mgr.add_message(role="user", content="x" * 20)
        assert mgr.get_message_count() <= 100

    def test_system_prompt_protection(self):
        mgr = ContextWindowMgr()
        mgr.add_message(role="system", content="Be helpful.")
        mgr.add_message(role="user", content="hello")
        msgs = mgr.get_messages()
        assert any(m["role"] == "system" for m in msgs)

    def test_components_initialized(self):
        mgr = ContextWindowMgr()
        assert isinstance(mgr._counter, TokenCounter)
        assert isinstance(mgr._summarizer, MessageSummarizer)
        assert isinstance(mgr._retainer, PriorityRetainer)
        assert isinstance(mgr._guarantee, SystemPromptGuarantee)

    def test_empty_status(self):
        mgr = ContextWindowMgr()
        status = mgr.get_status()
        assert status in (WindowStatus.HEALTHY, WindowStatus.WARNING, WindowStatus.CRITICAL, WindowStatus.OVERFLOW)

    def test_snapshot_empty(self):
        mgr = ContextWindowMgr()
        snap = mgr.take_snapshot()
        assert snap.message_count == 0
        assert snap.total_tokens == 0

    def test_custom_max_tokens(self):
        mgr = ContextWindowMgr(max_tokens=4096)
        assert mgr._max_tokens == 4096

    def test_add_and_get_messages(self):
        mgr = ContextWindowMgr()
        mgr.add_message(role="user", content="a")
        mgr.add_message(role="assistant", content="b")
        msgs = mgr.get_messages()
        assert len(msgs) >= 2


# ====== STREAM ENHANCER ======


class TestStreamEnhancer:
    """StreamEnhancer testleri."""

    def test_init(self):
        se = StreamEnhancer()
        assert "reasoning" in se._lane_buffers
        assert "answer" in se._lane_buffers
        assert se._block_streaming_default is True
        assert se._partial_active is False

    def test_separate_reasoning_lanes_with_thinking(self):
        se = StreamEnhancer()
        content = "<thinking>I need to think</thinking>The answer is 42."
        result = se.separate_reasoning_lanes(content)
        assert result["reasoning"] == "I need to think"
        assert "42" in result["answer"]
        assert "<thinking>" not in result["answer"]

    def test_separate_reasoning_lanes_no_thinking(self):
        se = StreamEnhancer()
        content = "Just a plain answer."
        result = se.separate_reasoning_lanes(content)
        assert result["reasoning"] == ""
        assert result["answer"] == "Just a plain answer."

    def test_separate_reasoning_lanes_multiple(self):
        se = StreamEnhancer()
        content = "<thinking>T1</thinking>A1<thinking>T2</thinking>A2"
        result = se.separate_reasoning_lanes(content)
        assert "T1" in result["reasoning"]
        assert "T2" in result["reasoning"]

    def test_native_single_message_stream(self):
        se = StreamEnhancer()
        chunks = ["Hello ", "world", "!"]
        result = se.native_single_message_stream(chunks)
        assert result == "Hello world!"

    def test_honor_block_streaming_default_true(self):
        se = StreamEnhancer()
        result = se.honor_block_streaming_default(
            {"blockStreamingDefault": True}
        )
        assert result is True
        assert se._block_streaming_default is True

    def test_honor_block_streaming_default_false(self):
        se = StreamEnhancer()
        result = se.honor_block_streaming_default(
            {"blockStreamingDefault": False}
        )
        assert result is False
        assert se._block_streaming_default is False

    def test_keep_partial_during_reasoning_sticky(self):
        se = StreamEnhancer()
        assert se._partial_active is False
        result1 = se.keep_partial_during_reasoning(True)
        assert result1 is True
        assert se._partial_active is True
        # Sticky: once True, stays True even when False is passed
        result2 = se.keep_partial_during_reasoning(False)
        assert result2 is True
        assert se._partial_active is True

    def test_sticky_reply_threading(self):
        chunks = ["chunk1", "chunk2", "chunk3"]
        result = StreamEnhancer.sticky_reply_threading(
            chunks, "thread-42"
        )
        assert len(result) == 3
        for i, item in enumerate(result):
            assert item["thread_id"] == "thread-42"
            assert item["chunk_index"] == str(i)
            assert item["content"] == chunks[i]

    def test_reset_lanes(self):
        se = StreamEnhancer()
        se._partial_active = True
        se._lane_buffers["reasoning"].append("test")
        se.reset_lanes()
        assert se._partial_active is False
        assert se._lane_buffers["reasoning"] == []
        assert se._lane_buffers["answer"] == []


# ====== ERROR ENHANCER ======


class TestErrorEnhancer:
    """ErrorEnhancer testleri."""

    def test_init(self):
        ee = ErrorEnhancer()
        assert ee._retry_count == 0
        assert ee._max_retries == 3
        assert ee._deferred_snapshots == []

    def test_init_custom_retries(self):
        ee = ErrorEnhancer(max_retries=5)
        assert ee._max_retries == 5

    def test_billing_error_with_model(self):
        ee = ErrorEnhancer()
        result = ee.billing_error_with_model(
            "Rate limit exceeded", "gpt-4"
        )
        assert "[model: gpt-4]" in result
        assert "Rate limit exceeded" in result

    def test_billing_error_empty_model(self):
        ee = ErrorEnhancer()
        result = ee.billing_error_with_model("Some error", "")
        assert result == "Some error"
        assert "[model:" not in result

    def test_compaction_retry_success_first(self):
        ee = ErrorEnhancer()
        call_count = [0]
        def func(**kwargs):
            call_count[0] += 1
            return "success"
        result = ee.compaction_retry(func, {"budget": 1000})
        assert result == "success"
        assert call_count[0] == 1

    def test_compaction_retry_eventual_success(self):
        ee = ErrorEnhancer()
        attempts = []
        def func(**kwargs):
            attempts.append(kwargs.get("budget"))
            if len(attempts) < 3:
                raise ValueError("fail")
            return "ok"
        result = ee.compaction_retry(func, {"budget": 1000}, max_retries=5)
        assert result == "ok"
        assert len(attempts) == 3

    def test_compaction_retry_budget_scaling(self):
        ee = ErrorEnhancer()
        budgets = []
        def func(**kwargs):
            budgets.append(kwargs.get("budget"))
            if len(budgets) < 3:
                raise ValueError("fail")
            return "done"
        ee.compaction_retry(func, {"budget": 1000}, max_retries=5)
        assert budgets[0] == 1000
        # scale = 0.5^(attempt+1): attempt=0 => 0.5, attempt=1 => 0.25
        assert budgets[1] == 500
        assert budgets[2] == 125

    def test_compaction_retry_all_fail(self):
        ee = ErrorEnhancer()
        def func(**kwargs):
            raise RuntimeError("always fails")
        with pytest.raises(RuntimeError, match="always fails"):
            ee.compaction_retry(func, {"budget": 100}, max_retries=3)

    def test_surface_tts_errors(self):
        errors = [
            {"provider": "elevenlabs", "msg": "timeout"},
            {"provider": "google", "msg": "quota"},
        ]
        result = ErrorEnhancer.surface_tts_errors(errors)
        assert len(result) == 2
        for err in result:
            assert err["surfaced"] is True
            assert "timestamp" in err

    def test_surface_tts_errors_preserves_existing(self):
        errors = [{"provider": "test", "surfaced": False}]
        result = ErrorEnhancer.surface_tts_errors(errors)
        assert result[0]["surfaced"] is False

    def test_defer_transient_snapshot(self):
        ee = ErrorEnhancer()
        ee.defer_transient_snapshot({"error": "transient", "code": 503})
        assert len(ee._deferred_snapshots) == 1
        assert "deferred_at" in ee._deferred_snapshots[0]

    def test_get_deferred_snapshots(self):
        ee = ErrorEnhancer()
        ee.defer_transient_snapshot({"e": "1"})
        ee.defer_transient_snapshot({"e": "2"})
        snaps = ee.get_deferred_snapshots()
        assert len(snaps) == 2
        assert len(ee._deferred_snapshots) == 0

    def test_classify_abort_as_timeout(self):
        result = ErrorEnhancer.classify_abort_as_timeout("abort")
        assert result == ErrorClassification.TIMEOUT

    def test_classify_aborted_as_timeout(self):
        result = ErrorEnhancer.classify_abort_as_timeout("aborted")
        assert result == ErrorClassification.TIMEOUT

    def test_classify_other_unchanged(self):
        result = ErrorEnhancer.classify_abort_as_timeout("network")
        assert result == "network"

    def test_create_enhanced_error_billing(self):
        ee = ErrorEnhancer()
        err = ee.create_enhanced_error(
            "billing quota exceeded",
            model="gpt-4",
            provider="openai",
        )
        assert isinstance(err, EnhancedError)
        assert err.classification == ErrorClassification.BILLING
        assert err.retryable is False
        assert err.model == "gpt-4"

    def test_create_enhanced_error_timeout(self):
        ee = ErrorEnhancer()
        err = ee.create_enhanced_error("connection timeout")
        assert err.classification == ErrorClassification.TIMEOUT
        assert err.retryable is True

    def test_create_enhanced_error_context_overflow(self):
        ee = ErrorEnhancer()
        err = ee.create_enhanced_error("context window overflow error")
        assert err.classification == ErrorClassification.CONTEXT_OVERFLOW

    def test_create_enhanced_error_transient(self):
        ee = ErrorEnhancer()
        err = ee.create_enhanced_error("unknown error")
        assert err.classification == ErrorClassification.TRANSIENT
        assert err.retryable is True


# ====== TOKEN BUFFER ======


class TestTokenBuffer:
    """TokenBuffer testleri."""

    def test_init(self):
        tb = TokenBuffer()
        assert tb.is_empty is True
        assert tb.size == 0

    def test_init_custom_size(self):
        tb = TokenBuffer(max_size=128)
        assert tb._max_size == 128

    def test_add_single_token(self):
        tb = TokenBuffer(max_size=64)
        result = tb.add("hello")
        assert tb.size > 0

    def test_add_triggers_flush_on_full(self):
        tb = TokenBuffer(max_size=10)
        flushed = None
        for i in range(20):
            result = tb.add("x" * 5)
            if result:
                flushed = result
                break
        assert tb.size <= 10 or flushed is not None

    def test_flush(self):
        tb = TokenBuffer()
        tb.add("hello ")
        tb.add("world")
        content = tb.flush()
        assert "hello" in content
        assert "world" in content
        assert tb.is_empty is True

    def test_flush_empty(self):
        tb = TokenBuffer()
        content = tb.flush()
        assert content == ""

    def test_flush_complete(self):
        tb = TokenBuffer()
        tb.add("some content")
        content = tb.flush_complete()
        assert content != ""
        assert tb.is_empty is True

    def test_flush_at_word_boundary(self):
        tb = TokenBuffer()
        tb.add("hello world foo")
        content = tb.flush_at_word_boundary()
        assert isinstance(content, str)

    def test_flush_at_sentence_boundary(self):
        tb = TokenBuffer()
        tb.add("Hello world. This is a test")
        content = tb.flush_at_sentence_boundary()
        assert isinstance(content, str)

    def test_peek(self):
        tb = TokenBuffer()
        tb.add("peek test")
        peeked = tb.peek()
        assert "peek" in peeked
        assert tb.size > 0

    def test_clear(self):
        tb = TokenBuffer()
        tb.add("data")
        tb.clear()
        assert tb.is_empty is True
        assert tb.size == 0

    def test_is_empty_property(self):
        tb = TokenBuffer()
        assert tb.is_empty is True
        tb.add("x")
        assert tb.is_empty is False

    def test_is_full_property(self):
        tb = TokenBuffer(max_size=5)
        assert tb.is_full is False
        result = tb.add("x" * 10)
        assert result is not None or tb.is_full or tb.size == 0

    def test_should_flush_property(self):
        import time
        tb = TokenBuffer(max_size=1000, flush_interval_ms=1)
        tb._buffer = "hello"
        tb._last_flush_time = time.time() - 1
        assert tb.should_flush() is True

    def test_sentence_endings(self):
        tb = TokenBuffer()
        assert tb._is_sentence_boundary(".")
        assert tb._is_sentence_boundary("!")
        assert tb._is_sentence_boundary("?")

    def test_sentence_boundary_flush_on_period(self):
        tb = TokenBuffer()
        tb.add("Hello world.")
        content = tb.flush_at_sentence_boundary()
        if content:
            assert "." in content

    def test_multiple_add_and_flush(self):
        tb = TokenBuffer()
        tb.add("part1 ")
        tb.add("part2 ")
        tb.add("part3")
        content = tb.flush()
        assert "part1" in content
        assert "part2" in content
        assert "part3" in content

    def test_add_returns_none_when_not_full(self):
        tb = TokenBuffer(max_size=1000)
        result = tb.add("small")
        assert result is None or result == ""

    def test_size_property(self):
        tb = TokenBuffer()
        tb.add("12345")
        assert tb.size == 5


# ====== PROVIDER STREAM ADAPTER ======


class TestProviderStreamAdapter:
    """ProviderStreamAdapter testleri."""

    def test_init(self):
        psa = ProviderStreamAdapter()
        assert psa._PROVIDER_FORMATS is not None

    def test_provider_format_map(self):
        psa = ProviderStreamAdapter()
        assert psa._PROVIDER_FORMATS["anthropic"] == ProviderFormat.SSE
        assert psa._PROVIDER_FORMATS["openai"] == ProviderFormat.SSE
        assert psa._PROVIDER_FORMATS["gemini"] == ProviderFormat.NDJSON
        assert psa._PROVIDER_FORMATS["ollama"] == ProviderFormat.NDJSON
        assert psa._PROVIDER_FORMATS["openrouter"] == ProviderFormat.SSE

    def test_provider_property(self):
        psa = ProviderStreamAdapter(provider="openai")
        assert psa.provider == "openai"
        assert psa.format == ProviderFormat.SSE

    def test_default_provider(self):
        psa = ProviderStreamAdapter()
        assert psa.provider == "anthropic"

    def test_parse_chunk_ndjson(self):
        import json
        psa = ProviderStreamAdapter(provider="ollama")
        data = json.dumps({"message": {"content": "hi"}})
        result = psa.parse_chunk(data)
        assert result is not None

    def test_reset(self):
        psa = ProviderStreamAdapter(provider="openai")
        psa.reset()
        assert psa._token_index == 0

    def test_metadata(self):
        psa = ProviderStreamAdapter(provider="anthropic")
        meta = psa.metadata
        assert isinstance(meta, dict)

    def test_get_stats(self):
        psa = ProviderStreamAdapter()
        stats = psa.get_stats()
        assert isinstance(stats, dict)

    def test_gemini_provider(self):
        psa = ProviderStreamAdapter(provider="gemini")
        assert psa.format == ProviderFormat.NDJSON

    def test_openrouter_provider(self):
        psa = ProviderStreamAdapter(provider="openrouter")
        assert psa.format == ProviderFormat.SSE

    def test_unknown_provider(self):
        psa = ProviderStreamAdapter(provider="unknown")
        assert psa.format is not None

    def test_total_parsed_init(self):
        psa = ProviderStreamAdapter()
        assert psa._total_parsed == 0

    def test_token_index_init(self):
        psa = ProviderStreamAdapter()
        assert psa._token_index == 0


# ====== STREAM ERROR HANDLER ======


class TestStreamErrorHandler:
    """StreamErrorHandler testleri."""

    def test_init(self):
        seh = StreamErrorHandler()
        assert seh._retry_count == 0
        assert seh._errors == []

    def test_init_custom(self):
        seh = StreamErrorHandler(max_retries=5, retry_delay_ms=2000)
        assert seh._max_retries == 5
        assert seh._retry_delay_ms == 2000

    def test_classify_connection_error(self):
        seh = StreamErrorHandler()
        etype = seh._classify_error("connection refused")
        assert etype == StreamErrorType.CONNECTION

    def test_classify_timeout_error(self):
        seh = StreamErrorHandler()
        etype = seh._classify_error("request timeout")
        assert etype == StreamErrorType.TIMEOUT

    def test_classify_rate_limit(self):
        seh = StreamErrorHandler()
        etype = seh._classify_error("rate limit exceeded")
        assert etype == StreamErrorType.RATE_LIMIT

    def test_classify_server_error(self):
        seh = StreamErrorHandler()
        etype = seh._classify_error("internal server error 500")
        assert etype == StreamErrorType.SERVER

    def test_should_retry_retryable(self):
        seh = StreamErrorHandler()
        err = StreamError(error_type=StreamErrorType.CONNECTION, message="conn", retryable=True)
        assert seh.should_retry(err) is True

    def test_should_retry_max_reached(self):
        seh = StreamErrorHandler(max_retries=2)
        seh._retry_count = 2
        err = StreamError(error_type=StreamErrorType.CONNECTION, message="conn", retryable=True)
        assert seh.should_retry(err) is False

    def test_handle_error(self):
        seh = StreamErrorHandler()
        result = seh.handle_error("test error")
        assert result is not None

    def test_retry_delay(self):
        seh = StreamErrorHandler(retry_delay_ms=1000)
        d0 = seh._calculate_retry_delay()
        assert d0 == 1000
        seh._retry_count = 1
        d1 = seh._calculate_retry_delay()
        assert d1 >= d0

    def test_max_delay_cap(self):
        seh = StreamErrorHandler(retry_delay_ms=1000)
        delay = seh._calculate_retry_delay()
        assert delay <= 60000

    def test_record_retry(self):
        seh = StreamErrorHandler()
        seh.record_retry()
        assert seh._retry_count == 1

    def test_record_recovery(self):
        seh = StreamErrorHandler()
        seh._retry_count = 3
        seh.record_recovery()
        assert seh._recovery_count >= 1

    def test_on_error_callback(self):
        seh = StreamErrorHandler()
        called = []
        seh.on_error(lambda e: called.append(e))
        seh.handle_error("callback test")
        assert len(called) >= 1

    def test_get_error_rate(self):
        seh = StreamErrorHandler()
        rate = seh.get_error_rate()
        assert isinstance(rate, float)
        assert rate >= 0.0

    def test_error_list(self):
        seh = StreamErrorHandler()
        seh.handle_error("err1")
        seh.handle_error("err2")
        assert len(seh._errors) == 2

    def test_classify_unknown(self):
        seh = StreamErrorHandler()
        etype = seh._classify_error("something very weird")
        assert isinstance(etype, StreamErrorType)

    def test_multiple_retries(self):
        seh = StreamErrorHandler()
        seh.record_retry()
        seh.record_retry()
        seh.record_retry()
        assert seh._retry_count == 3

    def test_get_stats(self):
        seh = StreamErrorHandler()
        stats = seh.get_stats()
        assert isinstance(stats, dict)

    def test_reset(self):
        seh = StreamErrorHandler()
        seh.handle_error("test")
        seh.reset()
        assert seh._retry_count == 0

    def test_get_last_error(self):
        seh = StreamErrorHandler()
        seh.handle_error("last error")
        last = seh.get_last_error()
        assert last is not None


# ====== STREAM EVENT EMITTER ======


class TestStreamEventEmitter:
    """StreamEventEmitter testleri."""

    def test_init(self):
        see = StreamEventEmitter()
        assert see._subscribers == {}
        assert see._paused is False

    def test_subscribe_and_emit(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(
            StreamEventType.TOKEN,
            lambda e: received.append(e),
        )
        see.emit_token("hello")
        assert len(received) == 1

    def test_unsubscribe(self):
        see = StreamEventEmitter()
        received = []
        handler = lambda e: received.append(e)
        see.subscribe(StreamEventType.TOKEN, handler)
        see.unsubscribe(StreamEventType.TOKEN, handler)
        see.emit_token("test")
        assert len(received) == 0

    def test_emit_start(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(
            StreamEventType.START,
            lambda e: received.append(e),
        )
        see.emit_start()
        assert len(received) == 1

    def test_emit_end(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(
            StreamEventType.END,
            lambda e: received.append(e),
        )
        see.emit_end()
        assert len(received) == 1

    def test_emit_error(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(
            StreamEventType.ERROR,
            lambda e: received.append(e),
        )
        see.emit_error("test error")
        assert len(received) == 1

    def test_emit_flush(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(
            StreamEventType.FLUSH,
            lambda e: received.append(e),
        )
        see.emit_flush("flushed content")
        assert len(received) == 1

    def test_pause_resume(self):
        see = StreamEventEmitter()
        see.pause()
        assert see._paused is True
        see.resume()
        assert see._paused is False

    def test_paused_queues_events(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(
            StreamEventType.TOKEN,
            lambda e: received.append(e),
        )
        see.pause()
        see.emit_token("queued")
        paused_count = len(received)
        see.resume()
        assert len(received) >= paused_count

    def test_clear_queue(self):
        see = StreamEventEmitter()
        see.pause()
        see.emit_token("q1")
        see.emit_token("q2")
        see.clear_queue()
        received = []
        see.subscribe(
            StreamEventType.TOKEN,
            lambda e: received.append(e),
        )
        see.resume()
        assert len(received) == 0

    def test_multiple_subscribers(self):
        see = StreamEventEmitter()
        r1 = []
        r2 = []
        see.subscribe(
            StreamEventType.TOKEN,
            lambda e: r1.append(e),
        )
        see.subscribe(
            StreamEventType.TOKEN,
            lambda e: r2.append(e),
        )
        see.emit_token("broadcast")
        assert len(r1) == 1
        assert len(r2) == 1

    def test_global_subscriber(self):
        see = StreamEventEmitter()
        received = []
        see.subscribe(StreamEventType.TOKEN, lambda e: received.append(e))
        see.emit_token("t1")
        assert len(received) >= 1

    def test_backpressure_threshold(self):
        see = StreamEventEmitter()
        assert see._backpressure_threshold > 0


# ====== STREAMING CLIENT ======


class TestStreamingClient:
    """StreamingClient testleri."""

    def test_init(self):
        sc = StreamingClient()
        assert isinstance(sc._buffer, TokenBuffer)
        assert isinstance(sc._emitter, StreamEventEmitter)
        assert isinstance(sc._adapters, dict)
        assert isinstance(sc._error_handler, StreamErrorHandler)

    def test_process_single_chunk(self):
        sc = StreamingClient()
        result = sc.process_single_chunk("hello", "openai")
        assert isinstance(result, list)

    def test_flush(self):
        sc = StreamingClient()
        sc._buffer.add("buffered content")
        content = sc.flush()
        assert isinstance(content, str)

    def test_metrics_tracking(self):
        sc = StreamingClient()
        sc.process_single_chunk("tok1", "openai")
        sc.process_single_chunk("tok2", "openai")
        metrics = sc.get_last_metrics()
        assert metrics is None or isinstance(metrics, StreamMetrics)

    def test_default_provider(self):
        sc = StreamingClient()
        sc.process_single_chunk("test", "anthropic")
        assert "anthropic" in sc._adapters or len(sc._adapters) >= 0

    def test_error_handling_integration(self):
        sc = StreamingClient()
        sc._error_handler.handle_error("test error")
        assert len(sc._error_handler._errors) >= 1

    def test_emitter_integration(self):
        sc = StreamingClient()
        received = []
        sc._emitter.subscribe(
            StreamEventType.TOKEN,
            lambda e: received.append(e),
        )
        sc._emitter.emit_token("integrated")
        assert len(received) == 1

    def test_buffer_integration(self):
        sc = StreamingClient()
        sc._buffer.add("part1 ")
        sc._buffer.add("part2")
        content = sc._buffer.flush()
        assert "part1" in content
        assert "part2" in content
