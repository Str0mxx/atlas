"""DesireBase testleri.

Hedef benimseme, birakma, tamamlama, hiyerarsi,
onceliklendirme, cakisma cozme ve sorgulama islemlerini test eder.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.core.autonomy.desires import DesireBase
from app.core.decision_matrix import DecisionMatrix
from app.models.autonomy import (
    Desire,
    GoalPriority,
    GoalStatus,
)


# === TestDesireBaseInit ===


class TestDesireBaseInit:
    """DesireBase baslangic durumu testleri."""

    def test_init_empty(self) -> None:
        """Bos baslangic durumunda desires dict'i bos olmalidir."""
        db = DesireBase()
        assert db.desires == {}

    def test_init_custom_matrix(self) -> None:
        """DecisionMatrix mock ile olusturulabilmelidir."""
        mock_matrix = MagicMock(spec=DecisionMatrix)
        db = DesireBase(decision_matrix=mock_matrix)
        assert db.decision_matrix is mock_matrix


# === TestDesireAdopt ===


class TestDesireAdopt:
    """Hedef benimseme testleri."""

    async def test_adopt_stores_desire(self) -> None:
        """Benimsenen hedef desires dict'inde saklanmalidir."""
        db = DesireBase()
        desire = Desire(name="test")
        result = await db.adopt(desire)
        assert desire.id in db.desires
        assert db.desires[desire.id] is result

    async def test_adopt_sets_priority_score(self) -> None:
        """CRITICAL oncelik 0.9, LOW oncelik 0.3 skor almalidir."""
        db = DesireBase()
        critical = Desire(name="critical_goal", priority=GoalPriority.CRITICAL)
        low = Desire(name="low_goal", priority=GoalPriority.LOW)

        await db.adopt(critical)
        await db.adopt(low)

        assert critical.priority_score == 0.9
        assert low.priority_score == 0.3

    async def test_adopt_medium_default(self) -> None:
        """MEDIUM oncelik 0.5 skor almalidir."""
        db = DesireBase()
        medium = Desire(name="medium_goal", priority=GoalPriority.MEDIUM)
        await db.adopt(medium)
        assert medium.priority_score == 0.5


# === TestDesireDrop ===


class TestDesireDrop:
    """Hedef birakma testleri."""

    async def test_drop_existing(self) -> None:
        """Mevcut hedef DROPPED durumuna gecmeli ve drop_reason metadata'ya eklenmeli."""
        db = DesireBase()
        desire = Desire(name="to_drop")
        await db.adopt(desire)

        result = await db.drop(desire.id, reason="artik gerekli degil")

        assert result is not None
        assert result.status == GoalStatus.DROPPED
        assert result.metadata["drop_reason"] == "artik gerekli degil"

    async def test_drop_nonexistent(self) -> None:
        """Var olmayan hedef icin None donmelidir."""
        db = DesireBase()
        result = await db.drop("nonexistent-id")
        assert result is None


# === TestDesireAchieve ===


class TestDesireAchieve:
    """Hedef tamamlama testleri."""

    async def test_achieve_existing(self) -> None:
        """Mevcut hedef ACHIEVED durumuna gecmelidir."""
        db = DesireBase()
        desire = Desire(name="achievable")
        await db.adopt(desire)

        result = await db.achieve(desire.id)

        assert result is not None
        assert result.status == GoalStatus.ACHIEVED

    async def test_achieve_nonexistent(self) -> None:
        """Var olmayan hedef icin None donmelidir."""
        db = DesireBase()
        result = await db.achieve("nonexistent-id")
        assert result is None


# === TestDesireHierarchy ===


class TestDesireHierarchy:
    """Hedef hiyerarsisi testleri."""

    async def test_add_sub_goal(self) -> None:
        """Alt hedef eklendiginde parent.sub_goal_ids child'i icermeli,
        child.parent_id ust hedefin ID'si olmalidir.
        """
        db = DesireBase()
        parent = Desire(name="parent_goal")
        child = Desire(name="child_goal")
        await db.adopt(parent)

        result = await db.add_sub_goal(parent.id, child)

        assert result is not None
        assert child.id in parent.sub_goal_ids
        assert child.parent_id == parent.id

    async def test_get_sub_goals(self) -> None:
        """Alt hedefleri dogru sekilde dondurmeli."""
        db = DesireBase()
        parent = Desire(name="parent")
        child1 = Desire(name="child1")
        child2 = Desire(name="child2")
        await db.adopt(parent)
        await db.add_sub_goal(parent.id, child1)
        await db.add_sub_goal(parent.id, child2)

        subs = db.get_sub_goals(parent.id)

        assert len(subs) == 2
        sub_names = {s.name for s in subs}
        assert sub_names == {"child1", "child2"}

    async def test_add_sub_goal_nonexistent_parent(self) -> None:
        """Var olmayan ust hedef icin None donmelidir."""
        db = DesireBase()
        child = Desire(name="orphan")
        result = await db.add_sub_goal("nonexistent-parent", child)
        assert result is None


# === TestDesirePriorities ===


class TestDesirePriorities:
    """Dinamik onceliklendirme testleri."""

    async def test_base_score(self) -> None:
        """CRITICAL=0.9, LOW=0.3 baz puanlar dogru hesaplanmalidir."""
        db = DesireBase()
        crit = Desire(name="crit", priority=GoalPriority.CRITICAL)
        low = Desire(name="low", priority=GoalPriority.LOW)
        await db.adopt(crit)
        await db.adopt(low)

        updated = await db.update_priorities({})

        crit_updated = next(d for d in updated if d.name == "crit")
        low_updated = next(d for d in updated if d.name == "low")
        assert crit_updated.priority_score == 0.9
        assert low_updated.priority_score == 0.3

    async def test_time_pressure(self) -> None:
        """Deadline gecmisse +0.3 bonus eklenmelidir."""
        db = DesireBase()
        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        desire = Desire(
            name="urgent",
            priority=GoalPriority.LOW,
            deadline=past_deadline,
        )
        await db.adopt(desire)

        await db.update_priorities({})

        # LOW baz=0.3 + time_bonus=0.3 = 0.6
        assert desire.priority_score == pytest.approx(0.6, abs=0.01)

    async def test_belief_alignment(self) -> None:
        """On kosullar kismen saglandiginda kismi bonus verilmelidir."""
        db = DesireBase()
        desire = Desire(
            name="aligned",
            priority=GoalPriority.MEDIUM,
            preconditions={"server_online": True, "disk_ok": True},
        )
        await db.adopt(desire)

        # Sadece 1/2 precondition saglaniyor
        beliefs = {"server_online": True, "disk_ok": False}
        await db.update_priorities(beliefs)

        # MEDIUM baz=0.5 + belief_bonus=0.1*(1/2)=0.05 = 0.55
        assert desire.priority_score == pytest.approx(0.55, abs=0.01)

    async def test_update_all(self) -> None:
        """Birden fazla hedefin puanlari toplu guncellenmelidir."""
        db = DesireBase()
        d1 = Desire(name="d1", priority=GoalPriority.HIGH)
        d2 = Desire(name="d2", priority=GoalPriority.LOW)
        d3 = Desire(name="d3", priority=GoalPriority.CRITICAL)
        await db.adopt(d1)
        await db.adopt(d2)
        await db.adopt(d3)

        updated = await db.update_priorities({})

        assert len(updated) == 3


# === TestDesireConflicts ===


class TestDesireConflicts:
    """Cakisma cozme testleri."""

    async def test_resolve_highest_priority(self) -> None:
        """En yuksek priority_score'a sahip hedef secilmelidir."""
        db = DesireBase()
        low = Desire(name="low", priority=GoalPriority.LOW)
        high = Desire(name="high", priority=GoalPriority.CRITICAL)
        await db.adopt(low)
        await db.adopt(high)

        winner_id = await db.resolve_conflicts([low.id, high.id])

        assert winner_id == high.id

    async def test_resolve_empty(self) -> None:
        """Bos ID listesi icin None donmelidir."""
        db = DesireBase()
        result = await db.resolve_conflicts([])
        assert result is None

    async def test_resolve_nonexistent_ids(self) -> None:
        """Var olmayan ID'ler icin None donmelidir."""
        db = DesireBase()
        result = await db.resolve_conflicts(["fake-1", "fake-2"])
        assert result is None


# === TestDesireQuery ===


class TestDesireQuery:
    """Hedef sorgulama testleri."""

    async def test_get_active_sorted(self) -> None:
        """Aktif hedefler priority_score'a gore azalan sirada donmelidir."""
        db = DesireBase()
        low = Desire(name="low", priority=GoalPriority.LOW)
        high = Desire(name="high", priority=GoalPriority.HIGH)
        crit = Desire(name="crit", priority=GoalPriority.CRITICAL)
        await db.adopt(low)
        await db.adopt(high)
        await db.adopt(crit)

        active = db.get_active()

        assert len(active) == 3
        assert active[0].name == "crit"
        assert active[1].name == "high"
        assert active[2].name == "low"

    async def test_get_achievable(self) -> None:
        """Sadece on kosullari saglanan hedefler donmelidir."""
        db = DesireBase()
        achievable = Desire(
            name="achievable",
            preconditions={"ready": True},
        )
        not_achievable = Desire(
            name="not_achievable",
            preconditions={"ready": False},
        )
        no_precond = Desire(name="no_precond")
        await db.adopt(achievable)
        await db.adopt(not_achievable)
        await db.adopt(no_precond)

        beliefs = {"ready": True}
        result = db.get_achievable(beliefs)

        result_names = {d.name for d in result}
        assert "achievable" in result_names
        assert "no_precond" in result_names
        assert "not_achievable" not in result_names

    async def test_snapshot(self) -> None:
        """Snapshot, total, active ve desires anahtarlarini icermelidir."""
        db = DesireBase()
        d1 = Desire(name="active_one")
        d2 = Desire(name="dropped_one")
        await db.adopt(d1)
        await db.adopt(d2)
        await db.drop(d2.id, reason="test")

        snap = db.snapshot()

        assert snap["total"] == 2
        assert snap["active"] == 1
        assert d1.id in snap["desires"]
        assert d2.id in snap["desires"]
        assert snap["desires"][d2.id]["status"] == "dropped"
