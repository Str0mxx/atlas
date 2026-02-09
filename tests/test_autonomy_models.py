"""BDI otonomi veri modelleri unit testleri.

Belief, Desire, Intention, Plan ve ilgili enum'larin
varsayilan degerleri, ozel degerler ve sinir kosullarini test eder.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.autonomy import (
    Belief,
    BeliefCategory,
    BeliefSource,
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


# === Enum Testleri ===


class TestBeliefSource:
    """BeliefSource enum testleri."""

    def test_values(self) -> None:
        """Tum BeliefSource degerlerini dogrular."""
        assert BeliefSource.MONITOR == "monitor"
        assert BeliefSource.AGENT == "agent"
        assert BeliefSource.USER == "user"
        assert BeliefSource.INFERENCE == "inference"

    def test_count(self) -> None:
        """BeliefSource uye sayisini dogrular."""
        assert len(BeliefSource) == 4


class TestBeliefCategory:
    """BeliefCategory enum testleri."""

    def test_values(self) -> None:
        """Tum BeliefCategory degerlerini dogrular."""
        assert BeliefCategory.SERVER == "server"
        assert BeliefCategory.SECURITY == "security"
        assert BeliefCategory.MARKETING == "marketing"
        assert BeliefCategory.COMMUNICATION == "communication"
        assert BeliefCategory.OPPORTUNITY == "opportunity"
        assert BeliefCategory.SYSTEM == "system"

    def test_count(self) -> None:
        """BeliefCategory uye sayisini dogrular."""
        assert len(BeliefCategory) == 6


class TestGoalStatus:
    """GoalStatus enum testleri."""

    def test_values(self) -> None:
        """Tum GoalStatus degerlerini dogrular."""
        assert GoalStatus.ACTIVE == "active"
        assert GoalStatus.ACHIEVED == "achieved"
        assert GoalStatus.DROPPED == "dropped"
        assert GoalStatus.SUSPENDED == "suspended"
        assert GoalStatus.FAILED == "failed"

    def test_count(self) -> None:
        """GoalStatus uye sayisini dogrular."""
        assert len(GoalStatus) == 5


class TestGoalPriority:
    """GoalPriority enum testleri."""

    def test_values(self) -> None:
        """Tum GoalPriority degerlerini dogrular."""
        assert GoalPriority.CRITICAL == "critical"
        assert GoalPriority.HIGH == "high"
        assert GoalPriority.MEDIUM == "medium"
        assert GoalPriority.LOW == "low"

    def test_count(self) -> None:
        """GoalPriority uye sayisini dogrular."""
        assert len(GoalPriority) == 4


class TestPlanStatus:
    """PlanStatus enum testleri."""

    def test_values(self) -> None:
        """Tum PlanStatus degerlerini dogrular."""
        assert PlanStatus.READY == "ready"
        assert PlanStatus.EXECUTING == "executing"
        assert PlanStatus.SUCCEEDED == "succeeded"
        assert PlanStatus.FAILED == "failed"
        assert PlanStatus.ABORTED == "aborted"

    def test_count(self) -> None:
        """PlanStatus uye sayisini dogrular."""
        assert len(PlanStatus) == 5


class TestCommitmentStrategy:
    """CommitmentStrategy enum testleri."""

    def test_values(self) -> None:
        """Tum CommitmentStrategy degerlerini dogrular."""
        assert CommitmentStrategy.BLIND == "blind"
        assert CommitmentStrategy.SINGLE_MINDED == "single_minded"
        assert CommitmentStrategy.OPEN_MINDED == "open_minded"

    def test_count(self) -> None:
        """CommitmentStrategy uye sayisini dogrular."""
        assert len(CommitmentStrategy) == 3


# === Model Testleri ===


class TestBelief:
    """Belief modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        belief = Belief(key="test:key", value="test_value")
        assert belief.confidence == 1.0
        assert belief.source == BeliefSource.MONITOR
        assert belief.category == BeliefCategory.SYSTEM
        assert belief.decay_rate == 0.1
        assert belief.metadata == {}
        assert belief.id  # UUID otomatik uretilmeli
        assert isinstance(belief.timestamp, datetime)

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        belief = Belief(
            key="server:cpu",
            value=85.5,
            confidence=0.9,
            source=BeliefSource.AGENT,
            category=BeliefCategory.SERVER,
            decay_rate=0.05,
            metadata={"unit": "percent"},
        )
        assert belief.key == "server:cpu"
        assert belief.value == 85.5
        assert belief.confidence == 0.9
        assert belief.source == BeliefSource.AGENT
        assert belief.category == BeliefCategory.SERVER
        assert belief.decay_rate == 0.05
        assert belief.metadata == {"unit": "percent"}

    def test_confidence_lower_bound(self) -> None:
        """Guven skorunun 0'in altina dusmedigini dogrular."""
        belief = Belief(key="test", value="v", confidence=0.0)
        assert belief.confidence == 0.0
        with pytest.raises(ValidationError):
            Belief(key="test", value="v", confidence=-0.1)

    def test_confidence_upper_bound(self) -> None:
        """Guven skorunun 1'i asmamasi dogrulanir."""
        belief = Belief(key="test", value="v", confidence=1.0)
        assert belief.confidence == 1.0
        with pytest.raises(ValidationError):
            Belief(key="test", value="v", confidence=1.1)


class TestBeliefUpdate:
    """BeliefUpdate modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        update = BeliefUpdate(key="test:key", value=42)
        assert update.confidence == 1.0
        assert update.source == BeliefSource.MONITOR

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        update = BeliefUpdate(
            key="security:threat",
            value="brute_force",
            confidence=0.85,
            source=BeliefSource.AGENT,
        )
        assert update.key == "security:threat"
        assert update.value == "brute_force"
        assert update.confidence == 0.85
        assert update.source == BeliefSource.AGENT


class TestDesire:
    """Desire modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        desire = Desire(name="test_goal")
        assert desire.priority == GoalPriority.MEDIUM
        assert desire.priority_score == 0.5
        assert desire.status == GoalStatus.ACTIVE
        assert desire.parent_id is None
        assert desire.sub_goal_ids == []
        assert desire.preconditions == {}
        assert desire.success_conditions == {}
        assert desire.deadline is None
        assert desire.description == ""
        assert desire.metadata == {}
        assert desire.id  # UUID otomatik uretilmeli

    def test_hierarchy(self) -> None:
        """Ust ve alt hedef iliskisinin dogru kuruldigini dogrular."""
        parent = Desire(name="parent_goal")
        child = Desire(
            name="child_goal",
            parent_id=parent.id,
        )
        parent_updated = Desire(
            id=parent.id,
            name="parent_goal",
            sub_goal_ids=[child.id],
        )
        assert child.parent_id == parent.id
        assert child.id in parent_updated.sub_goal_ids

    def test_deadline(self) -> None:
        """Son teslim zamani ile Desire olusturmayi dogrular."""
        deadline = datetime(2026, 12, 31, tzinfo=timezone.utc)
        desire = Desire(
            name="deadline_goal",
            deadline=deadline,
            priority=GoalPriority.HIGH,
            priority_score=0.8,
        )
        assert desire.deadline == deadline
        assert desire.priority == GoalPriority.HIGH
        assert desire.priority_score == 0.8


class TestPlanStep:
    """PlanStep modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        step = PlanStep(description="Sunucu durumunu kontrol et")
        assert step.description == "Sunucu durumunu kontrol et"
        assert step.target_agent is None
        assert step.task_params == {}
        assert step.order == 0
        assert step.completed is False

    def test_custom_with_target_agent(self) -> None:
        """Hedef agent ile PlanStep olusturmayi dogrular."""
        step = PlanStep(
            description="Guvenlik tarasi yap",
            target_agent="security_agent",
            task_params={"scan_type": "full", "depth": 3},
            order=1,
            completed=True,
        )
        assert step.target_agent == "security_agent"
        assert step.task_params["scan_type"] == "full"
        assert step.task_params["depth"] == 3
        assert step.order == 1
        assert step.completed is True


class TestPlan:
    """Plan modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        plan = Plan(name="test_plan")
        assert plan.status == PlanStatus.READY
        assert plan.success_rate == 0.5
        assert plan.steps == []
        assert plan.preconditions == {}
        assert plan.description == ""
        assert plan.goal_name == ""
        assert plan.metadata == {}
        assert plan.id  # UUID otomatik uretilmeli

    def test_steps_list(self) -> None:
        """Birden fazla adimli plan olusturmayi dogrular."""
        steps = [
            PlanStep(description="Adim 1", order=0),
            PlanStep(description="Adim 2", order=1, target_agent="security_agent"),
            PlanStep(description="Adim 3", order=2),
        ]
        plan = Plan(
            name="multi_step_plan",
            steps=steps,
        )
        assert len(plan.steps) == 3
        assert plan.steps[0].description == "Adim 1"
        assert plan.steps[1].target_agent == "security_agent"
        assert plan.steps[2].order == 2

    def test_preconditions(self) -> None:
        """On kosullu plan olusturmayi dogrular."""
        plan = Plan(
            name="conditional_plan",
            preconditions={
                "server:status": "online",
                "security:threat_level": "low",
            },
            success_rate=0.85,
        )
        assert plan.preconditions["server:status"] == "online"
        assert plan.preconditions["security:threat_level"] == "low"
        assert plan.success_rate == 0.85


class TestIntention:
    """Intention modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        intention = Intention(desire_id="d-1", plan_id="p-1")
        assert intention.status == PlanStatus.READY
        assert intention.commitment == CommitmentStrategy.SINGLE_MINDED
        assert intention.max_retries == 3
        assert intention.current_step == 0
        assert intention.retry_count == 0
        assert intention.metadata == {}
        assert intention.id  # UUID otomatik uretilmeli
        assert isinstance(intention.started_at, datetime)

    def test_custom_values(self) -> None:
        """Ozel degerlerle Intention olusturmayi dogrular."""
        intention = Intention(
            desire_id="d-42",
            plan_id="p-99",
            status=PlanStatus.EXECUTING,
            current_step=2,
            commitment=CommitmentStrategy.OPEN_MINDED,
            retry_count=1,
            max_retries=5,
            metadata={"reason": "high_priority"},
        )
        assert intention.desire_id == "d-42"
        assert intention.plan_id == "p-99"
        assert intention.status == PlanStatus.EXECUTING
        assert intention.current_step == 2
        assert intention.commitment == CommitmentStrategy.OPEN_MINDED
        assert intention.retry_count == 1
        assert intention.max_retries == 5
        assert intention.metadata["reason"] == "high_priority"
