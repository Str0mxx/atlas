"""TemporalPlanner testleri.

Zamansal planlama: CPM, kritik yol, PERT tahmin,
kisit kontrolu ve zamanlama testleri.
"""

import pytest

from app.core.planning.temporal import TemporalPlanner
from app.models.planning import ConstraintType, TemporalConstraint


# === Yardimci fonksiyonlar ===


def _make_planner() -> TemporalPlanner:
    """Bos TemporalPlanner olusturur."""
    return TemporalPlanner()


def _linear_pipeline() -> TemporalPlanner:
    """A(10) -> B(20) -> C(5) seri pipeline olusturur."""
    p = _make_planner()
    p.add_task("A", "Task A", 10.0)
    p.add_task("B", "Task B", 20.0, predecessors=["A"])
    p.add_task("C", "Task C", 5.0, predecessors=["B"])
    return p


def _parallel_pipeline() -> TemporalPlanner:
    """
    A(10) -+-> C(5)
    B(20) -+
    Paralel pipeline.
    """
    p = _make_planner()
    p.add_task("A", "Task A", 10.0)
    p.add_task("B", "Task B", 20.0)
    p.add_task("C", "Task C", 5.0, predecessors=["A", "B"])
    return p


# === Init Testleri ===


class TestTemporalPlannerInit:
    """TemporalPlanner initialization testleri."""

    def test_default(self) -> None:
        p = _make_planner()
        assert p.tasks == {}
        assert p.constraints == []
        assert p.dependencies == {}


# === add_task Testleri ===


class TestTemporalPlannerAddTask:
    """add_task testleri."""

    def test_simple_task(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        assert "t1" in p.tasks
        assert p.tasks["t1"]["duration"] == 10.0

    def test_with_predecessors(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_task("t2", "Task 2", 5.0, predecessors=["t1"])
        assert p.dependencies["t2"] == ["t1"]

    def test_no_predecessors(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        assert p.dependencies.get("t1", []) == []


# === add_constraint Testleri ===


class TestTemporalPlannerAddConstraint:
    """add_constraint testleri."""

    def test_deadline_constraint(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        c = TemporalConstraint(
            constraint_type=ConstraintType.DEADLINE,
            task_id="t1",
            value=15.0,
        )
        p.add_constraint(c)
        assert len(p.constraints) == 1

    def test_dependency_constraint_adds_dep(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_task("t2", "Task 2", 5.0)
        c = TemporalConstraint(
            constraint_type=ConstraintType.DEPENDENCY,
            task_id="t2",
            reference_task_id="t1",
        )
        p.add_constraint(c)
        assert "t1" in p.dependencies.get("t2", [])

    def test_no_duplicate_dependency(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_task("t2", "Task 2", 5.0, predecessors=["t1"])
        c = TemporalConstraint(
            constraint_type=ConstraintType.DEPENDENCY,
            task_id="t2",
            reference_task_id="t1",
        )
        p.add_constraint(c)
        assert p.dependencies["t2"].count("t1") == 1


# === schedule Testleri ===


class TestTemporalPlannerSchedule:
    """schedule testleri."""

    async def test_empty(self) -> None:
        p = _make_planner()
        result = await p.schedule()
        assert result.feasible is True
        assert result.entries == []

    async def test_single_task(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        result = await p.schedule()
        assert result.feasible is True
        assert len(result.entries) == 1
        assert result.total_duration == 10.0
        entry = result.entries[0]
        assert entry.start_time == 0.0
        assert entry.end_time == 10.0
        assert entry.on_critical_path is True

    async def test_linear_pipeline(self) -> None:
        p = _linear_pipeline()
        result = await p.schedule()
        assert result.feasible is True
        assert result.total_duration == 35.0  # 10 + 20 + 5
        assert len(result.critical_path) == 3
        # Tum gorevler kritik yolda
        for entry in result.entries:
            assert entry.on_critical_path is True
            assert entry.slack == 0.0

    async def test_parallel_pipeline(self) -> None:
        p = _parallel_pipeline()
        result = await p.schedule()
        assert result.feasible is True
        assert result.total_duration == 25.0  # max(10, 20) + 5

        # B ve C kritik yolda, A degil
        entries = {e.task_id: e for e in result.entries}
        assert entries["B"].on_critical_path is True
        assert entries["C"].on_critical_path is True
        assert entries["A"].on_critical_path is False
        assert entries["A"].slack == 10.0  # 20 - 10

    async def test_complex_dag(self) -> None:
        """
        A(10) -> C(15) -> E(5)
        B(20) -> D(10) -> E(5)
        """
        p = _make_planner()
        p.add_task("A", "A", 10.0)
        p.add_task("B", "B", 20.0)
        p.add_task("C", "C", 15.0, predecessors=["A"])
        p.add_task("D", "D", 10.0, predecessors=["B"])
        p.add_task("E", "E", 5.0, predecessors=["C", "D"])
        result = await p.schedule()
        assert result.feasible is True
        # Kritik yol: B(20) -> D(10) -> E(5) = 35 veya A(10) -> C(15) -> E(5) = 30
        assert result.total_duration == 35.0

    async def test_cyclic_dependency(self) -> None:
        p = _make_planner()
        p.add_task("A", "A", 10.0, predecessors=["B"])
        p.add_task("B", "B", 10.0, predecessors=["A"])
        result = await p.schedule()
        assert result.feasible is False
        assert len(result.constraint_violations) > 0


# === Constraint Violation Testleri ===


class TestTemporalPlannerConstraints:
    """Kisit ihlali testleri."""

    async def test_deadline_met(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.DEADLINE,
            task_id="t1",
            value=15.0,
        ))
        result = await p.schedule()
        assert result.feasible is True
        assert len(result.constraint_violations) == 0

    async def test_deadline_violated(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.DEADLINE,
            task_id="t1",
            value=5.0,  # Gorev 10 saniye, deadline 5
        ))
        result = await p.schedule()
        assert result.feasible is False
        assert any("Deadline" in v for v in result.constraint_violations)

    async def test_start_after_met(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.START_AFTER,
            task_id="t1",
            value=0.0,
        ))
        result = await p.schedule()
        assert result.feasible is True

    async def test_start_after_violated(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.START_AFTER,
            task_id="t1",
            value=5.0,  # Gorev 0'da basliyor
        ))
        result = await p.schedule()
        assert result.feasible is False

    async def test_finish_before_violated(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.FINISH_BEFORE,
            task_id="t1",
            value=5.0,
        ))
        result = await p.schedule()
        assert result.feasible is False

    async def test_duration_max_violated(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.DURATION_MAX,
            task_id="t1",
            value=5.0,
        ))
        result = await p.schedule()
        assert result.feasible is False

    async def test_duration_max_met(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.DURATION_MAX,
            task_id="t1",
            value=15.0,
        ))
        result = await p.schedule()
        assert result.feasible is True

    async def test_unknown_task_constraint_ignored(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 10.0)
        p.add_constraint(TemporalConstraint(
            constraint_type=ConstraintType.DEADLINE,
            task_id="nonexistent",
            value=5.0,
        ))
        result = await p.schedule()
        assert result.feasible is True


# === estimate_duration Testleri ===


class TestTemporalPlannerPERT:
    """PERT tahmin testleri."""

    async def test_symmetric(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 0.0)
        est = await p.estimate_duration("t1", 10.0, 20.0, 30.0)
        assert est == pytest.approx(20.0)

    async def test_skewed(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 0.0)
        est = await p.estimate_duration("t1", 5.0, 10.0, 30.0)
        # (5 + 40 + 30) / 6 = 12.5
        assert est == pytest.approx(12.5)

    async def test_updates_task(self) -> None:
        p = _make_planner()
        p.add_task("t1", "Task 1", 0.0)
        est = await p.estimate_duration("t1", 10.0, 20.0, 30.0)
        assert p.tasks["t1"]["duration"] == est

    async def test_unknown_task(self) -> None:
        p = _make_planner()
        est = await p.estimate_duration("unknown", 10.0, 20.0, 30.0)
        assert est == pytest.approx(20.0)


# === get_critical_path Testleri ===


class TestTemporalPlannerCriticalPath:
    """Kritik yol testleri."""

    async def test_linear(self) -> None:
        p = _linear_pipeline()
        path = await p.get_critical_path()
        assert path == ["A", "B", "C"]

    async def test_parallel(self) -> None:
        p = _parallel_pipeline()
        path = await p.get_critical_path()
        assert "B" in path
        assert "C" in path
        assert "A" not in path


# === get_total_slack Testleri ===


class TestTemporalPlannerSlack:
    """Bolluk testleri."""

    async def test_critical_path_zero_slack(self) -> None:
        p = _linear_pipeline()
        slack = await p.get_total_slack("A")
        assert slack == 0.0

    async def test_noncritical_has_slack(self) -> None:
        p = _parallel_pipeline()
        slack = await p.get_total_slack("A")
        assert slack is not None
        assert slack == 10.0

    async def test_unknown_task(self) -> None:
        p = _make_planner()
        slack = await p.get_total_slack("nonexistent")
        assert slack is None
