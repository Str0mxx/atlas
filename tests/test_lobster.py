"""Lobster Workflow Engine sistemi testleri."""

import time
import pytest

from app.models.lobster_models import (
    ApprovalRequest, LobsterConfig, PipelineStep, StepStatus, StepType,
    Workflow, WorkflowExecution, WorkflowStatus,
)
from app.core.lobster.workflow_engine import LobsterWorkflowEngine
from app.core.lobster.pipeline_builder import PipelineBuilder
from app.core.lobster.approval_gate import ApprovalGate
from app.core.lobster.workflow_store import WorkflowStore


# ======================= Model Tests =======================


class TestLobsterModels:
    """Lobster modelleri testleri."""

    def test_pipeline_step_defaults(self):
        """PipelineStep varsayilan degerleri."""
        step = PipelineStep()
        assert step.step_type == StepType.ACTION
        assert step.status == StepStatus.PENDING
        assert step.max_retries == 3

    def test_pipeline_step_custom(self):
        """PipelineStep ozel degerlerle."""
        step = PipelineStep(step_id="s1", name="test", step_type=StepType.APPROVAL, requires_approval=True)
        assert step.step_id == "s1"
        assert step.requires_approval is True

    def test_workflow_defaults(self):
        """Workflow varsayilan degerleri."""
        wf = Workflow()
        assert wf.status == WorkflowStatus.DRAFT
        assert wf.steps == []
        assert wf.variables == {}

    def test_workflow_with_steps(self):
        """Workflow adimlarla."""
        step = PipelineStep(step_id="s1", name="step1")
        wf = Workflow(workflow_id="w1", name="test", steps=[step])
        assert len(wf.steps) == 1

    def test_approval_request(self):
        """ApprovalRequest olusturma."""
        ar = ApprovalRequest(request_id="r1", workflow_id="w1", step_id="s1")
        assert ar.status == "pending"

    def test_workflow_execution(self):
        """WorkflowExecution olusturma."""
        we = WorkflowExecution(execution_id="e1", workflow_id="w1")
        assert we.status == WorkflowStatus.RUNNING
        assert we.steps_completed == 0

    def test_lobster_config(self):
        """LobsterConfig varsayilan degerleri."""
        config = LobsterConfig()
        assert config.max_steps == 100
        assert config.enable_recording is True

    def test_step_type_values(self):
        """StepType degerleri."""
        assert StepType.ACTION.value == "action"
        assert StepType.APPROVAL.value == "approval"
        assert StepType.CONDITION.value == "condition"

    def test_step_status_values(self):
        """StepStatus degerleri."""
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"


# ======================= WorkflowEngine Tests =======================


class TestWorkflowEngine:
    """Is akisi motoru testleri."""

    def test_register_action(self):
        """Aksiyon kayit."""
        engine = LobsterWorkflowEngine()
        engine.register_action("greet", lambda ctx: {"msg": "hello"})
        assert "greet" in engine._action_handlers

    def test_create_workflow(self):
        """Is akisi olusturma."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test_wf")
        assert wf.name == "test_wf"
        assert wf.status == WorkflowStatus.DRAFT

    def test_run_workflow_action(self):
        """Aksiyon adimi calistirma."""
        engine = LobsterWorkflowEngine()
        engine.register_action("noop", lambda ctx: {"ok": True})
        wf = engine.create_workflow("test")
        step = PipelineStep(step_id="s1", name="step1", step_type=StepType.ACTION, action="noop")
        wf.steps.append(step)
        result = engine.run_workflow(wf.workflow_id)
        assert result.status == WorkflowStatus.COMPLETED

    def test_run_workflow_condition_true(self):
        """Kosul adimi - dogru."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test")
        step = PipelineStep(step_id="s1", name="cond1", step_type=StepType.CONDITION, condition="1 == 1")
        wf.steps.append(step)
        result = engine.run_workflow(wf.workflow_id)
        assert result is not None

    def test_run_workflow_not_found(self):
        """Bulunamayan is akisi."""
        engine = LobsterWorkflowEngine()
        with pytest.raises(ValueError):
            engine.run_workflow("nonexistent")

    def test_pause_workflow(self):
        """Is akisi duraklatma."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test")
        wf.status = WorkflowStatus.RUNNING
        assert engine.pause_workflow(wf.workflow_id) is True

    def test_resume_workflow(self):
        """Is akisi devam ettirme."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test")
        wf.status = WorkflowStatus.RUNNING
        engine.pause_workflow(wf.workflow_id)
        assert engine.resume_workflow(wf.workflow_id) is True

    def test_cancel_workflow(self):
        """Is akisi iptal."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test")
        assert engine.cancel_workflow(wf.workflow_id) is True

    def test_get_workflow(self):
        """Is akisi sorgulama."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test")
        found = engine.get_workflow(wf.workflow_id)
        assert found is not None
        assert found.name == "test"

    def test_list_workflows(self):
        """Is akisi listeleme."""
        engine = LobsterWorkflowEngine()
        engine.create_workflow("wf1")
        engine.create_workflow("wf2")
        assert len(engine.list_workflows()) == 2

    def test_execute_step(self):
        """Tek adim calistirma."""
        engine = LobsterWorkflowEngine()
        engine.register_action("noop", lambda ctx: {"ok": True})
        wf = engine.create_workflow("test")
        step = PipelineStep(step_id="s1", name="step1", step_type=StepType.ACTION, action="noop")
        wf.steps.append(step)
        result = engine.execute_step(wf, step)
        assert result is not None

    def test_handle_step_failure(self):
        """Adim hatasi isleme."""
        engine = LobsterWorkflowEngine()
        wf = engine.create_workflow("test")
        step = PipelineStep(step_id="s1", name="step1", max_retries=0)
        wf.steps.append(step)
        engine.handle_step_failure(wf, step, "test error")
        assert step.status == StepStatus.FAILED

    def test_get_execution_history(self):
        """Calistirma gecmisi."""
        engine = LobsterWorkflowEngine()
        engine.register_action("noop", lambda ctx: {"ok": True})
        wf = engine.create_workflow("test")
        step = PipelineStep(step_id="s1", name="step1", step_type=StepType.ACTION, action="noop")
        wf.steps.append(step)
        engine.run_workflow(wf.workflow_id)
        history = engine.get_execution_history(wf.workflow_id)
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_replay_workflow(self):
        """Is akisi tekrar oynatma."""
        engine = LobsterWorkflowEngine()
        engine.register_action("noop", lambda ctx: {"ok": True})
        wf = engine.create_workflow("test")
        step = PipelineStep(step_id="s1", name="step1", step_type=StepType.ACTION, action="noop")
        wf.steps.append(step)
        engine.run_workflow(wf.workflow_id)
        result = engine.replay_workflow(wf.workflow_id)
        assert result is not None
        assert isinstance(result, WorkflowExecution)

    def test_get_stats(self):
        """Istatistik kontrolu."""
        engine = LobsterWorkflowEngine()
        stats = engine.get_stats()
        assert "total_workflows" in stats

    def test_get_history(self):
        """Gecmis kayit kontrolu."""
        engine = LobsterWorkflowEngine()
        engine.create_workflow("test")
        assert len(engine.get_history()) >= 1


# ======================= PipelineBuilder Tests =======================


class TestPipelineBuilder:
    """Pipeline olusturucu testleri."""

    def test_new_pipeline(self):
        """Yeni pipeline olusturma."""
        pb = PipelineBuilder()
        result = pb.new("test_pipeline", "Test aciklamasi")
        assert result is pb

    def test_add_step(self):
        """Adim ekleme."""
        pb = PipelineBuilder()
        pb.new("test").add_step("step1", "do_something")
        assert pb.get_stats()["step_count"] == 1

    def test_add_approval(self):
        """Onay adimi ekleme."""
        pb = PipelineBuilder()
        pb.new("test").add_step("s1", "act")
        pb.add_approval("review", "admin")
        assert pb.get_stats()["step_count"] == 2

    def test_add_condition(self):
        """Kosul adimi ekleme."""
        pb = PipelineBuilder()
        pb.new("test").add_step("s1", "act")
        pb.add_condition("check", "x > 0")
        assert pb.get_stats()["step_count"] == 2

    def test_add_delay(self):
        """Gecikme adimi ekleme."""
        pb = PipelineBuilder()
        pb.new("test").add_step("s1", "act")
        pb.add_delay("wait", 60)
        assert pb.get_stats()["step_count"] == 2

    def test_set_variable(self):
        """Degisken ayarlama."""
        pb = PipelineBuilder()
        pb.new("test").add_step("s1", "act")
        pb.set_variable("key", "value")
        assert pb.get_stats()["variable_count"] == 1

    def test_add_tag(self):
        """Etiket ekleme."""
        pb = PipelineBuilder()
        pb.new("test").add_step("s1", "act")
        pb.add_tag("important")
        wf = pb.build()
        assert "important" in wf.tags

    def test_build(self):
        """Pipeline derleme."""
        pb = PipelineBuilder()
        wf = pb.new("test").add_step("s1", "act").build()
        assert isinstance(wf, Workflow)
        assert wf.name == "test"

    def test_validate_empty_name(self):
        """Bos isimle dogrulama hatasi."""
        pb = PipelineBuilder()
        pb.new("").add_step("s1", "act")
        errors = pb.validate()
        assert len(errors) > 0

    def test_validate_no_steps(self):
        """Adimsiz dogrulama hatasi."""
        pb = PipelineBuilder()
        pb.new("test")
        errors = pb.validate()
        assert len(errors) > 0

    def test_build_invalid_raises(self):
        """Gecersiz pipeline derleme hatasi."""
        pb = PipelineBuilder()
        pb.new("")
        with pytest.raises(ValueError):
            pb.build()

    def test_from_dict(self):
        """Sozlukten yukleme."""
        data = {
            "name": "test",
            "steps": [{"step_id": "s1", "name": "step1", "step_type": "action", "action": "do"}]
        }
        wf = PipelineBuilder.from_dict(data)
        assert isinstance(wf, Workflow)

    def test_to_dict(self):
        """Sozluge donusturme."""
        pb = PipelineBuilder()
        wf = pb.new("test").add_step("s1", "act").build()
        d = PipelineBuilder.to_dict(wf)
        assert isinstance(d, dict)
        assert d["name"] == "test"

    def test_get_stats(self):
        """Istatistik kontrolu."""
        pb = PipelineBuilder()
        pb.new("test").add_step("s1", "act")
        stats = pb.get_stats()
        assert stats["name"] == "test"

    def test_get_history(self):
        """Gecmis kayit kontrolu."""
        pb = PipelineBuilder()
        pb.new("test")
        assert len(pb.get_history()) >= 1


# ======================= ApprovalGate Tests =======================


class TestApprovalGate:
    """Onay kapisi testleri."""

    def test_request_approval(self):
        """Onay istegi olusturma."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1", "Test onay")
        assert req.status == "pending"
        assert req.workflow_id == "w1"

    def test_approve(self):
        """Onay verme."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1")
        assert ag.approve(req.request_id, "admin") is True

    def test_reject(self):
        """Red verme."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1")
        assert ag.reject(req.request_id, "admin", "not ok") is True

    def test_approve_already_approved(self):
        """Zaten onaylanmis istegi onaylama."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1")
        ag.approve(req.request_id)
        assert ag.approve(req.request_id) is False

    def test_reject_already_rejected(self):
        """Zaten reddedilmis istegi reddetme."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1")
        ag.reject(req.request_id)
        assert ag.reject(req.request_id) is False

    def test_get_pending(self):
        """Bekleyen istekleri sorgulama."""
        ag = ApprovalGate()
        ag.request_approval("w1", "s1")
        ag.request_approval("w1", "s2")
        assert len(ag.get_pending()) == 2

    def test_is_approved(self):
        """Onay durumu kontrolu."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1")
        assert ag.is_approved(req.request_id) is False
        ag.approve(req.request_id)
        assert ag.is_approved(req.request_id) is True

    def test_is_expired(self):
        """Sure dolma kontrolu."""
        ag = ApprovalGate(approval_timeout=0)
        req = ag.request_approval("w1", "s1")
        time.sleep(0.01)
        assert ag.is_expired(req.request_id) is True

    def test_approve_expired(self):
        """Suresi dolmus istegi onaylama."""
        ag = ApprovalGate(approval_timeout=0)
        req = ag.request_approval("w1", "s1")
        time.sleep(0.01)
        assert ag.approve(req.request_id) is False

    def test_cleanup_expired(self):
        """Suresi dolmus istekleri temizleme."""
        ag = ApprovalGate(approval_timeout=0)
        ag.request_approval("w1", "s1")
        ag.request_approval("w1", "s2")
        time.sleep(0.01)
        count = ag.cleanup_expired()
        assert count >= 2

    def test_get_request(self):
        """Istek sorgulama."""
        ag = ApprovalGate()
        req = ag.request_approval("w1", "s1")
        found = ag.get_request(req.request_id)
        assert found is not None
        assert found.request_id == req.request_id

    def test_get_stats(self):
        """Istatistik kontrolu."""
        ag = ApprovalGate()
        ag.request_approval("w1", "s1")
        stats = ag.get_stats()
        assert stats["total_requests"] == 1

    def test_get_history(self):
        """Gecmis kayit kontrolu."""
        ag = ApprovalGate()
        ag.request_approval("w1", "s1")
        assert len(ag.get_history()) >= 1


# ======================= WorkflowStore Tests =======================


class TestWorkflowStore:
    """Is akisi deposu testleri."""

    def test_save(self):
        """Is akisi kaydetme."""
        ws = WorkflowStore()
        wf = Workflow(workflow_id="w1", name="test")
        wid = ws.save(wf)
        assert wid == "w1"

    def test_load(self):
        """Is akisi yukleme."""
        ws = WorkflowStore()
        wf = Workflow(workflow_id="w1", name="test")
        ws.save(wf)
        loaded = ws.load("w1")
        assert loaded is not None
        assert loaded.name == "test"

    def test_load_not_found(self):
        """Bulunamayan is akisi yukleme."""
        ws = WorkflowStore()
        assert ws.load("nonexistent") is None

    def test_delete(self):
        """Is akisi silme."""
        ws = WorkflowStore()
        wf = Workflow(workflow_id="w1", name="test")
        ws.save(wf)
        assert ws.delete("w1") is True
        assert ws.load("w1") is None

    def test_delete_not_found(self):
        """Bulunamayan is akisi silme."""
        ws = WorkflowStore()
        assert ws.delete("nonexistent") is False

    def test_list_all(self):
        """Tum is akislarini listeleme."""
        ws = WorkflowStore()
        ws.save(Workflow(workflow_id="w1", name="test1"))
        ws.save(Workflow(workflow_id="w2", name="test2"))
        items = ws.list_all()
        assert len(items) == 2

    def test_export_workflow(self):
        """Is akisi disa aktarma."""
        ws = WorkflowStore()
        ws.save(Workflow(workflow_id="w1", name="test"))
        exported = ws.export_workflow("w1")
        assert isinstance(exported, dict)
        assert exported["name"] == "test"

    def test_export_not_found(self):
        """Bulunamayan is akisi disa aktarma."""
        ws = WorkflowStore()
        with pytest.raises(ValueError):
            ws.export_workflow("nonexistent")

    def test_import_workflow(self):
        """Is akisi ice aktarma."""
        ws = WorkflowStore()
        data = {"workflow_id": "w1", "name": "imported", "steps": [], "status": "draft"}
        wf = ws.import_workflow(data)
        assert isinstance(wf, Workflow)
        assert wf.name == "imported"

    def test_search(self):
        """Is akisi arama."""
        ws = WorkflowStore()
        ws.save(Workflow(workflow_id="w1", name="deploy prod"))
        ws.save(Workflow(workflow_id="w2", name="test staging"))
        results = ws.search("deploy")
        assert len(results) == 1

    def test_search_no_results(self):
        """Sonucsuz arama."""
        ws = WorkflowStore()
        ws.save(Workflow(workflow_id="w1", name="test"))
        results = ws.search("nonexistent_query")
        assert len(results) == 0

    def test_get_stats(self):
        """Istatistik kontrolu."""
        ws = WorkflowStore()
        ws.save(Workflow(workflow_id="w1", name="test"))
        stats = ws.get_stats()
        assert stats["total_stored"] == 1

    def test_get_history(self):
        """Gecmis kayit kontrolu."""
        ws = WorkflowStore()
        ws.save(Workflow(workflow_id="w1", name="test"))
        assert len(ws.get_history()) >= 1
