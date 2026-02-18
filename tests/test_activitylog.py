"""
Decision & Activity Log Dashboard testleri.

ActivityTimeline, DecisionExplorer,
LogFilterEngine, SearchableLog,
CausalChainViewer, RollbackTrigger,
ComplianceExporter, AuditTrailVisualizer,
ActivityLogOrchestrator testleri.
"""

import pytest

from app.models.activitylog_models import (
    ActivityEventRecord,
    AuditEntry,
    AuditResult,
    CausalEvent,
    ComplianceFormat,
    ComplianceRecord,
    DecisionOutcome,
    DecisionRecord,
    EventType,
    LogLevel,
    LogRecord,
    RollbackRecord,
    RollbackStatus,
    SearchEntry,
)


# ==================== Model Testleri ====================


class TestActivityLogModels:
    """Model testleri."""

    def test_event_type_enum(self):
        """EventType enum testi."""
        assert EventType.action == "action"
        assert EventType.decision == "decision"
        assert EventType.alert == "alert"
        assert EventType.change == "change"
        assert EventType.system == "system"

    def test_log_level_enum(self):
        """LogLevel enum testi."""
        assert LogLevel.debug == "debug"
        assert LogLevel.info == "info"
        assert LogLevel.warning == "warning"
        assert LogLevel.error == "error"
        assert LogLevel.critical == "critical"

    def test_rollback_status_enum(self):
        """RollbackStatus enum testi."""
        assert (
            RollbackStatus.initiated
            == "initiated"
        )
        assert (
            RollbackStatus.completed
            == "completed"
        )
        assert (
            RollbackStatus.failed == "failed"
        )
        assert (
            RollbackStatus.cancelled
            == "cancelled"
        )

    def test_compliance_format_enum(self):
        """ComplianceFormat enum testi."""
        assert ComplianceFormat.json == "json"
        assert ComplianceFormat.csv == "csv"
        assert ComplianceFormat.pdf == "pdf"
        assert ComplianceFormat.xml == "xml"

    def test_audit_result_enum(self):
        """AuditResult enum testi."""
        assert AuditResult.success == "success"
        assert AuditResult.failure == "failure"
        assert AuditResult.denied == "denied"
        assert AuditResult.error == "error"

    def test_decision_outcome_enum(self):
        """DecisionOutcome enum testi."""
        assert (
            DecisionOutcome.pending
            == "pending"
        )
        assert (
            DecisionOutcome.success
            == "success"
        )
        assert (
            DecisionOutcome.partial
            == "partial"
        )

    def test_activity_event_record(self):
        """ActivityEventRecord testi."""
        rec = ActivityEventRecord(
            event_type="action",
            actor="system",
            description="test event",
        )
        assert rec.event_type == "action"
        assert rec.actor == "system"
        assert rec.description == "test event"
        assert rec.event_id

    def test_decision_record(self):
        """DecisionRecord testi."""
        rec = DecisionRecord(
            title="Test karar",
            actor="admin",
            confidence=0.9,
        )
        assert rec.title == "Test karar"
        assert rec.actor == "admin"
        assert rec.confidence == 0.9
        assert rec.outcome == "pending"

    def test_log_record(self):
        """LogRecord testi."""
        rec = LogRecord(
            source="api",
            action="request",
            level="info",
        )
        assert rec.source == "api"
        assert rec.action == "request"
        assert rec.level == "info"

    def test_search_entry(self):
        """SearchEntry testi."""
        rec = SearchEntry(
            content="test content",
            source="system",
        )
        assert rec.content == "test content"
        assert rec.entry_type == "log"

    def test_causal_event(self):
        """CausalEvent testi."""
        rec = CausalEvent(
            name="root cause",
            event_type="error",
        )
        assert rec.name == "root cause"
        assert rec.cause_id == ""

    def test_rollback_record(self):
        """RollbackRecord testi."""
        rec = RollbackRecord(
            action_id="ac_123",
            reason="hata",
        )
        assert rec.action_id == "ac_123"
        assert rec.status == "initiated"

    def test_compliance_record(self):
        """ComplianceRecord testi."""
        rec = ComplianceRecord(
            record_type="audit",
            actor="admin",
            regulation="GDPR",
        )
        assert rec.regulation == "GDPR"

    def test_audit_entry(self):
        """AuditEntry testi."""
        rec = AuditEntry(
            actor="admin",
            action="read",
            resource="config",
        )
        assert rec.result == "success"


# ==================== ActivityTimeline Testleri ====================


class TestActivityTimeline:
    """ActivityTimeline testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.activity_timeline import (
            ActivityTimeline,
        )

        self.timeline = ActivityTimeline()

    def test_init(self):
        """Baslatma testi."""
        assert self.timeline.event_count == 0

    def test_record_event(self):
        """Olay kaydi testi."""
        result = self.timeline.record_event(
            event_type="action",
            actor="admin",
            description="Test olay",
            category="system",
        )
        assert result["recorded"] is True
        assert "event_id" in result
        assert self.timeline.event_count == 1

    def test_record_multiple_events(self):
        """Coklu olay kaydi testi."""
        for i in range(5):
            self.timeline.record_event(
                actor=f"actor_{i}",
                description=f"Olay {i}",
            )
        assert self.timeline.event_count == 5

    def test_get_timeline(self):
        """Zaman cizelgesi testi."""
        for i in range(25):
            self.timeline.record_event(
                description=f"Olay {i}",
            )
        result = self.timeline.get_timeline(
            page=1, page_size=10
        )
        assert result["retrieved"] is True
        assert len(result["events"]) == 10
        assert result["total_pages"] == 3
        assert result["has_more"] is True

    def test_get_timeline_pagination(self):
        """Sayfalama testi."""
        for i in range(5):
            self.timeline.record_event(
                description=f"Olay {i}",
            )
        result = self.timeline.get_timeline(
            page=1, page_size=20
        )
        assert result["has_more"] is False

    def test_get_by_actor(self):
        """Aktore gore testi."""
        self.timeline.record_event(
            actor="admin", description="a"
        )
        self.timeline.record_event(
            actor="system", description="b"
        )
        self.timeline.record_event(
            actor="admin", description="c"
        )

        result = self.timeline.get_by_actor(
            actor="admin"
        )
        assert result["retrieved"] is True
        assert result["event_count"] == 2

    def test_get_by_category(self):
        """Kategoriye gore testi."""
        self.timeline.record_event(
            category="core", description="a"
        )
        self.timeline.record_event(
            category="api", description="b"
        )

        result = (
            self.timeline.get_by_category(
                category="core"
            )
        )
        assert result["event_count"] == 1

    def test_get_by_type(self):
        """Ture gore testi."""
        self.timeline.record_event(
            event_type="action"
        )
        self.timeline.record_event(
            event_type="decision"
        )
        self.timeline.record_event(
            event_type="action"
        )

        result = self.timeline.get_by_type(
            event_type="action"
        )
        assert result["event_count"] == 2

    def test_archive_old_events(self):
        """Arsivleme testi."""
        self.timeline.record_event(
            description="recent"
        )

        result = (
            self.timeline.archive_old_events(
                max_age_days=90
            )
        )
        assert result["archived"] is True
        assert result["remaining_count"] == 1

    def test_get_summary(self):
        """Ozet testi."""
        self.timeline.record_event(
            actor="admin",
            category="core",
            event_type="action",
        )
        self.timeline.record_event(
            actor="system",
            category="api",
            event_type="decision",
        )

        result = self.timeline.get_summary()
        assert result["retrieved"] is True
        assert result["total_events"] == 2
        assert "categories" in result
        assert "actors" in result


# ==================== DecisionExplorer Testleri ====================


class TestDecisionExplorer:
    """DecisionExplorer testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.decision_explorer import (
            DecisionExplorer,
        )

        self.explorer = DecisionExplorer()

    def test_init(self):
        """Baslatma testi."""
        assert self.explorer.decision_count == 0

    def test_record_decision(self):
        """Karar kaydi testi."""
        result = self.explorer.record_decision(
            title="Test karar",
            actor="admin",
            context="Test baglam",
            reasoning="Test muhakeme",
            alternatives=["A", "B"],
        )
        assert result["recorded"] is True
        assert "decision_id" in result
        assert (
            self.explorer.decision_count == 1
        )

    def test_explore_decision(self):
        """Karar kesfetme testi."""
        rec = self.explorer.record_decision(
            title="Kesfedilecek karar",
            actor="admin",
        )
        did = rec["decision_id"]

        result = (
            self.explorer.explore_decision(
                decision_id=did
            )
        )
        assert result["found"] is True
        assert (
            result["decision"]["title"]
            == "Kesfedilecek karar"
        )

    def test_explore_not_found(self):
        """Bulunamayan karar testi."""
        result = (
            self.explorer.explore_decision(
                decision_id="nonexistent"
            )
        )
        assert result["found"] is False

    def test_track_outcome(self):
        """Sonuc takibi testi."""
        rec = self.explorer.record_decision(
            title="Sonuc takip",
        )
        did = rec["decision_id"]

        result = self.explorer.track_outcome(
            decision_id=did,
            outcome="basarili",
            success=True,
            notes="Iyi sonuc",
        )
        assert result["tracked"] is True

    def test_track_outcome_not_found(self):
        """Bulunamayan karar sonucu testi."""
        result = self.explorer.track_outcome(
            decision_id="nonexistent"
        )
        assert result["tracked"] is False

    def test_compare_decisions(self):
        """Karar karsilastirma testi."""
        r1 = self.explorer.record_decision(
            title="Karar 1"
        )
        r2 = self.explorer.record_decision(
            title="Karar 2"
        )

        result = (
            self.explorer.compare_decisions(
                decision_ids=[
                    r1["decision_id"],
                    r2["decision_id"],
                ]
            )
        )
        assert result["compared"] is True
        assert result["compared_count"] == 2

    def test_get_by_actor(self):
        """Aktore gore testi."""
        self.explorer.record_decision(
            title="K1", actor="admin"
        )
        self.explorer.record_decision(
            title="K2", actor="system"
        )

        result = self.explorer.get_by_actor(
            actor="admin"
        )
        assert result["decision_count"] == 1

    def test_get_by_category(self):
        """Kategoriye gore testi."""
        self.explorer.record_decision(
            title="K1",
            category="strategic",
        )
        self.explorer.record_decision(
            title="K2",
            category="operational",
        )

        result = (
            self.explorer.get_by_category(
                category="strategic"
            )
        )
        assert result["decision_count"] == 1

    def test_get_success_rate(self):
        """Basari orani testi."""
        rec = self.explorer.record_decision(
            title="Test"
        )
        did = rec["decision_id"]
        self.explorer.track_outcome(
            decision_id=did,
            outcome="ok",
            success=True,
        )

        result = (
            self.explorer.get_success_rate()
        )
        assert result["calculated"] is True
        assert result["success_rate"] == 100.0

    def test_get_success_rate_empty(self):
        """Bos basari orani testi."""
        result = (
            self.explorer.get_success_rate()
        )
        assert result["success_rate"] == 0.0


# ==================== LogFilterEngine Testleri ====================


class TestLogFilterEngine:
    """LogFilterEngine testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.log_filter_engine import (
            LogFilterEngine,
        )

        self.engine = LogFilterEngine()

    def test_init(self):
        """Baslatma testi."""
        assert self.engine.filter_count == 0
        assert self.engine.log_count == 0

    def test_add_log(self):
        """Log ekleme testi."""
        result = self.engine.add_log(
            source="api",
            action="request",
            actor="admin",
            level="info",
        )
        assert result["added"] is True
        assert self.engine.log_count == 1

    def test_create_filter(self):
        """Filtre olusturma testi."""
        result = self.engine.create_filter(
            name="Admin filtresi",
            conditions={"actor": "admin"},
        )
        assert result["created"] is True
        assert self.engine.filter_count == 1

    def test_apply_filter(self):
        """Filtre uygulama testi."""
        self.engine.add_log(
            actor="admin", source="api"
        )
        self.engine.add_log(
            actor="system", source="core"
        )

        filt = self.engine.create_filter(
            name="Admin",
            conditions={"actor": "admin"},
        )
        fid = filt["filter_id"]

        result = self.engine.apply_filter(
            filter_id=fid
        )
        assert result["applied"] is True
        assert result["result_count"] == 1

    def test_apply_filter_not_found(self):
        """Bulunamayan filtre testi."""
        result = self.engine.apply_filter(
            filter_id="nonexistent"
        )
        assert result["applied"] is False

    def test_filter_logs(self):
        """Log filtreleme testi."""
        self.engine.add_log(
            actor="admin",
            level="error",
            category="core",
        )
        self.engine.add_log(
            actor="system",
            level="info",
            category="api",
        )

        result = self.engine.filter_logs(
            actor="admin"
        )
        assert result["filtered"] is True
        assert result["result_count"] == 1

    def test_filter_by_level(self):
        """Seviyeye gore filtreleme testi."""
        self.engine.add_log(level="error")
        self.engine.add_log(level="info")
        self.engine.add_log(level="error")

        result = self.engine.filter_logs(
            level="error"
        )
        assert result["result_count"] == 2

    def test_filter_by_date_range(self):
        """Tarih araligi filtreleme testi."""
        self.engine.add_log(source="test")

        result = (
            self.engine.filter_by_date_range(
                start_date="2020-01-01",
                end_date="2030-12-31",
            )
        )
        assert result["filtered"] is True
        assert result["result_count"] == 1

    def test_get_saved_filters(self):
        """Kayitli filtreler testi."""
        self.engine.create_filter(
            name="F1"
        )
        self.engine.create_filter(
            name="F2"
        )

        result = (
            self.engine.get_saved_filters()
        )
        assert result["filter_count"] == 2

    def test_delete_filter(self):
        """Filtre silme testi."""
        filt = self.engine.create_filter(
            name="Silinecek"
        )
        fid = filt["filter_id"]

        result = self.engine.delete_filter(
            filter_id=fid
        )
        assert result["deleted"] is True
        assert self.engine.filter_count == 0


# ==================== SearchableLog Testleri ====================


class TestSearchableLog:
    """SearchableLog testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.searchable_log import (
            SearchableLog,
        )

        self.log = SearchableLog()

    def test_init(self):
        """Baslatma testi."""
        assert self.log.entry_count == 0
        assert self.log.search_count == 0

    def test_index_entry(self):
        """Indeksleme testi."""
        result = self.log.index_entry(
            content="Test icerik",
            source="api",
            entry_type="log",
            tags=["test"],
        )
        assert result["indexed"] is True
        assert self.log.entry_count == 1

    def test_search(self):
        """Arama testi."""
        self.log.index_entry(
            content="API error occurred"
        )
        self.log.index_entry(
            content="Database connected"
        )

        result = self.log.search(
            query="error"
        )
        assert result["searched"] is True
        assert result["result_count"] == 1

    def test_search_no_results(self):
        """Sonucsuz arama testi."""
        self.log.index_entry(
            content="Test icerik"
        )

        result = self.log.search(
            query="nonexistent"
        )
        assert result["result_count"] == 0

    def test_search_with_highlights(self):
        """Vurgulu arama testi."""
        self.log.index_entry(
            content="API error in module"
        )

        result = self.log.search(
            query="error"
        )
        assert result["result_count"] == 1
        assert (
            "highlights" in result["results"][0]
        )

    def test_faceted_search(self):
        """Fasetli arama testi."""
        self.log.index_entry(
            content="API error",
            source="api",
            entry_type="error",
            tags=["critical"],
        )
        self.log.index_entry(
            content="DB connected",
            source="db",
            entry_type="info",
        )

        result = self.log.faceted_search(
            query="error",
            source="api",
        )
        assert result["searched"] is True
        assert result["result_count"] == 1
        assert "facets" in result

    def test_faceted_search_by_tags(self):
        """Etiket fasetli arama testi."""
        self.log.index_entry(
            content="Onemli olay",
            tags=["critical", "api"],
        )
        self.log.index_entry(
            content="Normal olay",
            tags=["info"],
        )

        result = self.log.faceted_search(
            tags=["critical"]
        )
        assert result["result_count"] == 1

    def test_get_suggestions(self):
        """Oneri testi."""
        self.log.search(query="api error")
        self.log.search(query="api timeout")

        result = self.log.get_suggestions(
            partial="api"
        )
        assert result["retrieved"] is True
        assert (
            result["suggestion_count"] >= 1
        )

    def test_get_recent_searches(self):
        """Son aramalar testi."""
        self.log.search(query="test1")
        self.log.search(query="test2")

        result = self.log.get_recent_searches(
            limit=5
        )
        assert result["retrieved"] is True
        assert result["search_count"] == 2


# ==================== CausalChainViewer Testleri ====================


class TestCausalChainViewer:
    """CausalChainViewer testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.causal_chain_viewer import (
            CausalChainViewer,
        )

        self.viewer = CausalChainViewer()

    def test_init(self):
        """Baslatma testi."""
        assert self.viewer.event_count == 0
        assert self.viewer.chain_count == 0

    def test_add_event(self):
        """Olay ekleme testi."""
        result = self.viewer.add_event(
            name="Root event",
            event_type="error",
            actor="system",
        )
        assert result["added"] is True
        assert self.viewer.event_count == 1

    def test_add_event_with_cause(self):
        """Nedenli olay ekleme testi."""
        r1 = self.viewer.add_event(
            name="Cause"
        )
        eid1 = r1["event_id"]

        r2 = self.viewer.add_event(
            name="Effect",
            cause_id=eid1,
        )
        assert r2["added"] is True
        assert r2["cause_id"] == eid1

    def test_build_chain(self):
        """Zincir olusturma testi."""
        r1 = self.viewer.add_event(
            name="Root"
        )
        eid1 = r1["event_id"]

        r2 = self.viewer.add_event(
            name="Child1",
            cause_id=eid1,
        )
        r3 = self.viewer.add_event(
            name="Child2",
            cause_id=eid1,
        )

        result = self.viewer.build_chain(
            root_event_id=eid1
        )
        assert result["built"] is True
        assert result["total_events"] == 3
        assert result["depth"] == 2

    def test_build_chain_not_found(self):
        """Bulunamayan zincir testi."""
        result = self.viewer.build_chain(
            root_event_id="nonexistent"
        )
        assert result["built"] is False

    def test_trace_root_cause(self):
        """Kok neden izleme testi."""
        r1 = self.viewer.add_event(
            name="Root cause"
        )
        eid1 = r1["event_id"]

        r2 = self.viewer.add_event(
            name="Effect1",
            cause_id=eid1,
        )
        eid2 = r2["event_id"]

        r3 = self.viewer.add_event(
            name="Effect2",
            cause_id=eid2,
        )
        eid3 = r3["event_id"]

        result = (
            self.viewer.trace_root_cause(
                event_id=eid3
            )
        )
        assert result["traced"] is True
        assert result["path_length"] == 3
        assert (
            result["root_cause"]["name"]
            == "Root cause"
        )

    def test_get_impact_path(self):
        """Etki yolu testi."""
        r1 = self.viewer.add_event(
            name="Source"
        )
        eid1 = r1["event_id"]

        self.viewer.add_event(
            name="Impact1",
            cause_id=eid1,
        )
        self.viewer.add_event(
            name="Impact2",
            cause_id=eid1,
        )

        result = self.viewer.get_impact_path(
            event_id=eid1
        )
        assert result["retrieved"] is True
        assert result["impact_count"] == 2

    def test_get_timeline_view(self):
        """Zaman cizelgesi gorunumu testi."""
        r1 = self.viewer.add_event(
            name="Root"
        )
        eid1 = r1["event_id"]
        self.viewer.add_event(
            name="Child", cause_id=eid1
        )

        chain = self.viewer.build_chain(
            root_event_id=eid1
        )
        cid = chain["chain_id"]

        result = (
            self.viewer.get_timeline_view(
                chain_id=cid
            )
        )
        assert result["retrieved"] is True
        assert result["event_count"] == 2

    def test_get_timeline_view_not_found(self):
        """Bulunamayan zaman cizelgesi testi."""
        result = (
            self.viewer.get_timeline_view(
                chain_id="nonexistent"
            )
        )
        assert result["retrieved"] is False


# ==================== RollbackTrigger Testleri ====================


class TestRollbackTrigger:
    """RollbackTrigger testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.rollback_trigger import (
            RollbackTrigger,
        )

        self.trigger = RollbackTrigger()

    def test_init(self):
        """Baslatma testi."""
        assert self.trigger.rollback_count == 0

    def test_register_action(self):
        """Aksiyon kaydi testi."""
        result = self.trigger.register_action(
            action_name="config_change",
            actor="admin",
            target="app_config",
            previous_state={"key": "old"},
            current_state={"key": "new"},
        )
        assert result["registered"] is True

    def test_preview_rollback(self):
        """Geri alma onizleme testi."""
        reg = self.trigger.register_action(
            action_name="update",
            target="config",
            previous_state={"v": 1},
            current_state={"v": 2},
        )
        aid = reg["action_id"]

        result = self.trigger.preview_rollback(
            action_id=aid
        )
        assert result["previewed"] is True
        assert "risk_level" in result
        assert result["previous_state"] == {
            "v": 1
        }

    def test_preview_not_found(self):
        """Bulunamayan onizleme testi."""
        result = self.trigger.preview_rollback(
            action_id="nonexistent"
        )
        assert result["previewed"] is False

    def test_initiate_rollback(self):
        """Geri alma baslama testi."""
        reg = self.trigger.register_action(
            action_name="update",
            target="config",
        )
        aid = reg["action_id"]

        result = (
            self.trigger.initiate_rollback(
                action_id=aid,
                reason="hata",
                approved_by="admin",
            )
        )
        assert result["initiated"] is True
        assert (
            self.trigger.rollback_count == 1
        )

    def test_complete_rollback(self):
        """Geri alma tamamlama testi."""
        reg = self.trigger.register_action(
            action_name="update",
        )
        aid = reg["action_id"]
        rb = self.trigger.initiate_rollback(
            action_id=aid
        )
        rid = rb["rollback_id"]

        result = (
            self.trigger.complete_rollback(
                rollback_id=rid,
                success=True,
            )
        )
        assert result["completed"] is True
        assert result["success"] is True

    def test_complete_rollback_failure(self):
        """Basarisiz geri alma testi."""
        reg = self.trigger.register_action(
            action_name="update",
        )
        aid = reg["action_id"]
        rb = self.trigger.initiate_rollback(
            action_id=aid
        )
        rid = rb["rollback_id"]

        result = (
            self.trigger.complete_rollback(
                rollback_id=rid,
                success=False,
            )
        )
        assert result["status"] == "failed"

    def test_cancel_rollback(self):
        """Geri alma iptal testi."""
        reg = self.trigger.register_action(
            action_name="update",
        )
        aid = reg["action_id"]
        rb = self.trigger.initiate_rollback(
            action_id=aid
        )
        rid = rb["rollback_id"]

        result = (
            self.trigger.cancel_rollback(
                rollback_id=rid,
                reason="gereksiz",
            )
        )
        assert result["cancelled"] is True

    def test_cancel_completed_rollback(self):
        """Tamamlanmis geri alma iptal testi."""
        reg = self.trigger.register_action(
            action_name="update",
        )
        aid = reg["action_id"]
        rb = self.trigger.initiate_rollback(
            action_id=aid
        )
        rid = rb["rollback_id"]
        self.trigger.complete_rollback(
            rollback_id=rid
        )

        result = (
            self.trigger.cancel_rollback(
                rollback_id=rid
            )
        )
        assert result["cancelled"] is False

    def test_get_rollback_history(self):
        """Geri alma gecmisi testi."""
        reg = self.trigger.register_action(
            action_name="update",
        )
        self.trigger.initiate_rollback(
            action_id=reg["action_id"]
        )

        result = (
            self.trigger.get_rollback_history()
        )
        assert result["retrieved"] is True
        assert result["rollback_count"] == 1

    def test_preview_risk_level(self):
        """Risk seviyesi testi."""
        reg = self.trigger.register_action(
            action_name="update",
            target="config",
        )
        aid = reg["action_id"]

        result = self.trigger.preview_rollback(
            action_id=aid
        )
        assert result["risk_level"] == "low"


# ==================== ComplianceExporter Testleri ====================


class TestComplianceExporter:
    """ComplianceExporter testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.compliance_exporter import (
            ComplianceExporter,
        )

        self.exporter = ComplianceExporter()

    def test_init(self):
        """Baslatma testi."""
        assert self.exporter.record_count == 0
        assert self.exporter.export_count == 0

    def test_add_record(self):
        """Kayit ekleme testi."""
        result = self.exporter.add_record(
            record_type="audit",
            source="api",
            action="request",
            actor="admin",
            regulation="GDPR",
        )
        assert result["added"] is True
        assert (
            self.exporter.record_count == 1
        )

    def test_export_compliance_report(self):
        """Uyumluluk raporu dis aktarma testi."""
        self.exporter.add_record(
            source="api",
            actor="admin",
            regulation="GDPR",
        )

        result = (
            self.exporter
            .export_compliance_report(
                report_type="audit_trail",
                format_type="json",
            )
        )
        assert result["exported"] is True
        assert result["record_count"] == 1

    def test_export_filtered_by_regulation(
        self,
    ):
        """Duzenlemeye gore dis aktarma testi."""
        self.exporter.add_record(
            regulation="GDPR"
        )
        self.exporter.add_record(
            regulation="KVKK"
        )
        self.exporter.add_record(
            regulation="GDPR"
        )

        result = (
            self.exporter
            .export_compliance_report(
                regulation="GDPR",
            )
        )
        assert result["record_count"] == 2

    def test_generate_audit_trail(self):
        """Denetim izi olusturma testi."""
        self.exporter.add_record(
            actor="admin", source="api"
        )
        self.exporter.add_record(
            actor="system", source="core"
        )

        result = (
            self.exporter
            .generate_audit_trail(
                actor="admin"
            )
        )
        assert result["generated"] is True
        assert result["record_count"] == 1

    def test_generate_audit_trail_date(self):
        """Tarihli denetim izi testi."""
        self.exporter.add_record(
            source="test"
        )

        result = (
            self.exporter
            .generate_audit_trail(
                start_date="2020-01-01",
                end_date="2030-12-31",
            )
        )
        assert result["record_count"] >= 1

    def test_schedule_export(self):
        """Zamanlanmis dis aktarma testi."""
        result = (
            self.exporter.schedule_export(
                name="Gunluk rapor",
                frequency="daily",
            )
        )
        assert result["scheduled"] is True

    def test_check_retention_compliance(self):
        """Saklama uyumlulugu testi."""
        self.exporter.add_record(
            source="test"
        )

        result = (
            self.exporter
            .check_retention_compliance(
                retention_days=365
            )
        )
        assert result["checked"] is True
        assert result["is_compliant"] is True

    def test_get_export_history(self):
        """Dis aktarma gecmisi testi."""
        self.exporter.add_record(
            source="test"
        )
        self.exporter.export_compliance_report()

        result = (
            self.exporter.get_export_history()
        )
        assert result["retrieved"] is True
        assert result["export_count"] == 1


# ==================== AuditTrailVisualizer Testleri ====================


class TestAuditTrailVisualizer:
    """AuditTrailVisualizer testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.audit_trail_visualizer import (
            AuditTrailVisualizer,
        )

        self.visualizer = (
            AuditTrailVisualizer()
        )

    def test_init(self):
        """Baslatma testi."""
        assert (
            self.visualizer.entry_count == 0
        )

    def test_add_entry(self):
        """Kayit ekleme testi."""
        result = self.visualizer.add_entry(
            actor="admin",
            action="read",
            resource="config",
            permission="config.read",
        )
        assert result["added"] is True
        assert (
            self.visualizer.entry_count == 1
        )

    def test_visualize_trail(self):
        """Gorsel denetim izi testi."""
        self.visualizer.add_entry(
            actor="admin",
            action="read",
            resource="config",
        )
        self.visualizer.add_entry(
            actor="admin",
            action="write",
            resource="config",
        )

        result = (
            self.visualizer.visualize_trail(
                actor="admin"
            )
        )
        assert result["visualized"] is True
        assert result["node_count"] == 2

    def test_visualize_by_resource(self):
        """Kaynak bazli gorsel testi."""
        self.visualizer.add_entry(
            actor="admin",
            resource="config",
        )
        self.visualizer.add_entry(
            actor="system",
            resource="database",
        )

        result = (
            self.visualizer.visualize_trail(
                resource="config"
            )
        )
        assert result["node_count"] == 1

    def test_get_actor_actions(self):
        """Aktor aksiyonlari testi."""
        self.visualizer.add_entry(
            actor="admin",
            action="read",
            resource="config",
        )
        self.visualizer.add_entry(
            actor="admin",
            action="write",
            resource="database",
        )

        result = (
            self.visualizer.get_actor_actions(
                actor="admin"
            )
        )
        assert result["retrieved"] is True
        assert result["total_actions"] == 2

    def test_highlight_changes(self):
        """Degisiklik vurgulama testi."""
        rec = self.visualizer.add_entry(
            actor="admin",
            action="update",
            changes={
                "name": {
                    "old": "eski",
                    "new": "yeni",
                }
            },
        )
        aid = rec["audit_id"]

        result = (
            self.visualizer.highlight_changes(
                audit_id=aid
            )
        )
        assert result["highlighted"] is True
        assert result["change_count"] == 1

    def test_highlight_not_found(self):
        """Bulunamayan vurgulama testi."""
        result = (
            self.visualizer.highlight_changes(
                audit_id="nonexistent"
            )
        )
        assert result["highlighted"] is False

    def test_track_permissions(self):
        """Izin takibi testi."""
        self.visualizer.add_entry(
            actor="admin",
            action="read",
            permission="config.read",
            result="success",
        )
        self.visualizer.add_entry(
            actor="admin",
            action="write",
            permission="config.write",
            result="denied",
        )

        result = (
            self.visualizer
            .track_permissions(
                actor="admin"
            )
        )
        assert result["tracked"] is True
        assert result["permission_count"] == 2

    def test_export_visualization(self):
        """Gorsel dis aktarma testi."""
        self.visualizer.add_entry(
            actor="admin", action="read"
        )
        vis = self.visualizer.visualize_trail(
            actor="admin"
        )
        vid = vis["view_id"]

        result = (
            self.visualizer
            .export_visualization(
                view_id=vid,
                format_type="json",
            )
        )
        assert result["exported"] is True

    def test_export_not_found(self):
        """Bulunamayan dis aktarma testi."""
        result = (
            self.visualizer
            .export_visualization(
                view_id="nonexistent"
            )
        )
        assert result["exported"] is False


# ==================== ActivityLogOrchestrator Testleri ====================


class TestActivityLogOrchestrator:
    """ActivityLogOrchestrator testleri."""

    def setup_method(self):
        """Her test oncesi."""
        from app.core.activitylog.activitylog_orchestrator import (
            ActivityLogOrchestrator,
        )

        self.orchestrator = (
            ActivityLogOrchestrator()
        )

    def test_init(self):
        """Baslatma testi."""
        assert self.orchestrator is not None

    def test_log_and_index(self):
        """Log ve indeksleme testi."""
        result = (
            self.orchestrator.log_and_index(
                event_type="action",
                actor="admin",
                description="Test islem",
                category="system",
                source="api",
            )
        )
        assert result["completed"] is True
        assert result["indexed"] is True
        assert result["audit_logged"] is True

    def test_record_and_explore_decision(
        self,
    ):
        """Karar kaydi ve kesfetme testi."""
        result = (
            self.orchestrator
            .record_and_explore_decision(
                title="Strateji karari",
                actor="admin",
                context="Test baglami",
                reasoning="Test muhakemesi",
                alternatives=["A", "B"],
            )
        )
        assert result["completed"] is True
        assert "decision_id" in result

    def test_search_and_filter(self):
        """Arama ve filtreleme testi."""
        self.orchestrator.log_and_index(
            actor="admin",
            description="API error olustu",
            category="api",
        )

        result = (
            self.orchestrator
            .search_and_filter(
                query="error",
            )
        )
        assert result["completed"] is True
        assert result["search_results"] >= 1

    def test_search_and_filter_with_actor(
        self,
    ):
        """Aktor filtreli arama testi."""
        self.orchestrator.log_and_index(
            actor="admin",
            description="Test",
        )

        result = (
            self.orchestrator
            .search_and_filter(
                actor="admin",
            )
        )
        assert result["completed"] is True

    def test_export_compliance(self):
        """Uyumluluk dis aktarma testi."""
        self.orchestrator.log_and_index(
            actor="admin",
            description="Test",
        )

        self.orchestrator.record_and_explore_decision(
            title="Test karar",
            actor="admin",
        )

        result = (
            self.orchestrator
            .export_compliance(
                report_type="audit_trail",
                format_type="json",
            )
        )
        assert result["completed"] is True

    def test_get_analytics(self):
        """Analitik testi."""
        self.orchestrator.log_and_index(
            actor="admin",
            description="Test",
        )

        result = (
            self.orchestrator.get_analytics()
        )
        assert result["retrieved"] is True
        assert result["events"] >= 1
        assert result["components"] == 8

    def test_full_pipeline(self):
        """Tam pipeline testi."""
        self.orchestrator.log_and_index(
            event_type="action",
            actor="admin",
            description="Config degistirildi",
            category="system",
        )

        self.orchestrator.record_and_explore_decision(
            title="Config guncelleme",
            actor="admin",
            reasoning="Performans icin",
        )

        search = (
            self.orchestrator
            .search_and_filter(
                query="Config",
            )
        )
        assert search["completed"] is True

        export = (
            self.orchestrator
            .export_compliance()
        )
        assert export["completed"] is True

        analytics = (
            self.orchestrator.get_analytics()
        )
        assert analytics["retrieved"] is True
        assert analytics["events"] >= 2
