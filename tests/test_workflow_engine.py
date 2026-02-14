"""Workflow & Automation Engine testleri.

WorkflowDesigner, TriggerManager,
ActionExecutor, ConditionEvaluator,
VariableManager, LoopController,
WorkflowErrorHandler, ExecutionTracker,
WorkflowOrchestrator testleri.
"""

import time

import pytest

from app.models.workflow_engine import (
    ActionType,
    ExecutionRecord,
    LoopType,
    NodeType,
    TriggerRecord,
    TriggerType,
    VariableScope,
    WorkflowRecord,
    WorkflowSnapshot,
    WorkflowStatus,
)

from app.core.workflow.workflow_designer import (
    WorkflowDesigner,
)
from app.core.workflow.trigger_manager import (
    TriggerManager,
)
from app.core.workflow.action_executor import (
    ActionExecutor,
)
from app.core.workflow.condition_evaluator import (
    ConditionEvaluator,
)
from app.core.workflow.variable_manager import (
    VariableManager,
)
from app.core.workflow.loop_controller import (
    LoopController,
)
from app.core.workflow.error_handler import (
    WorkflowErrorHandler,
)
from app.core.workflow.execution_tracker import (
    ExecutionTracker,
)
from app.core.workflow.workflow_orchestrator import (
    WorkflowOrchestrator,
)


# ===================== Models =====================


class TestWorkflowModels:
    """Model testleri."""

    def test_node_type_values(self) -> None:
        assert NodeType.ACTION == "action"
        assert NodeType.CONDITION == "condition"
        assert NodeType.TRIGGER == "trigger"
        assert NodeType.LOOP == "loop"

    def test_trigger_type_values(self) -> None:
        assert TriggerType.EVENT == "event"
        assert TriggerType.SCHEDULE == "schedule"
        assert TriggerType.WEBHOOK == "webhook"
        assert TriggerType.MANUAL == "manual"
        assert TriggerType.CONDITIONAL == "conditional"

    def test_workflow_status_values(self) -> None:
        assert WorkflowStatus.DRAFT == "draft"
        assert WorkflowStatus.ACTIVE == "active"
        assert WorkflowStatus.RUNNING == "running"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"

    def test_action_type_values(self) -> None:
        assert ActionType.BUILTIN == "builtin"
        assert ActionType.CUSTOM == "custom"
        assert ActionType.API_CALL == "api_call"

    def test_variable_scope_values(self) -> None:
        assert VariableScope.LOCAL == "local"
        assert VariableScope.WORKFLOW == "workflow"
        assert VariableScope.GLOBAL == "global"
        assert VariableScope.SECRET == "secret"

    def test_loop_type_values(self) -> None:
        assert LoopType.FOR_EACH == "for_each"
        assert LoopType.WHILE == "while"
        assert LoopType.PARALLEL == "parallel"
        assert LoopType.COUNT == "count"

    def test_workflow_record(self) -> None:
        rec = WorkflowRecord(name="test")
        assert rec.workflow_id
        assert rec.name == "test"
        assert rec.status == WorkflowStatus.DRAFT

    def test_execution_record(self) -> None:
        rec = ExecutionRecord(workflow_id="w1")
        assert rec.execution_id
        assert rec.workflow_id == "w1"
        assert rec.status == WorkflowStatus.RUNNING

    def test_trigger_record(self) -> None:
        rec = TriggerRecord(workflow_id="w1")
        assert rec.trigger_id
        assert rec.enabled

    def test_workflow_snapshot(self) -> None:
        snap = WorkflowSnapshot(
            total_workflows=5,
            running=2,
            completed=3,
        )
        assert snap.total_workflows == 5


# ========== WorkflowDesigner ==========


class TestWorkflowDesigner:
    """WorkflowDesigner testleri."""

    def test_create_workflow(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        assert wf.name == "test"
        assert d.workflow_count == 1

    def test_add_node(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        node = d.add_node(
            wf.workflow_id, "start",
            NodeType.TRIGGER,
        )
        assert node is not None
        assert node["name"] == "start"

    def test_add_node_invalid_wf(self) -> None:
        d = WorkflowDesigner()
        assert d.add_node(
            "invalid", "n1", NodeType.ACTION,
        ) is None

    def test_remove_node(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        node = d.add_node(
            wf.workflow_id, "n1", NodeType.ACTION,
        )
        assert d.remove_node(
            wf.workflow_id, node["id"],
        )
        assert len(wf.nodes) == 0

    def test_add_connection(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        n1 = d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        n2 = d.add_node(
            wf.workflow_id, "b", NodeType.ACTION,
        )
        conn = d.add_connection(
            wf.workflow_id, n1["id"], n2["id"],
        )
        assert conn is not None
        assert len(wf.connections) == 1

    def test_add_connection_invalid_node(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        assert d.add_connection(
            wf.workflow_id, "n_1", "invalid",
        ) is None

    def test_remove_connection(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        n1 = d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        n2 = d.add_node(
            wf.workflow_id, "b", NodeType.ACTION,
        )
        d.add_connection(
            wf.workflow_id, n1["id"], n2["id"],
        )
        assert d.remove_connection(
            wf.workflow_id, n1["id"], n2["id"],
        )
        assert len(wf.connections) == 0

    def test_validate_empty(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        result = d.validate(wf.workflow_id)
        assert not result["valid"]

    def test_validate_valid(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        result = d.validate(wf.workflow_id)
        assert result["valid"]

    def test_validate_nonexistent(self) -> None:
        d = WorkflowDesigner()
        result = d.validate("invalid")
        assert not result["valid"]

    def test_save_template(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        t = d.save_template("tmpl", wf.workflow_id)
        assert t is not None
        assert d.template_count == 1

    def test_create_from_template(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("original")
        d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        d.save_template("tmpl", wf.workflow_id)
        new_wf = d.create_from_template(
            "tmpl", "copy",
        )
        assert new_wf is not None
        assert new_wf.name == "copy"
        assert len(new_wf.nodes) == 1

    def test_create_from_missing_template(self) -> None:
        d = WorkflowDesigner()
        assert d.create_from_template(
            "invalid", "x",
        ) is None

    def test_activate(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        d.add_node(
            wf.workflow_id, "a", NodeType.ACTION,
        )
        assert d.activate(wf.workflow_id)
        assert wf.status == WorkflowStatus.ACTIVE

    def test_activate_empty(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        assert not d.activate(wf.workflow_id)

    def test_delete_workflow(self) -> None:
        d = WorkflowDesigner()
        wf = d.create_workflow("test")
        assert d.delete_workflow(wf.workflow_id)
        assert d.workflow_count == 0


# ========== TriggerManager ==========


class TestTriggerManager:
    """TriggerManager testleri."""

    def test_create_trigger(self) -> None:
        tm = TriggerManager()
        t = tm.create_trigger(
            "w1", TriggerType.MANUAL,
        )
        assert t.workflow_id == "w1"
        assert tm.trigger_count == 1

    def test_fire_event(self) -> None:
        tm = TriggerManager()
        tm.create_trigger(
            "w1", TriggerType.EVENT,
            {"event": "deploy"},
        )
        triggered = tm.fire_event("deploy")
        assert "w1" in triggered
        assert tm.fired_count == 1

    def test_fire_event_no_match(self) -> None:
        tm = TriggerManager()
        triggered = tm.fire_event("unknown")
        assert len(triggered) == 0

    def test_check_schedule(self) -> None:
        tm = TriggerManager()
        tm.create_trigger(
            "w1", TriggerType.SCHEDULE,
            {"interval_seconds": 60, "last_run": 0},
        )
        triggered = tm.check_schedule(
            current_time=100,
        )
        assert "w1" in triggered

    def test_check_schedule_not_due(self) -> None:
        tm = TriggerManager()
        now = time.time()
        tm.create_trigger(
            "w1", TriggerType.SCHEDULE,
            {"interval_seconds": 3600, "last_run": now},
        )
        triggered = tm.check_schedule(
            current_time=now + 10,
        )
        assert len(triggered) == 0

    def test_fire_webhook(self) -> None:
        tm = TriggerManager()
        tm.create_trigger(
            "w1", TriggerType.WEBHOOK,
            {"webhook_id": "hook1"},
        )
        triggered = tm.fire_webhook("hook1")
        assert "w1" in triggered

    def test_fire_webhook_no_match(self) -> None:
        tm = TriggerManager()
        triggered = tm.fire_webhook("unknown")
        assert len(triggered) == 0

    def test_fire_manual(self) -> None:
        tm = TriggerManager()
        t = tm.create_trigger(
            "w1", TriggerType.MANUAL,
        )
        wf_id = tm.fire_manual(t.trigger_id)
        assert wf_id == "w1"

    def test_fire_manual_disabled(self) -> None:
        tm = TriggerManager()
        t = tm.create_trigger(
            "w1", TriggerType.MANUAL,
        )
        tm.disable_trigger(t.trigger_id)
        assert tm.fire_manual(t.trigger_id) is None

    def test_enable_disable(self) -> None:
        tm = TriggerManager()
        t = tm.create_trigger(
            "w1", TriggerType.MANUAL,
        )
        assert tm.disable_trigger(t.trigger_id)
        assert tm.active_count == 0
        assert tm.enable_trigger(t.trigger_id)
        assert tm.active_count == 1

    def test_remove_trigger(self) -> None:
        tm = TriggerManager()
        t = tm.create_trigger(
            "w1", TriggerType.MANUAL,
        )
        assert tm.remove_trigger(t.trigger_id)
        assert tm.trigger_count == 0


# ========== ActionExecutor ==========


class TestActionExecutor:
    """ActionExecutor testleri."""

    def test_init_builtins(self) -> None:
        ae = ActionExecutor()
        assert ae.builtin_count >= 6
        assert ae.action_count >= 6

    def test_execute_log(self) -> None:
        ae = ActionExecutor()
        result = ae.execute(
            "log", {"message": "test"},
        )
        assert result["success"]
        assert ae.history_count == 1

    def test_execute_notify(self) -> None:
        ae = ActionExecutor()
        result = ae.execute(
            "notify", {"recipient": "admin"},
        )
        assert result["success"]

    def test_execute_wait(self) -> None:
        ae = ActionExecutor()
        result = ae.execute("wait")
        assert result["success"]

    def test_execute_nonexistent(self) -> None:
        ae = ActionExecutor()
        result = ae.execute("invalid")
        assert not result["success"]

    def test_register_custom(self) -> None:
        ae = ActionExecutor()
        ae.register_action(
            "greet", ActionType.CUSTOM,
            handler=lambda name="": f"Hi {name}",
        )
        result = ae.execute(
            "greet", {"name": "Fatih"},
        )
        assert result["success"]
        assert result["result"] == "Hi Fatih"

    def test_execute_sequence(self) -> None:
        ae = ActionExecutor()
        results = ae.execute_sequence([
            {"name": "log", "params": {"message": "a"}},
            {"name": "log", "params": {"message": "b"}},
        ])
        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_execute_sequence_break(self) -> None:
        ae = ActionExecutor()
        results = ae.execute_sequence([
            {"name": "log", "params": {"message": "a"}},
            {"name": "invalid"},
            {"name": "log", "params": {"message": "c"}},
        ])
        assert len(results) == 2
        assert not results[1]["success"]

    def test_enable_disable(self) -> None:
        ae = ActionExecutor()
        assert ae.disable_action("log")
        result = ae.execute("log")
        assert not result["success"]
        assert ae.enable_action("log")

    def test_custom_handler_error(self) -> None:
        ae = ActionExecutor()
        ae.register_action(
            "fail", ActionType.CUSTOM,
            handler=lambda: 1 / 0,
        )
        result = ae.execute("fail")
        assert not result["success"]
        assert result["error"]


# ======= ConditionEvaluator =======


class TestConditionEvaluator:
    """ConditionEvaluator testleri."""

    def test_evaluate_true(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate("true")

    def test_evaluate_false(self) -> None:
        ce = ConditionEvaluator()
        assert not ce.evaluate("false")

    def test_evaluate_comparison_gt(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate(
            "score > 80", {"score": 90},
        )
        assert not ce.evaluate(
            "score > 80", {"score": 70},
        )

    def test_evaluate_comparison_eq(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate(
            "status == 200", {"status": 200},
        )

    def test_evaluate_comparison_ne(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate(
            "status != 500", {"status": 200},
        )

    def test_evaluate_comparison_lte(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate(
            "count <= 10", {"count": 10},
        )

    def test_evaluate_variable(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate(
            "enabled", {"enabled": True},
        )
        assert not ce.evaluate(
            "enabled", {"enabled": False},
        )

    def test_compare_operators(self) -> None:
        ce = ConditionEvaluator()
        assert ce.compare(5, "gt", 3)
        assert ce.compare(3, "lt", 5)
        assert ce.compare(5, "eq", 5)
        assert ce.compare(5, "ne", 3)
        assert ce.compare(5, "gte", 5)
        assert ce.compare(5, "lte", 5)
        assert ce.compare(1, "in", [1, 2, 3])
        assert ce.compare(4, "not_in", [1, 2, 3])
        assert ce.compare("hello", "contains", "ell")

    def test_compare_invalid_op(self) -> None:
        ce = ConditionEvaluator()
        assert not ce.compare(1, "invalid", 2)

    def test_evaluate_all(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate_all(
            ["true", "score > 50"],
            {"score": 80},
        )
        assert not ce.evaluate_all(
            ["true", "score > 50"],
            {"score": 30},
        )

    def test_evaluate_any(self) -> None:
        ce = ConditionEvaluator()
        assert ce.evaluate_any(
            ["false", "score > 50"],
            {"score": 80},
        )
        assert not ce.evaluate_any(
            ["false", "score > 90"],
            {"score": 80},
        )

    def test_time_condition(self) -> None:
        ce = ConditionEvaluator()
        assert ce.check_time_condition(
            9, 17, current_hour=12,
        )
        assert not ce.check_time_condition(
            9, 17, current_hour=20,
        )

    def test_time_condition_midnight(self) -> None:
        ce = ConditionEvaluator()
        assert ce.check_time_condition(
            22, 6, current_hour=23,
        )
        assert ce.check_time_condition(
            22, 6, current_hour=3,
        )
        assert not ce.check_time_condition(
            22, 6, current_hour=12,
        )

    def test_register_named(self) -> None:
        ce = ConditionEvaluator()
        ce.register_condition(
            "high_score", "score > 80",
        )
        assert ce.condition_count == 1
        assert ce.evaluate_named(
            "high_score", {"score": 90},
        )

    def test_evaluate_named_missing(self) -> None:
        ce = ConditionEvaluator()
        assert not ce.evaluate_named("missing")

    def test_evaluation_count(self) -> None:
        ce = ConditionEvaluator()
        ce.evaluate("true")
        ce.evaluate("false")
        assert ce.evaluation_count == 2


# ========= VariableManager =========


class TestVariableManager:
    """VariableManager testleri."""

    def test_set_get_global(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "app_name", "ATLAS",
            VariableScope.GLOBAL,
        )
        assert vm.get_variable(
            "app_name", VariableScope.GLOBAL,
        ) == "ATLAS"

    def test_set_get_workflow(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "step", 1,
            VariableScope.WORKFLOW, "w1",
        )
        assert vm.get_variable(
            "step", VariableScope.WORKFLOW, "w1",
        ) == 1

    def test_scope_fallback(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "name", "ATLAS",
            VariableScope.GLOBAL,
        )
        # Workflow scope falls back to global
        val = vm.get_variable(
            "name", VariableScope.WORKFLOW, "w1",
        )
        assert val == "ATLAS"

    def test_local_fallback(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "x", 42,
            VariableScope.WORKFLOW, "w1",
        )
        val = vm.get_variable(
            "x", VariableScope.LOCAL, "w1",
        )
        assert val == 42

    def test_get_default(self) -> None:
        vm = VariableManager()
        val = vm.get_variable(
            "missing", VariableScope.GLOBAL,
            default="default_val",
        )
        assert val == "default_val"

    def test_delete_variable(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "x", 1, VariableScope.GLOBAL,
        )
        assert vm.delete_variable(
            "x", VariableScope.GLOBAL,
        )
        assert vm.get_variable(
            "x", VariableScope.GLOBAL,
        ) is None

    def test_delete_nonexistent(self) -> None:
        vm = VariableManager()
        assert not vm.delete_variable(
            "x", VariableScope.GLOBAL,
        )

    def test_secrets(self) -> None:
        vm = VariableManager()
        vm.set_secret("api_key", "env:API_KEY")
        assert vm.get_secret("api_key") == "env:API_KEY"
        assert vm.secret_count == 1

    def test_secret_missing(self) -> None:
        vm = VariableManager()
        assert vm.get_secret("missing") is None

    def test_resolve_template(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "name", "Fatih",
            VariableScope.GLOBAL,
        )
        vm.set_variable(
            "role", "Admin",
            VariableScope.WORKFLOW, "w1",
        )
        result = vm.resolve(
            "Hello {name}, role: {role}",
            VariableScope.WORKFLOW, "w1",
        )
        assert "Hello Fatih" in result
        assert "role: Admin" in result

    def test_get_scope_variables(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "a", 1, VariableScope.GLOBAL,
        )
        vm.set_variable(
            "b", 2, VariableScope.GLOBAL,
        )
        vars_ = vm.get_scope_variables(
            VariableScope.GLOBAL,
        )
        assert len(vars_) == 2

    def test_clear_scope(self) -> None:
        vm = VariableManager()
        vm.set_variable(
            "a", 1, VariableScope.GLOBAL,
        )
        vm.set_variable(
            "b", 2, VariableScope.GLOBAL,
        )
        cleared = vm.clear_scope(
            VariableScope.GLOBAL,
        )
        assert cleared == 2
        assert vm.get_variable(
            "a", VariableScope.GLOBAL,
        ) is None


# ========== LoopController ==========


class TestLoopController:
    """LoopController testleri."""

    def test_create_for_each(self) -> None:
        lc = LoopController()
        loop = lc.create_for_each(
            "items", [1, 2, 3],
        )
        assert loop["name"] == "items"
        assert lc.loop_count == 1

    def test_execute_for_each(self) -> None:
        lc = LoopController()
        results: list[int] = []
        loop = lc.create_for_each(
            "nums", [1, 2, 3],
            action=lambda x: x * 2,
        )
        result = lc.execute_for_each(loop["id"])
        assert result["success"]
        assert result["iterations"] == 3
        assert result["results"] == [2, 4, 6]

    def test_for_each_break(self) -> None:
        lc = LoopController()
        loop = lc.create_for_each(
            "nums", [1, 2, 3, 4, 5],
            action=lambda x: x,
        )
        result = lc.execute_for_each(
            loop["id"],
            break_on=lambda x: x == 3,
        )
        assert result["broken"]
        assert result["iterations"] == 3

    def test_create_while(self) -> None:
        lc = LoopController()
        loop = lc.create_while("wait")
        assert loop["type"] == "while"

    def test_execute_while(self) -> None:
        lc = LoopController()
        counter = {"v": 0}

        def cond() -> bool:
            return counter["v"] < 3

        def act() -> int:
            counter["v"] += 1
            return counter["v"]

        loop = lc.create_while(
            "count", condition=cond, action=act,
        )
        result = lc.execute_while(loop["id"])
        assert result["success"]
        assert result["iterations"] == 3

    def test_create_count(self) -> None:
        lc = LoopController()
        loop = lc.create_count("repeat", 5)
        assert loop["count"] == 5

    def test_execute_count(self) -> None:
        lc = LoopController()
        loop = lc.create_count(
            "repeat", 4,
            action=lambda i: i * 10,
        )
        result = lc.execute_count(loop["id"])
        assert result["success"]
        assert result["iterations"] == 4
        assert result["results"] == [0, 10, 20, 30]

    def test_max_iterations(self) -> None:
        lc = LoopController(max_iterations=5)
        loop = lc.create_for_each(
            "big", list(range(100)),
            action=lambda x: x,
        )
        result = lc.execute_for_each(loop["id"])
        assert result["iterations"] == 5

    def test_execute_nonexistent(self) -> None:
        lc = LoopController()
        result = lc.execute_for_each("invalid")
        assert not result["success"]

    def test_remove_loop(self) -> None:
        lc = LoopController()
        loop = lc.create_count("r", 3)
        assert lc.remove_loop(loop["id"])
        assert lc.loop_count == 0

    def test_history(self) -> None:
        lc = LoopController()
        loop = lc.create_count("r", 2)
        lc.execute_count(loop["id"])
        assert lc.history_count == 1


# ======== WorkflowErrorHandler ========


class TestWorkflowErrorHandler:
    """WorkflowErrorHandler testleri."""

    def test_execute_with_retry_success(self) -> None:
        eh = WorkflowErrorHandler()
        result = eh.execute_with_retry(
            "action1", lambda: "ok",
        )
        assert result["success"]
        assert result["attempts"] == 1

    def test_execute_with_retry_fail(self) -> None:
        eh = WorkflowErrorHandler(max_retries=2)

        def fail() -> None:
            raise ValueError("err")

        result = eh.execute_with_retry(
            "action1", fail,
        )
        assert not result["success"]
        assert result["attempts"] == 3  # 1 + 2 retries

    def test_retry_with_fallback(self) -> None:
        eh = WorkflowErrorHandler(max_retries=1)
        eh.register_fallback(
            "act", lambda: "fallback_result",
        )

        def fail() -> None:
            raise ValueError("err")

        result = eh.execute_with_retry("act", fail)
        assert result["success"]
        assert result["fallback"]
        assert result["result"] == "fallback_result"

    def test_retry_policy(self) -> None:
        eh = WorkflowErrorHandler()
        policy = eh.set_retry_policy(
            "api_call", max_retries=5,
            delay_seconds=2.0,
        )
        assert policy["max_retries"] == 5
        assert eh.policy_count == 1

    def test_handle_error(self) -> None:
        eh = WorkflowErrorHandler()
        handled = []
        eh.register_handler(
            "ValueError",
            lambda e: handled.append(str(e)),
        )
        result = eh.handle_error(
            ValueError("test"),
        )
        assert result["handled"]
        assert eh.handler_count == 1

    def test_handle_unknown_error(self) -> None:
        eh = WorkflowErrorHandler()
        result = eh.handle_error(
            RuntimeError("unknown"),
        )
        assert not result["handled"]
        assert eh.error_count == 1

    def test_compensation(self) -> None:
        eh = WorkflowErrorHandler()
        compensated: list[str] = []
        eh.register_compensation(
            "step1",
            lambda: compensated.append("s1"),
        )
        eh.register_compensation(
            "step2",
            lambda: compensated.append("s2"),
        )
        results = eh.compensate(["step1", "step2"])
        assert len(results) == 2
        assert all(r["compensated"] for r in results)
        # Reversed order
        assert compensated == ["s2", "s1"]

    def test_compensation_count(self) -> None:
        eh = WorkflowErrorHandler()
        eh.register_compensation(
            "s1", lambda: None,
        )
        assert eh.compensation_count == 1

    def test_error_count(self) -> None:
        eh = WorkflowErrorHandler(max_retries=0)

        def fail() -> None:
            raise ValueError("e")

        eh.execute_with_retry("a", fail)
        assert eh.error_count >= 1


# ======== ExecutionTracker ========


class TestExecutionTracker:
    """ExecutionTracker testleri."""

    def test_start_execution(self) -> None:
        et = ExecutionTracker()
        ex = et.start_execution("w1")
        assert ex.workflow_id == "w1"
        assert ex.status == WorkflowStatus.RUNNING
        assert et.execution_count == 1

    def test_log_step(self) -> None:
        et = ExecutionTracker()
        ex = et.start_execution("w1")
        log = et.log_step(
            ex.execution_id, "step1", "running",
        )
        assert log["step"] == "step1"
        logs = et.get_step_logs(ex.execution_id)
        assert len(logs) == 1

    def test_complete_execution(self) -> None:
        et = ExecutionTracker()
        ex = et.start_execution("w1")
        assert et.complete_execution(
            ex.execution_id,
        )
        assert ex.status == WorkflowStatus.COMPLETED

    def test_fail_execution(self) -> None:
        et = ExecutionTracker()
        ex = et.start_execution("w1")
        assert et.fail_execution(
            ex.execution_id, "timeout",
        )
        assert ex.status == WorkflowStatus.FAILED

    def test_complete_nonexistent(self) -> None:
        et = ExecutionTracker()
        assert not et.complete_execution("invalid")

    def test_debug_log(self) -> None:
        et = ExecutionTracker()
        ex = et.start_execution("w1")
        et.debug_log(
            ex.execution_id, "test msg",
        )
        assert et.debug_count == 1

    def test_get_history(self) -> None:
        et = ExecutionTracker()
        et.start_execution("w1")
        et.start_execution("w1")
        et.start_execution("w2")
        all_h = et.get_history()
        assert len(all_h) == 3
        w1_h = et.get_history(workflow_id="w1")
        assert len(w1_h) == 2

    def test_get_metrics(self) -> None:
        et = ExecutionTracker()
        e1 = et.start_execution("w1")
        e2 = et.start_execution("w1")
        et.complete_execution(e1.execution_id)
        et.fail_execution(e2.execution_id)
        metrics = et.get_metrics()
        assert metrics["total"] == 2
        assert metrics["completed"] == 1
        assert metrics["failed"] == 1
        assert metrics["success_rate"] == 0.5

    def test_audit_trail(self) -> None:
        et = ExecutionTracker()
        et.start_execution("w1")
        trail = et.get_audit_trail()
        assert len(trail) >= 1
        assert et.audit_count >= 1


# ======= WorkflowOrchestrator =======


class TestWorkflowOrchestrator:
    """WorkflowOrchestrator testleri."""

    def test_init(self) -> None:
        orch = WorkflowOrchestrator()
        assert orch.designer is not None
        assert orch.triggers is not None
        assert orch.actions is not None
        assert orch.running_count == 0

    def test_execute_workflow(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("test")
        orch.designer.add_node(
            wf.workflow_id, "log",
            NodeType.ACTION,
        )
        result = orch.execute_workflow(
            wf.workflow_id,
        )
        assert result["success"]
        assert result["steps_completed"] == 1

    def test_execute_with_input(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("test")
        orch.designer.add_node(
            wf.workflow_id, "log",
            NodeType.ACTION,
        )
        result = orch.execute_workflow(
            wf.workflow_id,
            input_data={"key": "value"},
        )
        assert result["success"]

    def test_execute_nonexistent(self) -> None:
        orch = WorkflowOrchestrator()
        result = orch.execute_workflow("invalid")
        assert not result["success"]

    def test_max_concurrent(self) -> None:
        orch = WorkflowOrchestrator(
            max_concurrent=1,
        )
        wf = orch.designer.create_workflow("test")
        # Manually fill running set
        orch._running.add("fake")
        result = orch.execute_workflow(
            wf.workflow_id,
        )
        assert not result["success"]
        assert result["reason"] == "max_concurrent_reached"

    def test_execute_condition_node(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("test")
        orch.designer.add_node(
            wf.workflow_id, "check",
            NodeType.CONDITION,
            {"expression": "true"},
        )
        result = orch.execute_workflow(
            wf.workflow_id,
        )
        assert result["success"]

    def test_trigger_workflow(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("auto")
        orch.designer.add_node(
            wf.workflow_id, "log",
            NodeType.ACTION,
        )
        orch.triggers.create_trigger(
            wf.workflow_id, TriggerType.EVENT,
            {"event": "deploy"},
        )
        results = orch.trigger_workflow("deploy")
        assert len(results) == 1
        assert results[0]["success"]

    def test_get_analytics(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("test")
        orch.designer.add_node(
            wf.workflow_id, "log",
            NodeType.ACTION,
        )
        orch.execute_workflow(wf.workflow_id)
        analytics = orch.get_analytics()
        assert analytics["total_workflows"] == 1
        assert analytics["total_executions"] == 1
        assert analytics["completed"] == 1

    def test_get_snapshot(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("test")
        orch.designer.add_node(
            wf.workflow_id, "log",
            NodeType.ACTION,
        )
        orch.execute_workflow(wf.workflow_id)
        snap = orch.get_snapshot()
        assert isinstance(snap, WorkflowSnapshot)
        assert snap.total_workflows == 1
        assert snap.completed == 1

    def test_multi_node_workflow(self) -> None:
        orch = WorkflowOrchestrator()
        wf = orch.designer.create_workflow("multi")
        orch.designer.add_node(
            wf.workflow_id, "log",
            NodeType.ACTION,
        )
        orch.designer.add_node(
            wf.workflow_id, "notify",
            NodeType.ACTION,
        )
        orch.designer.add_node(
            wf.workflow_id, "done",
            NodeType.END,
        )
        result = orch.execute_workflow(
            wf.workflow_id,
        )
        assert result["success"]
        assert result["steps_completed"] == 3


# ============ Config ============


class TestWorkflowConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings
        assert hasattr(settings, "workflow_enabled")
        assert hasattr(
            settings, "max_concurrent_workflows",
        )
        assert hasattr(
            settings, "workflow_default_timeout",
        )
        assert hasattr(
            settings, "max_loop_iterations",
        )
        assert hasattr(
            settings, "execution_history_days",
        )

    def test_config_values(self) -> None:
        from app.config import settings
        assert settings.workflow_enabled is True
        assert settings.max_concurrent_workflows == 10
        assert settings.workflow_default_timeout == 3600
        assert settings.max_loop_iterations == 1000
        assert settings.execution_history_days == 30


# ============ Imports ============


class TestWorkflowImports:
    """Import testleri."""

    def test_import_all(self) -> None:
        from app.core.workflow import (
            ActionExecutor,
            ConditionEvaluator,
            ExecutionTracker,
            LoopController,
            TriggerManager,
            VariableManager,
            WorkflowDesigner,
            WorkflowErrorHandler,
            WorkflowOrchestrator,
        )
        assert ActionExecutor is not None
        assert ConditionEvaluator is not None
        assert ExecutionTracker is not None
        assert LoopController is not None
        assert TriggerManager is not None
        assert VariableManager is not None
        assert WorkflowDesigner is not None
        assert WorkflowErrorHandler is not None
        assert WorkflowOrchestrator is not None

    def test_import_models(self) -> None:
        from app.models.workflow_engine import (
            ActionType,
            ExecutionRecord,
            LoopType,
            NodeType,
            TriggerRecord,
            TriggerType,
            VariableScope,
            WorkflowRecord,
            WorkflowSnapshot,
            WorkflowStatus,
        )
        assert NodeType is not None
        assert TriggerType is not None
        assert WorkflowStatus is not None
        assert ActionType is not None
        assert VariableScope is not None
        assert LoopType is not None
        assert WorkflowRecord is not None
        assert ExecutionRecord is not None
        assert TriggerRecord is not None
        assert WorkflowSnapshot is not None
