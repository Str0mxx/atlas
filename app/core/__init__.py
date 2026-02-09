"""ATLAS cekirdek modulleri.

Lazy import ile dairesel bagimliligi onler.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.autonomy.bdi_agent import BDIAgent
    from app.core.decision_matrix import (
        ActionType,
        DecisionMatrix,
        RiskLevel,
        UrgencyLevel,
    )
    from app.core.master_agent import MasterAgent
    from app.core.task_manager import TaskManager

__all__ = [
    "ActionType",
    "BDIAgent",
    "DecisionMatrix",
    "MasterAgent",
    "RiskLevel",
    "TaskManager",
    "UrgencyLevel",
]


def __getattr__(name: str) -> type:
    """Lazy import ile modulleri yukler."""
    if name in ("ActionType", "DecisionMatrix", "RiskLevel", "UrgencyLevel"):
        from app.core.decision_matrix import (
            ActionType,
            DecisionMatrix,
            RiskLevel,
            UrgencyLevel,
        )
        return {"ActionType": ActionType, "DecisionMatrix": DecisionMatrix,
                "RiskLevel": RiskLevel, "UrgencyLevel": UrgencyLevel}[name]
    if name == "MasterAgent":
        from app.core.master_agent import MasterAgent
        return MasterAgent
    if name == "TaskManager":
        from app.core.task_manager import TaskManager
        return TaskManager
    if name == "BDIAgent":
        from app.core.autonomy.bdi_agent import BDIAgent
        return BDIAgent
    raise AttributeError(f"module 'app.core' has no attribute {name!r}")
