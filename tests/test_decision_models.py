"""Karar modelleri unit testleri.

DecisionCreate, DecisionResponse, ApprovalStatus, EscalationLevel,
DecisionAuditEntry, ApprovalRequest, EscalationRecord ve RuleChangeRecord
modellerinin varsayilan degerler, ozel degerler, dogrulama kurallari,
serializasyon ve sinir kosullarini test eder.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.decision import (
    ApprovalRequest,
    ApprovalStatus,
    DecisionAuditEntry,
    DecisionCreate,
    DecisionResponse,
    EscalationLevel,
    EscalationRecord,
    RuleChangeRecord,
)


# === Yardimci Fonksiyonlar ===


def _make_decision_create(**overrides: object) -> DecisionCreate:
    """Varsayilan DecisionCreate olusturur.

    Args:
        **overrides: Degistirilecek alan degerleri.

    Returns:
        DecisionCreate ornegi.
    """
    defaults: dict = {
        "risk": "high",
        "urgency": "high",
        "action": "auto_fix",
        "confidence": 0.85,
        "reason": "Test karari",
    }
    defaults.update(overrides)
    return DecisionCreate(**defaults)


def _make_decision_response(**overrides: object) -> DecisionResponse:
    """Varsayilan DecisionResponse olusturur.

    Args:
        **overrides: Degistirilecek alan degerleri.

    Returns:
        DecisionResponse ornegi.
    """
    defaults: dict = {
        "id": "resp-001",
        "task_id": "task-001",
        "risk": "low",
        "urgency": "low",
        "action": "log_and_watch",
        "confidence": 0.7,
        "reason": "Dusuk riskli gorev",
        "created_at": datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return DecisionResponse(**defaults)


def _make_audit_entry(**overrides: object) -> DecisionAuditEntry:
    """Varsayilan DecisionAuditEntry olusturur.

    Args:
        **overrides: Degistirilecek alan degerleri.

    Returns:
        DecisionAuditEntry ornegi.
    """
    defaults: dict = {
        "task_description": "Sunucu izleme gorevi",
        "risk": "high",
        "urgency": "medium",
        "action": "notify",
        "confidence": 0.9,
        "reason": "CPU kullanimi yuksek",
        "agent_selected": "security_agent",
    }
    defaults.update(overrides)
    return DecisionAuditEntry(**defaults)


def _make_approval_request(**overrides: object) -> ApprovalRequest:
    """Varsayilan ApprovalRequest olusturur.

    Args:
        **overrides: Degistirilecek alan degerleri.

    Returns:
        ApprovalRequest ornegi.
    """
    defaults: dict = {
        "task": {"type": "server_restart", "target": "web-01"},
        "action": "restart_server",
    }
    defaults.update(overrides)
    return ApprovalRequest(**defaults)


def _make_escalation_record(**overrides: object) -> EscalationRecord:
    """Varsayilan EscalationRecord olusturur.

    Args:
        **overrides: Degistirilecek alan degerleri.

    Returns:
        EscalationRecord ornegi.
    """
    defaults: dict = {
        "original_action": "auto_fix",
        "escalated_action": "notify_human",
        "original_agent": "coding_agent",
        "escalated_agent": "security_agent",
        "level": EscalationLevel.ALTERNATE_AGENT,
        "reason": "Ilk agent basarisiz oldu",
    }
    defaults.update(overrides)
    return EscalationRecord(**defaults)


def _make_rule_change(**overrides: object) -> RuleChangeRecord:
    """Varsayilan RuleChangeRecord olusturur.

    Args:
        **overrides: Degistirilecek alan degerleri.

    Returns:
        RuleChangeRecord ornegi.
    """
    defaults: dict = {
        "risk": "high",
        "urgency": "low",
        "old_action": "auto_fix",
        "new_action": "notify",
        "old_confidence": 0.7,
        "new_confidence": 0.85,
    }
    defaults.update(overrides)
    return RuleChangeRecord(**defaults)


# === Enum Testleri ===


class TestApprovalStatus:
    """ApprovalStatus enum testleri."""

    def test_values(self) -> None:
        """Tum ApprovalStatus degerlerini dogrular."""
        assert ApprovalStatus.PENDING == "pending"
        assert ApprovalStatus.APPROVED == "approved"
        assert ApprovalStatus.REJECTED == "rejected"
        assert ApprovalStatus.TIMEOUT == "timeout"

    def test_count(self) -> None:
        """ApprovalStatus uye sayisini dogrular."""
        assert len(ApprovalStatus) == 4

    def test_string_membership(self) -> None:
        """String degerlerle enum uyeligi dogrulanir."""
        assert ApprovalStatus("pending") is ApprovalStatus.PENDING
        assert ApprovalStatus("approved") is ApprovalStatus.APPROVED
        assert ApprovalStatus("rejected") is ApprovalStatus.REJECTED
        assert ApprovalStatus("timeout") is ApprovalStatus.TIMEOUT

    def test_is_str_subclass(self) -> None:
        """ApprovalStatus str alt sinifi olmalidir."""
        assert isinstance(ApprovalStatus.PENDING, str)
        assert isinstance(ApprovalStatus.APPROVED, str)


class TestEscalationLevel:
    """EscalationLevel enum testleri."""

    def test_values(self) -> None:
        """Tum EscalationLevel degerlerini dogrular."""
        assert EscalationLevel.NONE == "none"
        assert EscalationLevel.RETRY_SAME == "retry_same"
        assert EscalationLevel.ALTERNATE_AGENT == "alternate_agent"
        assert EscalationLevel.NOTIFY_HUMAN == "notify_human"

    def test_count(self) -> None:
        """EscalationLevel uye sayisini dogrular."""
        assert len(EscalationLevel) == 4

    def test_string_membership(self) -> None:
        """String degerlerle enum uyeligi dogrulanir."""
        assert EscalationLevel("none") is EscalationLevel.NONE
        assert EscalationLevel("retry_same") is EscalationLevel.RETRY_SAME
        assert EscalationLevel("alternate_agent") is EscalationLevel.ALTERNATE_AGENT
        assert EscalationLevel("notify_human") is EscalationLevel.NOTIFY_HUMAN

    def test_is_str_subclass(self) -> None:
        """EscalationLevel str alt sinifi olmalidir."""
        assert isinstance(EscalationLevel.NONE, str)
        assert isinstance(EscalationLevel.NOTIFY_HUMAN, str)


# === DecisionCreate Testleri ===


class TestDecisionCreate:
    """DecisionCreate modeli testleri."""

    def test_required_fields(self) -> None:
        """Zorunlu alanlarin dogru atandigini dogrular."""
        dc = _make_decision_create()
        assert dc.risk == "high"
        assert dc.urgency == "high"
        assert dc.action == "auto_fix"
        assert dc.confidence == pytest.approx(0.85)
        assert dc.reason == "Test karari"

    def test_defaults(self) -> None:
        """Varsayilan task_id ve reason degerlerini dogrular."""
        dc = DecisionCreate(risk="low", urgency="low", action="log", confidence=0.5)
        assert dc.task_id is None
        assert dc.reason == ""

    def test_custom_task_id(self) -> None:
        """Ozel task_id atamasini dogrular."""
        dc = _make_decision_create(task_id="task-abc-123")
        assert dc.task_id == "task-abc-123"

    def test_confidence_lower_bound(self) -> None:
        """Guven skorunun 0.0 alt sinirini dogrular."""
        dc = _make_decision_create(confidence=0.0)
        assert dc.confidence == pytest.approx(0.0)

    def test_confidence_upper_bound(self) -> None:
        """Guven skorunun 1.0 ust sinirini dogrular."""
        dc = _make_decision_create(confidence=1.0)
        assert dc.confidence == pytest.approx(1.0)

    def test_confidence_below_zero_rejected(self) -> None:
        """Negatif guven skoru reddedilmelidir."""
        with pytest.raises(ValidationError):
            _make_decision_create(confidence=-0.01)

    def test_confidence_above_one_rejected(self) -> None:
        """1'den buyuk guven skoru reddedilmelidir."""
        with pytest.raises(ValidationError):
            _make_decision_create(confidence=1.01)

    def test_serialization(self) -> None:
        """model_dump serializasyonunu dogrular."""
        dc = _make_decision_create(task_id="t-1")
        data = dc.model_dump()
        assert data["risk"] == "high"
        assert data["urgency"] == "high"
        assert data["action"] == "auto_fix"
        assert data["task_id"] == "t-1"
        assert data["confidence"] == pytest.approx(0.85)

    def test_json_roundtrip(self) -> None:
        """JSON serializasyon ve deserializasyonunu dogrular."""
        dc = _make_decision_create(task_id="t-round")
        json_str = dc.model_dump_json()
        restored = DecisionCreate.model_validate_json(json_str)
        assert restored.risk == dc.risk
        assert restored.urgency == dc.urgency
        assert restored.action == dc.action
        assert restored.confidence == pytest.approx(dc.confidence)
        assert restored.task_id == dc.task_id


# === DecisionResponse Testleri ===


class TestDecisionResponse:
    """DecisionResponse modeli testleri."""

    def test_all_fields(self) -> None:
        """Tum alanlarin dogru atandigini dogrular."""
        dr = _make_decision_response()
        assert dr.id == "resp-001"
        assert dr.task_id == "task-001"
        assert dr.risk == "low"
        assert dr.urgency == "low"
        assert dr.action == "log_and_watch"
        assert dr.confidence == pytest.approx(0.7)
        assert dr.reason == "Dusuk riskli gorev"
        assert isinstance(dr.created_at, datetime)

    def test_task_id_none(self) -> None:
        """task_id None olarak atanabilmelidir."""
        dr = _make_decision_response(task_id=None)
        assert dr.task_id is None

    def test_from_attributes_config(self) -> None:
        """from_attributes yapilandirmasinin aktif oldugunu dogrular."""
        assert DecisionResponse.model_config.get("from_attributes") is True

    def test_serialization(self) -> None:
        """model_dump serializasyonunu dogrular."""
        dr = _make_decision_response()
        data = dr.model_dump()
        assert data["id"] == "resp-001"
        assert data["risk"] == "low"
        assert "created_at" in data

    def test_json_roundtrip(self) -> None:
        """JSON serializasyon ve deserializasyonunu dogrular."""
        dr = _make_decision_response()
        json_str = dr.model_dump_json()
        restored = DecisionResponse.model_validate_json(json_str)
        assert restored.id == dr.id
        assert restored.risk == dr.risk
        assert restored.confidence == pytest.approx(dr.confidence)


# === DecisionAuditEntry Testleri ===


class TestDecisionAuditEntry:
    """DecisionAuditEntry modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        entry = DecisionAuditEntry()
        assert entry.task_description == ""
        assert entry.risk == ""
        assert entry.urgency == ""
        assert entry.action == ""
        assert entry.confidence == pytest.approx(0.0)
        assert entry.reason == ""
        assert entry.agent_selected is None
        assert entry.agent_selection_method == "explicit"
        assert entry.outcome_success is None
        assert entry.escalated_from is None

    def test_uuid_auto_generation(self) -> None:
        """UUID otomatik uretildigini dogrular."""
        entry = DecisionAuditEntry()
        assert entry.id
        assert len(entry.id) == 36  # UUID4 format

    def test_uuid_uniqueness(self) -> None:
        """Farkli orneklerin farkli UUID aldigini dogrular."""
        entry1 = DecisionAuditEntry()
        entry2 = DecisionAuditEntry()
        assert entry1.id != entry2.id

    def test_timestamp_auto_generation(self) -> None:
        """Timestamp otomatik olarak UTC olarak uretilmelidir."""
        before = datetime.now(timezone.utc)
        entry = DecisionAuditEntry()
        after = datetime.now(timezone.utc)
        assert isinstance(entry.timestamp, datetime)
        assert before <= entry.timestamp <= after

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        entry = _make_audit_entry()
        assert entry.task_description == "Sunucu izleme gorevi"
        assert entry.risk == "high"
        assert entry.urgency == "medium"
        assert entry.action == "notify"
        assert entry.confidence == pytest.approx(0.9)
        assert entry.reason == "CPU kullanimi yuksek"
        assert entry.agent_selected == "security_agent"

    def test_custom_timestamp(self) -> None:
        """Ozel timestamp atamasini dogrular."""
        custom_ts = datetime(2026, 6, 1, 10, 30, 0, tzinfo=timezone.utc)
        entry = _make_audit_entry(timestamp=custom_ts)
        assert entry.timestamp == custom_ts

    def test_confidence_lower_bound(self) -> None:
        """Guven skorunun 0.0 alt sinirini dogrular."""
        entry = DecisionAuditEntry(confidence=0.0)
        assert entry.confidence == pytest.approx(0.0)
        with pytest.raises(ValidationError):
            DecisionAuditEntry(confidence=-0.01)

    def test_confidence_upper_bound(self) -> None:
        """Guven skorunun 1.0 ust sinirini dogrular."""
        entry = DecisionAuditEntry(confidence=1.0)
        assert entry.confidence == pytest.approx(1.0)
        with pytest.raises(ValidationError):
            DecisionAuditEntry(confidence=1.01)

    def test_agent_selection_methods(self) -> None:
        """Farkli agent secim yontemlerini dogrular."""
        for method in ("explicit", "keyword", "fallback", "none"):
            entry = DecisionAuditEntry(agent_selection_method=method)
            assert entry.agent_selection_method == method

    def test_outcome_success_true(self) -> None:
        """Basarili sonuc durumunu dogrular."""
        entry = _make_audit_entry(outcome_success=True)
        assert entry.outcome_success is True

    def test_outcome_success_false(self) -> None:
        """Basarisiz sonuc durumunu dogrular."""
        entry = _make_audit_entry(outcome_success=False)
        assert entry.outcome_success is False

    def test_escalated_from(self) -> None:
        """Eskalasyon kaynak aksiyonunun kaydedildigini dogrular."""
        entry = _make_audit_entry(escalated_from="auto_fix")
        assert entry.escalated_from == "auto_fix"

    def test_serialization(self) -> None:
        """model_dump serializasyonunu dogrular."""
        entry = _make_audit_entry()
        data = entry.model_dump()
        assert data["task_description"] == "Sunucu izleme gorevi"
        assert data["risk"] == "high"
        assert data["agent_selected"] == "security_agent"
        assert "id" in data
        assert "timestamp" in data

    def test_json_roundtrip(self) -> None:
        """JSON serializasyon ve deserializasyonunu dogrular."""
        entry = _make_audit_entry(outcome_success=True, escalated_from="retry")
        json_str = entry.model_dump_json()
        restored = DecisionAuditEntry.model_validate_json(json_str)
        assert restored.task_description == entry.task_description
        assert restored.confidence == pytest.approx(entry.confidence)
        assert restored.outcome_success is True
        assert restored.escalated_from == "retry"
        assert restored.id == entry.id


# === ApprovalRequest Testleri ===


class TestApprovalRequest:
    """ApprovalRequest modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        req = ApprovalRequest()
        assert req.task == {}
        assert req.action == ""
        assert req.decision is None
        assert req.status == ApprovalStatus.PENDING
        assert req.responded_at is None
        assert req.timeout_seconds == 300
        assert req.auto_execute_on_timeout is False

    def test_uuid_auto_generation(self) -> None:
        """UUID otomatik uretildigini dogrular."""
        req = ApprovalRequest()
        assert req.id
        assert len(req.id) == 36

    def test_uuid_uniqueness(self) -> None:
        """Farkli orneklerin farkli UUID aldigini dogrular."""
        req1 = ApprovalRequest()
        req2 = ApprovalRequest()
        assert req1.id != req2.id

    def test_timestamp_auto_generation(self) -> None:
        """requested_at otomatik olarak UTC olarak uretilmelidir."""
        before = datetime.now(timezone.utc)
        req = ApprovalRequest()
        after = datetime.now(timezone.utc)
        assert isinstance(req.requested_at, datetime)
        assert before <= req.requested_at <= after

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        req = _make_approval_request()
        assert req.task == {"type": "server_restart", "target": "web-01"}
        assert req.action == "restart_server"

    def test_with_decision(self) -> None:
        """DecisionCreate iliskisinin dogru kuruldigini dogrular."""
        dc = _make_decision_create()
        req = _make_approval_request(decision=dc)
        assert req.decision is not None
        assert req.decision.risk == "high"
        assert req.decision.confidence == pytest.approx(0.85)

    def test_status_approved(self) -> None:
        """Onaylandi durumuna gecisi dogrular."""
        responded = datetime(2026, 3, 1, 14, 0, 0, tzinfo=timezone.utc)
        req = _make_approval_request(
            status=ApprovalStatus.APPROVED,
            responded_at=responded,
        )
        assert req.status == ApprovalStatus.APPROVED
        assert req.responded_at == responded

    def test_status_rejected(self) -> None:
        """Reddedildi durumuna gecisi dogrular."""
        req = _make_approval_request(status=ApprovalStatus.REJECTED)
        assert req.status == ApprovalStatus.REJECTED

    def test_status_timeout(self) -> None:
        """Zaman asimi durumuna gecisi dogrular."""
        req = _make_approval_request(status=ApprovalStatus.TIMEOUT)
        assert req.status == ApprovalStatus.TIMEOUT

    def test_timeout_seconds_custom(self) -> None:
        """Ozel zaman asimi suresi atamasini dogrular."""
        req = _make_approval_request(timeout_seconds=600)
        assert req.timeout_seconds == 600

    def test_timeout_seconds_zero(self) -> None:
        """Sifir zaman asimi suresinin kabul edildigini dogrular."""
        req = _make_approval_request(timeout_seconds=0)
        assert req.timeout_seconds == 0

    def test_timeout_seconds_negative_rejected(self) -> None:
        """Negatif zaman asimi suresinin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            _make_approval_request(timeout_seconds=-1)

    def test_auto_execute_on_timeout_true(self) -> None:
        """Zaman asiminda otomatik calistirma bayragi dogrulanir."""
        req = _make_approval_request(auto_execute_on_timeout=True)
        assert req.auto_execute_on_timeout is True

    def test_serialization(self) -> None:
        """model_dump serializasyonunu dogrular."""
        dc = _make_decision_create()
        req = _make_approval_request(decision=dc)
        data = req.model_dump()
        assert data["action"] == "restart_server"
        assert data["status"] == "pending"
        assert data["timeout_seconds"] == 300
        assert data["decision"]["risk"] == "high"
        assert "id" in data
        assert "requested_at" in data

    def test_json_roundtrip(self) -> None:
        """JSON serializasyon ve deserializasyonunu dogrular."""
        dc = _make_decision_create(task_id="t-approval")
        req = _make_approval_request(
            decision=dc,
            status=ApprovalStatus.APPROVED,
            auto_execute_on_timeout=True,
            timeout_seconds=120,
        )
        json_str = req.model_dump_json()
        restored = ApprovalRequest.model_validate_json(json_str)
        assert restored.action == req.action
        assert restored.status == ApprovalStatus.APPROVED
        assert restored.decision is not None
        assert restored.decision.task_id == "t-approval"
        assert restored.auto_execute_on_timeout is True
        assert restored.timeout_seconds == 120
        assert restored.id == req.id

    def test_empty_task_dict(self) -> None:
        """Bos gorev sozlugunun varsayilan oldugunu dogrular."""
        req = ApprovalRequest()
        assert req.task == {}

    def test_complex_task_dict(self) -> None:
        """Karmasik gorev sozlugunun kabul edildigini dogrular."""
        complex_task: dict = {
            "type": "deployment",
            "services": ["api", "worker"],
            "config": {"replicas": 3, "memory": "512Mi"},
        }
        req = _make_approval_request(task=complex_task)
        assert req.task["services"] == ["api", "worker"]
        assert req.task["config"]["replicas"] == 3


# === EscalationRecord Testleri ===


class TestEscalationRecord:
    """EscalationRecord modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        rec = EscalationRecord()
        assert rec.original_action == ""
        assert rec.escalated_action == ""
        assert rec.original_agent is None
        assert rec.escalated_agent is None
        assert rec.level == EscalationLevel.NONE
        assert rec.reason == ""

    def test_uuid_auto_generation(self) -> None:
        """UUID otomatik uretildigini dogrular."""
        rec = EscalationRecord()
        assert rec.id
        assert len(rec.id) == 36

    def test_uuid_uniqueness(self) -> None:
        """Farkli orneklerin farkli UUID aldigini dogrular."""
        rec1 = EscalationRecord()
        rec2 = EscalationRecord()
        assert rec1.id != rec2.id

    def test_timestamp_auto_generation(self) -> None:
        """Timestamp otomatik olarak UTC olarak uretilmelidir."""
        before = datetime.now(timezone.utc)
        rec = EscalationRecord()
        after = datetime.now(timezone.utc)
        assert isinstance(rec.timestamp, datetime)
        assert before <= rec.timestamp <= after

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        rec = _make_escalation_record()
        assert rec.original_action == "auto_fix"
        assert rec.escalated_action == "notify_human"
        assert rec.original_agent == "coding_agent"
        assert rec.escalated_agent == "security_agent"
        assert rec.level == EscalationLevel.ALTERNATE_AGENT
        assert rec.reason == "Ilk agent basarisiz oldu"

    def test_level_none(self) -> None:
        """NONE eskalasyon seviyesini dogrular."""
        rec = _make_escalation_record(level=EscalationLevel.NONE)
        assert rec.level == EscalationLevel.NONE

    def test_level_retry_same(self) -> None:
        """RETRY_SAME eskalasyon seviyesini dogrular."""
        rec = _make_escalation_record(level=EscalationLevel.RETRY_SAME)
        assert rec.level == EscalationLevel.RETRY_SAME

    def test_level_alternate_agent(self) -> None:
        """ALTERNATE_AGENT eskalasyon seviyesini dogrular."""
        rec = _make_escalation_record(level=EscalationLevel.ALTERNATE_AGENT)
        assert rec.level == EscalationLevel.ALTERNATE_AGENT

    def test_level_notify_human(self) -> None:
        """NOTIFY_HUMAN eskalasyon seviyesini dogrular."""
        rec = _make_escalation_record(level=EscalationLevel.NOTIFY_HUMAN)
        assert rec.level == EscalationLevel.NOTIFY_HUMAN

    def test_agents_none(self) -> None:
        """Agent alanlari None olabilmelidir."""
        rec = EscalationRecord(
            original_action="scan",
            escalated_action="deep_scan",
            original_agent=None,
            escalated_agent=None,
        )
        assert rec.original_agent is None
        assert rec.escalated_agent is None

    def test_custom_timestamp(self) -> None:
        """Ozel timestamp atamasini dogrular."""
        custom_ts = datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc)
        rec = _make_escalation_record(timestamp=custom_ts)
        assert rec.timestamp == custom_ts

    def test_serialization(self) -> None:
        """model_dump serializasyonunu dogrular."""
        rec = _make_escalation_record()
        data = rec.model_dump()
        assert data["original_action"] == "auto_fix"
        assert data["escalated_action"] == "notify_human"
        assert data["level"] == "alternate_agent"
        assert "id" in data
        assert "timestamp" in data

    def test_json_roundtrip(self) -> None:
        """JSON serializasyon ve deserializasyonunu dogrular."""
        rec = _make_escalation_record()
        json_str = rec.model_dump_json()
        restored = EscalationRecord.model_validate_json(json_str)
        assert restored.original_action == rec.original_action
        assert restored.escalated_action == rec.escalated_action
        assert restored.level == EscalationLevel.ALTERNATE_AGENT
        assert restored.original_agent == rec.original_agent
        assert restored.escalated_agent == rec.escalated_agent
        assert restored.id == rec.id


# === RuleChangeRecord Testleri ===


class TestRuleChangeRecord:
    """RuleChangeRecord modeli testleri."""

    def test_required_fields(self) -> None:
        """Zorunlu alanlarin dogru atandigini dogrular."""
        rc = _make_rule_change()
        assert rc.risk == "high"
        assert rc.urgency == "low"
        assert rc.old_action == "auto_fix"
        assert rc.new_action == "notify"
        assert rc.old_confidence == pytest.approx(0.7)
        assert rc.new_confidence == pytest.approx(0.85)

    def test_defaults(self) -> None:
        """Varsayilan changed_by degerini dogrular."""
        rc = _make_rule_change()
        assert rc.changed_by == "system"

    def test_changed_by_user(self) -> None:
        """Kullanici tarafindan degisikligi dogrular."""
        rc = _make_rule_change(changed_by="user")
        assert rc.changed_by == "user"

    def test_changed_by_learning(self) -> None:
        """Ogrenme sistemi tarafindan degisikligi dogrular."""
        rc = _make_rule_change(changed_by="learning")
        assert rc.changed_by == "learning"

    def test_timestamp_auto_generation(self) -> None:
        """Timestamp otomatik olarak UTC olarak uretilmelidir."""
        before = datetime.now(timezone.utc)
        rc = _make_rule_change()
        after = datetime.now(timezone.utc)
        assert isinstance(rc.timestamp, datetime)
        assert before <= rc.timestamp <= after

    def test_custom_timestamp(self) -> None:
        """Ozel timestamp atamasini dogrular."""
        custom_ts = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        rc = _make_rule_change(timestamp=custom_ts)
        assert rc.timestamp == custom_ts

    def test_missing_required_field_risk(self) -> None:
        """risk alani olmadan olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            RuleChangeRecord(
                urgency="high",
                old_action="a",
                new_action="b",
                old_confidence=0.5,
                new_confidence=0.6,
            )

    def test_missing_required_field_urgency(self) -> None:
        """urgency alani olmadan olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            RuleChangeRecord(
                risk="high",
                old_action="a",
                new_action="b",
                old_confidence=0.5,
                new_confidence=0.6,
            )

    def test_missing_required_field_old_action(self) -> None:
        """old_action alani olmadan olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            RuleChangeRecord(
                risk="high",
                urgency="low",
                new_action="b",
                old_confidence=0.5,
                new_confidence=0.6,
            )

    def test_missing_required_field_new_confidence(self) -> None:
        """new_confidence alani olmadan olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            RuleChangeRecord(
                risk="high",
                urgency="low",
                old_action="a",
                new_action="b",
                old_confidence=0.5,
            )

    def test_same_action_change(self) -> None:
        """Ayni aksiyonla kural degisikliginin kabul edildigini dogrular."""
        rc = _make_rule_change(old_action="notify", new_action="notify")
        assert rc.old_action == rc.new_action

    def test_confidence_change_direction(self) -> None:
        """Guven skoru azalma yonunun kabul edildigini dogrular."""
        rc = _make_rule_change(old_confidence=0.9, new_confidence=0.3)
        assert rc.old_confidence > rc.new_confidence

    def test_serialization(self) -> None:
        """model_dump serializasyonunu dogrular."""
        rc = _make_rule_change()
        data = rc.model_dump()
        assert data["risk"] == "high"
        assert data["urgency"] == "low"
        assert data["old_action"] == "auto_fix"
        assert data["new_action"] == "notify"
        assert data["changed_by"] == "system"
        assert "timestamp" in data

    def test_json_roundtrip(self) -> None:
        """JSON serializasyon ve deserializasyonunu dogrular."""
        rc = _make_rule_change(changed_by="learning")
        json_str = rc.model_dump_json()
        restored = RuleChangeRecord.model_validate_json(json_str)
        assert restored.risk == rc.risk
        assert restored.urgency == rc.urgency
        assert restored.old_action == rc.old_action
        assert restored.new_action == rc.new_action
        assert restored.old_confidence == pytest.approx(rc.old_confidence)
        assert restored.new_confidence == pytest.approx(rc.new_confidence)
        assert restored.changed_by == "learning"


# === Coklu Model Entegrasyon Testleri ===


class TestModelInteraction:
    """Modeller arasi etkilesim testleri."""

    def test_approval_request_with_full_decision(self) -> None:
        """ApprovalRequest icinde tam bir DecisionCreate'in calistigini dogrular."""
        dc = _make_decision_create(
            task_id="task-full",
            risk="low",
            urgency="high",
            action="notify",
            confidence=0.6,
            reason="Bildirim gerekli",
        )
        req = _make_approval_request(
            decision=dc,
            action="notify",
            status=ApprovalStatus.PENDING,
        )
        assert req.decision is not None
        assert req.decision.task_id == "task-full"
        assert req.decision.risk == "low"
        assert req.decision.urgency == "high"
        assert req.decision.confidence == pytest.approx(0.6)

    def test_audit_entry_serialization_with_all_fields(self) -> None:
        """Tum alanlari dolu DecisionAuditEntry serializasyonunu dogrular."""
        entry = DecisionAuditEntry(
            task_description="Tam denetim kaydi",
            risk="high",
            urgency="high",
            action="immediate",
            confidence=0.95,
            reason="Kritik durum",
            agent_selected="security_agent",
            agent_selection_method="keyword",
            outcome_success=True,
            escalated_from="auto_fix",
        )
        data = entry.model_dump()
        json_str = json.dumps(data, default=str)
        parsed = json.loads(json_str)
        assert parsed["task_description"] == "Tam denetim kaydi"
        assert parsed["confidence"] == 0.95
        assert parsed["outcome_success"] is True
        assert parsed["escalated_from"] == "auto_fix"

    def test_escalation_with_all_levels(self) -> None:
        """Tum eskalasyon seviyelerinin EscalationRecord'da calistigini dogrular."""
        for level in EscalationLevel:
            rec = _make_escalation_record(level=level)
            assert rec.level == level
            data = rec.model_dump()
            assert data["level"] == level.value

    def test_rule_change_float_precision(self) -> None:
        """Kayan nokta hassasiyetinin korunmasi dogrulanir."""
        rc = _make_rule_change(old_confidence=0.333, new_confidence=0.667)
        assert rc.old_confidence == pytest.approx(0.333)
        assert rc.new_confidence == pytest.approx(0.667)
        json_str = rc.model_dump_json()
        restored = RuleChangeRecord.model_validate_json(json_str)
        assert restored.old_confidence == pytest.approx(0.333)
        assert restored.new_confidence == pytest.approx(0.667)

    def test_approval_all_statuses_roundtrip(self) -> None:
        """Tum ApprovalStatus degerlerinin JSON roundtrip calistigini dogrular."""
        for status in ApprovalStatus:
            req = _make_approval_request(status=status)
            json_str = req.model_dump_json()
            restored = ApprovalRequest.model_validate_json(json_str)
            assert restored.status == status

    def test_multiple_audit_entries_unique_ids(self) -> None:
        """Coklu denetim kayitlarinin benzersiz ID aldigini dogrular."""
        entries = [_make_audit_entry() for _ in range(10)]
        ids = {e.id for e in entries}
        assert len(ids) == 10

    def test_multiple_escalation_records_unique_ids(self) -> None:
        """Coklu eskalasyon kayitlarinin benzersiz ID aldigini dogrular."""
        records = [_make_escalation_record() for _ in range(10)]
        ids = {r.id for r in records}
        assert len(ids) == 10

    def test_multiple_approval_requests_unique_ids(self) -> None:
        """Coklu onay isteklerinin benzersiz ID aldigini dogrular."""
        requests = [_make_approval_request() for _ in range(10)]
        ids = {r.id for r in requests}
        assert len(ids) == 10

    def test_escalation_record_long_reason(self) -> None:
        """Uzun eskalasyon nedeninin kabul edildigini dogrular."""
        long_reason = "A" * 5000
        rec = _make_escalation_record(reason=long_reason)
        assert len(rec.reason) == 5000

    def test_audit_entry_empty_string_fields(self) -> None:
        """Tum string alanlarin bos string kabul ettigini dogrular."""
        entry = DecisionAuditEntry(
            task_description="",
            risk="",
            urgency="",
            action="",
            reason="",
            agent_selection_method="",
        )
        assert entry.task_description == ""
        assert entry.risk == ""
        assert entry.urgency == ""
        assert entry.action == ""
        assert entry.reason == ""
        assert entry.agent_selection_method == ""

    def test_decision_create_missing_required_risk(self) -> None:
        """risk alani olmadan DecisionCreate olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            DecisionCreate(urgency="high", action="fix", confidence=0.5)

    def test_decision_create_missing_required_action(self) -> None:
        """action alani olmadan DecisionCreate olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            DecisionCreate(risk="high", urgency="low", confidence=0.5)

    def test_decision_create_missing_required_confidence(self) -> None:
        """confidence alani olmadan DecisionCreate olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            DecisionCreate(risk="high", urgency="high", action="fix")

    def test_decision_response_missing_required_id(self) -> None:
        """id alani olmadan DecisionResponse olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            DecisionResponse(
                risk="low",
                urgency="low",
                action="log",
                confidence=0.5,
                reason="test",
                created_at=datetime.now(timezone.utc),
            )

    def test_approval_request_decision_none_serialization(self) -> None:
        """decision=None olan ApprovalRequest serializasyonunu dogrular."""
        req = ApprovalRequest(action="check")
        data = req.model_dump()
        assert data["decision"] is None
        json_str = req.model_dump_json()
        restored = ApprovalRequest.model_validate_json(json_str)
        assert restored.decision is None

    def test_rule_change_missing_new_action(self) -> None:
        """new_action alani olmadan olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            RuleChangeRecord(
                risk="high",
                urgency="low",
                old_action="a",
                old_confidence=0.5,
                new_confidence=0.6,
            )

    def test_rule_change_missing_old_confidence(self) -> None:
        """old_confidence alani olmadan olusturmanin reddedildigini dogrular."""
        with pytest.raises(ValidationError):
            RuleChangeRecord(
                risk="high",
                urgency="low",
                old_action="a",
                new_action="b",
                new_confidence=0.6,
            )

    def test_audit_entry_confidence_midpoint(self) -> None:
        """Guven skoru orta deger (0.5) atamasini dogrular."""
        entry = DecisionAuditEntry(confidence=0.5)
        assert entry.confidence == pytest.approx(0.5)

    def test_decision_create_confidence_midpoint(self) -> None:
        """DecisionCreate guven skoru orta deger atamasini dogrular."""
        dc = _make_decision_create(confidence=0.5)
        assert dc.confidence == pytest.approx(0.5)

    def test_approval_request_large_timeout(self) -> None:
        """Buyuk zaman asimi suresinin kabul edildigini dogrular."""
        req = _make_approval_request(timeout_seconds=86400)
        assert req.timeout_seconds == 86400

    def test_escalation_record_same_agent(self) -> None:
        """Ayni agent ile eskalasyonun kabul edildigini dogrular."""
        rec = _make_escalation_record(
            original_agent="security_agent",
            escalated_agent="security_agent",
            level=EscalationLevel.RETRY_SAME,
        )
        assert rec.original_agent == rec.escalated_agent
        assert rec.level == EscalationLevel.RETRY_SAME

    def test_audit_entry_model_dump_keys(self) -> None:
        """DecisionAuditEntry model_dump tum anahtarlari icermelidir."""
        entry = DecisionAuditEntry()
        data = entry.model_dump()
        expected_keys = {
            "id", "task_description", "risk", "urgency", "action",
            "confidence", "reason", "agent_selected",
            "agent_selection_method", "outcome_success",
            "escalated_from", "timestamp",
        }
        assert set(data.keys()) == expected_keys

    def test_approval_request_model_dump_keys(self) -> None:
        """ApprovalRequest model_dump tum anahtarlari icermelidir."""
        req = ApprovalRequest()
        data = req.model_dump()
        expected_keys = {
            "id", "task", "action", "decision", "status",
            "requested_at", "responded_at", "timeout_seconds",
            "auto_execute_on_timeout",
        }
        assert set(data.keys()) == expected_keys

    def test_escalation_record_model_dump_keys(self) -> None:
        """EscalationRecord model_dump tum anahtarlari icermelidir."""
        rec = EscalationRecord()
        data = rec.model_dump()
        expected_keys = {
            "id", "original_action", "escalated_action",
            "original_agent", "escalated_agent", "level",
            "reason", "timestamp",
        }
        assert set(data.keys()) == expected_keys

    def test_rule_change_model_dump_keys(self) -> None:
        """RuleChangeRecord model_dump tum anahtarlari icermelidir."""
        rc = _make_rule_change()
        data = rc.model_dump()
        expected_keys = {
            "risk", "urgency", "old_action", "new_action",
            "old_confidence", "new_confidence", "changed_by",
            "timestamp",
        }
        assert set(data.keys()) == expected_keys

    def test_decision_create_model_dump_keys(self) -> None:
        """DecisionCreate model_dump tum anahtarlari icermelidir."""
        dc = _make_decision_create()
        data = dc.model_dump()
        expected_keys = {
            "task_id", "risk", "urgency", "action",
            "confidence", "reason",
        }
        assert set(data.keys()) == expected_keys

    def test_approval_enum_iteration(self) -> None:
        """ApprovalStatus enum uzerinde iterasyon calistigini dogrular."""
        values = [s.value for s in ApprovalStatus]
        assert values == ["pending", "approved", "rejected", "timeout"]

    def test_escalation_enum_iteration(self) -> None:
        """EscalationLevel enum uzerinde iterasyon calistigini dogrular."""
        values = [e.value for e in EscalationLevel]
        assert values == ["none", "retry_same", "alternate_agent", "notify_human"]

    def test_rule_change_zero_confidences(self) -> None:
        """Sifir guven skorlarinin kabul edildigini dogrular."""
        rc = _make_rule_change(old_confidence=0.0, new_confidence=0.0)
        assert rc.old_confidence == pytest.approx(0.0)
        assert rc.new_confidence == pytest.approx(0.0)

    def test_approval_request_responded_at_with_pending(self) -> None:
        """Pending durumda responded_at None olmasi beklenir."""
        req = _make_approval_request(
            status=ApprovalStatus.PENDING,
            responded_at=None,
        )
        assert req.status == ApprovalStatus.PENDING
        assert req.responded_at is None
