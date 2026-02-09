"""BDI Agent unit testleri.

BDIAgent sinifinin Sense-Plan-Act dongusu, otonom calisma,
kayit islemleri, taahhut stratejileri ve raporlama
fonksiyonlarini test eder.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base_agent import BaseAgent, TaskResult
from app.core.autonomy.bdi_agent import BDIAgent
from app.core.decision_matrix import DecisionMatrix
from app.models.autonomy import (
    BeliefUpdate,
    CommitmentStrategy,
    Desire,
    GoalPriority,
    GoalStatus,
    Intention,
    Plan,
    PlanStatus,
    PlanStep,
)


# === Yardimci Fonksiyonlar ===


def _make_mock_agent(name: str = "test_agent") -> MagicMock:
    """Test icin sahte agent olusturur.

    Args:
        name: Agent adi.

    Returns:
        Mock agent nesnesi.
    """
    agent = MagicMock(spec=BaseAgent)
    agent.name = name
    agent.run = AsyncMock(return_value=TaskResult(success=True, message="ok"))
    return agent


def _make_plan(
    name: str = "test_plan",
    goal_name: str = "test_goal",
    steps: list[PlanStep] | None = None,
) -> Plan:
    """Test icin plan olusturur.

    Args:
        name: Plan adi.
        goal_name: Hedef adi.
        steps: Plan adimlari.

    Returns:
        Plan nesnesi.
    """
    if steps is None:
        steps = [PlanStep(description="step1", target_agent="test_agent", order=0)]
    return Plan(name=name, goal_name=goal_name, steps=steps, success_rate=0.8)


def _make_desire(
    name: str = "test_goal",
    priority: GoalPriority = GoalPriority.HIGH,
) -> Desire:
    """Test icin desire/hedef olusturur.

    Args:
        name: Hedef adi.
        priority: Hedef onceligi.

    Returns:
        Desire nesnesi.
    """
    return Desire(name=name, priority=priority)


# === Init Testleri ===


class TestBDIAgentInit:
    """BDIAgent ilk olusturma testleri."""

    def test_default_init(self) -> None:
        """Varsayilan parametrelerle BDIAgent olusturmayi dogrular."""
        bdi = BDIAgent()
        assert bdi.name == "BDIAgent"
        assert bdi.beliefs is not None
        assert bdi.desires is not None
        assert bdi.intentions is not None
        assert bdi._cycle_count == 0
        assert bdi._running is False

    def test_custom_params(self) -> None:
        """Ozel parametrelerle BDIAgent olusturmayi dogrular."""
        dm = DecisionMatrix()
        bdi = BDIAgent(
            decision_matrix=dm,
            commitment_strategy=CommitmentStrategy.OPEN_MINDED,
            cycle_interval=30,
        )
        assert bdi.decision_matrix is dm
        assert bdi.commitment_strategy == CommitmentStrategy.OPEN_MINDED
        assert bdi.cycle_interval == 30

    def test_inherits_base_agent(self) -> None:
        """BDIAgent'in BaseAgent'dan miras aldigini dogrular."""
        bdi = BDIAgent()
        assert isinstance(bdi, BaseAgent)


# === Execute Testleri ===


class TestBDIAgentExecute:
    """BDIAgent execute metodu testleri."""

    async def test_full_cycle_success(self) -> None:
        """Tam Sense-Plan-Act dongusunun basarili sonuclanmasini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        agent = _make_mock_agent()

        bdi.adopt_goal(desire)
        bdi.register_plan(plan)
        bdi.register_agent(agent)

        result = await bdi.execute({"description": "test task"})
        assert result.success is True

    async def test_no_goal(self) -> None:
        """Hedef yokken execute'un no_goal ile basarili donmesini dogrular."""
        bdi = BDIAgent()
        result = await bdi.execute({"description": "no goal task"})
        assert result.success is True
        assert "no_goal" in str(result.data)

    async def test_no_plan(self) -> None:
        """Hedef var ama plan yokken execute'un basarisiz donmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        bdi.adopt_goal(desire)

        result = await bdi.execute({"description": "no plan task"})
        assert result.success is False

    async def test_step_failure(self) -> None:
        """Agent adimi basarisiz oldugunda TaskResult.success=False dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        agent = _make_mock_agent()
        agent.run = AsyncMock(
            return_value=TaskResult(success=False, message="fail"),
        )

        bdi.adopt_goal(desire)
        bdi.register_plan(plan)
        bdi.register_agent(agent)

        result = await bdi.execute({"description": "failing task"})
        assert result.success is False

    async def test_with_belief_updates(self) -> None:
        """Task icerisinde belief guncellemelerinin uygulanmasini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        agent = _make_mock_agent()

        bdi.adopt_goal(desire)
        bdi.register_plan(plan)
        bdi.register_agent(agent)

        task = {
            "description": "task with beliefs",
            "beliefs": [{"key": "k", "value": "v"}],
        }
        await bdi.execute(task)

        belief = bdi.beliefs.get("k")
        assert belief is not None
        assert belief.value == "v"


# === Sense Testleri ===


class TestBDIAgentSense:
    """BDIAgent _sense asamasi testleri."""

    async def test_sense_decay(self) -> None:
        """Sense asamasinda belief decay'in cagrildigini dogrular."""
        from datetime import datetime, timedelta, timezone

        bdi = BDIAgent()
        # Cok eski bir belief ekle (yuksek decay_rate ile kesinlikle silinecek)
        from app.models.autonomy import Belief, BeliefSource, BeliefCategory

        old_belief = Belief(
            key="old_key",
            value="old_value",
            confidence=0.15,
            decay_rate=0.5,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=24),
        )
        bdi.beliefs.beliefs["old_key"] = old_belief

        await bdi._sense({"description": "test"})

        # Decay sonrasi dusuk confidence'li eski belief silinmis olmali
        assert bdi.beliefs.get("old_key") is None

    async def test_sense_belief_updates(self) -> None:
        """Sense asamasinda task.beliefs guncellemelerinin uygulanmasini dogrular."""
        bdi = BDIAgent()
        task = {
            "description": "test",
            "beliefs": [{"key": "sensor:temp", "value": 42}],
        }
        await bdi._sense(task)

        belief = bdi.beliefs.get("sensor:temp")
        assert belief is not None
        assert belief.value == 42

    async def test_sense_monitor_data(self) -> None:
        """Sense asamasinda monitor verisinin belief'lere donusmesini dogrular."""
        bdi = BDIAgent()
        task = {
            "description": "monitor result",
            "monitor_name": "server",
            "risk": "high",
            "urgency": "medium",
            "details": [{"cpu_usage": 95}],
        }
        await bdi._sense(task)

        risk_belief = bdi.beliefs.get("server:risk")
        assert risk_belief is not None
        assert risk_belief.value == "high"


# === Deliberate Testleri ===


class TestBDIAgentDeliberate:
    """BDIAgent _deliberate asamasi testleri."""

    async def test_specific_goal_name(self) -> None:
        """Task'ta belirtilen goal_name ile eslesen hedefin secilmesini dogrular."""
        bdi = BDIAgent()
        d1 = _make_desire(name="fix", priority=GoalPriority.LOW)
        d2 = _make_desire(name="optimize", priority=GoalPriority.HIGH)
        bdi.adopt_goal(d1)
        bdi.adopt_goal(d2)

        result = await bdi._deliberate({"goal_name": "fix"})
        assert result is not None
        assert result.name == "fix"

    async def test_highest_priority(self) -> None:
        """Birden fazla hedef varken en yuksek onceliklinin secilmesini dogrular."""
        bdi = BDIAgent()
        low = _make_desire(name="low_goal", priority=GoalPriority.LOW)
        low.priority_score = 0.3
        high = _make_desire(name="high_goal", priority=GoalPriority.CRITICAL)
        high.priority_score = 0.9
        bdi.adopt_goal(low)
        bdi.adopt_goal(high)

        result = await bdi._deliberate({"description": "pick best"})
        assert result is not None
        assert result.name == "high_goal"

    async def test_no_achievable(self) -> None:
        """On kosullari saglanmayan hedeflerle None donmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire(name="guarded")
        desire.preconditions = {"required_key": "required_value"}
        bdi.adopt_goal(desire)

        result = await bdi._deliberate({"description": "no match"})
        assert result is None


# === Means-Ends Testleri ===


class TestBDIAgentMeansEnds:
    """BDIAgent _means_ends asamasi testleri."""

    async def test_new_plan_selected(self) -> None:
        """Yeni intention olusturulup plan secilmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        bdi.adopt_goal(desire)
        bdi.register_plan(plan)

        intention = await bdi._means_ends(desire)
        assert intention is not None
        assert intention.status == PlanStatus.EXECUTING

    async def test_existing_intention_reused(self) -> None:
        """Mevcut EXECUTING intention'in yeniden kullanilmasini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        bdi.adopt_goal(desire)
        bdi.register_plan(plan)

        # Ilk means-ends: intention olusturulur
        first = await bdi._means_ends(desire)
        assert first is not None

        # Ikinci means-ends: ayni intention donmeli
        second = await bdi._means_ends(desire)
        assert second is not None
        assert second.id == first.id

    async def test_no_plan_available(self) -> None:
        """Uygun plan yokken None donmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire(name="unplanned")
        bdi.adopt_goal(desire)

        intention = await bdi._means_ends(desire)
        assert intention is None


# === Act Testleri ===


class TestBDIAgentAct:
    """BDIAgent _act asamasi testleri."""

    async def test_step_runs_agent(self) -> None:
        """Plan adiminin hedef agent uzerinden calistirilmasini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        agent = _make_mock_agent()
        bdi.adopt_goal(desire)
        bdi.register_plan(plan)
        bdi.register_agent(agent)

        intention = await bdi._means_ends(desire)
        assert intention is not None

        result = await bdi._act(intention)
        agent.run.assert_called_once()
        assert result.success is True

    async def test_all_steps_done(self) -> None:
        """Tum adimlar tamamlandiginda hedefin achieve edilmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        plan = _make_plan()
        agent = _make_mock_agent()
        bdi.adopt_goal(desire)
        bdi.register_plan(plan)
        bdi.register_agent(agent)

        intention = await bdi._means_ends(desire)
        assert intention is not None

        # Ilk adimi calistir (basarili)
        await bdi._act(intention)

        # Simdi tum adimlar tamamlanmis olmali, tekrar act "completed" donmeli
        result = await bdi._act(intention)
        assert result.success is True
        assert result.data.get("status") == "completed"

    async def test_agent_not_found(self) -> None:
        """Hedef agent bulunamayinca basarisiz sonuc donmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        # Plan'da target_agent="unknown" olacak (kayitli degil)
        plan = _make_plan(
            steps=[PlanStep(description="step1", target_agent="unknown", order=0)],
        )
        bdi.adopt_goal(desire)
        bdi.register_plan(plan)

        intention = await bdi._means_ends(desire)
        assert intention is not None

        result = await bdi._act(intention)
        assert result.success is False


# === Cycle Testleri ===


class TestBDIAgentCycle:
    """BDI otonom dongu testleri."""

    async def test_start_stop(self) -> None:
        """start_cycle ve stop_cycle'in running durumunu degistirmesini dogrular."""
        bdi = BDIAgent(cycle_interval=1)
        assert bdi.is_running is False

        await bdi.start_cycle()
        assert bdi.is_running is True

        await bdi.stop_cycle()
        assert bdi.is_running is False

    async def test_start_twice(self) -> None:
        """Ikinci start_cycle cagrisinin islem yapmadan donmesini dogrular."""
        bdi = BDIAgent(cycle_interval=1)
        await bdi.start_cycle()
        first_task = bdi._cycle_task

        await bdi.start_cycle()
        assert bdi._cycle_task is first_task  # Ayni task, degismemis

        await bdi.stop_cycle()

    async def test_cycle_increments_count(self) -> None:
        """Dongu calistiktan sonra _cycle_count'un artmasini dogrular."""
        bdi = BDIAgent(cycle_interval=0)
        assert bdi._cycle_count == 0

        await bdi.start_cycle()
        # Kisa bir sure bekle ki en az bir dongu tamamlansin
        await asyncio.sleep(0.1)
        await bdi.stop_cycle()

        assert bdi._cycle_count > 0


# === Commitment Strategy Testleri ===


class TestCommitmentStrategies:
    """Taahhut stratejisi davranislari testleri."""

    def test_blind_never_reconsiders(self) -> None:
        """BLIND stratejisinin hicbir durumda yeniden degerlendirmemesini dogrular."""
        bdi = BDIAgent()
        intention = Intention(
            desire_id="d1",
            plan_id="p1",
            commitment=CommitmentStrategy.BLIND,
            status=PlanStatus.FAILED,
        )
        assert bdi._should_reconsider(intention) is False

    def test_single_minded_on_failure(self) -> None:
        """SINGLE_MINDED stratejisinin sadece FAILED'da True donmesini dogrular."""
        bdi = BDIAgent()

        executing = Intention(
            desire_id="d1",
            plan_id="p1",
            commitment=CommitmentStrategy.SINGLE_MINDED,
            status=PlanStatus.EXECUTING,
        )
        assert bdi._should_reconsider(executing) is False

        failed = Intention(
            desire_id="d1",
            plan_id="p1",
            commitment=CommitmentStrategy.SINGLE_MINDED,
            status=PlanStatus.FAILED,
        )
        assert bdi._should_reconsider(failed) is True

    def test_open_minded_always(self) -> None:
        """OPEN_MINDED stratejisinin her zaman True donmesini dogrular."""
        bdi = BDIAgent()
        intention = Intention(
            desire_id="d1",
            plan_id="p1",
            commitment=CommitmentStrategy.OPEN_MINDED,
            status=PlanStatus.EXECUTING,
        )
        assert bdi._should_reconsider(intention) is True


# === Registration Testleri ===


class TestBDIAgentRegistration:
    """BDIAgent kayit islemleri testleri."""

    def test_register_agent(self) -> None:
        """Agent'in self.agents'a kaydedilmesini dogrular."""
        bdi = BDIAgent()
        agent = _make_mock_agent("my_agent")
        bdi.register_agent(agent)
        assert "my_agent" in bdi.agents
        assert bdi.agents["my_agent"] is agent

    def test_register_plan(self) -> None:
        """Plan'in plan kutuphanesine kaydedilmesini dogrular."""
        bdi = BDIAgent()
        plan = _make_plan()
        bdi.register_plan(plan)
        assert plan.id in bdi.intentions.plan_library

    def test_adopt_goal(self) -> None:
        """Desire'in desires sozlugune kaydedilmesini dogrular."""
        bdi = BDIAgent()
        desire = _make_desire()
        bdi.adopt_goal(desire)
        assert desire.id in bdi.desires.desires


# === Info Testleri ===


class TestBDIAgentInfo:
    """BDIAgent bilgi metodlari testleri."""

    def test_get_info(self) -> None:
        """get_info'nun gerekli alanlari icermesini dogrular."""
        bdi = BDIAgent()
        info = bdi.get_info()
        assert "beliefs_count" in info
        assert "active_desires" in info
        assert "active_intentions" in info
        assert "cycle_count" in info
        assert "cycle_running" in info
        assert "commitment_strategy" in info
        assert "registered_agents" in info
        assert "plan_library_size" in info

    async def test_analyze(self) -> None:
        """analyze'in snapshot sozlugu dondurmesini dogrular."""
        bdi = BDIAgent()
        result = await bdi.analyze({})
        assert "beliefs_count" in result
        assert "active_desires" in result
        assert "active_intentions" in result
        assert "cycle_count" in result
        assert "beliefs_snapshot" in result
        assert "desires_snapshot" in result
        assert "intentions_snapshot" in result


# === Report Testleri ===


class TestBDIAgentReport:
    """BDIAgent raporlama testleri."""

    async def test_report_format(self) -> None:
        """Report metninin [BDI] ve BASARILI/BASARISIZ icermesini dogrular."""
        bdi = BDIAgent()

        success_result = TaskResult(success=True, message="completed")
        report = await bdi.report(success_result)
        assert "[BDI]" in report
        assert "BASARILI" in report

        fail_result = TaskResult(success=False, message="error occurred")
        report = await bdi.report(fail_result)
        assert "[BDI]" in report
        assert "BASARISIZ" in report
