"""Persistent Chat History testleri.

ConversationStore, MessageLogger,
ContextRetriever, HistorySearch,
MemoryPruner testleri.
"""

import time

import pytest

from app.config import Settings
from app.core.chathistory import (
    ContextRetriever,
    ConversationStore,
    HistorySearch,
    MemoryPruner,
    MessageLogger,
)
from app.models.chathistory_models import (
    Conversation,
    ConversationStatus,
    ConversationSummary,
    Message,
    MessageRole,
    RetentionAction,
    RetentionPolicy,
    SearchQuery,
    StorageBackend,
)


# ---- Config Testleri ----


class TestChatHistoryConfig:
    """Config ayar testleri."""

    def test_defaults(self) -> None:
        s = Settings()
        assert s.chathistory_enabled is False
        assert s.storage_backend == "memory"
        assert s.retention_days == 30
        assert s.auto_prune is False

    def test_custom_values(self) -> None:
        s = Settings(
            chathistory_enabled=True,
            storage_backend="postgresql",
            retention_days=30,
            auto_prune=True,
        )
        assert s.chathistory_enabled is True
        assert s.storage_backend == "postgresql"
        assert s.retention_days == 30
        assert s.auto_prune is True


# ---- Model Testleri ----


class TestChatHistoryModels:
    """Model testleri."""

    def test_message_role_enum(self) -> None:
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL == "tool"

    def test_storage_backend_enum(self) -> None:
        assert StorageBackend.MEMORY == "memory"
        assert StorageBackend.SQLITE == "sqlite"
        assert StorageBackend.POSTGRESQL == "postgresql"

    def test_retention_action_enum(self) -> None:
        assert RetentionAction.KEEP == "keep"
        assert RetentionAction.ARCHIVE == "archive"
        assert RetentionAction.SUMMARIZE == "summarize"
        assert RetentionAction.DELETE == "delete"

    def test_conversation_status_enum(self) -> None:
        assert (
            ConversationStatus.ACTIVE == "active"
        )
        assert (
            ConversationStatus.ARCHIVED
            == "archived"
        )
        assert (
            ConversationStatus.DELETED == "deleted"
        )

    def test_conversation_model(self) -> None:
        c = Conversation(title="test")
        assert c.title == "test"
        assert c.conversation_id
        assert c.status == ConversationStatus.ACTIVE
        assert c.message_count == 0
        assert c.tags == []
        assert c.metadata == {}

    def test_message_model(self) -> None:
        m = Message(
            conversation_id="c1",
            role=MessageRole.USER,
            content="hello",
            timestamp=time.time(),
        )
        assert m.content == "hello"
        assert m.role == MessageRole.USER
        assert m.message_id
        assert m.thread_id == ""
        assert m.attachments == []

    def test_search_query_model(self) -> None:
        q = SearchQuery(text="test")
        assert q.text == "test"
        assert q.limit == 50

    def test_retention_policy_model(self) -> None:
        p = RetentionPolicy(
            name="default",
            retention_days=30,
        )
        assert p.name == "default"
        assert p.retention_days == 30
        assert p.enabled is True
        assert (
            p.action == RetentionAction.ARCHIVE
        )

    def test_conversation_summary_model(
        self,
    ) -> None:
        s = ConversationSummary(
            conversation_id="c1",
            summary_text="ozet",
            message_count=5,
        )
        assert s.summary_text == "ozet"
        assert s.message_count == 5
        assert s.key_points == []


# ---- ConversationStore Testleri ----


class TestConversationStore:
    """ConversationStore testleri."""

    def setup_method(self) -> None:
        self.store = ConversationStore()

    def test_init(self) -> None:
        assert self.store._backend == "memory"
        assert len(self.store._conversations) == 0

    def test_init_custom_backend(self) -> None:
        s = ConversationStore(backend="sqlite")
        assert s._backend == "sqlite"

    def test_create_conversation(self) -> None:
        c = self.store.create_conversation(
            title="Test",
        )
        assert c.title == "Test"
        assert c.conversation_id
        assert (
            c.conversation_id
            in self.store._conversations
        )

    def test_create_with_all_params(
        self,
    ) -> None:
        c = self.store.create_conversation(
            title="Full",
            channel="telegram",
            user_id="u1",
            persona_id="p1",
            tags=["tag1"],
            metadata={"key": "val"},
        )
        assert c.channel == "telegram"
        assert c.user_id == "u1"
        assert c.persona_id == "p1"
        assert c.tags == ["tag1"]
        assert c.metadata == {"key": "val"}

    def test_get_conversation(self) -> None:
        c = self.store.create_conversation(
            title="T",
        )
        got = self.store.get_conversation(
            c.conversation_id,
        )
        assert got is not None
        assert got.title == "T"

    def test_get_conversation_not_found(
        self,
    ) -> None:
        assert (
            self.store.get_conversation("bad")
            is None
        )

    def test_update_conversation(self) -> None:
        c = self.store.create_conversation(
            title="Old",
        )
        ok = self.store.update_conversation(
            c.conversation_id,
            title="New",
        )
        assert ok is True
        assert c.title == "New"

    def test_update_conversation_tags(
        self,
    ) -> None:
        c = self.store.create_conversation()
        self.store.update_conversation(
            c.conversation_id,
            tags=["a", "b"],
        )
        assert c.tags == ["a", "b"]

    def test_update_conversation_metadata(
        self,
    ) -> None:
        c = self.store.create_conversation(
            metadata={"x": 1},
        )
        self.store.update_conversation(
            c.conversation_id,
            metadata={"y": 2},
        )
        assert c.metadata == {"x": 1, "y": 2}

    def test_update_conversation_status(
        self,
    ) -> None:
        c = self.store.create_conversation()
        self.store.update_conversation(
            c.conversation_id,
            status=ConversationStatus.ARCHIVED,
        )
        assert (
            c.status
            == ConversationStatus.ARCHIVED
        )

    def test_update_conversation_not_found(
        self,
    ) -> None:
        ok = self.store.update_conversation(
            "bad", title="X",
        )
        assert ok is False

    def test_delete_conversation(self) -> None:
        c = self.store.create_conversation()
        ok = self.store.delete_conversation(
            c.conversation_id,
        )
        assert ok is True
        assert (
            self.store.get_conversation(
                c.conversation_id,
            )
            is None
        )

    def test_delete_conversation_not_found(
        self,
    ) -> None:
        assert (
            self.store.delete_conversation(
                "bad",
            )
            is False
        )

    def test_archive_conversation(
        self,
    ) -> None:
        c = self.store.create_conversation()
        ok = self.store.archive_conversation(
            c.conversation_id,
        )
        assert ok is True
        assert (
            c.status
            == ConversationStatus.ARCHIVED
        )

    def test_list_conversations(self) -> None:
        self.store.create_conversation(
            title="A",
        )
        self.store.create_conversation(
            title="B",
        )
        result = (
            self.store.list_conversations()
        )
        assert len(result) == 2

    def test_list_by_channel(self) -> None:
        self.store.create_conversation(
            channel="tg",
        )
        self.store.create_conversation(
            channel="email",
        )
        result = (
            self.store.list_conversations(
                channel="tg",
            )
        )
        assert len(result) == 1

    def test_list_by_user(self) -> None:
        self.store.create_conversation(
            user_id="u1",
        )
        self.store.create_conversation(
            user_id="u2",
        )
        result = (
            self.store.list_conversations(
                user_id="u1",
            )
        )
        assert len(result) == 1

    def test_list_by_status(self) -> None:
        c1 = self.store.create_conversation()
        self.store.create_conversation()
        self.store.archive_conversation(
            c1.conversation_id,
        )
        result = (
            self.store.list_conversations(
                status=(
                    ConversationStatus.ARCHIVED
                ),
            )
        )
        assert len(result) == 1

    def test_list_by_tag(self) -> None:
        self.store.create_conversation(
            tags=["vip"],
        )
        self.store.create_conversation(
            tags=["normal"],
        )
        result = (
            self.store.list_conversations(
                tag="vip",
            )
        )
        assert len(result) == 1

    def test_list_with_limit(self) -> None:
        for _ in range(5):
            self.store.create_conversation()
        result = (
            self.store.list_conversations(
                limit=3,
            )
        )
        assert len(result) == 3

    def test_add_message(self) -> None:
        c = self.store.create_conversation()
        m = self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "hello",
        )
        assert m is not None
        assert m.content == "hello"
        assert c.message_count == 1

    def test_add_message_with_extras(
        self,
    ) -> None:
        c = self.store.create_conversation()
        m = self.store.add_message(
            c.conversation_id,
            MessageRole.ASSISTANT,
            "hi",
            thread_id="t1",
            parent_id="p1",
            attachments=[{"type": "image"}],
            metadata={"key": "val"},
            token_count=10,
        )
        assert m is not None
        assert m.thread_id == "t1"
        assert m.parent_id == "p1"
        assert len(m.attachments) == 1
        assert m.token_count == 10

    def test_add_message_no_conversation(
        self,
    ) -> None:
        m = self.store.add_message(
            "bad",
            MessageRole.USER,
            "hi",
        )
        assert m is None

    def test_get_messages(self) -> None:
        c = self.store.create_conversation()
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "one",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.ASSISTANT,
            "two",
        )
        msgs = self.store.get_messages(
            c.conversation_id,
        )
        assert len(msgs) == 2

    def test_get_messages_with_role(
        self,
    ) -> None:
        c = self.store.create_conversation()
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "u",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.ASSISTANT,
            "a",
        )
        msgs = self.store.get_messages(
            c.conversation_id,
            role=MessageRole.USER,
        )
        assert len(msgs) == 1
        assert msgs[0].content == "u"

    def test_get_messages_with_offset_limit(
        self,
    ) -> None:
        c = self.store.create_conversation()
        for i in range(10):
            self.store.add_message(
                c.conversation_id,
                MessageRole.USER,
                f"msg{i}",
            )
        msgs = self.store.get_messages(
            c.conversation_id,
            limit=3,
            offset=2,
        )
        assert len(msgs) == 3
        assert msgs[0].content == "msg2"

    def test_get_message(self) -> None:
        c = self.store.create_conversation()
        m = self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "hi",
        )
        got = self.store.get_message(
            c.conversation_id,
            m.message_id,
        )
        assert got is not None
        assert got.content == "hi"

    def test_get_message_not_found(
        self,
    ) -> None:
        c = self.store.create_conversation()
        got = self.store.get_message(
            c.conversation_id, "bad",
        )
        assert got is None

    def test_delete_message(self) -> None:
        c = self.store.create_conversation()
        m = self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "del",
        )
        ok = self.store.delete_message(
            c.conversation_id,
            m.message_id,
        )
        assert ok is True
        assert c.message_count == 0

    def test_delete_message_not_found(
        self,
    ) -> None:
        c = self.store.create_conversation()
        ok = self.store.delete_message(
            c.conversation_id, "bad",
        )
        assert ok is False

    def test_get_thread(self) -> None:
        c = self.store.create_conversation()
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "t1",
            thread_id="th1",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "t2",
            thread_id="th1",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "other",
            thread_id="th2",
        )
        thread = self.store.get_thread(
            c.conversation_id, "th1",
        )
        assert len(thread) == 2

    def test_get_message_count(self) -> None:
        c = self.store.create_conversation()
        assert (
            self.store.get_message_count(
                c.conversation_id,
            )
            == 0
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "m",
        )
        assert (
            self.store.get_message_count(
                c.conversation_id,
            )
            == 1
        )

    def test_search_messages(self) -> None:
        c = self.store.create_conversation()
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "hello world",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "goodbye",
        )
        result = self.store.search_messages(
            "hello",
        )
        assert len(result) == 1

    def test_search_messages_empty(
        self,
    ) -> None:
        result = self.store.search_messages("")
        assert len(result) == 0

    def test_search_in_conversation(
        self,
    ) -> None:
        c1 = self.store.create_conversation()
        c2 = self.store.create_conversation()
        self.store.add_message(
            c1.conversation_id,
            MessageRole.USER,
            "alpha",
        )
        self.store.add_message(
            c2.conversation_id,
            MessageRole.USER,
            "alpha beta",
        )
        result = self.store.search_messages(
            "alpha",
            conversation_id=(
                c1.conversation_id
            ),
        )
        assert len(result) == 1

    def test_export_conversation(self) -> None:
        c = self.store.create_conversation(
            title="Exp",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "hi",
        )
        data = self.store.export_conversation(
            c.conversation_id,
        )
        assert data is not None
        assert "conversation" in data
        assert "messages" in data
        assert len(data["messages"]) == 1

    def test_export_not_found(self) -> None:
        assert (
            self.store.export_conversation(
                "bad",
            )
            is None
        )

    def test_import_conversation(self) -> None:
        c = self.store.create_conversation(
            title="Imp",
        )
        self.store.add_message(
            c.conversation_id,
            MessageRole.USER,
            "msg",
        )
        data = self.store.export_conversation(
            c.conversation_id,
        )
        self.store.delete_conversation(
            c.conversation_id,
        )
        imported = (
            self.store.import_conversation(data)
        )
        assert imported is not None
        assert imported.title == "Imp"

    def test_import_invalid(self) -> None:
        assert (
            self.store.import_conversation({})
            is None
        )
        assert (
            self.store.import_conversation(None)
            is None
        )

    def test_export_all(self) -> None:
        self.store.create_conversation()
        self.store.create_conversation()
        data = self.store.export_all()
        assert len(data) == 2

    def test_to_json(self) -> None:
        c = self.store.create_conversation(
            title="J",
        )
        j = self.store.to_json(
            c.conversation_id,
        )
        assert len(j) > 0
        assert "J" in j

    def test_to_json_not_found(self) -> None:
        assert self.store.to_json("bad") == ""

    def test_from_json(self) -> None:
        c = self.store.create_conversation(
            title="FJ",
        )
        j = self.store.to_json(
            c.conversation_id,
        )
        self.store.delete_conversation(
            c.conversation_id,
        )
        imported = self.store.from_json(j)
        assert imported is not None
        assert imported.title == "FJ"

    def test_from_json_invalid(self) -> None:
        assert self.store.from_json("") is None
        assert (
            self.store.from_json("bad") is None
        )

    def test_get_stats(self) -> None:
        self.store.create_conversation()
        stats = self.store.get_stats()
        assert stats["backend"] == "memory"
        assert stats["total_conversations"] == 1
        assert stats["total_messages"] == 0
        assert "status_counts" in stats


# ---- MessageLogger Testleri ----


class TestMessageLogger:
    """MessageLogger testleri."""

    def setup_method(self) -> None:
        self.logger = MessageLogger()

    def test_init(self) -> None:
        assert self.logger._enabled is True
        assert len(self.logger._buffer) == 0

    def test_init_custom_buffer(self) -> None:
        ml = MessageLogger(buffer_size=100)
        assert ml._buffer_size == 100

    def test_log_message(self) -> None:
        m = self.logger.log_message(
            "c1",
            MessageRole.USER,
            "hello",
        )
        assert m is not None
        assert m.content == "hello"
        assert m.conversation_id == "c1"

    def test_log_message_with_extras(
        self,
    ) -> None:
        m = self.logger.log_message(
            "c1",
            MessageRole.USER,
            "hi",
            thread_id="t1",
            parent_id="p1",
            attachments=[{"type": "img"}],
            metadata={"k": "v"},
            token_count=5,
        )
        assert m.thread_id == "t1"
        assert m.parent_id == "p1"
        assert len(m.attachments) == 1
        assert m.token_count == 5

    def test_log_empty_content(self) -> None:
        m = self.logger.log_message(
            "c1", MessageRole.USER, "",
        )
        assert m is None

    def test_log_empty_conv_id(self) -> None:
        m = self.logger.log_message(
            "", MessageRole.USER, "hi",
        )
        assert m is None

    def test_log_disabled(self) -> None:
        self.logger.disable()
        m = self.logger.log_message(
            "c1", MessageRole.USER, "hi",
        )
        assert m is None

    def test_log_user(self) -> None:
        m = self.logger.log_user("c1", "hi")
        assert m is not None
        assert m.role == MessageRole.USER

    def test_log_assistant(self) -> None:
        m = self.logger.log_assistant(
            "c1", "hi",
        )
        assert m is not None
        assert m.role == MessageRole.ASSISTANT

    def test_log_system(self) -> None:
        m = self.logger.log_system(
            "c1", "sys",
        )
        assert m is not None
        assert m.role == MessageRole.SYSTEM

    def test_buffer_overflow(self) -> None:
        ml = MessageLogger(buffer_size=5)
        for i in range(10):
            ml.log_message(
                "c1",
                MessageRole.USER,
                f"msg{i}",
            )
        assert len(ml._buffer) == 5

    def test_get_buffer(self) -> None:
        self.logger.log_user("c1", "a")
        self.logger.log_user("c2", "b")
        buf = self.logger.get_buffer()
        assert len(buf) == 2

    def test_get_buffer_filtered(self) -> None:
        self.logger.log_user("c1", "a")
        self.logger.log_user("c2", "b")
        buf = self.logger.get_buffer(
            conversation_id="c1",
        )
        assert len(buf) == 1

    def test_get_buffer_limit(self) -> None:
        for i in range(10):
            self.logger.log_user(
                "c1", f"m{i}",
            )
        buf = self.logger.get_buffer(limit=3)
        assert len(buf) == 3

    def test_flush_buffer(self) -> None:
        self.logger.log_user("c1", "a")
        self.logger.log_user("c1", "b")
        flushed = self.logger.flush_buffer()
        assert len(flushed) == 2
        assert len(self.logger._buffer) == 0

    def test_clear_buffer(self) -> None:
        self.logger.log_user("c1", "a")
        count = self.logger.clear_buffer()
        assert count == 1
        assert len(self.logger._buffer) == 0

    def test_thread_tracking(self) -> None:
        self.logger.log_message(
            "c1",
            MessageRole.USER,
            "t",
            thread_id="th1",
        )
        self.logger.log_message(
            "c1",
            MessageRole.USER,
            "t2",
            thread_id="th1",
        )
        ids = self.logger.get_thread_messages(
            "th1",
        )
        assert len(ids) == 2

    def test_list_threads(self) -> None:
        self.logger.log_message(
            "c1",
            MessageRole.USER,
            "a",
            thread_id="t1",
        )
        self.logger.log_message(
            "c1",
            MessageRole.USER,
            "b",
            thread_id="t2",
        )
        threads = self.logger.list_threads()
        assert len(threads) == 2
        assert threads["t1"] == 1
        assert threads["t2"] == 1

    def test_callback(self) -> None:
        received = []
        self.logger.on_message(
            lambda m: received.append(m),
        )
        self.logger.log_user("c1", "hi")
        assert len(received) == 1

    def test_callback_none(self) -> None:
        ok = self.logger.on_message(None)
        assert ok is False

    def test_remove_callback(self) -> None:
        cb = lambda m: None  # noqa: E731
        self.logger.on_message(cb)
        ok = self.logger.remove_callback(cb)
        assert ok is True

    def test_remove_callback_not_found(
        self,
    ) -> None:
        ok = self.logger.remove_callback(
            lambda: None,
        )
        assert ok is False

    def test_default_metadata(self) -> None:
        self.logger.set_default_metadata(
            {"env": "test"},
        )
        m = self.logger.log_user("c1", "hi")
        assert m.metadata["env"] == "test"

    def test_default_metadata_merge(
        self,
    ) -> None:
        self.logger.set_default_metadata(
            {"a": 1},
        )
        m = self.logger.log_message(
            "c1",
            MessageRole.USER,
            "hi",
            metadata={"b": 2},
        )
        assert m.metadata["a"] == 1
        assert m.metadata["b"] == 2

    def test_get_default_metadata(
        self,
    ) -> None:
        self.logger.set_default_metadata(
            {"x": 1},
        )
        meta = (
            self.logger.get_default_metadata()
        )
        assert meta == {"x": 1}

    def test_enable_disable(self) -> None:
        assert self.logger.is_enabled() is True
        self.logger.disable()
        assert self.logger.is_enabled() is False
        self.logger.enable()
        assert self.logger.is_enabled() is True

    def test_get_stats(self) -> None:
        self.logger.log_user("c1", "a")
        self.logger.log_assistant("c1", "b")
        stats = self.logger.get_stats()
        assert stats["enabled"] is True
        assert stats["buffer_size"] == 2
        assert stats["total_logged"] == 2
        assert "role_counts" in stats
        assert stats["role_counts"]["user"] == 1


# ---- ContextRetriever Testleri ----


class TestContextRetriever:
    """ContextRetriever testleri."""

    def setup_method(self) -> None:
        self.retriever = ContextRetriever()

    def _make_messages(
        self,
        count: int = 5,
        conv_id: str = "c1",
    ) -> list[Message]:
        now = time.time()
        msgs = []
        for i in range(count):
            msgs.append(
                Message(
                    conversation_id=conv_id,
                    role=MessageRole.USER,
                    content=f"message {i}",
                    timestamp=now - (
                        count - i
                    ) * 100,
                ),
            )
        return msgs

    def test_init(self) -> None:
        assert (
            self.retriever._token_budget
            == 4000
        )
        assert (
            self.retriever._recency_weight
            == 0.7
        )

    def test_init_custom(self) -> None:
        r = ContextRetriever(
            token_budget=2000,
            recency_weight=0.5,
            relevance_weight=0.5,
        )
        assert r._token_budget == 2000
        assert r._recency_weight == 0.5
        assert r._relevance_weight == 0.5

    def test_set_token_budget(self) -> None:
        self.retriever.set_token_budget(8000)
        assert (
            self.retriever.get_token_budget()
            == 8000
        )

    def test_token_budget_max(self) -> None:
        self.retriever.set_token_budget(
            999999,
        )
        assert (
            self.retriever.get_token_budget()
            == 128000
        )

    def test_token_budget_min(self) -> None:
        self.retriever.set_token_budget(-100)
        assert (
            self.retriever.get_token_budget()
            == 0
        )

    def test_estimate_tokens(self) -> None:
        assert (
            ContextRetriever.estimate_tokens("")
            == 0
        )
        assert (
            ContextRetriever.estimate_tokens(
                "abcd",
            )
            == 1
        )
        assert (
            ContextRetriever.estimate_tokens(
                "a" * 100,
            )
            == 25
        )

    def test_set_recency_weight(self) -> None:
        self.retriever.set_recency_weight(0.5)
        assert (
            self.retriever._recency_weight
            == 0.5
        )

    def test_recency_weight_clamp(
        self,
    ) -> None:
        self.retriever.set_recency_weight(2.0)
        assert (
            self.retriever._recency_weight
            == 1.0
        )
        self.retriever.set_recency_weight(-1.0)
        assert (
            self.retriever._recency_weight
            == 0.0
        )

    def test_set_relevance_weight(
        self,
    ) -> None:
        self.retriever.set_relevance_weight(
            0.8,
        )
        assert (
            self.retriever._relevance_weight
            == 0.8
        )

    def test_retrieve_recent(self) -> None:
        msgs = self._make_messages(5)
        result = self.retriever.retrieve_recent(
            msgs,
        )
        assert len(result) > 0
        # Zaman sirasinda
        for i in range(len(result) - 1):
            assert (
                result[i].timestamp
                <= result[i + 1].timestamp
            )

    def test_retrieve_recent_limit(
        self,
    ) -> None:
        msgs = self._make_messages(10)
        result = self.retriever.retrieve_recent(
            msgs, limit=3,
        )
        assert len(result) <= 3

    def test_retrieve_recent_budget(
        self,
    ) -> None:
        r = ContextRetriever(token_budget=10)
        msgs = self._make_messages(10)
        result = r.retrieve_recent(msgs)
        total = sum(
            r.estimate_tokens(m.content)
            for m in result
        )
        assert total <= 10

    def test_retrieve_relevant(self) -> None:
        msgs = self._make_messages(5)
        msgs[2] = Message(
            conversation_id="c1",
            role=MessageRole.USER,
            content="special keyword here",
            timestamp=msgs[2].timestamp,
        )
        result = (
            self.retriever.retrieve_relevant(
                msgs, "keyword",
            )
        )
        assert len(result) > 0

    def test_retrieve_relevant_empty_query(
        self,
    ) -> None:
        msgs = self._make_messages(3)
        result = (
            self.retriever.retrieve_relevant(
                msgs, "",
            )
        )
        # Empty query falls back to recent
        assert len(result) > 0

    def test_retrieve_context(self) -> None:
        now = time.time()
        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.SYSTEM,
                content="You are helpful",
                timestamp=now - 500,
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="hello world",
                timestamp=now - 100,
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.ASSISTANT,
                content="hi there",
                timestamp=now - 50,
            ),
        ]
        result = (
            self.retriever.retrieve_context(
                msgs,
            )
        )
        assert len(result) > 0

    def test_retrieve_context_with_query(
        self,
    ) -> None:
        now = time.time()
        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.SYSTEM,
                content="sys",
                timestamp=now - 500,
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="python coding",
                timestamp=now - 100,
            ),
        ]
        result = (
            self.retriever.retrieve_context(
                msgs, query="python",
            )
        )
        assert len(result) > 0

    def test_retrieve_context_no_system(
        self,
    ) -> None:
        msgs = self._make_messages(3)
        result = (
            self.retriever.retrieve_context(
                msgs, include_system=False,
            )
        )
        assert len(result) > 0

    def test_count_context_tokens(
        self,
    ) -> None:
        msgs = self._make_messages(3)
        total = (
            self.retriever.count_context_tokens(
                msgs,
            )
        )
        assert total > 0

    def test_fits_budget(self) -> None:
        r = ContextRetriever(
            token_budget=10000,
        )
        msgs = self._make_messages(3)
        assert r.fits_budget(msgs) is True

    def test_does_not_fit_budget(self) -> None:
        r = ContextRetriever(token_budget=1)
        msgs = self._make_messages(3)
        assert r.fits_budget(msgs) is False

    def test_excluded_keys(self) -> None:
        self.retriever.add_excluded_key("k1")
        assert "k1" in (
            self.retriever._excluded_keys
        )

    def test_add_excluded_key_empty(
        self,
    ) -> None:
        self.retriever.add_excluded_key("")
        assert len(
            self.retriever._excluded_keys,
        ) == 0

    def test_add_excluded_key_duplicate(
        self,
    ) -> None:
        self.retriever.add_excluded_key("k1")
        self.retriever.add_excluded_key("k1")
        assert (
            self.retriever._excluded_keys.count(
                "k1",
            )
            == 1
        )

    def test_remove_excluded_key(self) -> None:
        self.retriever.add_excluded_key("k1")
        ok = self.retriever.remove_excluded_key(
            "k1",
        )
        assert ok is True
        assert (
            "k1"
            not in self.retriever._excluded_keys
        )

    def test_remove_excluded_not_found(
        self,
    ) -> None:
        ok = self.retriever.remove_excluded_key(
            "bad",
        )
        assert ok is False

    def test_get_stats(self) -> None:
        stats = self.retriever.get_stats()
        assert stats["token_budget"] == 4000
        assert (
            stats["total_retrievals"] == 0
        )

    def test_recency_score(self) -> None:
        now = time.time()
        msg = Message(
            conversation_id="c1",
            role=MessageRole.USER,
            content="t",
            timestamp=now,
        )
        score = self.retriever._recency_score(
            msg, now, 3600.0,
        )
        assert 0.9 <= score <= 1.0

    def test_recency_score_old(self) -> None:
        now = time.time()
        msg = Message(
            conversation_id="c1",
            role=MessageRole.USER,
            content="t",
            timestamp=now - 7200,
        )
        score = self.retriever._recency_score(
            msg, now, 3600.0,
        )
        assert score < 0.5

    def test_relevance_score(self) -> None:
        msg = Message(
            conversation_id="c1",
            role=MessageRole.USER,
            content="python coding tutorial",
            timestamp=time.time(),
        )
        score = (
            self.retriever._relevance_score(
                msg, "python tutorial",
            )
        )
        assert score > 0.5

    def test_relevance_score_no_query(
        self,
    ) -> None:
        msg = Message(
            conversation_id="c1",
            role=MessageRole.USER,
            content="test",
            timestamp=time.time(),
        )
        score = (
            self.retriever._relevance_score(
                msg, "",
            )
        )
        assert score == 0.5


# ---- HistorySearch Testleri ----


class TestHistorySearch:
    """HistorySearch testleri."""

    def setup_method(self) -> None:
        self.search = HistorySearch()
        now = time.time()
        self.messages = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="hello world",
                timestamp=now - 300,
                metadata={
                    "channel": "tg",
                    "user_id": "u1",
                    "tags": ["greet"],
                },
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.ASSISTANT,
                content="hi there",
                timestamp=now - 200,
                metadata={
                    "channel": "tg",
                    "user_id": "bot",
                },
            ),
            Message(
                conversation_id="c2",
                role=MessageRole.USER,
                content="python code help",
                timestamp=now - 100,
                metadata={
                    "channel": "email",
                    "user_id": "u2",
                    "tags": ["code"],
                },
            ),
            Message(
                conversation_id="c2",
                role=MessageRole.SYSTEM,
                content="system prompt",
                timestamp=now - 50,
                metadata={
                    "channel": "email",
                },
            ),
        ]

    def test_init(self) -> None:
        assert self.search._total_searches == 0

    def test_search_text(self) -> None:
        result = self.search.search(
            self.messages, text="hello",
        )
        assert len(result) == 1
        assert "hello" in result[0].content

    def test_search_case_insensitive(
        self,
    ) -> None:
        result = self.search.search(
            self.messages, text="HELLO",
        )
        assert len(result) == 1

    def test_search_by_role(self) -> None:
        result = self.search.search(
            self.messages, role="system",
        )
        assert len(result) == 1

    def test_search_by_conversation(
        self,
    ) -> None:
        result = self.search.search(
            self.messages,
            conversation_id="c1",
        )
        assert len(result) == 2

    def test_search_by_channel(self) -> None:
        result = self.search.search(
            self.messages, channel="tg",
        )
        assert len(result) == 2

    def test_search_by_user(self) -> None:
        result = self.search.search(
            self.messages, user_id="u1",
        )
        assert len(result) == 1

    def test_search_by_tags(self) -> None:
        result = self.search.search(
            self.messages, tags=["code"],
        )
        assert len(result) == 1

    def test_search_date_from(self) -> None:
        now = time.time()
        result = self.search.search(
            self.messages,
            date_from=now - 150,
        )
        assert len(result) == 2

    def test_search_date_to(self) -> None:
        now = time.time()
        result = self.search.search(
            self.messages,
            date_to=now - 250,
        )
        assert len(result) == 1

    def test_search_limit(self) -> None:
        result = self.search.search(
            self.messages, limit=2,
        )
        assert len(result) == 2

    def test_search_combined_filters(
        self,
    ) -> None:
        result = self.search.search(
            self.messages,
            channel="tg",
            role="user",
        )
        assert len(result) == 1

    def test_search_no_results(self) -> None:
        result = self.search.search(
            self.messages,
            text="nonexistent",
        )
        assert len(result) == 0

    def test_search_sorted_reverse(
        self,
    ) -> None:
        result = self.search.search(
            self.messages,
        )
        for i in range(len(result) - 1):
            assert (
                result[i].timestamp
                >= result[i + 1].timestamp
            )

    def test_search_with_query(self) -> None:
        q = SearchQuery(
            text="python",
            channel="email",
        )
        result = self.search.search_with_query(
            self.messages, q,
        )
        assert len(result) == 1

    def test_search_regex(self) -> None:
        result = self.search.search_regex(
            self.messages, r"hel+o",
        )
        assert len(result) == 1

    def test_search_regex_empty(self) -> None:
        result = self.search.search_regex(
            self.messages, "",
        )
        assert len(result) == 0

    def test_search_regex_invalid(
        self,
    ) -> None:
        result = self.search.search_regex(
            self.messages, r"[invalid",
        )
        assert len(result) == 0

    def test_search_regex_limit(self) -> None:
        result = self.search.search_regex(
            self.messages, r".*", limit=2,
        )
        assert len(result) == 2

    def test_search_by_attachment(
        self,
    ) -> None:
        now = time.time()
        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="pic",
                timestamp=now,
                attachments=[
                    {"type": "image"},
                ],
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="text only",
                timestamp=now,
            ),
        ]
        result = (
            self.search.search_by_attachment(
                msgs,
            )
        )
        assert len(result) == 1

    def test_search_by_attachment_type(
        self,
    ) -> None:
        now = time.time()
        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="pic",
                timestamp=now,
                attachments=[
                    {"type": "image"},
                ],
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="doc",
                timestamp=now,
                attachments=[
                    {"type": "document"},
                ],
            ),
        ]
        result = (
            self.search.search_by_attachment(
                msgs,
                attachment_type="image",
            )
        )
        assert len(result) == 1

    def test_save_query(self) -> None:
        q = self.search.save_query(
            "my_search", text="hello",
        )
        assert q is not None
        assert q.text == "hello"

    def test_save_query_empty_name(
        self,
    ) -> None:
        q = self.search.save_query("")
        assert q is None

    def test_get_saved_query(self) -> None:
        self.search.save_query(
            "sq1", text="test",
        )
        q = self.search.get_saved_query("sq1")
        assert q is not None
        assert q.text == "test"

    def test_get_saved_query_not_found(
        self,
    ) -> None:
        q = self.search.get_saved_query("bad")
        assert q is None

    def test_remove_saved_query(self) -> None:
        self.search.save_query(
            "rm", text="x",
        )
        ok = self.search.remove_saved_query(
            "rm",
        )
        assert ok is True

    def test_remove_saved_query_not_found(
        self,
    ) -> None:
        ok = self.search.remove_saved_query(
            "bad",
        )
        assert ok is False

    def test_list_saved_queries(self) -> None:
        self.search.save_query("a", text="1")
        self.search.save_query("b", text="2")
        queries = (
            self.search.list_saved_queries()
        )
        assert len(queries) == 2

    def test_run_saved_query(self) -> None:
        self.search.save_query(
            "find_hello", text="hello",
        )
        result = self.search.run_saved_query(
            "find_hello", self.messages,
        )
        assert len(result) == 1

    def test_run_saved_query_not_found(
        self,
    ) -> None:
        result = self.search.run_saved_query(
            "bad", self.messages,
        )
        assert len(result) == 0

    def test_export_json(self) -> None:
        result = self.search.export_results(
            self.messages[:2],
            format_type="json",
        )
        assert len(result) > 0
        assert "hello" in result

    def test_export_text(self) -> None:
        result = self.search.export_results(
            self.messages[:2],
            format_type="text",
        )
        assert "[user]" in result

    def test_search_history(self) -> None:
        self.search.search(
            self.messages, text="test",
        )
        history = (
            self.search.get_search_history()
        )
        assert len(history) == 1
        assert history[0]["query"] == "test"

    def test_get_stats(self) -> None:
        self.search.search(
            self.messages, text="x",
        )
        stats = self.search.get_stats()
        assert stats["total_searches"] == 1
        assert stats["saved_queries"] == 0


# ---- MemoryPruner Testleri ----


class TestMemoryPruner:
    """MemoryPruner testleri."""

    def setup_method(self) -> None:
        self.pruner = MemoryPruner()

    def _make_messages(
        self,
        count: int = 5,
        age_days: float = 0.0,
    ) -> list[Message]:
        now = time.time()
        base = now - age_days * 86400
        msgs = []
        for i in range(count):
            msgs.append(
                Message(
                    conversation_id="c1",
                    role=MessageRole.USER,
                    content=f"msg {i}",
                    timestamp=base + i * 10,
                ),
            )
        return msgs

    def test_init(self) -> None:
        assert (
            self.pruner._default_retention_days
            == 90
        )
        assert (
            self.pruner._auto_prune is False
        )

    def test_init_custom(self) -> None:
        p = MemoryPruner(
            default_retention_days=30,
            auto_prune=True,
        )
        assert (
            p._default_retention_days == 30
        )
        assert p._auto_prune is True

    def test_add_policy(self) -> None:
        p = self.pruner.add_policy(
            "default", retention_days=30,
        )
        assert p is not None
        assert p.name == "default"
        assert p.retention_days == 30

    def test_add_policy_empty_name(
        self,
    ) -> None:
        p = self.pruner.add_policy("")
        assert p is None

    def test_add_policy_with_action(
        self,
    ) -> None:
        p = self.pruner.add_policy(
            "summarize",
            action=RetentionAction.SUMMARIZE,
        )
        assert (
            p.action
            == RetentionAction.SUMMARIZE
        )

    def test_get_policy(self) -> None:
        p = self.pruner.add_policy("test")
        got = self.pruner.get_policy(
            p.policy_id,
        )
        assert got is not None
        assert got.name == "test"

    def test_get_policy_not_found(
        self,
    ) -> None:
        got = self.pruner.get_policy("bad")
        assert got is None

    def test_find_policy_by_name(self) -> None:
        self.pruner.add_policy("finder")
        got = self.pruner.find_policy_by_name(
            "finder",
        )
        assert got is not None

    def test_find_policy_by_name_not_found(
        self,
    ) -> None:
        got = self.pruner.find_policy_by_name(
            "bad",
        )
        assert got is None

    def test_remove_policy(self) -> None:
        p = self.pruner.add_policy("rm")
        ok = self.pruner.remove_policy(
            p.policy_id,
        )
        assert ok is True

    def test_remove_policy_not_found(
        self,
    ) -> None:
        ok = self.pruner.remove_policy("bad")
        assert ok is False

    def test_update_policy(self) -> None:
        p = self.pruner.add_policy(
            "upd", retention_days=90,
        )
        ok = self.pruner.update_policy(
            p.policy_id, retention_days=30,
        )
        assert ok is True
        assert p.retention_days == 30

    def test_update_policy_action(
        self,
    ) -> None:
        p = self.pruner.add_policy("act")
        self.pruner.update_policy(
            p.policy_id,
            action=RetentionAction.DELETE,
        )
        assert (
            p.action == RetentionAction.DELETE
        )

    def test_update_policy_enabled(
        self,
    ) -> None:
        p = self.pruner.add_policy("en")
        self.pruner.update_policy(
            p.policy_id, enabled=False,
        )
        assert p.enabled is False

    def test_update_policy_not_found(
        self,
    ) -> None:
        ok = self.pruner.update_policy(
            "bad", retention_days=10,
        )
        assert ok is False

    def test_list_policies(self) -> None:
        self.pruner.add_policy("a")
        self.pruner.add_policy("b")
        policies = self.pruner.list_policies()
        assert len(policies) == 2

    def test_identify_expired(self) -> None:
        # 100 gun onceki mesajlar
        msgs = self._make_messages(
            3, age_days=100,
        )
        expired = self.pruner.identify_expired(
            msgs,
        )
        assert len(expired) == 3

    def test_identify_expired_none(
        self,
    ) -> None:
        # Yeni mesajlar
        msgs = self._make_messages(3)
        expired = self.pruner.identify_expired(
            msgs,
        )
        assert len(expired) == 0

    def test_identify_expired_custom_days(
        self,
    ) -> None:
        msgs = self._make_messages(
            3, age_days=10,
        )
        expired = self.pruner.identify_expired(
            msgs, retention_days=5,
        )
        assert len(expired) == 3

    def test_prune_messages(self) -> None:
        msgs = self._make_messages(
            5, age_days=100,
        )
        remaining, count = (
            self.pruner.prune_messages(msgs)
        )
        assert count == 5
        assert len(remaining) == 0

    def test_prune_messages_partial(
        self,
    ) -> None:
        now = time.time()
        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="old",
                timestamp=now - 100 * 86400,
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="new",
                timestamp=now,
            ),
        ]
        remaining, count = (
            self.pruner.prune_messages(msgs)
        )
        assert count == 1
        assert len(remaining) == 1
        assert remaining[0].content == "new"

    def test_prune_by_policy(self) -> None:
        p = self.pruner.add_policy(
            "test", retention_days=5,
        )
        msgs = self._make_messages(
            3, age_days=10,
        )
        remaining, count = (
            self.pruner.prune_by_policy(
                msgs, p.policy_id,
            )
        )
        assert count == 3

    def test_prune_by_policy_disabled(
        self,
    ) -> None:
        p = self.pruner.add_policy("dis")
        self.pruner.update_policy(
            p.policy_id, enabled=False,
        )
        msgs = self._make_messages(
            3, age_days=100,
        )
        remaining, count = (
            self.pruner.prune_by_policy(
                msgs, p.policy_id,
            )
        )
        assert count == 0

    def test_prune_by_policy_not_found(
        self,
    ) -> None:
        msgs = self._make_messages(3)
        remaining, count = (
            self.pruner.prune_by_policy(
                msgs, "bad",
            )
        )
        assert count == 0

    def test_prune_by_policy_archive(
        self,
    ) -> None:
        p = self.pruner.add_policy(
            "arch",
            retention_days=5,
            action=RetentionAction.ARCHIVE,
        )
        msgs = self._make_messages(
            2, age_days=10,
        )
        remaining, count = (
            self.pruner.prune_by_policy(
                msgs, p.policy_id,
            )
        )
        assert count == 2
        assert (
            self.pruner.get_archive_size("c1")
            == 2
        )

    def test_prune_by_policy_summarize(
        self,
    ) -> None:
        p = self.pruner.add_policy(
            "sum",
            retention_days=5,
            action=RetentionAction.SUMMARIZE,
        )
        msgs = self._make_messages(
            3, age_days=10,
        )
        remaining, count = (
            self.pruner.prune_by_policy(
                msgs, p.policy_id,
            )
        )
        assert count == 3
        summary = self.pruner.get_summary("c1")
        assert summary is not None

    def test_prune_by_policy_min_messages(
        self,
    ) -> None:
        p = self.pruner.add_policy(
            "min",
            retention_days=5,
            min_messages=10,
        )
        msgs = self._make_messages(
            3, age_days=10,
        )
        remaining, count = (
            self.pruner.prune_by_policy(
                msgs, p.policy_id,
            )
        )
        assert count == 0

    def test_create_summary(self) -> None:
        msgs = self._make_messages(3)
        s = self.pruner.create_summary(
            "c1",
            msgs,
            summary_text="ozet",
            key_points=["kp1"],
        )
        assert s is not None
        assert s.summary_text == "ozet"
        assert s.key_points == ["kp1"]
        assert s.message_count == 3

    def test_create_summary_auto(self) -> None:
        msgs = self._make_messages(3)
        s = self.pruner.create_summary(
            "c1", msgs,
        )
        assert s is not None
        assert len(s.summary_text) > 0

    def test_create_summary_empty_id(
        self,
    ) -> None:
        s = self.pruner.create_summary(
            "", [], "text",
        )
        assert s is None

    def test_get_summary(self) -> None:
        msgs = self._make_messages(2)
        self.pruner.create_summary(
            "c1", msgs, "ozet",
        )
        s = self.pruner.get_summary("c1")
        assert s is not None

    def test_get_summary_not_found(
        self,
    ) -> None:
        s = self.pruner.get_summary("bad")
        assert s is None

    def test_remove_summary(self) -> None:
        msgs = self._make_messages(2)
        self.pruner.create_summary(
            "c1", msgs, "ozet",
        )
        ok = self.pruner.remove_summary("c1")
        assert ok is True

    def test_remove_summary_not_found(
        self,
    ) -> None:
        ok = self.pruner.remove_summary("bad")
        assert ok is False

    def test_archive_messages(self) -> None:
        msgs = self._make_messages(3)
        count = self.pruner.archive_messages(
            msgs,
        )
        assert count == 3

    def test_get_archived(self) -> None:
        msgs = self._make_messages(3)
        self.pruner.archive_messages(msgs)
        archived = self.pruner.get_archived(
            "c1",
        )
        assert len(archived) == 3

    def test_get_archived_limit(self) -> None:
        msgs = self._make_messages(5)
        self.pruner.archive_messages(msgs)
        archived = self.pruner.get_archived(
            "c1", limit=2,
        )
        assert len(archived) == 2

    def test_clear_archive(self) -> None:
        msgs = self._make_messages(3)
        self.pruner.archive_messages(msgs)
        ok = self.pruner.clear_archive("c1")
        assert ok is True
        assert (
            self.pruner.get_archive_size("c1")
            == 0
        )

    def test_clear_archive_not_found(
        self,
    ) -> None:
        ok = self.pruner.clear_archive("bad")
        assert ok is False

    def test_get_archive_size(self) -> None:
        msgs = self._make_messages(3)
        self.pruner.archive_messages(msgs)
        assert (
            self.pruner.get_archive_size("c1")
            == 3
        )

    def test_get_archive_size_total(
        self,
    ) -> None:
        m1 = self._make_messages(2)
        self.pruner.archive_messages(m1)
        assert (
            self.pruner.get_archive_size() == 2
        )

    def test_prune_history(self) -> None:
        msgs = self._make_messages(
            3, age_days=100,
        )
        self.pruner.prune_messages(msgs)
        history = (
            self.pruner.get_prune_history()
        )
        assert len(history) == 1
        assert history[0]["action"] == "prune"
        assert history[0]["count"] == 3

    def test_get_stats(self) -> None:
        self.pruner.add_policy("p1")
        stats = self.pruner.get_stats()
        assert (
            stats["default_retention_days"]
            == 90
        )
        assert stats["total_policies"] == 1
        assert stats["total_pruned"] == 0


# ---- Entegrasyon Testleri ----


class TestChatHistoryIntegration:
    """Entegrasyon testleri."""

    def test_full_conversation_flow(
        self,
    ) -> None:
        """Tam konusma akisi."""
        store = ConversationStore()
        logger = MessageLogger()

        # Konusma olustur
        conv = store.create_conversation(
            title="Test Chat",
            channel="telegram",
            user_id="fatih",
        )

        # Mesajlar logla ve kaydet
        m1 = logger.log_user(
            conv.conversation_id,
            "Merhaba",
        )
        store.add_message(
            conv.conversation_id,
            MessageRole.USER,
            "Merhaba",
        )

        m2 = logger.log_assistant(
            conv.conversation_id,
            "Merhaba! Size nasil yardimci olabilirim?",
        )
        store.add_message(
            conv.conversation_id,
            MessageRole.ASSISTANT,
            "Merhaba! Size nasil yardimci olabilirim?",
        )

        # Kontrol
        assert (
            store.get_message_count(
                conv.conversation_id,
            )
            == 2
        )
        assert logger._total_logged == 2

    def test_search_and_context(self) -> None:
        """Arama ve baglam getirme."""
        store = ConversationStore()
        search = HistorySearch()
        retriever = ContextRetriever()

        conv = store.create_conversation()
        now = time.time()

        # Mesajlar ekle
        for i in range(10):
            store.add_message(
                conv.conversation_id,
                MessageRole.USER,
                f"message about topic{i}",
            )

        msgs = store.get_messages(
            conv.conversation_id,
        )

        # Arama
        results = search.search(
            msgs, text="topic5",
        )
        assert len(results) == 1

        # Baglam getirme
        context = retriever.retrieve_recent(
            msgs, limit=5,
        )
        assert len(context) <= 5

    def test_prune_and_archive(self) -> None:
        """Budama ve arsivleme."""
        pruner = MemoryPruner()
        now = time.time()

        # Eski mesajlar
        old_msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content=f"old msg {i}",
                timestamp=now - 100 * 86400,
            )
            for i in range(5)
        ]

        # Yeni mesajlar
        new_msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content=f"new msg {i}",
                timestamp=now,
            )
            for i in range(3)
        ]

        all_msgs = old_msgs + new_msgs

        # Arsiv politikasi
        policy = pruner.add_policy(
            "archive_old",
            retention_days=30,
            action=RetentionAction.ARCHIVE,
        )

        remaining, count = (
            pruner.prune_by_policy(
                all_msgs, policy.policy_id,
            )
        )

        assert count == 5
        assert len(remaining) == 3
        assert (
            pruner.get_archive_size("c1") == 5
        )

    def test_export_import_roundtrip(
        self,
    ) -> None:
        """Disa aktarma iceri aktarma."""
        store = ConversationStore()

        conv = store.create_conversation(
            title="Export Test",
            tags=["test"],
        )
        store.add_message(
            conv.conversation_id,
            MessageRole.USER,
            "hello",
        )
        store.add_message(
            conv.conversation_id,
            MessageRole.ASSISTANT,
            "hi",
        )

        # JSON export
        json_str = store.to_json(
            conv.conversation_id,
        )
        assert len(json_str) > 0

        # Sil
        store.delete_conversation(
            conv.conversation_id,
        )
        assert (
            store.get_conversation(
                conv.conversation_id,
            )
            is None
        )

        # JSON import
        imported = store.from_json(json_str)
        assert imported is not None
        assert imported.title == "Export Test"
        msgs = store.get_messages(
            imported.conversation_id,
        )
        assert len(msgs) == 2

    def test_logger_with_search(self) -> None:
        """Logger ile arama."""
        logger = MessageLogger()
        search = HistorySearch()

        logger.log_user("c1", "python help")
        logger.log_assistant(
            "c1", "Sure, what do you need?",
        )
        logger.log_user(
            "c1", "javascript question",
        )

        msgs = logger.get_buffer()
        results = search.search(
            msgs, text="python",
        )
        assert len(results) == 1

    def test_context_with_system_msgs(
        self,
    ) -> None:
        """Sistem mesajli baglam."""
        retriever = ContextRetriever(
            token_budget=10000,
        )
        now = time.time()

        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.SYSTEM,
                content="You are ATLAS",
                timestamp=now - 1000,
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="hello",
                timestamp=now - 100,
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.ASSISTANT,
                content="hi",
                timestamp=now - 50,
            ),
        ]

        context = retriever.retrieve_context(
            msgs,
            include_system=True,
        )

        # Sistem mesaji dahil
        has_system = any(
            m.role == MessageRole.SYSTEM
            for m in context
        )
        assert has_system is True

    def test_saved_query_workflow(
        self,
    ) -> None:
        """Kaydedilen sorgu is akisi."""
        search = HistorySearch()
        now = time.time()

        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="error in production",
                timestamp=now,
                metadata={"channel": "tg"},
            ),
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content="all good",
                timestamp=now,
                metadata={
                    "channel": "email",
                },
            ),
        ]

        # Sorgu kaydet
        search.save_query(
            "prod_errors",
            text="error",
            channel="tg",
        )

        # Kayitli sorguyu calistir
        results = search.run_saved_query(
            "prod_errors", msgs,
        )
        assert len(results) == 1

    def test_summary_from_pruned(
        self,
    ) -> None:
        """Budanan mesajlardan ozet."""
        pruner = MemoryPruner()
        now = time.time()

        msgs = [
            Message(
                conversation_id="c1",
                role=MessageRole.USER,
                content=f"topic discussion {i}",
                timestamp=now - 100 * 86400,
            )
            for i in range(5)
        ]

        # Ozet politikasi
        policy = pruner.add_policy(
            "summarize",
            retention_days=30,
            action=RetentionAction.SUMMARIZE,
        )

        remaining, count = (
            pruner.prune_by_policy(
                msgs, policy.policy_id,
            )
        )

        assert count == 5
        summary = pruner.get_summary("c1")
        assert summary is not None
        assert summary.message_count == 5

    def test_multiple_conversations(
        self,
    ) -> None:
        """Coklu konusma yonetimi."""
        store = ConversationStore()

        c1 = store.create_conversation(
            title="Chat 1",
            channel="telegram",
        )
        c2 = store.create_conversation(
            title="Chat 2",
            channel="email",
        )

        store.add_message(
            c1.conversation_id,
            MessageRole.USER,
            "tg msg",
        )
        store.add_message(
            c2.conversation_id,
            MessageRole.USER,
            "email msg",
        )

        # Kanala gore listele
        tg_convs = store.list_conversations(
            channel="telegram",
        )
        assert len(tg_convs) == 1

        # Arsivle
        store.archive_conversation(
            c1.conversation_id,
        )
        active = store.list_conversations(
            status=ConversationStatus.ACTIVE,
        )
        assert len(active) == 1
