"""ATLAS dayaniklilik ve cevrimdisi calisma modulleri.

Baglanti kesildiginde graceful degradation, yerel karar verme,
durum kaliciligi ve otomatik failover saglar.
"""

from app.core.resilience.autonomous_fallback import (
    AutonomousFallback,
    EmergencyLevel,
    FallbackResponse,
)
from app.core.resilience.failover import (
    CircuitBreaker,
    CircuitState,
    FailoverManager,
    ServiceHealth,
)
from app.core.resilience.local_inference import LocalLLM, LocalLLMProvider
from app.core.resilience.offline_mode import (
    ConnectionStatus,
    OfflineManager,
    SyncItem,
)
from app.core.resilience.state_persistence import StatePersistence, StateSnapshot

__all__ = [
    "AutonomousFallback",
    "CircuitBreaker",
    "CircuitState",
    "ConnectionStatus",
    "EmergencyLevel",
    "FailoverManager",
    "FallbackResponse",
    "LocalLLM",
    "LocalLLMProvider",
    "OfflineManager",
    "ServiceHealth",
    "StatePersistence",
    "StateSnapshot",
    "SyncItem",
]
