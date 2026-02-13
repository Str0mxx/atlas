"""ATLAS Memory Palace veri modelleri.

Insansi hafiza modellemesi icin enum ve Pydantic modelleri:
epizodik, prosedurel, duygusal, iliskisel, calisma bellegi,
unutma egrisi, pekistirme ve otobiyografik hafiza.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class MemoryType(str, Enum):
    """Hafiza alt sistemi tipi."""

    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"
    WORKING = "working"
    AUTOBIOGRAPHICAL = "autobiographical"


class EmotionType(str, Enum):
    """Temel duygu siniflari (Plutchik modeli)."""

    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"


class Sentiment(str, Enum):
    """Basit duygu degerlendirmesi."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SkillLevel(str, Enum):
    """Beceri yeterlilik seviyesi."""

    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ProcessingMode(str, Enum):
    """Otomatik vs bilincli isleme modu."""

    AUTOMATIC = "automatic"
    CONTROLLED = "controlled"


class ConsolidationPhase(str, Enum):
    """Hafiza pekistirme asamasi."""

    ENCODING = "encoding"
    CONSOLIDATION = "consolidation"
    RETRIEVAL = "retrieval"
    RECONSOLIDATION = "reconsolidation"


class LifeChapterStatus(str, Enum):
    """Otobiyografik yasam bolumu durumu."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class MemoryStrength(str, Enum):
    """Hafiza gucu kategorisi."""

    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    FLASHBULB = "flashbulb"


class WorkingMemorySlotStatus(str, Enum):
    """Calisma bellegi slot durumu."""

    EMPTY = "empty"
    OCCUPIED = "occupied"
    LOCKED = "locked"


class AssociationType(str, Enum):
    """Iliskisel baglanti tipi."""

    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    EMOTIONAL = "emotional"
    CONTEXTUAL = "contextual"


class SchemaType(str, Enum):
    """Pekistirme sema tipi."""

    EVENT_SCRIPT = "event_script"
    CONCEPT_FRAME = "concept_frame"
    NARRATIVE_TEMPLATE = "narrative_template"
    PROCEDURAL_SCHEMA = "procedural_schema"


# === Epizodik Hafiza Modelleri ===


class Episode(BaseModel):
    """Tek bir olay kaydi.

    Attributes:
        id: Benzersiz olay kimlik numarasi.
        what: Ne oldugu.
        where: Nerede olduyu.
        when: Ne zaman oldugu.
        who: Katilimcilar.
        importance: Onem derecesi (0.0-1.0).
        memory_strength: Hafiza gucu.
        tags: Etiketler.
        context: Ek baglamsal bilgi.
        access_count: Erisim sayisi.
        last_accessed: Son erisim zamani.
        is_flashbulb: Flashbulb hafiza mi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    what: str
    where: str = ""
    when: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    who: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    memory_strength: MemoryStrength = MemoryStrength.MODERATE
    tags: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    access_count: int = 0
    last_accessed: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_flashbulb: bool = False


class EpisodeQuery(BaseModel):
    """Epizodik hafiza arama sorgusu.

    Attributes:
        time_start: Baslangic zamani filtresi.
        time_end: Bitis zamani filtresi.
        location: Konum filtresi.
        participants: Katilimci filtresi.
        tags: Etiket filtresi.
        min_importance: Minimum onem esigi.
        limit: Maksimum sonuc sayisi.
    """

    time_start: datetime | None = None
    time_end: datetime | None = None
    location: str | None = None
    participants: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    min_importance: float = 0.0
    limit: int = 10


# === Prosedurel Hafiza Modelleri ===


class SkillStep(BaseModel):
    """Beceri adimi.

    Attributes:
        order: Adim sirasi.
        description: Adim aciklamasi.
        duration_estimate: Tahmini sure (saniye).
    """

    order: int
    description: str
    duration_estimate: float = 0.0


class Skill(BaseModel):
    """Beceri kaydi.

    Attributes:
        id: Benzersiz beceri kimlik numarasi.
        name: Beceri adi.
        domain: Beceri alani.
        steps: Beceri adimlari.
        proficiency: Yeterlilik (0.0-1.0).
        level: Yeterlilik seviyesi.
        practice_count: Pratik sayisi.
        total_practice_time: Toplam pratik suresi (saniye).
        automaticity: Otomatiklik derecesi (0.0-1.0).
        processing_mode: Isleme modu.
        last_practiced: Son pratik zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    domain: str = ""
    steps: list[SkillStep] = Field(default_factory=list)
    proficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    level: SkillLevel = SkillLevel.NOVICE
    practice_count: int = 0
    total_practice_time: float = 0.0
    automaticity: float = Field(default=0.0, ge=0.0, le=1.0)
    processing_mode: ProcessingMode = ProcessingMode.CONTROLLED
    last_practiced: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PracticeLog(BaseModel):
    """Pratik kaydi.

    Attributes:
        skill_id: Iliskili beceri ID.
        duration: Pratik suresi (saniye).
        performance_score: Performans puani (0.0-1.0).
        practiced_at: Pratik zamani.
        notes: Notlar.
    """

    skill_id: str
    duration: float
    performance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    practiced_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


# === Duygusal Hafiza Modelleri ===


class EmotionalAssociation(BaseModel):
    """Hafiza-duygu iliskisi.

    Attributes:
        id: Benzersiz iliski kimlik numarasi.
        memory_id: Iliskili hafiza ID.
        emotion: Duygu tipi.
        intensity: Duygu yogunlugu (0.0-1.0).
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    memory_id: str
    emotion: EmotionType
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Preference(BaseModel):
    """Tercih kaydi.

    Attributes:
        id: Benzersiz tercih kimlik numarasi.
        subject: Konu.
        sentiment: Duygu degerlendirmesi.
        score: Tercih puani (-1.0 ile 1.0 arasi).
        interaction_count: Etkilesim sayisi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    subject: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    score: float = Field(default=0.0, ge=-1.0, le=1.0)
    interaction_count: int = 0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Unutma Egrisi Modelleri ===


class MemoryTrace(BaseModel):
    """Hafiza izi (unutma egrisi takibi).

    Attributes:
        id: Benzersiz iz kimlik numarasi.
        memory_id: Iliskili hafiza ID.
        memory_type: Hafiza tipi.
        strength: Hafiza gucu (0.0-1.0).
        stability: Stabilite parametresi (S).
        last_review: Son gozden gecirme zamani.
        next_review: Sonraki planlanan gozden gecirme.
        review_count: Gozden gecirme sayisi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    memory_id: str
    memory_type: MemoryType = MemoryType.EPISODIC
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    stability: float = Field(default=1.0, ge=0.0)
    last_review: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    next_review: datetime | None = None
    review_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewSchedule(BaseModel):
    """Tekrar zamanlama bilgisi.

    Attributes:
        memory_id: Hafiza ID.
        scheduled_at: Planlanan zaman.
        interval_seconds: Aralik (saniye).
        review_number: Kacinci tekrar.
    """

    memory_id: str
    scheduled_at: datetime
    interval_seconds: float
    review_number: int


# === Iliskisel Ag Modelleri ===


class ConceptNode(BaseModel):
    """Kavram dugumu.

    Attributes:
        id: Benzersiz dugum kimlik numarasi.
        name: Kavram adi.
        activation: Aktivasyon seviyesi (0.0-1.0).
        category: Kavram kategorisi.
        metadata: Ek bilgi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    activation: float = Field(default=0.0, ge=0.0, le=1.0)
    category: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConceptLink(BaseModel):
    """Kavramlar arasi baglanti.

    Attributes:
        source_id: Kaynak dugum ID.
        target_id: Hedef dugum ID.
        weight: Baglanti gucu (0.0-1.0).
        association_type: Iliski tipi.
    """

    source_id: str
    target_id: str
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    association_type: AssociationType = AssociationType.SEMANTIC
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActivationResult(BaseModel):
    """Yayilan aktivasyon sonucu.

    Attributes:
        node_id: Dugum ID.
        node_name: Dugum adi.
        activation_level: Aktivasyon seviyesi.
        depth: Yayilim derinligi.
    """

    node_id: str
    node_name: str
    activation_level: float
    depth: int


# === Pekistirme Modelleri ===


class ConsolidationCycle(BaseModel):
    """Pekistirme dongusu kaydi.

    Attributes:
        id: Benzersiz dongu kimlik numarasi.
        phase: Pekistirme asamasi.
        memories_processed: Islenen hafiza sayisi.
        patterns_found: Bulunan oruntu sayisi.
        memories_strengthened: Guclendirilen hafiza sayisi.
        memories_weakened: Zayiflanan hafiza sayisi.
        started_at: Baslangic zamani.
        completed_at: Bitis zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    phase: ConsolidationPhase = ConsolidationPhase.CONSOLIDATION
    memories_processed: int = 0
    patterns_found: int = 0
    memories_strengthened: int = 0
    memories_weakened: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class Schema(BaseModel):
    """Cikarilmis sema.

    Attributes:
        id: Benzersiz sema kimlik numarasi.
        name: Sema adi.
        schema_type: Sema tipi.
        pattern: Cikarilmis oruntu.
        source_memory_ids: Kaynak hafiza ID'leri.
        confidence: Guven derecesi (0.0-1.0).
        instance_count: Ornek sayisi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    schema_type: SchemaType = SchemaType.EVENT_SCRIPT
    pattern: dict[str, Any] = Field(default_factory=dict)
    source_memory_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    instance_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Otobiyografik Hafiza Modelleri ===


class LifeChapter(BaseModel):
    """Yasam bolumu.

    Attributes:
        id: Benzersiz bolum kimlik numarasi.
        title: Bolum basligi.
        description: Bolum aciklamasi.
        status: Bolum durumu.
        start_date: Baslangic tarihi.
        end_date: Bitis tarihi.
        episode_ids: Icerdigi olay ID'leri.
        themes: Temalar.
        core_beliefs: Cekirdek inanclar.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    status: LifeChapterStatus = LifeChapterStatus.ACTIVE
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: datetime | None = None
    episode_ids: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    core_beliefs: list[str] = Field(default_factory=list)


class PersonalTimeline(BaseModel):
    """Kisisel zaman cizgisi.

    Attributes:
        chapters: Yasam bolumleri.
        total_episodes: Toplam olay sayisi.
        identity_beliefs: Kimlik inanclari ve gucleri.
    """

    chapters: list[LifeChapter] = Field(default_factory=list)
    total_episodes: int = 0
    identity_beliefs: dict[str, float] = Field(default_factory=dict)


# === Calisma Bellegi Modelleri ===


class WorkingMemoryItem(BaseModel):
    """Calisma bellegi ogesi.

    Attributes:
        id: Benzersiz oge kimlik numarasi.
        content: Icerik.
        priority: Oncelik (0.0-1.0).
        cognitive_load: Bilissel yuk (0.0-1.0).
        chunk_id: Grup kimlik numarasi.
        added_at: Eklenme zamani.
        accessed_at: Son erisim zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: Any = None
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    cognitive_load: float = Field(default=0.1, ge=0.0, le=1.0)
    chunk_id: str | None = None
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkingMemoryState(BaseModel):
    """Calisma bellegi durumu.

    Attributes:
        items: Mevcut ogeler.
        capacity: Maksimum kapasite.
        current_load: Toplam bilissel yuk.
        chunks: Gruplama bilgisi.
    """

    items: list[WorkingMemoryItem] = Field(default_factory=list)
    capacity: int = 7
    current_load: float = 0.0
    chunks: dict[str, list[str]] = Field(default_factory=dict)


# === Yonetici / Sistem Arasi Modeller ===


class MemorySearchQuery(BaseModel):
    """Hafiza arama sorgusu.

    Attributes:
        query: Arama metni.
        memory_types: Aranacak hafiza tipleri (bos=hepsi).
        min_relevance: Minimum ilgi esigi.
        limit: Maksimum sonuc sayisi.
        include_emotional: Duygusal etiketleri dahil et.
        mood_filter: Ruh hali filtresi.
    """

    query: str
    memory_types: list[MemoryType] = Field(default_factory=list)
    min_relevance: float = 0.0
    limit: int = 10
    include_emotional: bool = True
    mood_filter: EmotionType | None = None


class MemorySearchResult(BaseModel):
    """Hafiza arama sonucu.

    Attributes:
        memory_id: Hafiza ID.
        memory_type: Hafiza tipi.
        content: Hafiza icerigi.
        relevance: Ilgi derecesi (0.0-1.0).
        emotional_tag: Duygusal etiket.
        strength: Hafiza gucu.
    """

    memory_id: str
    memory_type: MemoryType
    content: dict[str, Any] = Field(default_factory=dict)
    relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    emotional_tag: EmotionalAssociation | None = None
    strength: float = 1.0


class MemoryPalaceStats(BaseModel):
    """Memory Palace istatistikleri.

    Attributes:
        total_episodes: Toplam olay sayisi.
        total_skills: Toplam beceri sayisi.
        total_concepts: Toplam kavram sayisi.
        total_associations: Toplam iliski sayisi.
        working_memory_usage: Calisma bellegi kullanimi.
        avg_memory_strength: Ortalama hafiza gucu.
        consolidation_cycles: Pekistirme dongusu sayisi.
    """

    total_episodes: int = 0
    total_skills: int = 0
    total_concepts: int = 0
    total_associations: int = 0
    working_memory_usage: float = 0.0
    avg_memory_strength: float = 0.0
    consolidation_cycles: int = 0
