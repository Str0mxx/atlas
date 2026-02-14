"""ATLAS Swarm Intelligence modelleri.

Suru zekasi, kolektif karar alma, feromon sistemi,
oylama, gorev acik artirmasi ve hata toleransi modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SwarmState(str, Enum):
    """Suru durumu."""

    FORMING = "forming"
    ACTIVE = "active"
    WORKING = "working"
    CONVERGING = "converging"
    DISSOLVED = "dissolved"


class PheromoneType(str, Enum):
    """Feromon tipi."""

    ATTRACTION = "attraction"
    REPULSION = "repulsion"
    TRAIL = "trail"
    ALARM = "alarm"
    SUCCESS = "success"


class VoteType(str, Enum):
    """Oy tipi."""

    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"
    QUORUM = "quorum"


class AuctionState(str, Enum):
    """Acik artirma durumu."""

    OPEN = "open"
    BIDDING = "bidding"
    CLOSED = "closed"
    AWARDED = "awarded"
    CANCELLED = "cancelled"


class FaultAction(str, Enum):
    """Hata aksiyonu."""

    REASSIGN = "reassign"
    RETRY = "retry"
    SKIP = "skip"
    ESCALATE = "escalate"
    HEAL = "heal"


class BalanceStrategy(str, Enum):
    """Dengeleme stratejisi."""

    WORK_STEALING = "work_stealing"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    CAPABILITY_MATCH = "capability_match"


class SwarmInfo(BaseModel):
    """Suru bilgisi."""

    swarm_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    name: str = ""
    state: SwarmState = SwarmState.FORMING
    goal: str = ""
    members: list[str] = Field(default_factory=list)
    leader_id: str = ""
    min_size: int = 2
    max_size: int = 20
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class PheromoneMarker(BaseModel):
    """Feromon isareti."""

    marker_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    pheromone_type: PheromoneType = PheromoneType.TRAIL
    source_agent: str = ""
    location: str = ""
    intensity: float = Field(default=1.0, ge=0.0, le=1.0)
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class VoteSession(BaseModel):
    """Oylama oturumu."""

    session_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    topic: str = ""
    vote_type: VoteType = VoteType.MAJORITY
    options: list[str] = Field(default_factory=list)
    votes: dict[str, str] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    quorum: int = 0
    resolved: bool = False
    winner: str = ""


class AuctionRecord(BaseModel):
    """Acik artirma kaydi."""

    auction_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    task_id: str = ""
    task_description: str = ""
    state: AuctionState = AuctionState.OPEN
    required_capabilities: list[str] = Field(default_factory=list)
    bids: dict[str, float] = Field(default_factory=dict)
    winner_id: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class FaultEvent(BaseModel):
    """Hata olayi."""

    event_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    agent_id: str = ""
    task_id: str = ""
    fault_type: str = ""
    action_taken: FaultAction = FaultAction.REASSIGN
    resolved: bool = False
    reassigned_to: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class SwarmSnapshot(BaseModel):
    """Suru anlik goruntusu."""

    total_swarms: int = 0
    active_swarms: int = 0
    total_members: int = 0
    active_auctions: int = 0
    active_votes: int = 0
    total_pheromones: int = 0
    fault_events: int = 0
    avg_workload: float = 0.0
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
