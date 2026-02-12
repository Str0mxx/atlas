"""GoalTree testleri.

Hiyerarsik hedef agaci: ekleme, silme, AND/OR ilerleme,
bagimlilik kontrolu ve snapshot testleri.
"""

import pytest

from app.core.planning.goal_tree import GoalTree
from app.models.planning import GoalNodeStatus, GoalType


# === Yardimci fonksiyonlar ===


def _make_tree() -> GoalTree:
    """Bos GoalTree olusturur."""
    return GoalTree()


# === Init Testleri ===


class TestGoalTreeInit:
    """GoalTree initialization testleri."""

    def test_default(self) -> None:
        tree = _make_tree()
        assert tree.nodes == {}
        assert tree.root_id is None


# === add_goal Testleri ===


class TestGoalTreeAddGoal:
    """GoalTree.add_goal testleri."""

    async def test_add_root(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("root", GoalType.AND)
        assert node.name == "root"
        assert node.goal_type == GoalType.AND
        assert tree.root_id == node.id
        assert node.id in tree.nodes

    async def test_add_child(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        child = await tree.add_goal("child", GoalType.LEAF, parent_id=root.id)
        assert child.parent_id == root.id
        assert child.id in tree.nodes[root.id].children_ids

    async def test_add_with_dependencies(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a", GoalType.LEAF)
        b = await tree.add_goal("b", GoalType.LEAF, dependencies=[a.id])
        assert a.id in b.dependencies

    async def test_add_with_priority(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("high", priority=0.9)
        assert node.priority == 0.9

    async def test_add_with_metadata(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("m", metadata={"team": "dev"})
        assert node.metadata == {"team": "dev"}

    async def test_add_with_description(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("d", description="Test goal")
        assert node.description == "Test goal"

    async def test_invalid_parent(self) -> None:
        tree = _make_tree()
        with pytest.raises(ValueError, match="Parent goal not found"):
            await tree.add_goal("child", parent_id="nonexistent")

    async def test_invalid_dependency(self) -> None:
        tree = _make_tree()
        with pytest.raises(ValueError, match="Dependency goal not found"):
            await tree.add_goal("child", dependencies=["nonexistent"])

    async def test_first_goal_is_root(self) -> None:
        tree = _make_tree()
        first = await tree.add_goal("first")
        assert tree.root_id == first.id

    async def test_second_rootless_goal_not_root(self) -> None:
        tree = _make_tree()
        await tree.add_goal("first")
        second = await tree.add_goal("second")
        assert tree.root_id != second.id


# === remove_goal Testleri ===


class TestGoalTreeRemoveGoal:
    """GoalTree.remove_goal testleri."""

    async def test_remove_leaf(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        child = await tree.add_goal("child", parent_id=root.id)
        result = await tree.remove_goal(child.id)
        assert result is True
        assert child.id not in tree.nodes
        assert child.id not in tree.nodes[root.id].children_ids

    async def test_remove_subtree(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        child = await tree.add_goal("child", GoalType.AND, parent_id=root.id)
        grandchild = await tree.add_goal("gc", parent_id=child.id)
        await tree.remove_goal(child.id)
        assert child.id not in tree.nodes
        assert grandchild.id not in tree.nodes

    async def test_remove_nonexistent(self) -> None:
        tree = _make_tree()
        result = await tree.remove_goal("nonexistent")
        assert result is False

    async def test_remove_root(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root")
        await tree.remove_goal(root.id)
        assert tree.root_id is None

    async def test_remove_cleans_dependencies(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        b = await tree.add_goal("b", dependencies=[a.id])
        await tree.remove_goal(a.id)
        assert a.id not in tree.nodes[b.id].dependencies


# === update_status Testleri ===


class TestGoalTreeUpdateStatus:
    """GoalTree.update_status testleri."""

    async def test_complete_leaf(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("leaf")
        result = await tree.update_status(node.id, GoalNodeStatus.COMPLETED)
        assert result is not None
        assert result.status == GoalNodeStatus.COMPLETED
        assert result.progress == 1.0

    async def test_fail_leaf(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("leaf")
        result = await tree.update_status(node.id, GoalNodeStatus.FAILED)
        assert result is not None
        assert result.progress == 0.0

    async def test_nonexistent(self) -> None:
        tree = _make_tree()
        result = await tree.update_status("nope", GoalNodeStatus.COMPLETED)
        assert result is None

    async def test_in_progress(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("leaf")
        result = await tree.update_status(node.id, GoalNodeStatus.IN_PROGRESS)
        assert result is not None
        assert result.status == GoalNodeStatus.IN_PROGRESS


# === AND/OR Propagation Testleri ===


class TestGoalTreePropagation:
    """Ilerleme propagasyon testleri."""

    async def test_and_all_complete(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        c2 = await tree.add_goal("c2", parent_id=root.id)
        await tree.update_status(c1.id, GoalNodeStatus.COMPLETED)
        await tree.update_status(c2.id, GoalNodeStatus.COMPLETED)
        assert tree.nodes[root.id].status == GoalNodeStatus.COMPLETED
        assert tree.nodes[root.id].progress == 1.0

    async def test_and_partial(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        c2 = await tree.add_goal("c2", parent_id=root.id)
        await tree.update_status(c1.id, GoalNodeStatus.COMPLETED)
        assert tree.nodes[root.id].progress == 0.5

    async def test_and_one_fails(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        c2 = await tree.add_goal("c2", parent_id=root.id)
        await tree.update_status(c1.id, GoalNodeStatus.FAILED)
        assert tree.nodes[root.id].status == GoalNodeStatus.FAILED

    async def test_or_one_complete(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.OR)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        c2 = await tree.add_goal("c2", parent_id=root.id)
        await tree.update_status(c1.id, GoalNodeStatus.COMPLETED)
        assert tree.nodes[root.id].status == GoalNodeStatus.COMPLETED
        assert tree.nodes[root.id].progress == 1.0

    async def test_or_all_fail(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.OR)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        c2 = await tree.add_goal("c2", parent_id=root.id)
        await tree.update_status(c1.id, GoalNodeStatus.FAILED)
        await tree.update_status(c2.id, GoalNodeStatus.FAILED)
        assert tree.nodes[root.id].status == GoalNodeStatus.FAILED

    async def test_or_in_progress(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.OR)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        _c2 = await tree.add_goal("c2", parent_id=root.id)
        await tree.update_status(c1.id, GoalNodeStatus.IN_PROGRESS)
        assert tree.nodes[root.id].status == GoalNodeStatus.IN_PROGRESS

    async def test_deep_propagation(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        mid = await tree.add_goal("mid", GoalType.AND, parent_id=root.id)
        leaf = await tree.add_goal("leaf", parent_id=mid.id)
        await tree.update_status(leaf.id, GoalNodeStatus.COMPLETED)
        assert tree.nodes[mid.id].progress == 1.0
        assert tree.nodes[root.id].progress == 1.0


# === check_dependencies Testleri ===


class TestGoalTreeDependencies:
    """Bagimlilik kontrol testleri."""

    async def test_no_deps(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("a")
        assert await tree.check_dependencies(node.id) is True

    async def test_met_deps(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        b = await tree.add_goal("b", dependencies=[a.id])
        await tree.update_status(a.id, GoalNodeStatus.COMPLETED)
        assert await tree.check_dependencies(b.id) is True

    async def test_unmet_deps(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        b = await tree.add_goal("b", dependencies=[a.id])
        assert await tree.check_dependencies(b.id) is False

    async def test_nonexistent_node(self) -> None:
        tree = _make_tree()
        assert await tree.check_dependencies("nope") is False


# === get_actionable_goals Testleri ===


class TestGoalTreeActionableGoals:
    """Uygulanabilir hedef testleri."""

    async def test_no_goals(self) -> None:
        tree = _make_tree()
        result = await tree.get_actionable_goals()
        assert result == []

    async def test_actionable_leaf(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("a")
        result = await tree.get_actionable_goals()
        assert len(result) == 1
        assert result[0].id == node.id

    async def test_blocked_not_actionable(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        _b = await tree.add_goal("b", dependencies=[a.id])
        result = await tree.get_actionable_goals()
        # Sadece a actionable (b bagimliligi karsilanmamis)
        assert len(result) == 1
        assert result[0].id == a.id

    async def test_completed_not_actionable(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        await tree.update_status(a.id, GoalNodeStatus.COMPLETED)
        result = await tree.get_actionable_goals()
        assert result == []

    async def test_compound_not_actionable(self) -> None:
        tree = _make_tree()
        await tree.add_goal("parent", GoalType.AND)
        result = await tree.get_actionable_goals()
        assert result == []

    async def test_priority_ordering(self) -> None:
        tree = _make_tree()
        low = await tree.add_goal("low", priority=0.1)
        high = await tree.add_goal("high", priority=0.9)
        result = await tree.get_actionable_goals()
        assert result[0].id == high.id
        assert result[1].id == low.id


# === get_blocked_goals Testleri ===


class TestGoalTreeBlockedGoals:
    """Engellenmis hedef testleri."""

    async def test_no_blocked(self) -> None:
        tree = _make_tree()
        await tree.add_goal("a")
        result = await tree.get_blocked_goals()
        assert result == []

    async def test_blocked(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        b = await tree.add_goal("b", dependencies=[a.id])
        result = await tree.get_blocked_goals()
        assert len(result) == 1
        assert result[0].id == b.id

    async def test_unblocked_after_dep_complete(self) -> None:
        tree = _make_tree()
        a = await tree.add_goal("a")
        _b = await tree.add_goal("b", dependencies=[a.id])
        await tree.update_status(a.id, GoalNodeStatus.COMPLETED)
        result = await tree.get_blocked_goals()
        assert result == []


# === get_subtree Testleri ===


class TestGoalTreeSubtree:
    """Alt agac testleri."""

    async def test_leaf_subtree(self) -> None:
        tree = _make_tree()
        node = await tree.add_goal("leaf")
        result = tree.get_subtree(node.id)
        assert len(result) == 1

    async def test_full_subtree(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        c1 = await tree.add_goal("c1", parent_id=root.id)
        c2 = await tree.add_goal("c2", parent_id=root.id)
        result = tree.get_subtree(root.id)
        assert len(result) == 3
        ids = {n.id for n in result}
        assert root.id in ids
        assert c1.id in ids
        assert c2.id in ids

    def test_nonexistent(self) -> None:
        tree = _make_tree()
        result = tree.get_subtree("nope")
        assert result == []


# === snapshot Testleri ===


class TestGoalTreeSnapshot:
    """Snapshot testleri."""

    async def test_empty(self) -> None:
        tree = _make_tree()
        snap = await tree.snapshot()
        assert snap.root_id is None
        assert snap.nodes == {}
        assert snap.total_progress == 0.0

    async def test_with_progress(self) -> None:
        tree = _make_tree()
        root = await tree.add_goal("root", GoalType.AND)
        c = await tree.add_goal("c", parent_id=root.id)
        await tree.update_status(c.id, GoalNodeStatus.COMPLETED)
        snap = await tree.snapshot()
        assert snap.root_id == root.id
        assert snap.total_progress == 1.0
        assert len(snap.nodes) == 2
