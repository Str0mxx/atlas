"""ATLAS Agent Spawner sistemi.

Dinamik agent olusturma, yasam dongusu yonetimi,
kaynak tahsisi, yetenek enjeksiyonu ve havuz yonetimi.
"""

from app.core.spawner.agent_pool import AgentPool
from app.core.spawner.agent_registry import AgentRegistry
from app.core.spawner.agent_template import AgentTemplateManager
from app.core.spawner.capability_injector import CapabilityInjector
from app.core.spawner.lifecycle_manager import LifecycleManager
from app.core.spawner.resource_allocator import ResourceAllocator
from app.core.spawner.spawn_engine import SpawnEngine
from app.core.spawner.spawner_orchestrator import SpawnerOrchestrator
from app.core.spawner.termination_handler import TerminationHandler

__all__ = [
    "AgentPool",
    "AgentRegistry",
    "AgentTemplateManager",
    "CapabilityInjector",
    "LifecycleManager",
    "ResourceAllocator",
    "SpawnEngine",
    "SpawnerOrchestrator",
    "TerminationHandler",
]
