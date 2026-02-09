"""IntentionBase testleri.

Plan kaydedilmesi, plan secimi, taahhut, adim ilerleme,
yeniden planlama, iptal ve sorgulama islemlerini test eder.
"""

from unittest.mock import MagicMock

import pytest

from app.agents.base_agent import TaskResult
from app.core.autonomy.intentions import IntentionBase
from app.models.autonomy import (
    CommitmentStrategy,
    Desire,
    GoalPriority,
    Intention,
    Plan,
    PlanStatus,
    PlanStep,
)


# === Yardimci fonksiyonlar ===


def _make_plan(
    name: str = "test_plan",
    goal_name: str = "",
    success_rate: float = 0.5,
    steps: list[PlanStep] | None = None,
    preconditions: dict | None = None,
    plan_id: str | None = None,
) -> Plan:
    """Test icin Plan nesnesi olusturur."""
    kwargs: dict = {
        "name": name,
        "goal_name": goal_name,
        "success_rate": success_rate,
        "steps": steps or [],
        "preconditions": preconditions or {},
    }
    if plan_id is not None:
        kwargs["id"] = plan_id
    return Plan(**kwargs)


def _make_desire(
    name: str = "test_goal",
    priority: GoalPriority = GoalPriority.MEDIUM,
) -> Desire:
    """Test icin Desire nesnesi olusturur."""
    return Desire(name=name, priority=priority)


def _make_steps(count: int = 3) -> list[PlanStep]:
    """Belirtilen sayida PlanStep listesi olusturur."""
    return [
        PlanStep(description=f"step_{i}", order=i)
        for i in range(count)
    ]


# === TestIntentionBaseInit ===


class TestIntentionBaseInit:
    """IntentionBase baslangic durumu testleri."""

    def test_init_empty(self) -> None:
        """Bos baslangic durumunda intentions ve plan_library bos olmalidir."""
        ib = IntentionBase()
        assert ib.intentions == {}
        assert ib.plan_library == {}

    def test_init_types(self) -> None:
        """intentions ve plan_library dogru dict tiplerinde olmalidir."""
        ib = IntentionBase()
        assert isinstance(ib.intentions, dict)
        assert isinstance(ib.plan_library, dict)


# === TestPlanRegistration ===


class TestPlanRegistration:
    """Plan kayit testleri."""

    def test_register_plan(self) -> None:
        """Kaydedilen plan plan_library'de id ile saklanmalidir."""
        ib = IntentionBase()
        plan = _make_plan(name="fix_plan")
        ib.register_plan(plan)
        assert plan.id in ib.plan_library
        assert ib.plan_library[plan.id] is plan

    def test_register_plans_bulk(self) -> None:
        """Toplu plan kaydi calismalidir."""
        ib = IntentionBase()
        plans = [_make_plan(name=f"plan_{i}") for i in range(3)]
        ib.register_plans(plans)
        assert len(ib.plan_library) == 3

    def test_register_overwrites(self) -> None:
        """Ayni ID ile kaydedilen plan oncekinin uzerine yazilmalidir."""
        ib = IntentionBase()
        plan1 = _make_plan(name="original", plan_id="same-id")
        plan2 = _make_plan(name="replacement", plan_id="same-id")
        ib.register_plan(plan1)
        ib.register_plan(plan2)
        assert ib.plan_library["same-id"].name == "replacement"


# === TestPlanSelection ===


class TestPlanSelection:
    """Plan secimi testleri."""

    async def test_select_matching_goal(self) -> None:
        """goal_name='fix_server' olan plan, Desire(name='fix_server') ile eslesmelidir."""
        ib = IntentionBase()
        plan = _make_plan(name="server_fix", goal_name="fix_server")
        ib.register_plan(plan)

        desire = _make_desire(name="fix_server")
        result = await ib.select_plan(desire, beliefs={})

        assert result is not None
        assert result.name == "server_fix"

    async def test_select_best_success_rate(self) -> None:
        """En yuksek success_rate'e sahip plan secilmelidir."""
        ib = IntentionBase()
        low = _make_plan(name="low_rate", goal_name="deploy", success_rate=0.3)
        high = _make_plan(name="high_rate", goal_name="deploy", success_rate=0.9)
        ib.register_plans([low, high])

        desire = _make_desire(name="deploy")
        result = await ib.select_plan(desire, beliefs={})

        assert result is not None
        assert result.name == "high_rate"

    async def test_select_checks_preconditions(self) -> None:
        """On kosullari saglanmayan plan haric tutulmalidir."""
        ib = IntentionBase()
        plan_with_prereq = _make_plan(
            name="needs_ssh",
            goal_name="fix_server",
            preconditions={"ssh_available": True},
            success_rate=0.9,
        )
        plan_no_prereq = _make_plan(
            name="no_prereq",
            goal_name="fix_server",
            success_rate=0.5,
        )
        ib.register_plans([plan_with_prereq, plan_no_prereq])

        desire = _make_desire(name="fix_server")
        # ssh_available saglanamiyor
        result = await ib.select_plan(desire, beliefs={"ssh_available": False})

        assert result is not None
        assert result.name == "no_prereq"

    async def test_select_no_match(self) -> None:
        """Uygun plan yoksa None donmelidir."""
        ib = IntentionBase()
        plan = _make_plan(name="unrelated", goal_name="backup")
        ib.register_plan(plan)

        desire = _make_desire(name="fix_server")
        result = await ib.select_plan(desire, beliefs={})

        assert result is None


# === TestCommit ===


class TestCommit:
    """Taahhut testleri."""

    async def test_commit_creates_intention(self) -> None:
        """Commit sonrasi intention saklanmali ve status EXECUTING olmalidir."""
        ib = IntentionBase()
        plan = _make_plan(name="fix")
        ib.register_plan(plan)
        desire = _make_desire(name="fix")

        intention = await ib.commit(desire, plan)

        assert intention.id in ib.intentions
        assert intention.status == PlanStatus.EXECUTING

    async def test_commit_sets_plan_executing(self) -> None:
        """Commit sonrasi plan status'u EXECUTING olmalidir."""
        ib = IntentionBase()
        plan = _make_plan(name="fix")
        ib.register_plan(plan)
        desire = _make_desire(name="fix")

        await ib.commit(desire, plan)

        assert plan.status == PlanStatus.EXECUTING

    async def test_commit_custom_strategy(self) -> None:
        """Ozel CommitmentStrategy dogru saklanmalidir."""
        ib = IntentionBase()
        plan = _make_plan(name="fix")
        ib.register_plan(plan)
        desire = _make_desire(name="fix")

        intention = await ib.commit(
            desire, plan, commitment=CommitmentStrategy.OPEN_MINDED,
        )

        assert intention.commitment == CommitmentStrategy.OPEN_MINDED


# === TestGetNextStep ===


class TestGetNextStep:
    """Siradaki adim testleri."""

    async def test_first_step(self) -> None:
        """current_step=0 iken ilk adim donmelidir."""
        ib = IntentionBase()
        steps = _make_steps(3)
        plan = _make_plan(name="multi_step", steps=steps)
        ib.register_plan(plan)
        desire = _make_desire()
        intention = await ib.commit(desire, plan)

        step = await ib.get_next_step(intention.id)

        assert step is not None
        assert step.description == "step_0"

    async def test_all_done(self) -> None:
        """Tum adimlar tamamlandiginda None donmelidir."""
        ib = IntentionBase()
        steps = _make_steps(2)
        plan = _make_plan(name="short_plan", steps=steps)
        ib.register_plan(plan)
        desire = _make_desire()
        intention = await ib.commit(desire, plan)

        # Tum adimlari atla
        intention.current_step = len(steps)

        step = await ib.get_next_step(intention.id)
        assert step is None

    async def test_nonexistent_intention(self) -> None:
        """Var olmayan intention icin None donmelidir."""
        ib = IntentionBase()
        step = await ib.get_next_step("nonexistent-id")
        assert step is None


# === TestAdvance ===


class TestAdvance:
    """Adim ilerleme testleri."""

    async def test_success_advances(self) -> None:
        """Basarili sonuc adimi tamamlamali ve current_step'i artirmalidir."""
        ib = IntentionBase()
        steps = _make_steps(3)
        plan = _make_plan(name="advancing", steps=steps)
        ib.register_plan(plan)
        desire = _make_desire()
        intention = await ib.commit(desire, plan)

        result = TaskResult(success=True, message="ok")
        status = await ib.advance(intention.id, result)

        assert intention.current_step == 1
        assert steps[0].completed is True
        assert status == PlanStatus.EXECUTING

    async def test_all_steps_done_succeeds(self) -> None:
        """Son adim tamamlandiginda status SUCCEEDED olmalidir."""
        ib = IntentionBase()
        steps = _make_steps(1)
        plan = _make_plan(name="single_step", steps=steps)
        ib.register_plan(plan)
        desire = _make_desire()
        intention = await ib.commit(desire, plan)

        result = TaskResult(success=True, message="done")
        status = await ib.advance(intention.id, result)

        assert status == PlanStatus.SUCCEEDED
        assert intention.status == PlanStatus.SUCCEEDED

    async def test_failure_increments_retry(self) -> None:
        """Basarisiz sonuc retry_count'u artirmali, max asildiginda FAILED olmalidir."""
        ib = IntentionBase()
        steps = _make_steps(2)
        plan = _make_plan(name="retryable", steps=steps)
        ib.register_plan(plan)
        desire = _make_desire()
        intention = await ib.commit(desire, plan)
        intention.max_retries = 2

        fail_result = TaskResult(success=False, message="hata")

        # Ilk basarisizlik
        await ib.advance(intention.id, fail_result)
        assert intention.retry_count == 1
        assert intention.status == PlanStatus.EXECUTING

        # Ikinci basarisizlik -> max retry asildi
        await ib.advance(intention.id, fail_result)
        assert intention.retry_count == 2
        assert intention.status == PlanStatus.FAILED


# === TestReplan ===


class TestReplan:
    """Yeniden planlama testleri."""

    async def test_replan_finds_alternative(self) -> None:
        """Basarisiz plani disladiktan sonra alternatif plan secilmelidir."""
        ib = IntentionBase()
        plan_a = _make_plan(name="plan_a", goal_name="fix", success_rate=0.8)
        plan_b = _make_plan(name="plan_b", goal_name="fix", success_rate=0.6)
        ib.register_plans([plan_a, plan_b])

        desire = _make_desire(name="fix")
        intention = await ib.commit(desire, plan_a)

        new_plan = await ib.replan(intention.id, desire, beliefs={})

        assert new_plan is not None
        assert new_plan.name == "plan_b"

    async def test_replan_no_alternative(self) -> None:
        """Alternatif plan yoksa None donmelidir."""
        ib = IntentionBase()
        only_plan = _make_plan(name="only_one", goal_name="fix")
        ib.register_plan(only_plan)

        desire = _make_desire(name="fix")
        intention = await ib.commit(desire, only_plan)

        new_plan = await ib.replan(intention.id, desire, beliefs={})
        assert new_plan is None

    async def test_replan_creates_new_intention(self) -> None:
        """Yeniden planlama basarili olursa ayni hedef icin yeni intention olusturulmalidir."""
        ib = IntentionBase()
        plan_a = _make_plan(name="plan_a", goal_name="fix", success_rate=0.8)
        plan_b = _make_plan(name="plan_b", goal_name="fix", success_rate=0.6)
        ib.register_plans([plan_a, plan_b])

        desire = _make_desire(name="fix")
        old_intention = await ib.commit(desire, plan_a)
        old_id = old_intention.id

        await ib.replan(old_id, desire, beliefs={})

        # Eski intention FAILED olmali
        assert ib.intentions[old_id].status == PlanStatus.FAILED

        # Yeni intention olusturulmus olmali
        new_intention = ib.get_intention_for_desire(desire.id)
        assert new_intention is not None
        assert new_intention.id != old_id
        assert new_intention.plan_id == plan_b.id


# === TestAbort ===


class TestAbort:
    """Intention iptal testleri."""

    async def test_abort_existing(self) -> None:
        """Iptal edilen intention ABORTED durumuna gecmeli ve abort_reason eklenmelidir."""
        ib = IntentionBase()
        plan = _make_plan(name="abortable")
        ib.register_plan(plan)
        desire = _make_desire()
        intention = await ib.commit(desire, plan)

        result = await ib.abort(intention.id, reason="kaynak yetersiz")

        assert result is not None
        assert result.status == PlanStatus.ABORTED
        assert result.metadata["abort_reason"] == "kaynak yetersiz"

    async def test_abort_nonexistent(self) -> None:
        """Var olmayan intention icin None donmelidir."""
        ib = IntentionBase()
        result = await ib.abort("nonexistent-id")
        assert result is None


# === TestIntentionQuery ===


class TestIntentionQuery:
    """Intention sorgulama testleri."""

    async def test_get_active_intentions(self) -> None:
        """READY veya EXECUTING durumundaki intention'lar filtrelenmelidir."""
        ib = IntentionBase()
        plan1 = _make_plan(name="plan1")
        plan2 = _make_plan(name="plan2")
        plan3 = _make_plan(name="plan3")
        ib.register_plans([plan1, plan2, plan3])

        d1 = _make_desire(name="d1")
        d2 = _make_desire(name="d2")
        d3 = _make_desire(name="d3")

        i1 = await ib.commit(d1, plan1)  # EXECUTING
        i2 = await ib.commit(d2, plan2)  # EXECUTING
        i3 = await ib.commit(d3, plan3)  # EXECUTING -> ABORTED
        await ib.abort(i3.id, reason="test")

        active = ib.get_active_intentions()

        active_ids = {i.id for i in active}
        assert i1.id in active_ids
        assert i2.id in active_ids
        assert i3.id not in active_ids

    async def test_get_intention_for_desire(self) -> None:
        """Belirli bir hedef icin dogru intention bulunmalidir."""
        ib = IntentionBase()
        plan = _make_plan(name="target_plan")
        ib.register_plan(plan)
        desire = _make_desire(name="target_desire")
        intention = await ib.commit(desire, plan)

        found = ib.get_intention_for_desire(desire.id)

        assert found is not None
        assert found.id == intention.id
        assert found.desire_id == desire.id
