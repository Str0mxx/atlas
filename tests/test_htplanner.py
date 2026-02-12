"""HTNPlanner testleri.

Hierarchical Task Network: gorev kaydi, metot kaydi,
on kosul kontrolu, ayristirma, planlama ve dogrulama.
"""

import pytest

from app.core.planning.htplanner import HTNPlanner
from app.models.planning import (
    HTNMethod,
    HTNMethodStatus,
    HTNTask,
    HTNTaskType,
)


# === Yardimci fonksiyonlar ===


def _make_planner() -> HTNPlanner:
    """Bos HTNPlanner olusturur."""
    return HTNPlanner()


def _primitive(
    name: str,
    preconditions: dict | None = None,
    effects: dict | None = None,
    duration: float = 10.0,
    agent: str | None = None,
) -> HTNTask:
    """Primitive gorev olusturur."""
    return HTNTask(
        name=name,
        task_type=HTNTaskType.PRIMITIVE,
        preconditions=preconditions or {},
        effects=effects or {},
        duration_estimate=duration,
        agent=agent,
    )


def _compound(name: str) -> HTNTask:
    """Compound gorev olusturur."""
    return HTNTask(name=name, task_type=HTNTaskType.COMPOUND)


def _method(
    name: str,
    task_name: str,
    subtasks: list[str],
    preconditions: dict | None = None,
    preference: float = 0.5,
) -> HTNMethod:
    """Metot olusturur."""
    return HTNMethod(
        name=name,
        task_name=task_name,
        subtasks=subtasks,
        preconditions=preconditions or {},
        preference=preference,
    )


# === Init Testleri ===


class TestHTNPlannerInit:
    """HTNPlanner initialization testleri."""

    def test_default(self) -> None:
        p = _make_planner()
        assert p.tasks == {}
        assert p.methods == {}
        assert p.world_state == {}
        assert p.max_decomposition_depth == 20

    def test_custom_depth(self) -> None:
        p = HTNPlanner(max_decomposition_depth=5)
        assert p.max_decomposition_depth == 5


# === register_task Testleri ===


class TestHTNPlannerRegisterTask:
    """register_task testleri."""

    def test_register_primitive(self) -> None:
        p = _make_planner()
        task = _primitive("pick_up")
        p.register_task(task)
        assert "pick_up" in p.tasks
        assert p.tasks["pick_up"].task_type == HTNTaskType.PRIMITIVE

    def test_register_compound(self) -> None:
        p = _make_planner()
        task = _compound("deliver")
        p.register_task(task)
        assert "deliver" in p.tasks


# === register_method Testleri ===


class TestHTNPlannerRegisterMethod:
    """register_method testleri."""

    def test_register(self) -> None:
        p = _make_planner()
        m = _method("m1", "deliver", ["pick_up", "move", "drop"])
        p.register_method(m)
        assert "deliver" in p.methods
        assert len(p.methods["deliver"]) == 1

    def test_preference_ordering(self) -> None:
        p = _make_planner()
        m_low = _method("low", "deliver", ["a"], preference=0.3)
        m_high = _method("high", "deliver", ["b"], preference=0.9)
        p.register_method(m_low)
        p.register_method(m_high)
        assert p.methods["deliver"][0].name == "high"
        assert p.methods["deliver"][1].name == "low"


# === world_state Testleri ===


class TestHTNPlannerWorldState:
    """World state testleri."""

    def test_set_world_state(self) -> None:
        p = _make_planner()
        p.set_world_state({"location": "A", "has_package": False})
        assert p.world_state == {"location": "A", "has_package": False}

    def test_update_world_state(self) -> None:
        p = _make_planner()
        p.set_world_state({"location": "A"})
        p.update_world_state({"has_package": True})
        assert p.world_state == {"location": "A", "has_package": True}


# === check_preconditions Testleri ===


class TestHTNPlannerPreconditions:
    """check_preconditions testleri."""

    def test_empty_preconditions(self) -> None:
        p = _make_planner()
        assert p.check_preconditions({}) is True

    def test_met(self) -> None:
        p = _make_planner()
        p.set_world_state({"location": "A"})
        assert p.check_preconditions({"location": "A"}) is True

    def test_not_met(self) -> None:
        p = _make_planner()
        p.set_world_state({"location": "A"})
        assert p.check_preconditions({"location": "B"}) is False

    def test_missing_key(self) -> None:
        p = _make_planner()
        assert p.check_preconditions({"location": "A"}) is False


# === plan Testleri ===


class TestHTNPlannerPlan:
    """plan testleri."""

    async def test_single_primitive(self) -> None:
        p = _make_planner()
        task = _primitive("do_thing", effects={"done": True}, duration=5.0)
        p.register_task(task)
        plan = await p.plan("do_thing")
        assert plan.feasible is True
        assert len(plan.ordered_tasks) == 1
        assert plan.total_duration == 5.0

    async def test_primitive_precondition_fail(self) -> None:
        p = _make_planner()
        task = _primitive("locked", preconditions={"has_key": True})
        p.register_task(task)
        plan = await p.plan("locked")
        assert plan.feasible is False
        assert len(plan.ordered_tasks) == 0

    async def test_primitive_precondition_pass(self) -> None:
        p = _make_planner()
        task = _primitive("unlock", preconditions={"has_key": True}, effects={"unlocked": True})
        p.register_task(task)
        p.set_world_state({"has_key": True})
        plan = await p.plan("unlock")
        assert plan.feasible is True
        assert len(plan.ordered_tasks) == 1

    async def test_compound_decomposition(self) -> None:
        p = _make_planner()
        p.register_task(_compound("deliver"))
        p.register_task(_primitive("pick_up", effects={"has_package": True}, duration=10.0))
        p.register_task(
            _primitive(
                "drop_off",
                preconditions={"has_package": True},
                effects={"delivered": True},
                duration=5.0,
            )
        )
        p.register_method(_method("m1", "deliver", ["pick_up", "drop_off"]))

        plan = await p.plan("deliver")
        assert plan.feasible is True
        assert len(plan.ordered_tasks) == 2
        assert plan.ordered_tasks[0].name == "pick_up"
        assert plan.ordered_tasks[1].name == "drop_off"
        assert plan.total_duration == 15.0
        assert "m1" in plan.method_chain

    async def test_method_backtracking(self) -> None:
        p = _make_planner()
        p.register_task(_compound("travel"))
        p.register_task(
            _primitive("fly", preconditions={"has_ticket": True}, effects={"at_dest": True})
        )
        p.register_task(
            _primitive("drive", effects={"at_dest": True})
        )
        # fly metodu baskinda (precondition fail edecek)
        p.register_method(_method("fly_method", "travel", ["fly"], preference=0.9))
        p.register_method(_method("drive_method", "travel", ["drive"], preference=0.5))

        plan = await p.plan("travel")
        assert plan.feasible is True
        assert plan.ordered_tasks[0].name == "drive"

    async def test_no_methods(self) -> None:
        p = _make_planner()
        p.register_task(_compound("orphan"))
        plan = await p.plan("orphan")
        assert plan.feasible is False

    async def test_unknown_task(self) -> None:
        p = _make_planner()
        plan = await p.plan("nonexistent")
        assert plan.feasible is False

    async def test_max_depth(self) -> None:
        p = HTNPlanner(max_decomposition_depth=2)
        # Sonsuz dongu: A -> B -> A
        p.register_task(_compound("A"))
        p.register_task(_compound("B"))
        p.register_method(_method("m1", "A", ["B"]))
        p.register_method(_method("m2", "B", ["A"]))
        plan = await p.plan("A")
        assert plan.feasible is False

    async def test_effects_propagate(self) -> None:
        p = _make_planner()
        p.register_task(_compound("workflow"))
        p.register_task(_primitive("step1", effects={"step1_done": True}))
        p.register_task(
            _primitive("step2", preconditions={"step1_done": True}, effects={"step2_done": True})
        )
        p.register_method(_method("wf_method", "workflow", ["step1", "step2"]))

        plan = await p.plan("workflow")
        assert plan.feasible is True
        assert len(plan.ordered_tasks) == 2

    async def test_nested_compound(self) -> None:
        p = _make_planner()
        p.register_task(_compound("main"))
        p.register_task(_compound("sub"))
        p.register_task(_primitive("leaf1", effects={"a": True}, duration=1.0))
        p.register_task(
            _primitive("leaf2", preconditions={"a": True}, duration=2.0)
        )
        p.register_method(_method("sub_m", "sub", ["leaf1", "leaf2"]))
        p.register_method(_method("main_m", "main", ["sub"]))

        plan = await p.plan("main")
        assert plan.feasible is True
        assert len(plan.ordered_tasks) == 2
        assert plan.total_duration == 3.0


# === validate_plan Testleri ===


class TestHTNPlannerValidate:
    """validate_plan testleri."""

    async def test_valid_plan(self) -> None:
        p = _make_planner()
        p.register_task(_primitive("a", effects={"done": True}))
        plan = await p.plan("a")
        errors = await p.validate_plan(plan)
        assert errors == []

    async def test_empty_plan(self) -> None:
        p = _make_planner()
        plan = await p.plan("nonexistent")
        errors = await p.validate_plan(plan)
        assert len(errors) == 1
        assert "bos" in errors[0]

    async def test_invalid_precondition_in_plan(self) -> None:
        p = _make_planner()
        t1 = _primitive("step1", preconditions={"ready": True})
        p.register_task(t1)
        # Zorla plan olustur (precondition fail edecek dogrulama sirasinda)
        from app.models.planning import HTNPlan
        fake_plan = HTNPlan(
            task_name="test",
            ordered_tasks=[t1],
        )
        errors = await p.validate_plan(fake_plan)
        assert len(errors) >= 1


# === get_applicable_methods Testleri ===


class TestHTNPlannerApplicableMethods:
    """get_applicable_methods testleri."""

    def test_all_applicable(self) -> None:
        p = _make_planner()
        m = _method("m1", "deliver", ["a"])
        p.register_method(m)
        result = p.get_applicable_methods("deliver")
        assert len(result) == 1

    def test_precondition_filter(self) -> None:
        p = _make_planner()
        m = _method("m1", "deliver", ["a"], preconditions={"has_key": True})
        p.register_method(m)
        result = p.get_applicable_methods("deliver")
        assert len(result) == 0

    def test_no_methods(self) -> None:
        p = _make_planner()
        result = p.get_applicable_methods("unknown")
        assert result == []
