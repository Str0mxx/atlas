"""ATLAS Autonomous Business Runner veri modelleri.

Otonom is yonetimi icin enum ve Pydantic modelleri:
firsat tespiti, strateji uretimi, uygulama motoru,
performans analizi, optimizasyon, geri bildirim ve
7/24 otonom dongu yonetimi.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class OpportunityType(str, Enum):
    """Firsat tipi."""

    MARKET_GAP = "market_gap"
    TREND = "trend"
    COMPETITOR_WEAKNESS = "competitor_weakness"
    CUSTOMER_NEED = "customer_need"
    COST_REDUCTION = "cost_reduction"
    PARTNERSHIP = "partnership"


class OpportunityStatus(str, Enum):
    """Firsat durumu."""

    DETECTED = "detected"
    EVALUATING = "evaluating"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class StrategyStatus(str, Enum):
    """Strateji durumu."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionPriority(str, Enum):
    """Aksiyon onceligi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutionStatus(str, Enum):
    """Uygulama durumu."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class CheckpointStatus(str, Enum):
    """Checkpoint durumu."""

    SAVED = "saved"
    RESTORED = "restored"
    DISCARDED = "discarded"


class KPIDirection(str, Enum):
    """KPI yonu (artis mi azalis mi iyi)."""

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    TARGET_IS_BEST = "target_is_best"


class AnomalySeverity(str, Enum):
    """Anomali siddeti."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExperimentStatus(str, Enum):
    """A/B test deney durumu."""

    DRAFT = "draft"
    RUNNING = "running"
    CONCLUDED = "concluded"
    CANCELLED = "cancelled"


class CyclePhase(str, Enum):
    """Otonom dongu asamasi."""

    DETECT = "detect"
    PLAN = "plan"
    EXECUTE = "execute"
    MEASURE = "measure"
    OPTIMIZE = "optimize"
    SLEEP = "sleep"


class CycleStatus(str, Enum):
    """Dongu durumu."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    EMERGENCY = "emergency"
    STOPPED = "stopped"


class EscalationLevel(str, Enum):
    """Eskalasyon seviyesi."""

    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    APPROVAL_NEEDED = "approval_needed"
    EMERGENCY = "emergency"


class InsightType(str, Enum):
    """Ogrenme tur tipi."""

    SUCCESS_PATTERN = "success_pattern"
    FAILURE_LESSON = "failure_lesson"
    MARKET_KNOWLEDGE = "market_knowledge"
    CUSTOMER_INSIGHT = "customer_insight"
    COMPETITIVE_INTEL = "competitive_intel"
    PROCESS_IMPROVEMENT = "process_improvement"


# === Firsat Tespiti Modelleri ===


class MarketSignal(BaseModel):
    """Pazar sinyali.

    Attributes:
        id: Benzersiz sinyal kimlik numarasi.
        source: Sinyal kaynagi.
        signal_type: Sinyal tipi.
        content: Sinyal icerigi.
        strength: Sinyal gucu (0.0-1.0).
        timestamp: Tespit zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str
    signal_type: str = ""
    content: str = ""
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Opportunity(BaseModel):
    """Tespit edilen is firsati.

    Attributes:
        id: Benzersiz firsat kimlik numarasi.
        title: Firsat basligi.
        description: Firsat aciklamasi.
        opportunity_type: Firsat tipi.
        status: Firsat durumu.
        confidence: Guven derecesi (0.0-1.0).
        potential_value: Tahmini deger.
        risk_level: Risk seviyesi (0.0-1.0).
        signals: Destekleyen pazar sinyalleri.
        tags: Etiketler.
        detected_at: Tespit zamani.
        expires_at: Son gecerlilik zamani.
        lead_score: Lead puani (0.0-1.0).
        metadata: Ek bilgi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    opportunity_type: OpportunityType = OpportunityType.MARKET_GAP
    status: OpportunityStatus = OpportunityStatus.DETECTED
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    potential_value: float = 0.0
    risk_level: float = Field(default=0.3, ge=0.0, le=1.0)
    signals: list[MarketSignal] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    lead_score: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendData(BaseModel):
    """Trend verisi.

    Attributes:
        keyword: Anahtar kelime.
        direction: Trend yonu (positive/negative/stable).
        momentum: Momentum gucu (0.0-1.0).
        data_points: Veri noktaları sayisi.
        period_days: Analiz suresi (gun).
    """

    keyword: str
    direction: str = "stable"
    momentum: float = Field(default=0.0, ge=0.0, le=1.0)
    data_points: int = 0
    period_days: int = 30


class CompetitorInfo(BaseModel):
    """Rakip bilgisi.

    Attributes:
        id: Benzersiz kimlik numarasi.
        name: Rakip adi.
        strengths: Guclu yonleri.
        weaknesses: Zayif yonleri.
        market_share: Pazar payi (0.0-1.0).
        threat_level: Tehdit seviyesi (0.0-1.0).
        last_updated: Son guncelleme zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    market_share: float = Field(default=0.0, ge=0.0, le=1.0)
    threat_level: float = Field(default=0.3, ge=0.0, le=1.0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Strateji Uretimi Modelleri ===


class ActionStep(BaseModel):
    """Aksiyon plani adimi.

    Attributes:
        id: Benzersiz adim kimlik numarasi.
        description: Adim aciklamasi.
        priority: Oncelik.
        estimated_duration_hours: Tahmini sure (saat).
        required_resources: Gerekli kaynaklar.
        agent_type: Atanacak agent tipi.
        dependencies: Bagimliliklari (diger adim ID'leri).
        completed: Tamamlandi mi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    priority: ActionPriority = ActionPriority.MEDIUM
    estimated_duration_hours: float = 1.0
    required_resources: list[str] = Field(default_factory=list)
    agent_type: str = ""
    dependencies: list[str] = Field(default_factory=list)
    completed: bool = False


class ResourceEstimate(BaseModel):
    """Kaynak tahmini.

    Attributes:
        resource_type: Kaynak tipi (zaman, para, insan, sistem).
        amount: Miktar.
        unit: Birim.
        confidence: Tahmin guveni (0.0-1.0).
    """

    resource_type: str
    amount: float
    unit: str = ""
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RiskAssessment(BaseModel):
    """Risk degerlendirmesi.

    Attributes:
        risk_id: Benzersiz risk kimlik numarasi.
        description: Risk aciklamasi.
        probability: Gerceklesme olasiligi (0.0-1.0).
        impact: Etki buyuklugu (0.0-1.0).
        mitigation: Risk azaltma stratejisi.
        risk_score: Hesaplanan risk skoru.
    """

    risk_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    probability: float = Field(default=0.3, ge=0.0, le=1.0)
    impact: float = Field(default=0.5, ge=0.0, le=1.0)
    mitigation: str = ""
    risk_score: float = 0.0


class Strategy(BaseModel):
    """Is stratejisi.

    Attributes:
        id: Benzersiz strateji kimlik numarasi.
        title: Strateji basligi.
        opportunity_id: Iliskili firsat ID.
        status: Strateji durumu.
        goals: Hedefler listesi.
        action_steps: Aksiyon plani adimlari.
        resources: Kaynak tahminleri.
        risks: Risk degerlendirmeleri.
        estimated_roi: Tahmini ROI (yuzde).
        timeline_days: Tahmini sure (gun).
        created_at: Olusturulma zamani.
        metadata: Ek bilgi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    opportunity_id: str = ""
    status: StrategyStatus = StrategyStatus.DRAFT
    goals: list[str] = Field(default_factory=list)
    action_steps: list[ActionStep] = Field(default_factory=list)
    resources: list[ResourceEstimate] = Field(default_factory=list)
    risks: list[RiskAssessment] = Field(default_factory=list)
    estimated_roi: float = 0.0
    timeline_days: int = 30
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# === Uygulama Motoru Modelleri ===


class TaskExecution(BaseModel):
    """Gorev yurutme kaydi.

    Attributes:
        id: Benzersiz yurutme kimlik numarasi.
        strategy_id: Iliskili strateji ID.
        action_step_id: Iliskili aksiyon adimi ID.
        status: Yurutme durumu.
        agent_id: Atanan agent ID.
        scheduled_at: Planlanan zaman.
        started_at: Basladigi zaman.
        completed_at: Tamamlandigi zaman.
        result: Sonuc bilgisi.
        error: Hata bilgisi.
        retry_count: Tekrar deneme sayisi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    action_step_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    agent_id: str = ""
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    retry_count: int = 0


class Checkpoint(BaseModel):
    """Uygulama checkpoint'i.

    Attributes:
        id: Benzersiz checkpoint kimlik numarasi.
        strategy_id: Iliskili strateji ID.
        status: Checkpoint durumu.
        state_snapshot: Durum goruntusu.
        created_at: Olusturulma zamani.
        description: Checkpoint aciklamasi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    status: CheckpointStatus = CheckpointStatus.SAVED
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""


# === Performans Analizi Modelleri ===


class KPIDefinition(BaseModel):
    """KPI tanimi.

    Attributes:
        id: Benzersiz KPI kimlik numarasi.
        name: KPI adi.
        description: KPI aciklamasi.
        unit: Birim.
        direction: Yonu (artis/azalis/hedef).
        target_value: Hedef deger.
        warning_threshold: Uyari esigi.
        critical_threshold: Kritik esik.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    unit: str = ""
    direction: KPIDirection = KPIDirection.HIGHER_IS_BETTER
    target_value: float = 0.0
    warning_threshold: float | None = None
    critical_threshold: float | None = None


class KPIDataPoint(BaseModel):
    """KPI veri noktasi.

    Attributes:
        kpi_id: KPI kimlik numarasi.
        value: Olculen deger.
        timestamp: Olcum zamani.
        context: Baglamsal bilgi.
    """

    kpi_id: str
    value: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict[str, Any] = Field(default_factory=dict)


class Anomaly(BaseModel):
    """Tespit edilen anomali.

    Attributes:
        id: Benzersiz anomali kimlik numarasi.
        kpi_id: Iliskili KPI ID.
        severity: Anomali siddeti.
        expected_value: Beklenen deger.
        actual_value: Gerceklesen deger.
        deviation_pct: Sapma yuzdesi.
        detected_at: Tespit zamani.
        description: Anomali aciklamasi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    kpi_id: str
    severity: AnomalySeverity = AnomalySeverity.MEDIUM
    expected_value: float = 0.0
    actual_value: float = 0.0
    deviation_pct: float = 0.0
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""


class PerformanceReport(BaseModel):
    """Performans raporu.

    Attributes:
        id: Benzersiz rapor kimlik numarasi.
        strategy_id: Iliskili strateji ID.
        period_start: Donem baslangici.
        period_end: Donem bitisi.
        kpi_results: KPI sonuclari (kpi_id -> deger).
        goal_progress: Hedef ilerleme (hedef -> yuzde).
        anomalies: Tespit edilen anomaliler.
        summary: Rapor ozeti.
        generated_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str = ""
    period_start: datetime | None = None
    period_end: datetime | None = None
    kpi_results: dict[str, float] = Field(default_factory=dict)
    goal_progress: dict[str, float] = Field(default_factory=dict)
    anomalies: list[Anomaly] = Field(default_factory=list)
    summary: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Optimizasyon Modelleri ===


class ExperimentVariant(BaseModel):
    """Deney varyanti.

    Attributes:
        id: Benzersiz varyant kimlik numarasi.
        name: Varyant adi.
        parameters: Parametre degerleri.
        sample_size: Ornek buyuklugu.
        metric_value: Olculen metrik degeri.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0
    metric_value: float | None = None


class Experiment(BaseModel):
    """A/B test deneyimi.

    Attributes:
        id: Benzersiz deney kimlik numarasi.
        name: Deney adi.
        description: Deney aciklamasi.
        status: Deney durumu.
        metric_name: Olculecek metrik adi.
        variants: Deney varyantlari.
        winner_variant_id: Kazanan varyant ID.
        confidence_level: Guven duzeyi.
        started_at: Baslangic zamani.
        completed_at: Bitis zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    status: ExperimentStatus = ExperimentStatus.DRAFT
    metric_name: str = ""
    variants: list[ExperimentVariant] = Field(default_factory=list)
    winner_variant_id: str | None = None
    confidence_level: float = Field(default=0.95, ge=0.0, le=1.0)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class OptimizationSuggestion(BaseModel):
    """Optimizasyon onerisi.

    Attributes:
        id: Benzersiz oneri kimlik numarasi.
        area: Optimizasyon alani.
        description: Oneri aciklamasi.
        expected_improvement: Beklenen iyilestirme (yuzde).
        effort_estimate: Efor tahmini (saat).
        priority: Oncelik.
        applied: Uygulandı mi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    area: str
    description: str
    expected_improvement: float = 0.0
    effort_estimate: float = 0.0
    priority: ActionPriority = ActionPriority.MEDIUM
    applied: bool = False


# === Geri Bildirim Dongusu Modelleri ===


class FeedbackEntry(BaseModel):
    """Geri bildirim kaydi.

    Attributes:
        id: Benzersiz kayit kimlik numarasi.
        strategy_id: Iliskili strateji ID.
        source: Geri bildirim kaynagi.
        outcome: Sonuc (basari/basarisizlik/kismen).
        lessons: Cikarilan dersler.
        metrics: Metrik sonuclari.
        recorded_at: Kayit zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    source: str = ""
    outcome: str = ""
    lessons: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Insight(BaseModel):
    """Cikarilmis ic goru.

    Attributes:
        id: Benzersiz ic goru kimlik numarasi.
        insight_type: Ic goru tipi.
        title: Baslik.
        description: Aciklama.
        confidence: Guven derecesi (0.0-1.0).
        source_feedback_ids: Kaynak geri bildirim ID'leri.
        actionable: Eyleme gecirilebilir mi.
        applied_count: Kac kez uygulandigi.
        created_at: Olusturulma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    insight_type: InsightType = InsightType.SUCCESS_PATTERN
    title: str
    description: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_feedback_ids: list[str] = Field(default_factory=list)
    actionable: bool = True
    applied_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StrategyAdjustment(BaseModel):
    """Strateji duzeltmesi.

    Attributes:
        id: Benzersiz duzeltme kimlik numarasi.
        strategy_id: Iliskili strateji ID.
        insight_id: Tetikleyen ic goru ID.
        adjustment_type: Duzeltme tipi.
        description: Aciklama.
        applied_at: Uygulama zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    insight_id: str = ""
    adjustment_type: str = ""
    description: str = ""
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# === Otonom Dongu Modelleri ===


class CycleRun(BaseModel):
    """Dongu calistirma kaydi.

    Attributes:
        id: Benzersiz calistirma kimlik numarasi.
        cycle_number: Dongu numarasi.
        phase: Mevcut asama.
        status: Dongu durumu.
        started_at: Baslangic zamani.
        completed_at: Bitis zamani.
        opportunities_found: Bulunan firsat sayisi.
        strategies_created: Olusturulan strateji sayisi.
        tasks_executed: Yurutulen gorev sayisi.
        optimizations_applied: Uygulanan optimizasyon sayisi.
        escalations: Eskalasyon sayisi.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    cycle_number: int = 0
    phase: CyclePhase = CyclePhase.DETECT
    status: CycleStatus = CycleStatus.IDLE
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    opportunities_found: int = 0
    strategies_created: int = 0
    tasks_executed: int = 0
    optimizations_applied: int = 0
    escalations: int = 0


class EscalationRequest(BaseModel):
    """Eskalasyon istegi.

    Attributes:
        id: Benzersiz istek kimlik numarasi.
        level: Eskalasyon seviyesi.
        reason: Eskalasyon nedeni.
        context: Baglamsal bilgi.
        requires_response: Yanit gerektiriyor mu.
        response: Verilen yanit.
        created_at: Olusturulma zamani.
        responded_at: Yanitlanma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    level: EscalationLevel = EscalationLevel.INFO
    reason: str
    context: dict[str, Any] = Field(default_factory=dict)
    requires_response: bool = False
    response: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: datetime | None = None


# === Is Hafizasi Modelleri ===


class SuccessPattern(BaseModel):
    """Basari oruntuleri.

    Attributes:
        id: Benzersiz oruntu kimlik numarasi.
        pattern_name: Oruntu adi.
        description: Aciklama.
        conditions: Kosullar.
        expected_outcome: Beklenen sonuc.
        confidence: Guven derecesi (0.0-1.0).
        usage_count: Kullanim sayisi.
        last_used: Son kullanim zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    pattern_name: str
    description: str = ""
    conditions: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    usage_count: int = 0
    last_used: datetime | None = None


class FailureLesson(BaseModel):
    """Basarisizlik dersi.

    Attributes:
        id: Benzersiz ders kimlik numarasi.
        title: Ders basligi.
        what_happened: Ne oldugu.
        root_cause: Kok neden.
        what_to_avoid: Kacinilmasi gerekenler.
        severity: Ciddiyet (0.0-1.0).
        occurred_at: Yasandigi zaman.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    what_happened: str = ""
    root_cause: str = ""
    what_to_avoid: str = ""
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarketKnowledge(BaseModel):
    """Pazar bilgisi.

    Attributes:
        id: Benzersiz bilgi kimlik numarasi.
        domain: Alan (sac ekimi, kozmetik, e-ticaret, vb).
        topic: Konu.
        content: Icerik.
        reliability: Guvenilirlik (0.0-1.0).
        source: Kaynak.
        updated_at: Guncelleme zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    domain: str
    topic: str
    content: str = ""
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CustomerInsight(BaseModel):
    """Musteri ic gorusu.

    Attributes:
        id: Benzersiz ic goru kimlik numarasi.
        segment: Musteri segmenti.
        insight: Ic goru.
        evidence: Kanitlar.
        impact_score: Etki puani (0.0-1.0).
        recorded_at: Kayit zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    segment: str
    insight: str
    evidence: list[str] = Field(default_factory=list)
    impact_score: float = Field(default=0.5, ge=0.0, le=1.0)
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BusinessMemoryStats(BaseModel):
    """Is hafizasi istatistikleri.

    Attributes:
        total_success_patterns: Toplam basari oruntuleri.
        total_failure_lessons: Toplam basarisizlik dersleri.
        total_market_knowledge: Toplam pazar bilgisi.
        total_customer_insights: Toplam musteri ic goruleri.
        total_competitor_records: Toplam rakip kayitlari.
        avg_pattern_confidence: Ortalama oruntu guveni.
    """

    total_success_patterns: int = 0
    total_failure_lessons: int = 0
    total_market_knowledge: int = 0
    total_customer_insights: int = 0
    total_competitor_records: int = 0
    avg_pattern_confidence: float = 0.0
