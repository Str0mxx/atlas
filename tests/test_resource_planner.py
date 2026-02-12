"""ResourcePlanner testleri.

Kaynak planlamasi: kaynak kaydi, tahsis, serbest birakma,
catisma tespiti ve optimizasyon testleri.
"""

import pytest

from app.core.planning.resource import ResourcePlanner
from app.models.planning import (
    AllocationStatus,
    Resource,
    ResourceAllocation,
    ResourceConflict,
    ResourceType,
)


# === Yardimci fonksiyonlar ===


def _make_planner() -> ResourcePlanner:
    """Bos ResourcePlanner olusturur."""
    return ResourcePlanner()


def _cpu_resource(capacity: float = 100.0) -> Resource:
    """CPU kaynagi olusturur."""
    return Resource(
        name="CPU Pool",
        resource_type=ResourceType.CPU,
        capacity=capacity,
        available=capacity,
        unit="%",
        cost_per_unit=0.1,
    )


def _budget_resource(capacity: float = 10000.0) -> Resource:
    """Butce kaynagi olusturur."""
    return Resource(
        name="Budget",
        resource_type=ResourceType.BUDGET,
        capacity=capacity,
        available=capacity,
        unit="USD",
        cost_per_unit=1.0,
    )


# === Init Testleri ===


class TestResourcePlannerInit:
    """ResourcePlanner initialization testleri."""

    def test_default(self) -> None:
        rp = _make_planner()
        assert rp.resources == {}
        assert rp.allocations == {}
        assert rp.task_requirements == {}


# === register_resource Testleri ===


class TestResourcePlannerRegister:
    """register_resource testleri."""

    def test_register(self) -> None:
        rp = _make_planner()
        res = _cpu_resource()
        rp.register_resource(res)
        assert res.id in rp.resources
        assert rp.resources[res.id].name == "CPU Pool"

    def test_register_multiple(self) -> None:
        rp = _make_planner()
        rp.register_resource(_cpu_resource())
        rp.register_resource(_budget_resource())
        assert len(rp.resources) == 2


# === set_task_requirements Testleri ===


class TestResourcePlannerRequirements:
    """set_task_requirements testleri."""

    def test_set(self) -> None:
        rp = _make_planner()
        res = _cpu_resource()
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 30.0})
        assert rp.task_requirements["t1"][res.id] == 30.0

    def test_overwrite(self) -> None:
        rp = _make_planner()
        res = _cpu_resource()
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 30.0})
        rp.set_task_requirements("t1", {res.id: 50.0})
        assert rp.task_requirements["t1"][res.id] == 50.0


# === allocate Testleri ===


class TestResourcePlannerAllocate:
    """allocate testleri."""

    async def test_allocate_success(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        result = await rp.allocate("t1", res.id, 30.0)
        assert isinstance(result, ResourceAllocation)
        assert result.amount == 30.0
        assert result.status == AllocationStatus.ALLOCATED
        assert rp.resources[res.id].available == 70.0

    async def test_allocate_conflict(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(50.0)
        rp.register_resource(res)
        result = await rp.allocate("t1", res.id, 60.0)
        assert isinstance(result, ResourceConflict)
        assert result.requested == 60.0
        assert result.available == 50.0

    async def test_allocate_unknown_resource(self) -> None:
        rp = _make_planner()
        with pytest.raises(ValueError, match="Kaynak bulunamadi"):
            await rp.allocate("t1", "nope", 10.0)

    async def test_allocate_multiple(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        await rp.allocate("t1", res.id, 30.0)
        await rp.allocate("t2", res.id, 40.0)
        assert rp.resources[res.id].available == 30.0

    async def test_allocate_exact_capacity(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(50.0)
        rp.register_resource(res)
        result = await rp.allocate("t1", res.id, 50.0)
        assert isinstance(result, ResourceAllocation)
        assert rp.resources[res.id].available == 0.0


# === release Testleri ===


class TestResourcePlannerRelease:
    """release testleri."""

    async def test_release(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        alloc = await rp.allocate("t1", res.id, 30.0)
        assert isinstance(alloc, ResourceAllocation)
        result = await rp.release(alloc.id)
        assert result is True
        assert rp.resources[res.id].available == 100.0
        assert rp.allocations[alloc.id].status == AllocationStatus.RELEASED

    async def test_release_nonexistent(self) -> None:
        rp = _make_planner()
        result = await rp.release("nope")
        assert result is False

    async def test_double_release(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        alloc = await rp.allocate("t1", res.id, 30.0)
        assert isinstance(alloc, ResourceAllocation)
        await rp.release(alloc.id)
        result = await rp.release(alloc.id)
        assert result is False

    async def test_release_caps_at_capacity(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        alloc = await rp.allocate("t1", res.id, 30.0)
        assert isinstance(alloc, ResourceAllocation)
        # Kapasiteyi elle azalt
        rp.resources[res.id].capacity = 80.0
        await rp.release(alloc.id)
        assert rp.resources[res.id].available == 80.0  # capacity'yi asmaz


# === release_task_allocations Testleri ===


class TestResourcePlannerReleaseTask:
    """release_task_allocations testleri."""

    async def test_release_all(self) -> None:
        rp = _make_planner()
        cpu = _cpu_resource(100.0)
        budget = _budget_resource(10000.0)
        rp.register_resource(cpu)
        rp.register_resource(budget)
        await rp.allocate("t1", cpu.id, 30.0)
        await rp.allocate("t1", budget.id, 1000.0)
        released = await rp.release_task_allocations("t1")
        assert released == 2
        assert rp.resources[cpu.id].available == 100.0
        assert rp.resources[budget.id].available == 10000.0

    async def test_release_none(self) -> None:
        rp = _make_planner()
        released = await rp.release_task_allocations("nonexistent")
        assert released == 0


# === detect_conflicts Testleri ===


class TestResourcePlannerConflicts:
    """detect_conflicts testleri."""

    def test_no_conflicts(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 30.0})
        conflicts = rp.detect_conflicts()
        assert conflicts == []

    def test_conflict(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(50.0)
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 60.0})
        conflicts = rp.detect_conflicts()
        assert len(conflicts) == 1
        assert conflicts[0].resource_id == res.id
        assert conflicts[0].requested == 60.0

    def test_multiple_conflicts(self) -> None:
        rp = _make_planner()
        cpu = _cpu_resource(50.0)
        budget = _budget_resource(100.0)
        rp.register_resource(cpu)
        rp.register_resource(budget)
        rp.set_task_requirements("t1", {cpu.id: 60.0, budget.id: 200.0})
        conflicts = rp.detect_conflicts()
        assert len(conflicts) == 2


# === optimize Testleri ===


class TestResourcePlannerOptimize:
    """optimize testleri."""

    async def test_feasible(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 30.0})
        rp.set_task_requirements("t2", {res.id: 40.0})
        result = await rp.optimize()
        assert result.feasible is True
        assert len(result.allocations) == 2
        assert result.total_cost > 0

    async def test_infeasible(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(50.0)
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 30.0})
        rp.set_task_requirements("t2", {res.id: 30.0})
        result = await rp.optimize()
        # Biri tahsis edilemez
        assert result.feasible is False
        assert len(result.conflicts) > 0

    async def test_priority_ordering(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(50.0)
        rp.register_resource(res)
        rp.set_task_requirements("low", {res.id: 40.0})
        rp.set_task_requirements("high", {res.id: 40.0})
        result = await rp.optimize(task_priorities={"high": 1.0, "low": 0.1})
        # Yuksek oncelikli gorev tahsis edilmeli
        allocated_tasks = {a.task_id for a in result.allocations}
        assert "high" in allocated_tasks

    async def test_empty(self) -> None:
        rp = _make_planner()
        result = await rp.optimize()
        assert result.feasible is True
        assert result.allocations == []

    async def test_utilization(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 60.0})
        result = await rp.optimize()
        assert result.utilization[res.id] == pytest.approx(0.6)

    async def test_cost_calculation(self) -> None:
        rp = _make_planner()
        res = _budget_resource(10000.0)  # cost_per_unit = 1.0
        rp.register_resource(res)
        rp.set_task_requirements("t1", {res.id: 500.0})
        result = await rp.optimize()
        assert result.total_cost == pytest.approx(500.0)

    async def test_rollback_on_partial_fail(self) -> None:
        rp = _make_planner()
        cpu = _cpu_resource(100.0)
        budget = _budget_resource(50.0)
        rp.register_resource(cpu)
        rp.register_resource(budget)
        # t1 icin cpu OK ama budget FAIL
        rp.set_task_requirements("t1", {cpu.id: 30.0, budget.id: 100.0})
        result = await rp.optimize()
        assert result.feasible is False
        # CPU geri alinmali
        assert result.utilization.get(cpu.id, 0.0) == pytest.approx(0.0)


# === get_utilization Testleri ===


class TestResourcePlannerUtilization:
    """get_utilization testleri."""

    async def test_after_allocations(self) -> None:
        rp = _make_planner()
        res = _cpu_resource(100.0)
        rp.register_resource(res)
        await rp.allocate("t1", res.id, 40.0)
        util = rp.get_utilization()
        assert util[res.id] == pytest.approx(0.4)

    def test_empty(self) -> None:
        rp = _make_planner()
        assert rp.get_utilization() == {}

    def test_zero_capacity(self) -> None:
        rp = _make_planner()
        res = Resource(name="empty", capacity=0.0, available=0.0)
        rp.register_resource(res)
        util = rp.get_utilization()
        assert util[res.id] == 0.0
