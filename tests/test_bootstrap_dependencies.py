"""DependencyResolver testleri.

Bagimlilik grafi olusturma, topolojik siralama,
dongusel bagimlilik tespiti ve surum catismasi testleri.
"""

import pytest

from app.core.bootstrap.dependency_resolver import DependencyResolver
from app.models.bootstrap import (
    DependencyGraph,
    DependencyNode,
    DependencyRelation,
)


# === Yardimci Fonksiyonlar ===


def _make_resolver() -> DependencyResolver:
    """Test icin DependencyResolver olusturur."""
    return DependencyResolver()


def _make_node(**kwargs) -> DependencyNode:
    """Test icin DependencyNode olusturur."""
    defaults = {"name": "test_pkg"}
    defaults.update(kwargs)
    return DependencyNode(**defaults)


# === Enum Testleri ===


class TestDependencyRelation:
    """DependencyRelation enum testleri."""

    def test_requires_value(self) -> None:
        assert DependencyRelation.REQUIRES == "requires"

    def test_optional_value(self) -> None:
        assert DependencyRelation.OPTIONAL == "optional"

    def test_conflicts_value(self) -> None:
        assert DependencyRelation.CONFLICTS == "conflicts"


# === Model Testleri ===


class TestDependencyNode:
    """DependencyNode model testleri."""

    def test_defaults(self) -> None:
        node = _make_node()
        assert node.name == "test_pkg"
        assert node.version_spec == ""
        assert node.dependencies == []
        assert node.relation == DependencyRelation.REQUIRES

    def test_with_deps(self) -> None:
        node = _make_node(name="a", dependencies=["b", "c"])
        assert node.dependencies == ["b", "c"]

    def test_version_spec(self) -> None:
        node = _make_node(version_spec=">=1.0.0")
        assert node.version_spec == ">=1.0.0"


class TestDependencyGraph:
    """DependencyGraph model testleri."""

    def test_defaults(self) -> None:
        graph = DependencyGraph()
        assert graph.nodes == {}
        assert graph.install_order == []
        assert graph.has_cycles is False
        assert graph.conflicts == []

    def test_with_data(self) -> None:
        graph = DependencyGraph(
            has_cycles=True,
            conflicts=["a <-> b catismasi"],
        )
        assert graph.has_cycles is True
        assert len(graph.conflicts) == 1


# === DependencyResolver Init Testleri ===


class TestDependencyResolverInit:
    """DependencyResolver init testleri."""

    def test_default(self) -> None:
        r = _make_resolver()
        assert r.nodes == {}


# === AddDependency Testleri ===


class TestAddDependency:
    """add_dependency testleri."""

    def test_add_single(self) -> None:
        r = _make_resolver()
        node = r.add_dependency("requests")
        assert node.name == "requests"
        assert "requests" in r.nodes

    def test_add_with_deps(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        node = r.add_dependency("b", dependencies=["a"])
        assert node.dependencies == ["a"]

    def test_add_with_version(self) -> None:
        r = _make_resolver()
        node = r.add_dependency("flask", version_spec=">=2.0")
        assert node.version_spec == ">=2.0"

    def test_add_replaces_existing(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", version_spec=">=1.0")
        r.add_dependency("a", version_spec=">=2.0")
        assert r.nodes["a"].version_spec == ">=2.0"


# === RemoveDependency Testleri ===


class TestRemoveDependency:
    """remove_dependency testleri."""

    def test_remove_existing(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        assert r.remove_dependency("a") is True
        assert "a" not in r.nodes

    def test_remove_nonexistent(self) -> None:
        r = _make_resolver()
        assert r.remove_dependency("ghost") is False

    def test_remove_cleans_references(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency("b", dependencies=["a"])
        r.remove_dependency("a")
        assert "a" not in r.nodes["b"].dependencies


# === TopologicalSort Testleri ===


class TestTopologicalSort:
    """topological_sort testleri."""

    def test_linear_chain(self) -> None:
        """A -> B -> C"""
        r = _make_resolver()
        r.add_dependency("c")
        r.add_dependency("b", dependencies=["c"])
        r.add_dependency("a", dependencies=["b"])
        order = r.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_diamond(self) -> None:
        """A -> B, A -> C, B -> D, C -> D"""
        r = _make_resolver()
        r.add_dependency("d")
        r.add_dependency("b", dependencies=["d"])
        r.add_dependency("c", dependencies=["d"])
        r.add_dependency("a", dependencies=["b", "c"])
        order = r.topological_sort()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")

    def test_single_node(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        order = r.topological_sort()
        assert order == ["a"]

    def test_no_dependencies(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency("b")
        r.add_dependency("c")
        order = r.topological_sort()
        assert set(order) == {"a", "b", "c"}

    def test_cycle_raises(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", dependencies=["b"])
        r.add_dependency("b", dependencies=["a"])
        with pytest.raises(ValueError, match="Dongusel"):
            r.topological_sort()


# === DetectCycles Testleri ===


class TestDetectCycles:
    """detect_cycles testleri."""

    def test_no_cycles(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency("b", dependencies=["a"])
        cycles = r.detect_cycles()
        assert cycles == []

    def test_simple_cycle(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", dependencies=["b"])
        r.add_dependency("b", dependencies=["a"])
        cycles = r.detect_cycles()
        assert len(cycles) > 0

    def test_self_cycle(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", dependencies=["a"])
        cycles = r.detect_cycles()
        assert len(cycles) > 0

    def test_indirect_cycle(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", dependencies=["b"])
        r.add_dependency("b", dependencies=["c"])
        r.add_dependency("c", dependencies=["a"])
        cycles = r.detect_cycles()
        assert len(cycles) > 0


# === DetectConflicts Testleri ===


class TestDetectConflicts:
    """detect_conflicts testleri."""

    def test_no_conflicts(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency("b")
        conflicts = r.detect_conflicts()
        assert conflicts == []

    def test_conflict_detected(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency(
            "b",
            dependencies=["a"],
            relation=DependencyRelation.CONFLICTS,
        )
        conflicts = r.detect_conflicts()
        assert len(conflicts) == 1
        assert "a" in conflicts[0]
        assert "b" in conflicts[0]

    def test_conflict_missing_target(self) -> None:
        """Catisma hedefi mevcut degilse catisma raporlanmaz."""
        r = _make_resolver()
        r.add_dependency(
            "a",
            dependencies=["ghost"],
            relation=DependencyRelation.CONFLICTS,
        )
        conflicts = r.detect_conflicts()
        assert conflicts == []


# === Resolve Testleri ===


class TestResolve:
    """resolve testleri."""

    def test_resolve_simple(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency("b", dependencies=["a"])
        graph = r.resolve()
        assert isinstance(graph, DependencyGraph)
        assert graph.has_cycles is False
        assert len(graph.install_order) == 2

    def test_resolve_with_cycle(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", dependencies=["b"])
        r.add_dependency("b", dependencies=["a"])
        graph = r.resolve()
        assert graph.has_cycles is True
        assert graph.install_order == []

    def test_resolve_with_conflict(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency(
            "b", dependencies=["a"], relation=DependencyRelation.CONFLICTS
        )
        graph = r.resolve()
        assert len(graph.conflicts) == 1


# === GetInstallOrder Testleri ===


class TestGetInstallOrder:
    """get_install_order testleri."""

    def test_valid_order(self) -> None:
        r = _make_resolver()
        r.add_dependency("a")
        r.add_dependency("b", dependencies=["a"])
        order = r.get_install_order()
        assert order.index("a") > order.index("b")

    def test_cycle_returns_empty(self) -> None:
        r = _make_resolver()
        r.add_dependency("a", dependencies=["b"])
        r.add_dependency("b", dependencies=["a"])
        order = r.get_install_order()
        assert order == []
