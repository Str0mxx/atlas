"""ATLAS Knowledge Graph veri modelleri.

Bilgi grafi ve iliski yonetimi icin enum ve Pydantic modelleri:
varlik cikarma, iliski cikarma, graf olusturma, depolama,
sorgulama, cikarim, bilgi birlestirme ve ontoloji yonetimi.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class EntityType(str, Enum):
    """Varlik tipi."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    EVENT = "event"
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    METRIC = "metric"


class RelationType(str, Enum):
    """Iliski tipi."""

    IS_A = "is_a"
    HAS_A = "has_a"
    PART_OF = "part_of"
    CAUSES = "causes"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    LOCATED_IN = "located_in"
    WORKS_FOR = "works_for"
    PRODUCES = "produces"
    USES = "uses"


class NodeStatus(str, Enum):
    """Dugum durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    DELETED = "deleted"


class InferenceType(str, Enum):
    """Cikarim tipi."""

    TRANSITIVE = "transitive"
    INHERITANCE = "inheritance"
    INVERSE = "inverse"
    RULE_BASED = "rule_based"
    DERIVED = "derived"


class FusionStrategy(str, Enum):
    """Birlestirme stratejisi."""

    TRUST_BASED = "trust_based"
    MAJORITY_VOTE = "majority_vote"
    RECENCY = "recency"
    WEIGHTED = "weighted"


class ConflictResolution(str, Enum):
    """Catisma cozum yontemi."""

    KEEP_FIRST = "keep_first"
    KEEP_LATEST = "keep_latest"
    KEEP_TRUSTED = "keep_trusted"
    MERGE = "merge"
    FLAG = "flag"


class PropertyType(str, Enum):
    """Ozellik tipi."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    LIST = "list"


class QualityLevel(str, Enum):
    """Kalite seviyesi."""

    VERIFIED = "verified"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class QueryType(str, Enum):
    """Sorgu tipi."""

    PATH_FIND = "path_find"
    SUBGRAPH = "subgraph"
    PATTERN = "pattern"
    AGGREGATION = "aggregation"
    NATURAL_LANGUAGE = "natural_language"


# === Modeller ===


class KGEntity(BaseModel):
    """Bilgi grafi varligi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KGRelation(BaseModel):
    """Bilgi grafi iliskisi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    relation_type: RelationType = RelationType.RELATED_TO
    source_id: str = ""
    target_id: str = ""
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    bidirectional: bool = False
    temporal: bool = False
    start_time: datetime | None = None
    end_time: datetime | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GraphNode(BaseModel):
    """Graf dugumu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    entity: KGEntity = Field(default_factory=KGEntity)
    status: NodeStatus = NodeStatus.ACTIVE
    in_edges: list[str] = Field(default_factory=list)
    out_edges: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Graf kenari."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    relation: KGRelation = Field(default_factory=KGRelation)
    source_node_id: str = ""
    target_node_id: str = ""


class InferredFact(BaseModel):
    """Cikarilmis bilgi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    inference_type: InferenceType = InferenceType.RULE_BASED
    subject: str = ""
    predicate: str = ""
    obj: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    rule_name: str = ""
    inferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FusionResult(BaseModel):
    """Birlestirme sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy: FusionStrategy = FusionStrategy.TRUST_BASED
    entities_merged: int = 0
    relations_merged: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    quality: QualityLevel = QualityLevel.MEDIUM
    provenance: list[str] = Field(default_factory=list)
    merged_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class OntologyClass(BaseModel):
    """Ontoloji sinifi."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    parent_id: str | None = None
    properties: dict[str, PropertyType] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class QueryResult(BaseModel):
    """Sorgu sonucu."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    query_type: QueryType = QueryType.NATURAL_LANGUAGE
    query: str = ""
    nodes: list[str] = Field(default_factory=list)
    edges: list[str] = Field(default_factory=list)
    paths: list[list[str]] = Field(default_factory=list)
    aggregations: dict[str, Any] = Field(default_factory=dict)
    result_count: int = 0
    execution_time_ms: float = 0.0


class GraphStats(BaseModel):
    """Graf istatistikleri."""

    node_count: int = 0
    edge_count: int = 0
    entity_type_counts: dict[str, int] = Field(default_factory=dict)
    relation_type_counts: dict[str, int] = Field(default_factory=dict)
    avg_degree: float = 0.0
    connected_components: int = 0
    density: float = 0.0
