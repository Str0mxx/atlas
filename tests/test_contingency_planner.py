"""ContingencyPlanner testleri.

Olasilik planlamasi: plan kaydi, tetikleyici degerlendirme,
aktivasyon, cozum ve gecmis testleri.
"""

from app.core.planning.contingency import ContingencyPlanner
from app.models.planning import (
    ContingencyPlanDef,
    TriggerCondition,
    TriggerType,
)


# === Yardimci fonksiyonlar ===


def _make_planner() -> ContingencyPlanner:
    """Bos ContingencyPlanner olusturur."""
    return ContingencyPlanner()


def _threshold_plan(
    name: str = "Plan B",
    metric_key: str = "cpu",
    threshold: float = 90.0,
    operator: str = "gt",
    priority: int = 10,
) -> ContingencyPlanDef:
    """Threshold tetikleyicili plan olusturur."""
    return ContingencyPlanDef(
        name=name,
        trigger=TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key=metric_key,
            threshold=threshold,
            operator=operator,
            description=f"{metric_key} {operator} {threshold}",
        ),
        priority=priority,
        actions=[{"type": "alert"}],
        success_probability=0.8,
    )


def _failure_plan(
    name: str = "Plan C",
    metric_key: str = "api_errors",
    threshold: float = 5.0,
    priority: int = 5,
) -> ContingencyPlanDef:
    """Failure count tetikleyicili plan olusturur."""
    return ContingencyPlanDef(
        name=name,
        trigger=TriggerCondition(
            trigger_type=TriggerType.FAILURE_COUNT,
            metric_key=metric_key,
            threshold=threshold,
            operator="gte",
        ),
        priority=priority,
        actions=[{"type": "fallback"}],
    )


# === Init Testleri ===


class TestContingencyPlannerInit:
    """ContingencyPlanner initialization testleri."""

    def test_default(self) -> None:
        cp = _make_planner()
        assert cp.plans == {}
        assert cp.activations == []
        assert cp.active_plan_id is None
        assert cp.metrics == {}
        assert cp.failure_counts == {}


# === register_plan / remove_plan Testleri ===


class TestContingencyPlannerRegistration:
    """Plan kayit ve kaldirma testleri."""

    def test_register(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        assert plan.id in cp.plans

    def test_remove(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        assert cp.remove_plan(plan.id) is True
        assert plan.id not in cp.plans

    def test_remove_nonexistent(self) -> None:
        cp = _make_planner()
        assert cp.remove_plan("nope") is False

    def test_remove_active_clears(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        cp.active_plan_id = plan.id
        cp.remove_plan(plan.id)
        assert cp.active_plan_id is None


# === update_metrics / record_failure Testleri ===


class TestContingencyPlannerMetrics:
    """Metrik ve hata sayaci testleri."""

    def test_update_metrics(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"cpu": 85.0, "memory": 70.0})
        assert cp.metrics["cpu"] == 85.0
        assert cp.metrics["memory"] == 70.0

    def test_record_failure(self) -> None:
        cp = _make_planner()
        assert cp.record_failure("api") == 1
        assert cp.record_failure("api") == 2
        assert cp.record_failure("api") == 3

    def test_reset_failure(self) -> None:
        cp = _make_planner()
        cp.record_failure("api")
        cp.reset_failure("api")
        assert cp.failure_counts.get("api") is None

    def test_reset_nonexistent(self) -> None:
        cp = _make_planner()
        cp.reset_failure("nope")  # Hata vermemeli


# === _evaluate_trigger Testleri ===


class TestContingencyPlannerTrigger:
    """Tetikleyici degerlendirme testleri."""

    def test_threshold_gt_true(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"cpu": 95.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key="cpu",
            threshold=90.0,
            operator="gt",
        )
        assert cp._evaluate_trigger(trigger) is True

    def test_threshold_gt_false(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"cpu": 80.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key="cpu",
            threshold=90.0,
            operator="gt",
        )
        assert cp._evaluate_trigger(trigger) is False

    def test_threshold_lt(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"disk": 5.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key="disk",
            threshold=10.0,
            operator="lt",
        )
        assert cp._evaluate_trigger(trigger) is True

    def test_threshold_eq(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"status": 1.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key="status",
            threshold=1.0,
            operator="eq",
        )
        assert cp._evaluate_trigger(trigger) is True

    def test_threshold_missing_metric(self) -> None:
        cp = _make_planner()
        trigger = TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key="missing",
            threshold=1.0,
        )
        assert cp._evaluate_trigger(trigger) is False

    def test_failure_count_gte(self) -> None:
        cp = _make_planner()
        for _ in range(5):
            cp.record_failure("api")
        trigger = TriggerCondition(
            trigger_type=TriggerType.FAILURE_COUNT,
            metric_key="api",
            threshold=5.0,
            operator="gte",
        )
        assert cp._evaluate_trigger(trigger) is True

    def test_failure_count_below(self) -> None:
        cp = _make_planner()
        cp.record_failure("api")
        trigger = TriggerCondition(
            trigger_type=TriggerType.FAILURE_COUNT,
            metric_key="api",
            threshold=5.0,
            operator="gte",
        )
        assert cp._evaluate_trigger(trigger) is False

    def test_external_event(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"alert_fired": 1.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.EXTERNAL_EVENT,
            metric_key="alert_fired",
        )
        assert cp._evaluate_trigger(trigger) is True

    def test_external_event_not_fired(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"alert_fired": 0.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.EXTERNAL_EVENT,
            metric_key="alert_fired",
        )
        assert cp._evaluate_trigger(trigger) is False

    def test_condition_trigger(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"mode": 2.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.CONDITION,
            metric_key="mode",
            threshold=2.0,
            operator="eq",
        )
        assert cp._evaluate_trigger(trigger) is True

    def test_invalid_operator(self) -> None:
        cp = _make_planner()
        cp.update_metrics({"cpu": 50.0})
        trigger = TriggerCondition(
            trigger_type=TriggerType.THRESHOLD,
            metric_key="cpu",
            threshold=50.0,
            operator="invalid_op",
        )
        assert cp._evaluate_trigger(trigger) is False


# === evaluate Testleri ===


class TestContingencyPlannerEvaluate:
    """evaluate testleri."""

    async def test_no_plans(self) -> None:
        cp = _make_planner()
        result = await cp.evaluate()
        assert result is None

    async def test_no_trigger(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan(threshold=90.0)
        cp.register_plan(plan)
        cp.update_metrics({"cpu": 50.0})
        result = await cp.evaluate()
        assert result is None

    async def test_trigger_fires(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan(threshold=90.0)
        cp.register_plan(plan)
        cp.update_metrics({"cpu": 95.0})
        result = await cp.evaluate()
        assert result is not None
        assert result.plan_id == plan.id
        assert result.plan_name == "Plan B"
        assert cp.active_plan_id == plan.id

    async def test_priority_order(self) -> None:
        cp = _make_planner()
        low = _threshold_plan("Low", "cpu", 90.0, priority=5)
        high = _threshold_plan("High", "cpu", 80.0, priority=10)
        cp.register_plan(low)
        cp.register_plan(high)
        cp.update_metrics({"cpu": 95.0})
        result = await cp.evaluate()
        assert result is not None
        assert result.plan_name == "High"

    async def test_inactive_plan_ignored(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        plan.active = False
        cp.register_plan(plan)
        cp.update_metrics({"cpu": 95.0})
        result = await cp.evaluate()
        assert result is None

    async def test_failure_count_trigger(self) -> None:
        cp = _make_planner()
        plan = _failure_plan(threshold=3.0)
        cp.register_plan(plan)
        for _ in range(3):
            cp.record_failure("api_errors")
        result = await cp.evaluate()
        assert result is not None
        assert result.plan_id == plan.id


# === force_activate Testleri ===


class TestContingencyPlannerForceActivate:
    """force_activate testleri."""

    async def test_force(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        result = await cp.force_activate(plan.id, "Manuel test")
        assert result is not None
        assert result.trigger_reason == "Manuel test"
        assert cp.active_plan_id == plan.id

    async def test_force_nonexistent(self) -> None:
        cp = _make_planner()
        result = await cp.force_activate("nope")
        assert result is None


# === resolve Testleri ===


class TestContingencyPlannerResolve:
    """resolve testleri."""

    async def test_resolve_active(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        cp.update_metrics({"cpu": 95.0})
        await cp.evaluate()
        result = await cp.resolve()
        assert result is True
        assert cp.active_plan_id is None
        assert cp.activations[-1].resolved is True
        assert cp.activations[-1].resolution_time is not None

    async def test_resolve_no_active(self) -> None:
        cp = _make_planner()
        result = await cp.resolve()
        assert result is False

    async def test_resolve_specific(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        await cp.force_activate(plan.id)
        result = await cp.resolve(plan.id)
        assert result is True


# === get_active_plan Testleri ===


class TestContingencyPlannerActivePlan:
    """get_active_plan testleri."""

    def test_no_active(self) -> None:
        cp = _make_planner()
        assert cp.get_active_plan() is None

    async def test_with_active(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        await cp.force_activate(plan.id)
        active = cp.get_active_plan()
        assert active is not None
        assert active.id == plan.id


# === get_activation_history Testleri ===


class TestContingencyPlannerHistory:
    """Aktivasyon gecmisi testleri."""

    async def test_history(self) -> None:
        cp = _make_planner()
        plan = _threshold_plan()
        cp.register_plan(plan)
        await cp.force_activate(plan.id)
        await cp.resolve()
        await cp.force_activate(plan.id)
        history = cp.get_activation_history()
        assert len(history) == 2

    def test_empty_history(self) -> None:
        cp = _make_planner()
        assert cp.get_activation_history() == []


# === get_plans_by_priority Testleri ===


class TestContingencyPlannerPriority:
    """Oncelik siralama testleri."""

    def test_sorted(self) -> None:
        cp = _make_planner()
        low = _threshold_plan("Low", priority=1)
        high = _threshold_plan("High", priority=10)
        mid = _threshold_plan("Mid", priority=5)
        cp.register_plan(low)
        cp.register_plan(high)
        cp.register_plan(mid)
        sorted_plans = cp.get_plans_by_priority()
        assert sorted_plans[0].name == "High"
        assert sorted_plans[1].name == "Mid"
        assert sorted_plans[2].name == "Low"
