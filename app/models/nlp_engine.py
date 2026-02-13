"""ATLAS Natural Language Programming veri modelleri.

Dogal dil ile kod/sistem olusturma icin enum ve Pydantic modelleri:
niyet analizi, gorev ayristirma, gereksinim cikarma, spesifikasyon
uretimi, kod planlama, calistirma cevirisi, geri bildirim ve diyalog.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class IntentCategory(str, Enum):
    """Niyet kategorisi."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    QUERY = "query"
    EXECUTE = "execute"
    CONFIGURE = "configure"
    ANALYZE = "analyze"
    EXPLAIN = "explain"
    DEBUG = "debug"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Varlik tipi."""

    AGENT = "agent"
    TOOL = "tool"
    MODEL = "model"
    API = "api"
    DATABASE = "database"
    FILE = "file"
    SERVICE = "service"
    CONFIG = "config"
    METRIC = "metric"
    GENERIC = "generic"


class ConfidenceLevel(str, Enum):
    """Guven seviyesi."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AMBIGUOUS = "ambiguous"


class TaskRelation(str, Enum):
    """Gorev iliskisi."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    OPTIONAL = "optional"


class RequirementType(str, Enum):
    """Gereksinim tipi."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"


class RequirementPriority(str, Enum):
    """Gereksinim onceligi."""

    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


class SpecSectionType(str, Enum):
    """Spesifikasyon bolum tipi."""

    OVERVIEW = "overview"
    API_DESIGN = "api_design"
    DATA_MODEL = "data_model"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class CommandType(str, Enum):
    """Komut tipi."""

    AGENT_COMMAND = "agent_command"
    API_CALL = "api_call"
    DB_QUERY = "db_query"
    SHELL_COMMAND = "shell_command"
    SYSTEM_ACTION = "system_action"


class SafetyLevel(str, Enum):
    """Guvenlik seviyesi."""

    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class FeedbackType(str, Enum):
    """Geri bildirim tipi."""

    ERROR_EXPLANATION = "error_explanation"
    SUCCESS_CONFIRMATION = "success_confirmation"
    PROGRESS_REPORT = "progress_report"
    CLARIFICATION_REQUEST = "clarification_request"
    SUGGESTION = "suggestion"


class VerbosityLevel(str, Enum):
    """Ayrintili bilgi seviyesi."""

    MINIMAL = "minimal"
    NORMAL = "normal"
    DETAILED = "detailed"
    DEBUG = "debug"


class ConversationState(str, Enum):
    """Diyalog durumu."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    CLARIFYING = "clarifying"
    EXECUTING = "executing"
    REPORTING = "reporting"


class TopicStatus(str, Enum):
    """Konu durumu."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# === Niyet Analizi Modelleri ===


class Entity(BaseModel):
    """Cikarilmis varlik.

    Attributes:
        name: Varlik adi.
        entity_type: Varlik tipi.
        value: Varlik degeri.
        confidence: Guven derecesi (0.0-1.0).
        span: Kaynak metindeki pozisyon (baslangic, bitis).
    """

    name: str
    entity_type: EntityType = EntityType.GENERIC
    value: str = ""
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    span: tuple[int, int] = (0, 0)


class Intent(BaseModel):
    """Analiz edilmis niyet.

    Attributes:
        id: Benzersiz niyet kimlik numarasi.
        raw_input: Ham giris metni.
        category: Niyet kategorisi.
        action: Ana eylem.
        entities: Cikarilmis varliklar.
        confidence: Guven derecesi (0.0-1.0).
        confidence_level: Guven seviyesi.
        parameters: Ek parametreler.
        context_references: Baglam referanslari.
        ambiguities: Belirsizlikler.
        resolved: Belirsizlikler cozuldu mu.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_input: str
    category: IntentCategory = IntentCategory.UNKNOWN
    action: str = ""
    entities: list[Entity] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    parameters: dict[str, Any] = Field(default_factory=dict)
    context_references: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    resolved: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DialogueTurn(BaseModel):
    """Diyalog turu.

    Attributes:
        id: Benzersiz tur kimlik numarasi.
        role: Rol (user/system).
        content: Icerik.
        intent: Iliskili niyet.
        timestamp: Zaman damgasi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str = "user"
    content: str = ""
    intent: Intent | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Gorev Ayristirma Modelleri ===


class SubTask(BaseModel):
    """Alt gorev.

    Attributes:
        id: Benzersiz alt gorev kimlik numarasi.
        description: Gorev aciklamasi.
        dependencies: Bagimliliklar (diger alt gorev ID'leri).
        relation: Iliskili gorevlerle baginti tipi.
        estimated_complexity: Tahmini karmasiklik (1-10).
        validation_rules: Dogrulama kurallari.
        completed: Tamamlandi mi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    dependencies: list[str] = Field(default_factory=list)
    relation: TaskRelation = TaskRelation.SEQUENTIAL
    estimated_complexity: int = Field(default=1, ge=1, le=10)
    validation_rules: list[str] = Field(default_factory=list)
    completed: bool = False


class TaskDecomposition(BaseModel):
    """Gorev ayristirma sonucu.

    Attributes:
        id: Benzersiz ayristirma kimlik numarasi.
        original_task: Orijinal gorev aciklamasi.
        subtasks: Alt gorevler.
        total_complexity: Toplam karmasiklik.
        parallel_groups: Paralel calisabilecek gruplar.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    original_task: str
    subtasks: list[SubTask] = Field(default_factory=list)
    total_complexity: int = 0
    parallel_groups: list[list[str]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Gereksinim Cikarma Modelleri ===


class Requirement(BaseModel):
    """Gereksinim.

    Attributes:
        id: Benzersiz gereksinim kimlik numarasi.
        description: Gereksinim aciklamasi.
        requirement_type: Gereksinim tipi.
        priority: Oncelik.
        source_text: Kaynak metin.
        acceptance_criteria: Kabul kriterleri.
        constraints: Kisitlamalar.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    requirement_type: RequirementType = RequirementType.FUNCTIONAL
    priority: RequirementPriority = RequirementPriority.SHOULD
    source_text: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class RequirementSet(BaseModel):
    """Gereksinim seti.

    Attributes:
        id: Benzersiz set kimlik numarasi.
        title: Gereksinim seti basligi.
        requirements: Gereksinimler.
        assumptions: Varsayimlar.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    requirements: list[Requirement] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Spesifikasyon Uretimi Modelleri ===


class SpecSection(BaseModel):
    """Spesifikasyon bolumu.

    Attributes:
        id: Benzersiz bolum kimlik numarasi.
        section_type: Bolum tipi.
        title: Bolum basligi.
        content: Icerik.
        subsections: Alt bolumler.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    section_type: SpecSectionType = SpecSectionType.OVERVIEW
    title: str
    content: str = ""
    subsections: list[dict[str, str]] = Field(default_factory=list)


class TechnicalSpec(BaseModel):
    """Teknik spesifikasyon.

    Attributes:
        id: Benzersiz spesifikasyon kimlik numarasi.
        title: Spesifikasyon basligi.
        sections: Bolumler.
        api_endpoints: API endpoint tanimlari.
        data_models: Veri model tanimlari.
        architecture_notes: Mimari notlari.
        generated_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    sections: list[SpecSection] = Field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = Field(default_factory=list)
    data_models: list[dict[str, Any]] = Field(default_factory=list)
    architecture_notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Kod Planlama Modelleri ===


class PlannedFile(BaseModel):
    """Planlanmis dosya.

    Attributes:
        path: Dosya yolu.
        purpose: Dosya amaci.
        dependencies: Bagimliliklari.
        estimated_lines: Tahmini satir sayisi.
        priority: Olusturma onceligi.
    """

    path: str
    purpose: str = ""
    dependencies: list[str] = Field(default_factory=list)
    estimated_lines: int = 0
    priority: int = Field(default=1, ge=1)


class CodePlan(BaseModel):
    """Kod plani.

    Attributes:
        id: Benzersiz plan kimlik numarasi.
        title: Plan basligi.
        files: Planlanmis dosyalar.
        interfaces: Arayuz tanimlari.
        test_strategy: Test stratejisi.
        implementation_order: Uygulama sirasi (dosya yollari).
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    files: list[PlannedFile] = Field(default_factory=list)
    interfaces: list[dict[str, Any]] = Field(default_factory=list)
    test_strategy: str = ""
    implementation_order: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Calistirma Cevirisi Modelleri ===


class TranslatedCommand(BaseModel):
    """Cevrilmis komut.

    Attributes:
        id: Benzersiz komut kimlik numarasi.
        original_text: Orijinal dogal dil metni.
        command_type: Komut tipi.
        command: Cevrilmis komut.
        parameters: Parametreler.
        safety_level: Guvenlik seviyesi.
        safety_reason: Guvenlik gerekce.
        requires_confirmation: Onay gerektiriyor mu.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    original_text: str
    command_type: CommandType = CommandType.SYSTEM_ACTION
    command: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    safety_level: SafetyLevel = SafetyLevel.SAFE
    safety_reason: str = ""
    requires_confirmation: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Geri Bildirim Modelleri ===


class FeedbackMessage(BaseModel):
    """Geri bildirim mesaji.

    Attributes:
        id: Benzersiz mesaj kimlik numarasi.
        feedback_type: Geri bildirim tipi.
        content: Mesaj icerigi.
        technical_detail: Teknik detay.
        suggestions: Oneriler.
        verbosity: Ayrinti seviyesi.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    feedback_type: FeedbackType = FeedbackType.PROGRESS_REPORT
    content: str
    technical_detail: str = ""
    suggestions: list[str] = Field(default_factory=list)
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Diyalog Yonetimi Modelleri ===


class Topic(BaseModel):
    """Konusma konusu.

    Attributes:
        id: Benzersiz konu kimlik numarasi.
        name: Konu adi.
        status: Konu durumu.
        turn_ids: Iliskili tur ID'leri.
        context: Konu baglami.
        started_at: Baslangic zamani.
        ended_at: Bitis zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    status: TopicStatus = TopicStatus.ACTIVE
    turn_ids: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None


class ConversationContext(BaseModel):
    """Konusma baglami.

    Attributes:
        conversation_id: Benzersiz konusma kimlik numarasi.
        state: Diyalog durumu.
        turns: Diyalog turlari.
        topics: Konular.
        active_topic_id: Aktif konu ID.
        references: Referans haritasi (kisa ad -> tam ad).
        memory_keys: Hafiza anahtarlari.
        created_at: Olusturulma zamani.
    """

    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    state: ConversationState = ConversationState.IDLE
    turns: list[DialogueTurn] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    active_topic_id: str | None = None
    references: dict[str, str] = Field(default_factory=dict)
    memory_keys: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Orkestrator Modelleri ===


class NLPPipelineResult(BaseModel):
    """NLP pipeline sonucu.

    Attributes:
        id: Benzersiz sonuc kimlik numarasi.
        input_text: Giris metni.
        intent: Analiz edilmis niyet.
        decomposition: Gorev ayristirma.
        requirements: Gereksinimler.
        spec: Teknik spesifikasyon.
        code_plan: Kod plani.
        commands: Cevrilmis komutlar.
        feedback: Geri bildirim mesaji.
        success: Basarili mi.
        error: Hata mesaji.
        processing_time_ms: Isleme suresi (milisaniye).
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    input_text: str
    intent: Intent | None = None
    decomposition: TaskDecomposition | None = None
    requirements: RequirementSet | None = None
    spec: TechnicalSpec | None = None
    code_plan: CodePlan | None = None
    commands: list[TranslatedCommand] = Field(default_factory=list)
    feedback: FeedbackMessage | None = None
    success: bool = True
    error: str = ""
    processing_time_ms: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
