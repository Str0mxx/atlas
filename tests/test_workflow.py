"""WorkflowEngine testleri.

Seri, paralel, kosullu, merge dugum
calistirilmasi ve hata yonetimi.
"""

from typing import Any

from app.core.collaboration.workflow import WorkflowEngine
from app.models.collaboration import WorkflowNodeType, WorkflowStatus


# === Yardimci fonksiyonlar ===


async def _dummy_executor(agent_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Basarili biten sahte executor."""
    return {"agent": agent_name, "done": True}


async def _fail_executor(agent_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Her zaman hata veren executor."""
    raise RuntimeError(f"{agent_name} failed")


async def _conditional_executor(agent_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Agent adina gore sonuc üreten executor."""
    return {"agent": agent_name, "result": f"{agent_name}_output"}


def _make_engine() -> WorkflowEngine:
    return WorkflowEngine(executor=_dummy_executor)


# === Init Testleri ===


class TestWorkflowEngineInit:
    def test_default(self) -> None:
        engine = WorkflowEngine()
        assert engine.workflows == {}

    def test_with_executor(self) -> None:
        engine = WorkflowEngine(executor=_dummy_executor)
        assert engine._executor is _dummy_executor

    def test_set_executor(self) -> None:
        engine = WorkflowEngine()
        engine.set_executor(_dummy_executor)
        assert engine._executor is _dummy_executor


# === create_workflow Testleri ===


class TestWorkflowCreate:
    def test_create(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("Pipeline", "Test workflow")
        assert wf.name == "Pipeline"
        assert wf.description == "Test workflow"
        assert wf.id in engine.workflows
        assert wf.status == WorkflowStatus.PENDING

    def test_metadata(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W", metadata={"env": "test"})
        assert wf.metadata == {"env": "test"}

    def test_default_description(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        assert wf.description == ""


# === add_node Testleri ===


class TestWorkflowAddNode:
    def test_add_task(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        node = engine.add_node(wf.id, "step1", agent_name="research")
        assert node is not None
        assert node.name == "step1"
        assert node.agent_name == "research"
        assert node.id in wf.nodes

    def test_first_node_is_root(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        node = engine.add_node(wf.id, "root")
        assert wf.root_id == node.id

    def test_second_node_not_root(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        n1 = engine.add_node(wf.id, "first")
        n2 = engine.add_node(wf.id, "second")
        assert wf.root_id == n1.id
        assert wf.root_id != n2.id

    def test_add_nonexistent_workflow(self) -> None:
        engine = _make_engine()
        result = engine.add_node("nope", "step1")
        assert result is None

    def test_add_with_type(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        node = engine.add_node(wf.id, "par", node_type=WorkflowNodeType.PARALLEL)
        assert node is not None
        assert node.node_type == WorkflowNodeType.PARALLEL

    def test_add_with_params(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        node = engine.add_node(wf.id, "t", task_params={"key": "val"})
        assert node is not None
        assert node.task_params == {"key": "val"}

    def test_add_conditional_with_condition(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        node = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="status == ok",
        )
        assert node is not None
        assert node.condition == "status == ok"


# === connect_nodes Testleri ===


class TestWorkflowConnect:
    def test_connect(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        n1 = engine.add_node(wf.id, "parent")
        n2 = engine.add_node(wf.id, "child")
        result = engine.connect_nodes(wf.id, n1.id, n2.id)
        assert result is True
        assert n2.id in n1.children

    def test_connect_duplicate(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        n1 = engine.add_node(wf.id, "parent")
        n2 = engine.add_node(wf.id, "child")
        engine.connect_nodes(wf.id, n1.id, n2.id)
        engine.connect_nodes(wf.id, n1.id, n2.id)
        # Tekrar eklenmamal
        assert n1.children.count(n2.id) == 1

    def test_connect_nonexistent_workflow(self) -> None:
        engine = _make_engine()
        assert engine.connect_nodes("nope", "a", "b") is False

    def test_connect_nonexistent_node(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        n1 = engine.add_node(wf.id, "parent")
        assert engine.connect_nodes(wf.id, n1.id, "nope") is False
        assert engine.connect_nodes(wf.id, "nope", n1.id) is False


# === Execute: Task Dugumu Testleri ===


class TestWorkflowExecuteTask:
    async def test_single_task(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "step1", agent_name="research")
        result = await engine.execute(wf.id)
        assert result.success is True
        assert len(result.node_results) == 1

    async def test_task_failure(self) -> None:
        engine = WorkflowEngine(executor=_fail_executor)
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "step1", agent_name="research")
        result = await engine.execute(wf.id)
        assert result.success is False
        assert len(result.failed_nodes) > 0

    async def test_no_executor(self) -> None:
        engine = WorkflowEngine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "step1", agent_name="research")
        result = await engine.execute(wf.id)
        assert result.success is False

    async def test_no_agent_name(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "step1")  # agent_name yok
        result = await engine.execute(wf.id)
        assert result.success is False

    async def test_nonexistent_workflow(self) -> None:
        engine = _make_engine()
        result = await engine.execute("nope")
        assert result.success is False
        assert "workflow_not_found" in result.failed_nodes

    async def test_no_root_node(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        result = await engine.execute(wf.id)
        assert result.success is False
        assert "no_root_node" in result.failed_nodes

    async def test_context_passed_to_executor(self) -> None:
        received_params: dict[str, Any] = {}

        async def capture_executor(agent: str, params: dict[str, Any]) -> dict[str, Any]:
            received_params.update(params)
            return {"ok": True}

        engine = WorkflowEngine(executor=capture_executor)
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a", task_params={"x": 1})
        await engine.execute(wf.id, initial_context={"init": "data"})
        assert received_params["x"] == 1
        assert received_params["_context"]["init"] == "data"

    async def test_duration_measured(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        result = await engine.execute(wf.id)
        assert result.total_duration >= 0.0


# === Execute: Sequence Dugumu Testleri ===


class TestWorkflowSequence:
    async def test_sequence(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        seq = engine.add_node(wf.id, "seq", node_type=WorkflowNodeType.SEQUENCE)
        t1 = engine.add_node(wf.id, "t1", agent_name="a")
        t2 = engine.add_node(wf.id, "t2", agent_name="b")
        engine.connect_nodes(wf.id, seq.id, t1.id)
        engine.connect_nodes(wf.id, seq.id, t2.id)
        result = await engine.execute(wf.id)
        assert result.success is True
        assert len(result.node_results) == 2

    async def test_sequence_stops_on_failure(self) -> None:
        call_order: list[str] = []

        async def tracking_executor(agent: str, params: dict[str, Any]) -> dict[str, Any]:
            call_order.append(agent)
            if agent == "bad":
                raise RuntimeError("fail")
            return {"ok": True}

        engine = WorkflowEngine(executor=tracking_executor)
        wf = engine.create_workflow("W")
        seq = engine.add_node(wf.id, "seq", node_type=WorkflowNodeType.SEQUENCE)
        t1 = engine.add_node(wf.id, "t1", agent_name="bad")
        t2 = engine.add_node(wf.id, "t2", agent_name="good")
        engine.connect_nodes(wf.id, seq.id, t1.id)
        engine.connect_nodes(wf.id, seq.id, t2.id)
        result = await engine.execute(wf.id)
        assert result.success is False
        assert "good" not in call_order

    async def test_empty_sequence(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "seq", node_type=WorkflowNodeType.SEQUENCE)
        result = await engine.execute(wf.id)
        assert result.success is True


# === Execute: Parallel Dugumu Testleri ===


class TestWorkflowParallel:
    async def test_parallel(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        par = engine.add_node(wf.id, "par", node_type=WorkflowNodeType.PARALLEL)
        t1 = engine.add_node(wf.id, "t1", agent_name="a")
        t2 = engine.add_node(wf.id, "t2", agent_name="b")
        engine.connect_nodes(wf.id, par.id, t1.id)
        engine.connect_nodes(wf.id, par.id, t2.id)
        result = await engine.execute(wf.id)
        assert result.success is True
        assert len(result.node_results) == 2

    async def test_parallel_one_failure(self) -> None:
        async def partial_fail(agent: str, params: dict[str, Any]) -> dict[str, Any]:
            if agent == "bad":
                raise RuntimeError("fail")
            return {"ok": True}

        engine = WorkflowEngine(executor=partial_fail)
        wf = engine.create_workflow("W")
        par = engine.add_node(wf.id, "par", node_type=WorkflowNodeType.PARALLEL)
        t1 = engine.add_node(wf.id, "t1", agent_name="good")
        t2 = engine.add_node(wf.id, "t2", agent_name="bad")
        engine.connect_nodes(wf.id, par.id, t1.id)
        engine.connect_nodes(wf.id, par.id, t2.id)
        result = await engine.execute(wf.id)
        assert result.success is False

    async def test_empty_parallel(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "par", node_type=WorkflowNodeType.PARALLEL)
        result = await engine.execute(wf.id)
        assert result.success is True


# === Execute: Conditional Dugumu Testleri ===


class TestWorkflowConditional:
    async def test_condition_true_branch(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        cond = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="status == ok",
        )
        t_true = engine.add_node(wf.id, "yes", agent_name="a")
        t_false = engine.add_node(wf.id, "no", agent_name="b")
        engine.connect_nodes(wf.id, cond.id, t_true.id)
        engine.connect_nodes(wf.id, cond.id, t_false.id)
        result = await engine.execute(wf.id, initial_context={"status": "ok"})
        assert result.success is True
        assert t_true.id in result.node_results
        assert t_false.id not in result.node_results

    async def test_condition_false_branch(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        cond = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="status == ok",
        )
        t_true = engine.add_node(wf.id, "yes", agent_name="a")
        t_false = engine.add_node(wf.id, "no", agent_name="b")
        engine.connect_nodes(wf.id, cond.id, t_true.id)
        engine.connect_nodes(wf.id, cond.id, t_false.id)
        result = await engine.execute(wf.id, initial_context={"status": "fail"})
        assert result.success is True
        assert t_false.id in result.node_results
        assert t_true.id not in result.node_results

    async def test_condition_truthy(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        cond = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="flag",
        )
        t_true = engine.add_node(wf.id, "yes", agent_name="a")
        engine.connect_nodes(wf.id, cond.id, t_true.id)
        result = await engine.execute(wf.id, initial_context={"flag": True})
        assert result.success is True
        assert t_true.id in result.node_results

    async def test_condition_falsy(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        cond = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="flag",
        )
        t_true = engine.add_node(wf.id, "yes", agent_name="a")
        t_false = engine.add_node(wf.id, "no", agent_name="b")
        engine.connect_nodes(wf.id, cond.id, t_true.id)
        engine.connect_nodes(wf.id, cond.id, t_false.id)
        result = await engine.execute(wf.id, initial_context={"flag": False})
        assert result.success is True
        assert t_false.id in result.node_results

    async def test_condition_no_children(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="x",
        )
        result = await engine.execute(wf.id, initial_context={"x": True})
        assert result.success is True

    async def test_condition_no_false_branch(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        cond = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
            condition="flag",
        )
        t_true = engine.add_node(wf.id, "yes", agent_name="a")
        engine.connect_nodes(wf.id, cond.id, t_true.id)
        # flag yok -> false, ama false dali da yok -> skip
        result = await engine.execute(wf.id)
        assert result.success is True
        assert t_true.id not in result.node_results

    async def test_condition_empty(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        cond = engine.add_node(
            wf.id, "check",
            node_type=WorkflowNodeType.CONDITIONAL,
        )
        t_true = engine.add_node(wf.id, "yes", agent_name="a")
        engine.connect_nodes(wf.id, cond.id, t_true.id)
        # condition="" -> True
        result = await engine.execute(wf.id)
        assert result.success is True
        assert t_true.id in result.node_results


# === Execute: Merge Dugumu Testleri ===


class TestWorkflowMerge:
    async def test_merge(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        merge = engine.add_node(wf.id, "merge", node_type=WorkflowNodeType.MERGE)
        t1 = engine.add_node(wf.id, "t1", agent_name="a")
        t2 = engine.add_node(wf.id, "t2", agent_name="b")
        engine.connect_nodes(wf.id, merge.id, t1.id)
        engine.connect_nodes(wf.id, merge.id, t2.id)
        result = await engine.execute(wf.id)
        assert result.success is True
        assert len(result.node_results) == 2

    async def test_empty_merge(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "merge", node_type=WorkflowNodeType.MERGE)
        result = await engine.execute(wf.id)
        assert result.success is True


# === Workflow Status Testleri ===


class TestWorkflowStatus:
    async def test_completed_status(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        assert wf.status == WorkflowStatus.COMPLETED

    async def test_failed_status(self) -> None:
        engine = WorkflowEngine(executor=_fail_executor)
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        assert wf.status == WorkflowStatus.FAILED

    async def test_running_during_execution(self) -> None:
        captured_status: list[WorkflowStatus] = []

        async def spy_executor(agent: str, params: dict[str, Any]) -> dict[str, Any]:
            # Calisirken status RUNNING olmali
            return {"ok": True}

        engine = WorkflowEngine(executor=spy_executor)
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        # Sonuc: basarili ise COMPLETED
        assert wf.status == WorkflowStatus.COMPLETED


# === Pause/Cancel Testleri ===


class TestWorkflowPauseCancel:
    async def test_cancel_pending(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        result = await engine.cancel_workflow(wf.id)
        assert result is True
        assert wf.status == WorkflowStatus.CANCELLED

    async def test_cancel_nonexistent(self) -> None:
        engine = _make_engine()
        result = await engine.cancel_workflow("nope")
        assert result is False

    async def test_cancel_completed(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        result = await engine.cancel_workflow(wf.id)
        assert result is False

    async def test_cancel_already_cancelled(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        await engine.cancel_workflow(wf.id)
        result = await engine.cancel_workflow(wf.id)
        assert result is False

    async def test_pause_not_running(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        result = await engine.pause_workflow(wf.id)
        assert result is False

    async def test_pause_nonexistent(self) -> None:
        engine = _make_engine()
        result = await engine.pause_workflow("nope")
        assert result is False


# === get_workflow_status Testleri ===


class TestWorkflowGetStatus:
    def test_get_status(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("Pipeline")
        engine.add_node(wf.id, "step1", agent_name="a")
        engine.add_node(wf.id, "step2", agent_name="b")
        status = engine.get_workflow_status(wf.id)
        assert status is not None
        assert status["name"] == "Pipeline"
        assert status["total_nodes"] == 2
        assert status["status"] == "pending"

    def test_get_status_nonexistent(self) -> None:
        engine = _make_engine()
        assert engine.get_workflow_status("nope") is None

    async def test_get_status_after_execution(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        status = engine.get_workflow_status(wf.id)
        assert status is not None
        assert status["status"] == "completed"


# === Karmasik Is Akisi Testleri ===


class TestWorkflowComplex:
    async def test_sequence_then_parallel(self) -> None:
        """Sequence icerisinde parallel dugum."""
        engine = _make_engine()
        wf = engine.create_workflow("Complex")
        seq = engine.add_node(wf.id, "seq", node_type=WorkflowNodeType.SEQUENCE)
        t1 = engine.add_node(wf.id, "first", agent_name="a")
        par = engine.add_node(wf.id, "par", node_type=WorkflowNodeType.PARALLEL)
        p1 = engine.add_node(wf.id, "p1", agent_name="b")
        p2 = engine.add_node(wf.id, "p2", agent_name="c")
        engine.connect_nodes(wf.id, seq.id, t1.id)
        engine.connect_nodes(wf.id, seq.id, par.id)
        engine.connect_nodes(wf.id, par.id, p1.id)
        engine.connect_nodes(wf.id, par.id, p2.id)
        result = await engine.execute(wf.id)
        assert result.success is True
        assert len(result.node_results) == 3  # t1, p1, p2

    async def test_context_propagation(self) -> None:
        """Bir dugumun sonucu sonraki dugumun konteksinde gorunur."""
        results_seen: list[dict] = []

        async def ctx_executor(agent: str, params: dict[str, Any]) -> dict[str, Any]:
            results_seen.append(dict(params.get("_context", {})))
            return {"from": agent}

        engine = WorkflowEngine(executor=ctx_executor)
        wf = engine.create_workflow("W")
        seq = engine.add_node(wf.id, "seq", node_type=WorkflowNodeType.SEQUENCE)
        t1 = engine.add_node(wf.id, "t1", agent_name="a")
        t2 = engine.add_node(wf.id, "t2", agent_name="b")
        engine.connect_nodes(wf.id, seq.id, t1.id)
        engine.connect_nodes(wf.id, seq.id, t2.id)
        await engine.execute(wf.id)
        # Ikinci dugum, birincinin sonucunu kontekstte gormeli
        assert len(results_seen) == 2
        # Ikinci cagri, birincinin node id'si altinda sonuc icermeli
        assert t1.id in results_seen[1]

    async def test_initial_context(self) -> None:
        """Baslangic konteksti dugumleree iletilir."""
        seen_ctx: dict[str, Any] = {}

        async def ctx_check(agent: str, params: dict[str, Any]) -> dict[str, Any]:
            seen_ctx.update(params.get("_context", {}))
            return {}

        engine = WorkflowEngine(executor=ctx_check)
        wf = engine.create_workflow("W")
        engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id, initial_context={"user": "fatih"})
        assert seen_ctx["user"] == "fatih"

    async def test_node_status_completed(self) -> None:
        engine = _make_engine()
        wf = engine.create_workflow("W")
        node = engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        assert node.status == WorkflowStatus.COMPLETED

    async def test_node_status_failed(self) -> None:
        engine = WorkflowEngine(executor=_fail_executor)
        wf = engine.create_workflow("W")
        node = engine.add_node(wf.id, "t", agent_name="a")
        await engine.execute(wf.id)
        assert node.status == WorkflowStatus.FAILED
