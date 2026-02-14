"""ATLAS Agent Spawner sistemi testleri.

AgentTemplateManager, SpawnEngine, LifecycleManager,
ResourceAllocator, CapabilityInjector, AgentPool,
TerminationHandler, AgentRegistry, SpawnerOrchestrator testleri.
"""

import pytest

from app.models.spawner import (
    AgentState,
    AgentTemplate,
    CapabilityAction,
    CapabilityChange,
    PoolStatus,
    PoolStrategy,
    ResourceAllocation,
    ResourceType,
    SpawnedAgent,
    SpawnMethod,
    SpawnerSnapshot,
    TemplateCategory,
    TerminationRecord,
    TerminationType,
)

from app.core.spawner.agent_template import AgentTemplateManager
from app.core.spawner.spawn_engine import SpawnEngine
from app.core.spawner.lifecycle_manager import LifecycleManager
from app.core.spawner.resource_allocator import ResourceAllocator
from app.core.spawner.capability_injector import CapabilityInjector
from app.core.spawner.agent_pool import AgentPool
from app.core.spawner.termination_handler import TerminationHandler
from app.core.spawner.agent_registry import AgentRegistry
from app.core.spawner.spawner_orchestrator import SpawnerOrchestrator


# ── Yardimci ────────────────────────────────────────────────────

def _make_agent(
    name: str = "test-agent",
    state: AgentState = AgentState.ACTIVE,
    capabilities: list[str] | None = None,
) -> SpawnedAgent:
    """Test icin agent olusturur."""
    return SpawnedAgent(
        name=name,
        state=state,
        capabilities=capabilities or ["execute", "report"],
    )


# ── Model Testleri ──────────────────────────────────────────────

class TestSpawnerModels:
    """Spawner model testleri."""

    def test_agent_state_values(self):
        assert AgentState.INITIALIZING == "initializing"
        assert AgentState.ACTIVE == "active"
        assert AgentState.PAUSED == "paused"
        assert AgentState.ERROR == "error"
        assert AgentState.TERMINATING == "terminating"
        assert AgentState.TERMINATED == "terminated"

    def test_spawn_method_values(self):
        assert SpawnMethod.TEMPLATE == "template"
        assert SpawnMethod.SCRATCH == "scratch"
        assert SpawnMethod.CLONE == "clone"
        assert SpawnMethod.HYBRID == "hybrid"
        assert SpawnMethod.POOL == "pool"

    def test_termination_type_values(self):
        assert TerminationType.GRACEFUL == "graceful"
        assert TerminationType.FORCE == "force"
        assert TerminationType.TIMEOUT == "timeout"
        assert TerminationType.ERROR == "error"
        assert TerminationType.IDLE == "idle"

    def test_resource_type_values(self):
        assert ResourceType.MEMORY == "memory"
        assert ResourceType.CPU == "cpu"
        assert ResourceType.API_QUOTA == "api_quota"
        assert ResourceType.STORAGE == "storage"

    def test_capability_action_values(self):
        assert CapabilityAction.ADD == "add"
        assert CapabilityAction.REMOVE == "remove"
        assert CapabilityAction.UPGRADE == "upgrade"
        assert CapabilityAction.SWAP == "swap"

    def test_pool_strategy_values(self):
        assert PoolStrategy.FIXED == "fixed"
        assert PoolStrategy.ELASTIC == "elastic"
        assert PoolStrategy.ON_DEMAND == "on_demand"

    def test_template_category_values(self):
        assert TemplateCategory.WORKER == "worker"
        assert TemplateCategory.SPECIALIST == "specialist"
        assert TemplateCategory.MONITOR == "monitor"
        assert TemplateCategory.COORDINATOR == "coordinator"
        assert TemplateCategory.CUSTOM == "custom"

    def test_agent_template_defaults(self):
        t = AgentTemplate(name="test")
        assert t.template_id
        assert t.name == "test"
        assert t.category == TemplateCategory.WORKER
        assert t.capabilities == []
        assert t.behavior_preset == "default"

    def test_spawned_agent_defaults(self):
        a = SpawnedAgent(name="test")
        assert a.agent_id
        assert a.state == AgentState.INITIALIZING
        assert a.spawn_method == SpawnMethod.TEMPLATE
        assert a.workload == 0.0
        assert a.error_count == 0
        assert a.restart_count == 0

    def test_resource_allocation_defaults(self):
        r = ResourceAllocation(agent_id="a1")
        assert r.allocation_id
        assert r.resource_type == ResourceType.MEMORY
        assert r.allocated == 0.0
        assert r.used == 0.0

    def test_capability_change_defaults(self):
        c = CapabilityChange(agent_id="a1", capability="test")
        assert c.change_id
        assert c.action == CapabilityAction.ADD
        assert not c.success

    def test_termination_record_defaults(self):
        t = TerminationRecord(agent_id="a1")
        assert t.record_id
        assert t.termination_type == TerminationType.GRACEFUL
        assert not t.state_preserved
        assert not t.cleanup_done

    def test_pool_status_defaults(self):
        p = PoolStatus()
        assert p.total_agents == 0
        assert p.strategy == PoolStrategy.FIXED

    def test_spawner_snapshot_defaults(self):
        s = SpawnerSnapshot()
        assert s.total_agents == 0
        assert s.health_score == 1.0

    def test_spawned_agent_workload_bounds(self):
        a = SpawnedAgent(name="test", workload=0.5)
        assert a.workload == 0.5

    def test_spawner_snapshot_health_bounds(self):
        s = SpawnerSnapshot(health_score=0.85)
        assert s.health_score == 0.85


# ── AgentTemplateManager Testleri ───────────────────────────────

class TestAgentTemplateManager:
    """Sablon yoneticisi testleri."""

    def test_predefined_templates_loaded(self):
        mgr = AgentTemplateManager()
        assert mgr.template_count >= 6
        assert mgr.get_template("worker") is not None
        assert mgr.get_template("researcher") is not None
        assert mgr.get_template("monitor") is not None

    def test_get_predefined_worker(self):
        mgr = AgentTemplateManager()
        t = mgr.get_template("worker")
        assert t is not None
        assert t.name == "Worker Agent"
        assert "execute" in t.capabilities

    def test_get_predefined_coordinator(self):
        mgr = AgentTemplateManager()
        t = mgr.get_template("coordinator")
        assert t is not None
        assert "delegate" in t.capabilities

    def test_create_custom_template(self):
        mgr = AgentTemplateManager()
        t = mgr.create_template(
            name="Custom",
            capabilities=["custom_cap"],
            resource_profile={"memory": 128},
        )
        assert t.name == "Custom"
        assert t.category == TemplateCategory.CUSTOM
        assert "custom_cap" in t.capabilities

    def test_delete_template(self):
        mgr = AgentTemplateManager()
        t = mgr.create_template(name="To Delete")
        assert mgr.delete_template(t.template_id) is True
        assert mgr.get_template(t.template_id) is None

    def test_delete_nonexistent_template(self):
        mgr = AgentTemplateManager()
        assert mgr.delete_template("nonexistent") is False

    def test_list_templates_all(self):
        mgr = AgentTemplateManager()
        templates = mgr.list_templates()
        assert len(templates) >= 6

    def test_list_templates_by_category(self):
        mgr = AgentTemplateManager()
        specialists = mgr.list_templates(TemplateCategory.SPECIALIST)
        assert len(specialists) >= 2  # researcher, security, coder

    def test_merge_templates(self):
        mgr = AgentTemplateManager()
        merged = mgr.merge_templates(["worker", "monitor"], name="Merged")
        assert merged is not None
        assert "execute" in merged.capabilities
        assert "observe" in merged.capabilities

    def test_merge_empty_templates(self):
        mgr = AgentTemplateManager()
        result = mgr.merge_templates([])
        assert result is None

    def test_merge_nonexistent_templates(self):
        mgr = AgentTemplateManager()
        result = mgr.merge_templates(["nonexistent1", "nonexistent2"])
        assert result is None

    def test_behavior_presets(self):
        mgr = AgentTemplateManager()
        preset = mgr.get_behavior_preset("cautious")
        assert preset["autonomy"] == "low"
        assert preset["risk_tolerance"] == 0.1

    def test_behavior_preset_default_fallback(self):
        mgr = AgentTemplateManager()
        preset = mgr.get_behavior_preset("nonexistent")
        assert preset["autonomy"] == "medium"

    def test_register_custom_preset(self):
        mgr = AgentTemplateManager()
        mgr.register_preset("turbo", {"autonomy": "full", "speed": "max"})
        preset = mgr.get_behavior_preset("turbo")
        assert preset["autonomy"] == "full"

    def test_get_resource_profile(self):
        mgr = AgentTemplateManager()
        profile = mgr.get_resource_profile("coder")
        assert profile.get("memory") == 1024

    def test_get_resource_profile_nonexistent(self):
        mgr = AgentTemplateManager()
        profile = mgr.get_resource_profile("nonexistent")
        assert profile == {}

    def test_preset_count(self):
        mgr = AgentTemplateManager()
        assert mgr.preset_count >= 8


# ── SpawnEngine Testleri ────────────────────────────────────────

class TestSpawnEngine:
    """Olusturma motoru testleri."""

    def test_spawn_from_template(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agent = engine.spawn_from_template("worker", name="W1")
        assert agent is not None
        assert agent.name == "W1"
        assert agent.spawn_method == SpawnMethod.TEMPLATE
        assert "execute" in agent.capabilities

    def test_spawn_from_template_nonexistent(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agent = engine.spawn_from_template("nonexistent")
        assert agent is None

    def test_spawn_from_template_with_overrides(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agent = engine.spawn_from_template(
            "worker", config_overrides={"extra": True},
        )
        assert agent is not None
        assert agent.config.get("extra") is True

    def test_spawn_from_scratch(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agent = engine.spawn_from_scratch(
            name="Scratch",
            capabilities=["custom"],
            config={"key": "val"},
        )
        assert agent.name == "Scratch"
        assert agent.spawn_method == SpawnMethod.SCRATCH
        assert "custom" in agent.capabilities

    def test_clone_agent(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        source = engine.spawn_from_scratch("Source", capabilities=["cap1", "cap2"])
        clone = engine.clone_agent(source, "Clone")
        assert clone.name == "Clone"
        assert clone.spawn_method == SpawnMethod.CLONE
        assert clone.parent_agent_id == source.agent_id
        assert "cap1" in clone.capabilities

    def test_clone_default_name(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        source = engine.spawn_from_scratch("Original")
        clone = engine.clone_agent(source)
        assert "clone" in clone.name.lower()

    def test_spawn_hybrid(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agent = engine.spawn_hybrid(["worker", "monitor"], name="Hybrid")
        assert agent is not None
        assert agent.spawn_method == SpawnMethod.HYBRID
        assert "execute" in agent.capabilities
        assert "observe" in agent.capabilities

    def test_spawn_hybrid_nonexistent(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agent = engine.spawn_hybrid(["nonexistent"])
        assert agent is None

    def test_batch_spawn(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agents = engine.batch_spawn("worker", count=3, name_prefix="batch")
        assert len(agents) == 3
        assert agents[0].name == "batch-1"
        assert agents[2].name == "batch-3"

    def test_batch_spawn_nonexistent(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        agents = engine.batch_spawn("nonexistent", count=3)
        assert len(agents) == 0

    def test_total_spawned(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        engine.spawn_from_scratch("A1")
        engine.spawn_from_scratch("A2")
        assert engine.total_spawned == 2

    def test_spawn_history(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        engine.spawn_from_scratch("H1")
        history = engine.get_spawn_history()
        assert len(history) == 1
        assert history[0]["name"] == "H1"

    def test_spawn_history_limit(self):
        tmgr = AgentTemplateManager()
        engine = SpawnEngine(tmgr)
        for i in range(10):
            engine.spawn_from_scratch(f"A{i}")
        history = engine.get_spawn_history(limit=5)
        assert len(history) == 5


# ── LifecycleManager Testleri ───────────────────────────────────

class TestLifecycleManager:
    """Yasam dongusu yoneticisi testleri."""

    def test_register_and_activate(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        assert lm.activate(agent.agent_id) is True
        assert agent.state == AgentState.ACTIVE

    def test_activate_count(self):
        lm = LifecycleManager()
        a1 = SpawnedAgent(name="A1")
        a2 = SpawnedAgent(name="A2")
        lm.register(a1)
        lm.register(a2)
        lm.activate(a1.agent_id)
        lm.activate(a2.agent_id)
        assert lm.active_count == 2

    def test_pause_and_resume(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        assert lm.pause(agent.agent_id) is True
        assert agent.state == AgentState.PAUSED
        assert lm.resume(agent.agent_id) is True
        assert agent.state == AgentState.ACTIVE

    def test_invalid_transition(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test", state=AgentState.TERMINATED)
        lm.register(agent)
        assert lm.activate(agent.agent_id) is False

    def test_mark_error(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        assert lm.mark_error(agent.agent_id) is True
        assert agent.state == AgentState.ERROR
        assert agent.error_count == 1

    def test_auto_restart(self):
        lm = LifecycleManager(max_restarts=3)
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        lm.mark_error(agent.agent_id)
        assert lm.auto_restart(agent.agent_id) is True
        assert agent.state == AgentState.ACTIVE
        assert agent.restart_count == 1

    def test_auto_restart_max_exceeded(self):
        lm = LifecycleManager(max_restarts=2)
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        # 2 restart
        for _ in range(2):
            lm.mark_error(agent.agent_id)
            lm.auto_restart(agent.agent_id)
        # 3rd fail
        lm.mark_error(agent.agent_id)
        assert lm.auto_restart(agent.agent_id) is False

    def test_auto_restart_wrong_state(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        assert lm.auto_restart(agent.agent_id) is False

    def test_heartbeat(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        assert lm.heartbeat(agent.agent_id) is True

    def test_heartbeat_nonexistent(self):
        lm = LifecycleManager()
        assert lm.heartbeat("nonexistent") is False

    def test_check_health_active(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        lm.heartbeat(agent.agent_id)
        health = lm.check_health(agent.agent_id)
        assert health["healthy"] is True

    def test_check_health_nonexistent(self):
        lm = LifecycleManager()
        health = lm.check_health("nonexistent")
        assert health["healthy"] is False

    def test_begin_and_complete_termination(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        assert lm.begin_termination(agent.agent_id) is True
        assert agent.state == AgentState.TERMINATING
        assert lm.complete_termination(agent.agent_id) is True
        assert agent.state == AgentState.TERMINATED

    def test_get_agents_by_state(self):
        lm = LifecycleManager()
        a1 = SpawnedAgent(name="A1")
        a2 = SpawnedAgent(name="A2")
        lm.register(a1)
        lm.register(a2)
        lm.activate(a1.agent_id)
        active = lm.get_agents_by_state(AgentState.ACTIVE)
        assert len(active) == 1

    def test_state_history(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        lm.activate(agent.agent_id)
        lm.pause(agent.agent_id)
        history = lm.get_state_history(agent.agent_id)
        assert len(history) == 2

    def test_unregister(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        assert lm.managed_count == 1
        lm.unregister(agent.agent_id)
        assert lm.managed_count == 0

    def test_get_agent(self):
        lm = LifecycleManager()
        agent = SpawnedAgent(name="Test")
        lm.register(agent)
        found = lm.get_agent(agent.agent_id)
        assert found is not None
        assert found.name == "Test"


# ── ResourceAllocator Testleri ──────────────────────────────────

class TestResourceAllocator:
    """Kaynak tahsis testleri."""

    def test_allocate_memory(self):
        ra = ResourceAllocator()
        alloc = ra.allocate("a1", ResourceType.MEMORY, 512)
        assert alloc is not None
        assert alloc.allocated == 512

    def test_allocate_exceeds_capacity(self):
        ra = ResourceAllocator(
            system_capacity={ResourceType.MEMORY: 100},
        )
        alloc = ra.allocate("a1", ResourceType.MEMORY, 200)
        assert alloc is None

    def test_deallocate(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 256)
        assert ra.deallocate("a1", ResourceType.MEMORY) is True
        assert ra.total_agents == 0

    def test_deallocate_all(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 256)
        ra.allocate("a1", ResourceType.CPU, 1.0)
        assert ra.deallocate("a1") is True

    def test_deallocate_nonexistent(self):
        ra = ResourceAllocator()
        assert ra.deallocate("nonexistent") is False

    def test_update_usage(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 512)
        assert ra.update_usage("a1", ResourceType.MEMORY, 256) is True
        info = ra.get_allocation("a1")
        assert info["memory"]["used"] == 256

    def test_update_usage_capped(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 100)
        ra.update_usage("a1", ResourceType.MEMORY, 200)
        info = ra.get_allocation("a1")
        assert info["memory"]["used"] == 100  # capped at allocated

    def test_reallocate(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 256)
        assert ra.reallocate("a1", ResourceType.MEMORY, 512) is True
        info = ra.get_allocation("a1")
        assert info["memory"]["allocated"] == 512

    def test_reallocate_exceeds_capacity(self):
        ra = ResourceAllocator(
            system_capacity={ResourceType.MEMORY: 500},
        )
        ra.allocate("a1", ResourceType.MEMORY, 256)
        assert ra.reallocate("a1", ResourceType.MEMORY, 600) is False

    def test_get_system_usage(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 512)
        usage = ra.get_system_usage()
        assert usage["memory"]["allocated"] == 512
        assert usage["memory"]["available"] > 0

    def test_get_overutilized(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 100)
        ra.update_usage("a1", ResourceType.MEMORY, 95)
        over = ra.get_overutilized_agents(threshold=0.9)
        assert len(over) == 1
        assert over[0]["agent_id"] == "a1"

    def test_get_overutilized_none(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 100)
        ra.update_usage("a1", ResourceType.MEMORY, 10)
        over = ra.get_overutilized_agents()
        assert len(over) == 0

    def test_total_agents(self):
        ra = ResourceAllocator()
        ra.allocate("a1", ResourceType.MEMORY, 256)
        ra.allocate("a2", ResourceType.CPU, 1.0)
        assert ra.total_agents == 2


# ── CapabilityInjector Testleri ─────────────────────────────────

class TestCapabilityInjector:
    """Yetenek enjeksiyonu testleri."""

    def test_add_capability(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute"])
        ci.register(agent)
        change = ci.add_capability(agent.agent_id, "analyze")
        assert change is not None
        assert change.action == CapabilityAction.ADD
        assert "analyze" in agent.capabilities

    def test_add_duplicate_capability(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute"])
        ci.register(agent)
        change = ci.add_capability(agent.agent_id, "execute")
        assert change is None

    def test_add_with_auto_deps(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute"])
        ci.register(agent)
        ci.add_capability(agent.agent_id, "summarize", auto_resolve_deps=True)
        assert "analyze" in agent.capabilities  # auto-resolved dep
        assert "summarize" in agent.capabilities

    def test_remove_capability(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute", "report"])
        ci.register(agent)
        change = ci.remove_capability(agent.agent_id, "report")
        assert change is not None
        assert "report" not in agent.capabilities

    def test_remove_with_dependents(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["analyze", "summarize"])
        ci.register(agent)
        # summarize depends on analyze, so can't remove analyze
        change = ci.remove_capability(agent.agent_id, "analyze")
        assert change is None

    def test_remove_nonexistent_capability(self):
        ci = CapabilityInjector()
        agent = _make_agent()
        ci.register(agent)
        change = ci.remove_capability(agent.agent_id, "nonexistent")
        assert change is None

    def test_upgrade_capability(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute"])
        ci.register(agent)
        change = ci.upgrade_capability(agent.agent_id, "execute", "2.0")
        assert change is not None
        assert change.action == CapabilityAction.UPGRADE
        assert change.new_version == "2.0"

    def test_upgrade_nonexistent(self):
        ci = CapabilityInjector()
        agent = _make_agent()
        ci.register(agent)
        change = ci.upgrade_capability(agent.agent_id, "nonexistent", "2.0")
        assert change is None

    def test_hot_swap(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute", "report"])
        ci.register(agent)
        change = ci.hot_swap(agent.agent_id, "report", "analyze")
        assert change is not None
        assert change.action == CapabilityAction.SWAP
        assert "analyze" in agent.capabilities
        assert "report" not in agent.capabilities

    def test_hot_swap_nonexistent_old(self):
        ci = CapabilityInjector()
        agent = _make_agent()
        ci.register(agent)
        change = ci.hot_swap(agent.agent_id, "nonexistent", "new")
        assert change is None

    def test_check_dependencies(self):
        ci = CapabilityInjector()
        deps = ci.check_dependencies("deploy")
        assert "build" in deps
        assert "test" in deps

    def test_get_agent_capabilities(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["a", "b"])
        ci.register(agent)
        caps = ci.get_agent_capabilities(agent.agent_id)
        assert caps == ["a", "b"]

    def test_get_agent_capabilities_nonexistent(self):
        ci = CapabilityInjector()
        caps = ci.get_agent_capabilities("nonexistent")
        assert caps == []

    def test_change_history(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=["execute"])
        ci.register(agent)
        ci.add_capability(agent.agent_id, "analyze")
        ci.add_capability(agent.agent_id, "report")
        history = ci.get_change_history(agent.agent_id)
        assert len(history) == 2

    def test_total_changes(self):
        ci = CapabilityInjector()
        agent = _make_agent(capabilities=[])
        ci.register(agent)
        ci.add_capability(agent.agent_id, "a")
        ci.add_capability(agent.agent_id, "b")
        assert ci.total_changes == 2


# ── AgentPool Testleri ──────────────────────────────────────────

class TestAgentPool:
    """Agent havuzu testleri."""

    def test_add_to_pool(self):
        pool = AgentPool(target_size=5)
        agent = _make_agent()
        assert pool.add_to_pool(agent) is True
        assert pool.total_agents == 1

    def test_add_exceeds_fixed_size(self):
        pool = AgentPool(strategy=PoolStrategy.FIXED, target_size=1)
        a1 = _make_agent("A1")
        a2 = _make_agent("A2")
        pool.add_to_pool(a1)
        assert pool.add_to_pool(a2) is False

    def test_acquire(self):
        pool = AgentPool(target_size=5)
        agent = _make_agent()
        pool.add_to_pool(agent)
        acquired = pool.acquire()
        assert acquired is not None
        assert acquired.state == AgentState.ACTIVE
        assert pool.idle_count == 0
        assert pool.assigned_count == 1

    def test_acquire_with_capabilities(self):
        pool = AgentPool(target_size=5)
        a1 = _make_agent("A1", capabilities=["search"])
        a2 = _make_agent("A2", capabilities=["execute"])
        pool.add_to_pool(a1)
        pool.add_to_pool(a2)
        acquired = pool.acquire(required_capabilities=["search"])
        assert acquired is not None
        assert acquired.name == "A1"

    def test_acquire_no_match(self):
        pool = AgentPool(target_size=5)
        agent = _make_agent(capabilities=["execute"])
        pool.add_to_pool(agent)
        acquired = pool.acquire(required_capabilities=["nonexistent"])
        assert acquired is None

    def test_acquire_empty_pool(self):
        pool = AgentPool(target_size=5)
        assert pool.acquire() is None

    def test_release(self):
        pool = AgentPool(target_size=5)
        agent = _make_agent()
        pool.add_to_pool(agent)
        pool.acquire()
        assert pool.release(agent.agent_id) is True
        assert pool.idle_count == 1
        assert pool.assigned_count == 0

    def test_release_nonexistent(self):
        pool = AgentPool()
        assert pool.release("nonexistent") is False

    def test_remove_from_pool(self):
        pool = AgentPool(target_size=5)
        agent = _make_agent()
        pool.add_to_pool(agent)
        assert pool.remove_from_pool(agent.agent_id) is True
        assert pool.total_agents == 0

    def test_resize(self):
        pool = AgentPool(target_size=5)
        pool.resize(10)
        status = pool.get_status()
        assert status.target_size == 10

    def test_needs_scaling_fixed(self):
        pool = AgentPool(strategy=PoolStrategy.FIXED, target_size=3)
        scaling = pool.needs_scaling()
        assert scaling["needs_scale"] is True
        assert scaling["deficit"] == 3

    def test_needs_scaling_elastic_up(self):
        pool = AgentPool(strategy=PoolStrategy.ELASTIC, target_size=3)
        a1 = _make_agent()
        pool.add_to_pool(a1)
        pool.acquire()  # No idle left
        scaling = pool.needs_scaling()
        assert scaling["needs_scale"] is True
        assert scaling["direction"] == "up"

    def test_get_status(self):
        pool = AgentPool(pool_id="test", target_size=5)
        status = pool.get_status()
        assert status.pool_id == "test"
        assert status.strategy == PoolStrategy.FIXED

    def test_pool_id(self):
        pool = AgentPool(pool_id="custom")
        assert pool.pool_id == "custom"

    def test_total_assignments(self):
        pool = AgentPool(target_size=5)
        a1 = _make_agent("A1")
        a2 = _make_agent("A2")
        pool.add_to_pool(a1)
        pool.add_to_pool(a2)
        pool.acquire()
        pool.acquire()
        assert pool.total_assignments == 2


# ── TerminationHandler Testleri ─────────────────────────────────

class TestTerminationHandler:
    """Sonlandirma isleyicisi testleri."""

    def test_graceful_terminate(self):
        th = TerminationHandler()
        agent = _make_agent()
        record = th.graceful_terminate(agent, reason="Test")
        assert record.termination_type == TerminationType.GRACEFUL
        assert record.state_preserved is True
        assert record.cleanup_done is True
        assert agent.state == AgentState.TERMINATED

    def test_force_terminate(self):
        th = TerminationHandler()
        agent = _make_agent()
        record = th.force_terminate(agent, reason="Emergency")
        assert record.termination_type == TerminationType.FORCE
        assert record.state_preserved is False
        assert agent.state == AgentState.TERMINATED

    def test_timeout_terminate(self):
        th = TerminationHandler()
        agent = _make_agent()
        record = th.timeout_terminate(agent, timeout_seconds=30)
        assert record.termination_type == TerminationType.TIMEOUT
        assert "30" in record.reason

    def test_idle_terminate(self):
        th = TerminationHandler()
        agent = _make_agent()
        record = th.idle_terminate(agent, idle_seconds=600)
        assert record.termination_type == TerminationType.IDLE
        assert "600" in record.reason

    def test_error_terminate(self):
        th = TerminationHandler()
        agent = _make_agent()
        record = th.error_terminate(agent, error="OOM")
        assert record.termination_type == TerminationType.ERROR
        assert "OOM" in record.reason

    def test_preserved_state_retrieval(self):
        th = TerminationHandler()
        agent = _make_agent(capabilities=["search"])
        th.graceful_terminate(agent, preserve_state=True)
        state = th.get_preserved_state(agent.agent_id)
        assert state["name"] == "test-agent"
        assert "search" in state["capabilities"]

    def test_preserved_state_empty(self):
        th = TerminationHandler()
        state = th.get_preserved_state("nonexistent")
        assert state == {}

    def test_get_records_all(self):
        th = TerminationHandler()
        a1 = _make_agent("A1")
        a2 = _make_agent("A2")
        th.graceful_terminate(a1)
        th.force_terminate(a2)
        records = th.get_records()
        assert len(records) == 2

    def test_get_records_by_type(self):
        th = TerminationHandler()
        a1 = _make_agent("A1")
        a2 = _make_agent("A2")
        th.graceful_terminate(a1)
        th.force_terminate(a2)
        graceful = th.get_records(TerminationType.GRACEFUL)
        assert len(graceful) == 1

    def test_callback_notification(self):
        th = TerminationHandler()
        notifications = []
        th.register_callback(lambda r: notifications.append(r))
        agent = _make_agent()
        th.graceful_terminate(agent)
        assert len(notifications) == 1

    def test_total_terminated(self):
        th = TerminationHandler()
        th.graceful_terminate(_make_agent("A1"))
        th.force_terminate(_make_agent("A2"))
        assert th.total_terminated == 2

    def test_preserved_count(self):
        th = TerminationHandler()
        th.graceful_terminate(_make_agent("A1"), preserve_state=True)
        th.force_terminate(_make_agent("A2"))
        assert th.preserved_count == 1


# ── AgentRegistry Testleri ──────────────────────────────────────

class TestAgentRegistry:
    """Agent kayit defteri testleri."""

    def test_register_and_get(self):
        reg = AgentRegistry()
        agent = _make_agent()
        reg.register(agent)
        found = reg.get(agent.agent_id)
        assert found is not None
        assert found.name == "test-agent"

    def test_unregister(self):
        reg = AgentRegistry()
        agent = _make_agent()
        reg.register(agent)
        assert reg.unregister(agent.agent_id) is True
        assert reg.get(agent.agent_id) is None

    def test_unregister_nonexistent(self):
        reg = AgentRegistry()
        assert reg.unregister("nonexistent") is False

    def test_find_by_capability(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1", capabilities=["search"])
        a2 = _make_agent("A2", capabilities=["execute"])
        reg.register(a1)
        reg.register(a2)
        found = reg.find_by_capability("search")
        assert len(found) == 1
        assert found[0].name == "A1"

    def test_find_by_state(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1", state=AgentState.ACTIVE)
        a2 = _make_agent("A2", state=AgentState.PAUSED)
        reg.register(a1)
        reg.register(a2)
        active = reg.find_by_state(AgentState.ACTIVE)
        assert len(active) == 1

    def test_find_by_tag(self):
        reg = AgentRegistry()
        agent = _make_agent()
        reg.register(agent, tags=["important"])
        found = reg.find_by_tag("important")
        assert len(found) == 1

    def test_find_by_name(self):
        reg = AgentRegistry()
        a1 = _make_agent("Worker-1")
        a2 = _make_agent("Monitor-1")
        reg.register(a1)
        reg.register(a2)
        found = reg.find_by_name("worker")
        assert len(found) == 1

    def test_search_multi_filter(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1", state=AgentState.ACTIVE, capabilities=["search"])
        a2 = _make_agent("A2", state=AgentState.ACTIVE, capabilities=["execute"])
        reg.register(a1)
        reg.register(a2)
        found = reg.search(state=AgentState.ACTIVE, capability="search")
        assert len(found) == 1

    def test_search_by_workload(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1")
        a1.workload = 0.8
        a2 = _make_agent("A2")
        a2.workload = 0.2
        reg.register(a1)
        reg.register(a2)
        found = reg.search(min_workload=0.5)
        assert len(found) == 1

    def test_add_and_remove_tag(self):
        reg = AgentRegistry()
        agent = _make_agent()
        reg.register(agent)
        reg.add_tag(agent.agent_id, "vip")
        found = reg.find_by_tag("vip")
        assert len(found) == 1
        reg.remove_tag(agent.agent_id, "vip")
        found = reg.find_by_tag("vip")
        assert len(found) == 0

    def test_add_tag_nonexistent(self):
        reg = AgentRegistry()
        assert reg.add_tag("nonexistent", "tag") is False

    def test_update_capability_index(self):
        reg = AgentRegistry()
        agent = _make_agent(capabilities=["old_cap"])
        reg.register(agent)
        agent.capabilities = ["new_cap"]
        reg.update_capability_index(agent)
        assert len(reg.find_by_capability("old_cap")) == 0
        assert len(reg.find_by_capability("new_cap")) == 1

    def test_get_statistics(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1", state=AgentState.ACTIVE)
        a1.workload = 0.5
        reg.register(a1)
        stats = reg.get_statistics()
        assert stats["total_agents"] == 1
        assert stats["avg_workload"] == 0.5

    def test_list_all(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1")
        a2 = _make_agent("A2")
        reg.register(a1)
        reg.register(a2)
        assert len(reg.list_all()) == 2

    def test_count_properties(self):
        reg = AgentRegistry()
        a1 = _make_agent("A1", state=AgentState.ACTIVE, capabilities=["cap1"])
        reg.register(a1)
        assert reg.count == 1
        assert reg.active_count == 1
        assert reg.capability_count >= 1


# ── SpawnerOrchestrator Testleri ────────────────────────────────

class TestSpawnerOrchestrator:
    """Spawner orkestratoru testleri."""

    def test_spawn_from_template(self):
        orch = SpawnerOrchestrator(max_agents=10)
        result = orch.spawn_agent(template_id="worker", name="W1")
        assert result["success"] is True
        assert result["name"] == "W1"

    def test_spawn_from_scratch(self):
        orch = SpawnerOrchestrator(max_agents=10)
        result = orch.spawn_agent(
            name="Custom",
            capabilities=["cap1"],
            config={"key": "val"},
        )
        assert result["success"] is True
        assert result["name"] == "Custom"

    def test_spawn_max_limit(self):
        orch = SpawnerOrchestrator(max_agents=1)
        orch.spawn_agent(name="A1")
        result = orch.spawn_agent(name="A2")
        assert result["success"] is False
        assert "limit" in result["reason"].lower()

    def test_spawn_nonexistent_template(self):
        orch = SpawnerOrchestrator()
        result = orch.spawn_agent(template_id="nonexistent")
        assert result["success"] is False

    def test_terminate_agent(self):
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(template_id="worker", name="ToKill")
        agent_id = res["agent_id"]
        result = orch.terminate_agent(agent_id, reason="Test")
        assert result["success"] is True
        assert result["type"] == "graceful"
        assert result["state_preserved"] is True

    def test_terminate_force(self):
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(name="ForceKill")
        agent_id = res["agent_id"]
        result = orch.terminate_agent(agent_id, force=True)
        assert result["success"] is True
        assert result["type"] == "force"

    def test_terminate_nonexistent(self):
        orch = SpawnerOrchestrator()
        result = orch.terminate_agent("nonexistent")
        assert result["success"] is False

    def test_clone_agent(self):
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(template_id="worker", name="Original")
        agent_id = res["agent_id"]
        result = orch.clone_agent(agent_id, name="Clone")
        assert result["success"] is True
        assert result["cloned_from"] == agent_id

    def test_clone_nonexistent(self):
        orch = SpawnerOrchestrator()
        result = orch.clone_agent("nonexistent")
        assert result["success"] is False

    def test_add_capability(self):
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(name="Cap", capabilities=["execute"])
        agent_id = res["agent_id"]
        result = orch.add_capability(agent_id, "analyze")
        assert result["success"] is True

    def test_remove_capability(self):
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(name="Cap", capabilities=["execute", "report"])
        agent_id = res["agent_id"]
        result = orch.remove_capability(agent_id, "report")
        assert result["success"] is True

    def test_get_snapshot(self):
        orch = SpawnerOrchestrator()
        orch.spawn_agent(template_id="worker", name="S1")
        snapshot = orch.get_snapshot()
        assert snapshot.total_agents >= 1
        assert snapshot.active_agents >= 1
        assert snapshot.health_score > 0

    def test_find_agents(self):
        orch = SpawnerOrchestrator()
        orch.spawn_agent(name="F1", capabilities=["search"], tags=["team1"])
        orch.spawn_agent(name="F2", capabilities=["execute"])
        found = orch.find_agents(capability="search")
        assert len(found) == 1

    def test_find_agents_by_tag(self):
        orch = SpawnerOrchestrator()
        orch.spawn_agent(name="T1", tags=["vip"])
        orch.spawn_agent(name="T2")
        found = orch.find_agents(tag="vip")
        assert len(found) == 1

    def test_fill_pool(self):
        orch = SpawnerOrchestrator(pool_size=3)
        added = orch.fill_pool("worker")
        assert added == 3
        assert orch.pool.total_agents == 3

    def test_spawn_from_pool(self):
        orch = SpawnerOrchestrator(pool_size=2)
        orch.fill_pool("worker")
        result = orch.spawn_from_pool()
        assert result["success"] is True
        assert result["from_pool"] is True

    def test_spawn_from_empty_pool(self):
        orch = SpawnerOrchestrator(pool_size=0)
        result = orch.spawn_from_pool()
        assert result["success"] is False

    def test_auto_scale_check(self):
        orch = SpawnerOrchestrator(auto_scale=True, pool_size=3)
        actions = orch.auto_scale_check()
        # Pool is empty so should suggest scaling
        assert isinstance(actions, list)

    def test_auto_scale_disabled(self):
        orch = SpawnerOrchestrator(auto_scale=False)
        actions = orch.auto_scale_check()
        assert actions == []

    def test_subsystem_access(self):
        orch = SpawnerOrchestrator()
        assert orch.templates is not None
        assert orch.engine is not None
        assert orch.lifecycle is not None
        assert orch.resources is not None
        assert orch.capabilities is not None
        assert orch.pool is not None
        assert orch.termination is not None
        assert orch.registry is not None


# ── Entegrasyon Testleri ────────────────────────────────────────

class TestSpawnerIntegration:
    """Entegrasyon testleri."""

    def test_full_lifecycle(self):
        """Tam yasam dongusu: spawn -> use -> terminate."""
        orch = SpawnerOrchestrator()

        # Spawn
        res = orch.spawn_agent(
            template_id="worker",
            name="FullLife",
            tags=["test"],
        )
        assert res["success"]
        agent_id = res["agent_id"]

        # Find
        found = orch.find_agents(tag="test")
        assert len(found) == 1

        # Add capability
        orch.add_capability(agent_id, "analyze")
        agent = orch.registry.get(agent_id)
        assert "analyze" in agent.capabilities

        # Snapshot
        snap = orch.get_snapshot()
        assert snap.active_agents >= 1

        # Terminate
        result = orch.terminate_agent(agent_id, reason="Done")
        assert result["success"]
        assert result["state_preserved"]

    def test_pool_lifecycle(self):
        """Havuz yasam dongusu: fill -> acquire -> release."""
        orch = SpawnerOrchestrator(pool_size=3)
        orch.fill_pool("worker")
        assert orch.pool.total_agents == 3

        # Acquire
        res = orch.spawn_from_pool()
        assert res["success"]
        assert orch.pool.idle_count == 2

        # Release
        orch.pool.release(res["agent_id"])
        assert orch.pool.idle_count == 3

    def test_clone_and_modify(self):
        """Klonla ve degistir."""
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(
            name="Original",
            capabilities=["search", "analyze"],
        )
        orig_id = res["agent_id"]

        # Clone
        clone_res = orch.clone_agent(orig_id, name="Modified")
        clone_id = clone_res["agent_id"]

        # Add new cap to clone
        orch.add_capability(clone_id, "report")
        clone = orch.registry.get(clone_id)
        assert "report" in clone.capabilities

        # Original unchanged
        orig = orch.registry.get(orig_id)
        assert "report" not in orig.capabilities

    def test_batch_spawn_and_cleanup(self):
        """Toplu olustur ve temizle."""
        orch = SpawnerOrchestrator(max_agents=20)

        # Batch spawn via engine
        agents = orch.engine.batch_spawn("worker", 5, "batch")
        for a in agents:
            orch.lifecycle.register(a)
            orch.lifecycle.activate(a.agent_id)
            orch.registry.register(a)

        assert orch.registry.count >= 5

        # Terminate all
        for a in agents:
            orch.terminate_agent(a.agent_id)

        assert orch.termination.total_terminated >= 5

    def test_resource_lifecycle(self):
        """Kaynak tahsis yasam dongusu."""
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(
            name="Resourced",
            resources={"memory": 512, "cpu": 1.0},
        )
        agent_id = res["agent_id"]

        # Check allocation
        alloc = orch.resources.get_allocation(agent_id)
        assert "memory" in alloc

        # Terminate - resources freed
        orch.terminate_agent(agent_id)
        alloc = orch.resources.get_allocation(agent_id)
        assert alloc == {}

    def test_capability_injection_chain(self):
        """Yetenek enjeksiyon zinciri."""
        orch = SpawnerOrchestrator()
        res = orch.spawn_agent(name="Capable", capabilities=[])
        agent_id = res["agent_id"]

        # Add capabilities with auto-deps
        orch.capabilities.add_capability(
            agent_id, "deploy", auto_resolve_deps=True,
        )
        agent = orch.registry.get(agent_id)
        # deploy requires build and test, test requires code_analyze
        assert "build" in agent.capabilities
        assert "test" in agent.capabilities
        assert "code_analyze" in agent.capabilities
        assert "deploy" in agent.capabilities

    def test_multi_template_hybrid(self):
        """Coklu sablon hibrit olusturma."""
        orch = SpawnerOrchestrator()

        # Hybrid from worker + security
        agent = orch.engine.spawn_hybrid(
            ["worker", "security"], name="HybridAgent",
        )
        assert agent is not None
        assert "execute" in agent.capabilities
        assert "scan" in agent.capabilities
