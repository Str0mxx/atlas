"""Planlama modelleri testleri.

GoalNode, HTNTask, TemporalConstraint, ContingencyPlanDef,
Resource, Strategy ve ilgili modellerin testleri.
"""

from datetime import datetime, timezone

from app.models.planning import (
    AllocationStatus,
    ConstraintType,
    ContingencyActivation,
    ContingencyPlanDef,
    GoalNode,
    GoalNodeStatus,
    GoalTreeSnapshot,
    GoalType,
    HTNMethod,
    HTNMethodStatus,
    HTNPlan,
    HTNTask,
    HTNTaskType,
    OptimizationResult,
    Resource,
    ResourceAllocation,
    ResourceConflict,
    ResourceType,
    Scenario,
    ScenarioLikelihood,
    ScheduleEntry,
    ScheduleResult,
    Strategy,
    StrategyEvaluation,
    StrategyType,
    TemporalConstraint,
    TriggerCondition,
    TriggerType,
)


# === GoalType Enum Testleri ===


class TestGoalType:
    """GoalType enum testleri."""

    def test_values(self) -> None:
        assert GoalType.AND == "and"
        assert GoalType.OR == "or"
        assert GoalType.LEAF == "leaf"

    def test_membership(self) -> None:
        assert GoalType("and") is GoalType.AND
        assert GoalType("or") is GoalType.OR
        assert GoalType("leaf") is GoalType.LEAF


class TestGoalNodeStatus:
    """GoalNodeStatus enum testleri."""

    def test_values(self) -> None:
        assert GoalNodeStatus.PENDING == "pending"
        assert GoalNodeStatus.IN_PROGRESS == "in_progress"
        assert GoalNodeStatus.COMPLETED == "completed"
        assert GoalNodeStatus.FAILED == "failed"
        assert GoalNodeStatus.BLOCKED == "blocked"


class TestHTNTaskType:
    """HTNTaskType enum testleri."""

    def test_values(self) -> None:
        assert HTNTaskType.PRIMITIVE == "primitive"
        assert HTNTaskType.COMPOUND == "compound"


class TestHTNMethodStatus:
    """HTNMethodStatus enum testleri."""

    def test_values(self) -> None:
        assert HTNMethodStatus.APPLICABLE == "applicable"
        assert HTNMethodStatus.COMPLETED == "completed"
        assert HTNMethodStatus.FAILED == "failed"
        assert HTNMethodStatus.EXECUTING == "executing"
        assert HTNMethodStatus.NOT_APPLICABLE == "not_applicable"


class TestConstraintType:
    """ConstraintType enum testleri."""

    def test_values(self) -> None:
        assert ConstraintType.DEADLINE == "deadline"
        assert ConstraintType.START_AFTER == "start_after"
        assert ConstraintType.FINISH_BEFORE == "finish_before"
        assert ConstraintType.DURATION_MAX == "duration_max"
        assert ConstraintType.DEPENDENCY == "dependency"


class TestTriggerType:
    """TriggerType enum testleri."""

    def test_values(self) -> None:
        assert TriggerType.THRESHOLD == "threshold"
        assert TriggerType.TIMEOUT == "timeout"
        assert TriggerType.FAILURE_COUNT == "failure_count"
        assert TriggerType.EXTERNAL_EVENT == "external_event"
        assert TriggerType.CONDITION == "condition"


class TestResourceType:
    """ResourceType enum testleri."""

    def test_values(self) -> None:
        assert ResourceType.CPU == "cpu"
        assert ResourceType.MEMORY == "memory"
        assert ResourceType.BUDGET == "budget"
        assert ResourceType.AGENT == "agent"
        assert ResourceType.API_QUOTA == "api_quota"
        assert ResourceType.TIME == "time"
        assert ResourceType.CUSTOM == "custom"


class TestAllocationStatus:
    """AllocationStatus enum testleri."""

    def test_values(self) -> None:
        assert AllocationStatus.ALLOCATED == "allocated"
        assert AllocationStatus.RELEASED == "released"
        assert AllocationStatus.PENDING == "pending"
        assert AllocationStatus.CONFLICT == "conflict"


class TestStrategyType:
    """StrategyType enum testleri."""

    def test_values(self) -> None:
        assert StrategyType.LONG_TERM == "long_term"
        assert StrategyType.SHORT_TERM == "short_term"
        assert StrategyType.ADAPTIVE == "adaptive"
        assert StrategyType.DEFENSIVE == "defensive"
        assert StrategyType.AGGRESSIVE == "aggressive"


class TestScenarioLikelihood:
    """ScenarioLikelihood enum testleri."""

    def test_values(self) -> None:
        assert ScenarioLikelihood.VERY_LIKELY == "very_likely"
        assert ScenarioLikelihood.LIKELY == "likely"
        assert ScenarioLikelihood.POSSIBLE == "possible"
        assert ScenarioLikelihood.UNLIKELY == "unlikely"
        assert ScenarioLikelihood.RARE == "rare"


# === GoalNode Model Testleri ===


class TestGoalNode:
    """GoalNode model testleri."""

    def test_default(self) -> None:
        node = GoalNode(name="test")
        assert node.name == "test"
        assert node.goal_type == GoalType.LEAF
        assert node.status == GoalNodeStatus.PENDING
        assert node.progress == 0.0
        assert node.parent_id is None
        assert node.children_ids == []
        assert node.dependencies == []
        assert node.priority == 0.5
        assert node.id  # uuid olusturulmus olmali

    def test_custom(self) -> None:
        node = GoalNode(
            name="parent",
            goal_type=GoalType.AND,
            priority=0.9,
            description="Parent goal",
            metadata={"key": "val"},
        )
        assert node.goal_type == GoalType.AND
        assert node.priority == 0.9
        assert node.description == "Parent goal"
        assert node.metadata == {"key": "val"}

    def test_unique_ids(self) -> None:
        a = GoalNode(name="a")
        b = GoalNode(name="b")
        assert a.id != b.id


class TestGoalTreeSnapshot:
    """GoalTreeSnapshot model testleri."""

    def test_default(self) -> None:
        snap = GoalTreeSnapshot()
        assert snap.root_id is None
        assert snap.nodes == {}
        assert snap.total_progress == 0.0
        assert snap.timestamp is not None

    def test_with_nodes(self) -> None:
        node = GoalNode(name="root")
        snap = GoalTreeSnapshot(
            root_id=node.id,
            nodes={node.id: node},
            total_progress=0.5,
        )
        assert snap.root_id == node.id
        assert len(snap.nodes) == 1


# === HTN Model Testleri ===


class TestHTNTask:
    """HTNTask model testleri."""

    def test_default(self) -> None:
        task = HTNTask(name="test_task")
        assert task.name == "test_task"
        assert task.task_type == HTNTaskType.PRIMITIVE
        assert task.preconditions == {}
        assert task.effects == {}
        assert task.duration_estimate == 0.0
        assert task.agent is None

    def test_compound(self) -> None:
        task = HTNTask(
            name="compound",
            task_type=HTNTaskType.COMPOUND,
            duration_estimate=120.0,
            agent="research_agent",
        )
        assert task.task_type == HTNTaskType.COMPOUND
        assert task.agent == "research_agent"


class TestHTNMethod:
    """HTNMethod model testleri."""

    def test_default(self) -> None:
        method = HTNMethod(name="m1", task_name="t1")
        assert method.name == "m1"
        assert method.task_name == "t1"
        assert method.preconditions == {}
        assert method.subtasks == []
        assert method.preference == 0.5
        assert method.status == HTNMethodStatus.APPLICABLE

    def test_with_subtasks(self) -> None:
        method = HTNMethod(
            name="m1",
            task_name="t1",
            subtasks=["sub1", "sub2"],
            preference=0.9,
        )
        assert method.subtasks == ["sub1", "sub2"]
        assert method.preference == 0.9


class TestHTNPlan:
    """HTNPlan model testleri."""

    def test_default(self) -> None:
        plan = HTNPlan(task_name="main")
        assert plan.task_name == "main"
        assert plan.ordered_tasks == []
        assert plan.total_duration == 0.0
        assert plan.feasible is True

    def test_with_tasks(self) -> None:
        t1 = HTNTask(name="a", duration_estimate=10.0)
        t2 = HTNTask(name="b", duration_estimate=20.0)
        plan = HTNPlan(
            task_name="main",
            ordered_tasks=[t1, t2],
            total_duration=30.0,
            method_chain=["m1"],
        )
        assert len(plan.ordered_tasks) == 2
        assert plan.total_duration == 30.0


# === Temporal Model Testleri ===


class TestTemporalConstraint:
    """TemporalConstraint model testleri."""

    def test_deadline(self) -> None:
        c = TemporalConstraint(
            constraint_type=ConstraintType.DEADLINE,
            task_id="t1",
            value=3600.0,
        )
        assert c.constraint_type == ConstraintType.DEADLINE
        assert c.hard is True

    def test_dependency(self) -> None:
        c = TemporalConstraint(
            constraint_type=ConstraintType.DEPENDENCY,
            task_id="t2",
            reference_task_id="t1",
            hard=True,
        )
        assert c.reference_task_id == "t1"


class TestScheduleEntry:
    """ScheduleEntry model testleri."""

    def test_default(self) -> None:
        entry = ScheduleEntry(task_id="t1", task_name="task1")
        assert entry.start_time == 0.0
        assert entry.end_time == 0.0
        assert entry.slack == 0.0
        assert entry.on_critical_path is False


class TestScheduleResult:
    """ScheduleResult model testleri."""

    def test_default(self) -> None:
        result = ScheduleResult()
        assert result.entries == []
        assert result.total_duration == 0.0
        assert result.critical_path == []
        assert result.feasible is True
        assert result.constraint_violations == []


# === Contingency Model Testleri ===


class TestTriggerCondition:
    """TriggerCondition model testleri."""

    def test_default(self) -> None:
        trigger = TriggerCondition()
        assert trigger.trigger_type == TriggerType.THRESHOLD
        assert trigger.metric_key == ""
        assert trigger.threshold == 0.0
        assert trigger.operator == "gt"

    def test_custom(self) -> None:
        trigger = TriggerCondition(
            trigger_type=TriggerType.FAILURE_COUNT,
            metric_key="api_errors",
            threshold=5.0,
            operator="gte",
            description="API hata sayisi",
        )
        assert trigger.metric_key == "api_errors"
        assert trigger.threshold == 5.0


class TestContingencyPlanDef:
    """ContingencyPlanDef model testleri."""

    def test_default(self) -> None:
        plan = ContingencyPlanDef(name="Plan B")
        assert plan.name == "Plan B"
        assert plan.priority == 0
        assert plan.actions == []
        assert plan.active is True
        assert plan.success_probability == 0.5

    def test_with_trigger(self) -> None:
        trigger = TriggerCondition(
            metric_key="cpu",
            threshold=90.0,
        )
        plan = ContingencyPlanDef(
            name="Plan B",
            trigger=trigger,
            priority=10,
            actions=[{"type": "restart"}],
            estimated_recovery_time=60.0,
        )
        assert plan.trigger.metric_key == "cpu"
        assert plan.priority == 10


class TestContingencyActivation:
    """ContingencyActivation model testleri."""

    def test_default(self) -> None:
        act = ContingencyActivation(plan_id="p1", plan_name="Plan B")
        assert act.plan_id == "p1"
        assert act.resolved is False
        assert act.resolution_time is None
        assert act.activated_at is not None


# === Resource Model Testleri ===


class TestResource:
    """Resource model testleri."""

    def test_default(self) -> None:
        r = Resource(name="CPU Pool")
        assert r.name == "CPU Pool"
        assert r.resource_type == ResourceType.CUSTOM
        assert r.capacity == 100.0
        assert r.available == 100.0
        assert r.cost_per_unit == 0.0

    def test_custom(self) -> None:
        r = Resource(
            name="Budget",
            resource_type=ResourceType.BUDGET,
            capacity=10000.0,
            available=5000.0,
            unit="USD",
            cost_per_unit=1.0,
        )
        assert r.resource_type == ResourceType.BUDGET
        assert r.available == 5000.0
        assert r.unit == "USD"


class TestResourceAllocation:
    """ResourceAllocation model testleri."""

    def test_default(self) -> None:
        alloc = ResourceAllocation(resource_id="r1", task_id="t1")
        assert alloc.amount == 0.0
        assert alloc.status == AllocationStatus.PENDING
        assert alloc.released_at is None

    def test_allocated(self) -> None:
        alloc = ResourceAllocation(
            resource_id="r1",
            task_id="t1",
            amount=50.0,
            status=AllocationStatus.ALLOCATED,
        )
        assert alloc.amount == 50.0
        assert alloc.status == AllocationStatus.ALLOCATED


class TestResourceConflict:
    """ResourceConflict model testleri."""

    def test_default(self) -> None:
        conflict = ResourceConflict(resource_id="r1")
        assert conflict.competing_tasks == []
        assert conflict.resolution == ""


class TestOptimizationResult:
    """OptimizationResult model testleri."""

    def test_default(self) -> None:
        result = OptimizationResult()
        assert result.allocations == []
        assert result.total_cost == 0.0
        assert result.feasible is True
        assert result.conflicts == []


# === Strategy Model Testleri ===


class TestScenario:
    """Scenario model testleri."""

    def test_default(self) -> None:
        s = Scenario(name="Base case")
        assert s.name == "Base case"
        assert s.likelihood == ScenarioLikelihood.POSSIBLE
        assert s.probability == 0.5
        assert s.conditions == {}
        assert s.impact == {}

    def test_custom(self) -> None:
        s = Scenario(
            name="Market crash",
            likelihood=ScenarioLikelihood.UNLIKELY,
            probability=0.2,
            impact={"revenue": -0.5},
            recommended_actions=["cost_cut"],
        )
        assert s.probability == 0.2
        assert s.impact["revenue"] == -0.5


class TestStrategy:
    """Strategy model testleri."""

    def test_default(self) -> None:
        s = Strategy(name="Growth")
        assert s.name == "Growth"
        assert s.strategy_type == StrategyType.ADAPTIVE
        assert s.time_horizon == 30
        assert s.confidence == 0.5
        assert s.active is True

    def test_custom(self) -> None:
        s = Strategy(
            name="Defense",
            strategy_type=StrategyType.DEFENSIVE,
            goals=["reduce_cost"],
            kpis={"cost": 1000.0},
            time_horizon=90,
            confidence=0.8,
        )
        assert s.strategy_type == StrategyType.DEFENSIVE
        assert s.kpis == {"cost": 1000.0}

    def test_unique_ids(self) -> None:
        a = Strategy(name="a")
        b = Strategy(name="b")
        assert a.id != b.id


class TestStrategyEvaluation:
    """StrategyEvaluation model testleri."""

    def test_default(self) -> None:
        ev = StrategyEvaluation(strategy_id="s1")
        assert ev.score == 0.0
        assert ev.kpi_scores == {}
        assert ev.strengths == []
        assert ev.weaknesses == []
        assert ev.recommendation == ""

    def test_with_scores(self) -> None:
        ev = StrategyEvaluation(
            strategy_id="s1",
            score=0.85,
            kpi_scores={"revenue": 0.9, "cost": 0.8},
            strengths=["Revenue on target"],
            recommendation="Continue",
        )
        assert ev.score == 0.85
        assert len(ev.kpi_scores) == 2
