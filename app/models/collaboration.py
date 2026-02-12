"""Multi-Agent Collaboration veri modelleri.

Mesajlasma protokolu, muzakere, koordinasyon, takim yonetimi,
konsensus ve is akisi orkestrasyon modelleri.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class MessageType(str, Enum):
    """Agent mesaj tipi."""

    REQUEST = "request"
    RESPONSE = "response"
    INFORM = "inform"
    PROPOSE = "propose"
    ACCEPT = "accept"
    REJECT = "reject"
    CFP = "call_for_proposal"
    BROADCAST = "broadcast"


class MessagePriority(str, Enum):
    """Mesaj oncelik seviyesi."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NegotiationState(str, Enum):
    """Muzakere durumu."""

    OPEN = "open"
    BIDDING = "bidding"
    AWARDED = "awarded"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BidStatus(str, Enum):
    """Teklif durumu."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class TeamRole(str, Enum):
    """Takim rolu."""

    LEADER = "leader"
    MEMBER = "member"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


class TeamStatus(str, Enum):
    """Takim durumu."""

    FORMING = "forming"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    DISBANDED = "disbanded"


class VoteType(str, Enum):
    """Oy tipi."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class ConsensusMethod(str, Enum):
    """Konsensus yontemi."""

    MAJORITY = "majority"
    UNANIMOUS = "unanimous"
    WEIGHTED = "weighted"
    QUORUM = "quorum"


class WorkflowNodeType(str, Enum):
    """Is akisi dugum tipi."""

    TASK = "task"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    CONDITIONAL = "conditional"
    MERGE = "merge"


class WorkflowStatus(str, Enum):
    """Is akisi durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


# === Mesajlasma Modelleri ===


class AgentMessage(BaseModel):
    """Agentlar arasi mesaj.

    Attributes:
        id: Benzersiz mesaj kimlik numarasi.
        sender: Gonderen agent adi.
        receiver: Alici agent adi (None = broadcast).
        message_type: Mesaj tipi.
        priority: Mesaj onceligi.
        content: Mesaj icerigi.
        correlation_id: Iliskili mesaj ID (istek-yanit eslesmesi).
        topic: Mesaj konusu (pub/sub icin).
        timestamp: Gonderim zamani.
        ttl: Yasam suresi (saniye, 0 = sinirsiz).
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sender: str
    receiver: str | None = None
    message_type: MessageType = MessageType.INFORM
    priority: MessagePriority = MessagePriority.NORMAL
    content: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    topic: str | None = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    ttl: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Subscription(BaseModel):
    """Konu aboneligi.

    Attributes:
        agent_name: Abone agent adi.
        topic: Abone olunan konu.
        created_at: Abonelik zamani.
    """

    agent_name: str
    topic: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# === Muzakere Modelleri ===


class Bid(BaseModel):
    """Muzakere teklifi.

    Attributes:
        id: Benzersiz teklif kimlik numarasi.
        agent_name: Teklif veren agent adi.
        negotiation_id: Muzakere ID.
        price: Maliyet teklifi (dusuk = daha iyi).
        capability_score: Yetenek puani (0.0-1.0).
        estimated_duration: Tahmini sure (saniye).
        status: Teklif durumu.
        proposal: Detayli teklif icerigi.
        submitted_at: Teklif zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    negotiation_id: str = ""
    price: float = Field(default=0.0, ge=0.0)
    capability_score: float = Field(default=0.5, ge=0.0, le=1.0)
    estimated_duration: float = Field(default=0.0, ge=0.0)
    status: BidStatus = BidStatus.PENDING
    proposal: dict[str, Any] = Field(default_factory=dict)
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class Negotiation(BaseModel):
    """Muzakere oturumu.

    Attributes:
        id: Benzersiz muzakere kimlik numarasi.
        task_description: Gorev aciklamasi.
        initiator: Baslatan agent adi.
        state: Muzakere durumu.
        bids: Gelen teklifler.
        winner: Kazanan agent adi.
        deadline: Teklif son tarihi (saniye).
        criteria: Degerlendirme kriterleri ve agirliklar.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    initiator: str = ""
    state: NegotiationState = NegotiationState.OPEN
    bids: list[Bid] = Field(default_factory=list)
    winner: str | None = None
    deadline: float = 30.0
    criteria: dict[str, float] = Field(default_factory=lambda: {
        "capability_score": 0.5,
        "price": 0.3,
        "estimated_duration": 0.2,
    })
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# === Takim Modelleri ===


class TeamMember(BaseModel):
    """Takim uyesi.

    Attributes:
        agent_name: Agent adi.
        role: Takim rolu.
        capabilities: Yetenek listesi.
        workload: Mevcut is yuku (0.0-1.0).
        joined_at: Katilim zamani.
    """

    agent_name: str
    role: TeamRole = TeamRole.MEMBER
    capabilities: list[str] = Field(default_factory=list)
    workload: float = Field(default=0.0, ge=0.0, le=1.0)
    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class Team(BaseModel):
    """Agent takimi.

    Attributes:
        id: Benzersiz takim kimlik numarasi.
        name: Takim adi.
        objective: Takim hedefi.
        members: Takim uyeleri.
        status: Takim durumu.
        required_capabilities: Gerekli yetenekler.
        created_at: Olusturulma zamani.
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    objective: str = ""
    members: list[TeamMember] = Field(default_factory=list)
    status: TeamStatus = TeamStatus.FORMING
    required_capabilities: list[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


# === Konsensus Modelleri ===


class Vote(BaseModel):
    """Oy kaydi.

    Attributes:
        agent_name: Oy veren agent adi.
        vote_type: Oy tipi.
        weight: Oy agirligi (agirlikli oylamada).
        reason: Oy gerekçesi.
        cast_at: Oy verme zamani.
    """

    agent_name: str
    vote_type: VoteType = VoteType.APPROVE
    weight: float = Field(default=1.0, ge=0.0)
    reason: str = ""
    cast_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ConsensusSession(BaseModel):
    """Konsensus oturumu.

    Attributes:
        id: Benzersiz oturum kimlik numarasi.
        topic: Oylama konusu.
        method: Konsensus yontemi.
        votes: Oylar.
        quorum: Yeter sayi (0.0-1.0, katilimci orani).
        resolved: Sonuclanmis mi.
        result: Sonuc (approve/reject).
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    method: ConsensusMethod = ConsensusMethod.MAJORITY
    votes: list[Vote] = Field(default_factory=list)
    quorum: float = Field(default=0.5, ge=0.0, le=1.0)
    resolved: bool = False
    result: VoteType | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# === Is Akisi Modelleri ===


class WorkflowNode(BaseModel):
    """Is akisi dugumu.

    Attributes:
        id: Benzersiz dugum kimlik numarasi.
        name: Dugum adi.
        node_type: Dugum tipi (task, parallel, sequence, conditional, merge).
        agent_name: Atanan agent adi (task tipi icin).
        task_params: Gorev parametreleri.
        children: Alt dugum ID listesi.
        condition: Kosul ifadesi (conditional tipi icin).
        status: Dugum durumu.
        result: Calisma sonucu.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    node_type: WorkflowNodeType = WorkflowNodeType.TASK
    agent_name: str | None = None
    task_params: dict[str, Any] = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)
    condition: str | None = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: dict[str, Any] | None = None


class WorkflowDefinition(BaseModel):
    """Is akisi tanimi.

    Attributes:
        id: Benzersiz is akisi kimlik numarasi.
        name: Is akisi adi.
        description: Aciklama.
        nodes: Dugum sozlugu (id -> WorkflowNode).
        root_id: Kok dugum ID.
        status: Genel durum.
        created_at: Olusturulma zamani.
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    nodes: dict[str, WorkflowNode] = Field(default_factory=dict)
    root_id: str | None = None
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    """Is akisi sonucu.

    Attributes:
        workflow_id: Is akisi ID.
        success: Basarili mi.
        node_results: Dugum bazli sonuclar (dugum_id -> sonuc).
        total_duration: Toplam sure (saniye).
        failed_nodes: Basarisiz dugum ID listesi.
    """

    workflow_id: str
    success: bool = True
    node_results: dict[str, Any] = Field(default_factory=dict)
    total_duration: float = 0.0
    failed_nodes: list[str] = Field(default_factory=list)
