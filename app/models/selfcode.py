"""ATLAS self-coding veri modelleri.

Kod uretimi, analiz, test uretimi, hata ayiklama, yeniden duzenleme,
agent fabrikasi, API entegrasyonu ve guvenli calistirma icin Pydantic modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# === Enum'lar ===


class CodeGenStrategy(str, Enum):
    """Kod uretim stratejisi."""

    TEMPLATE = "template"
    LLM = "llm"
    HYBRID = "hybrid"


class CodeStyle(str, Enum):
    """Kod stili."""

    PEP8 = "pep8"
    GOOGLE = "google"
    NUMPY = "numpy"
    CUSTOM = "custom"


class AnalysisSeverity(str, Enum):
    """Analiz bulgu siddeti."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CodeSmellType(str, Enum):
    """Kod koku tipi."""

    LONG_METHOD = "long_method"
    LARGE_CLASS = "large_class"
    DUPLICATE_CODE = "duplicate_code"
    DEAD_CODE = "dead_code"
    GOD_CLASS = "god_class"
    FEATURE_ENVY = "feature_envy"
    DATA_CLUMPS = "data_clumps"
    PRIMITIVE_OBSESSION = "primitive_obsession"


class RefactorType(str, Enum):
    """Yeniden duzenleme tipi."""

    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    RENAME = "rename"
    INLINE = "inline"
    MOVE = "move"
    DEAD_CODE_REMOVAL = "dead_code_removal"
    SIMPLIFY = "simplify"


class ExecutionStatus(str, Enum):
    """Calistirma durumu."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


class FixConfidence(str, Enum):
    """Duzeltme guveni."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CERTAIN = "certain"


class TestType(str, Enum):
    """Test tipi."""

    UNIT = "unit"
    INTEGRATION = "integration"
    EDGE_CASE = "edge_case"
    REGRESSION = "regression"
    PERFORMANCE = "performance"


class APIAuthType(str, Enum):
    """API kimlik dogrulama tipi."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    BASIC = "basic"


class PipelineStage(str, Enum):
    """Pipeline asamasi."""

    ANALYZE = "analyze"
    GENERATE = "generate"
    TEST = "test"
    DEBUG = "debug"
    REFACTOR = "refactor"
    DEPLOY = "deploy"


# === Pydantic Modeller ===


class CodeGenerationRequest(BaseModel):
    """Kod uretim istegi.

    Attributes:
        description: Ne uretileceginin aciklamasi.
        language: Programlama dili.
        strategy: Uretim stratejisi.
        style: Kod stili.
        context: Ek baglamsal bilgi.
        dependencies: Gerekli bagimliliklar.
        max_attempts: Maksimum deneme sayisi.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    description: str = ""
    language: str = "python"
    strategy: CodeGenStrategy = CodeGenStrategy.TEMPLATE
    style: CodeStyle = CodeStyle.PEP8
    context: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    max_attempts: int = 3


class GeneratedCode(BaseModel):
    """Uretilen kod sonucu.

    Attributes:
        request_id: Istek kimligi.
        code: Uretilen kod metni.
        language: Programlama dili.
        imports: Gerekli importlar.
        docstring: Olusturulan docstring.
        confidence: Uretim guveni (0-1).
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    request_id: str = ""
    code: str = ""
    language: str = "python"
    imports: list[str] = Field(default_factory=list)
    docstring: str = ""
    confidence: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalysisIssue(BaseModel):
    """Analiz sorunu.

    Attributes:
        message: Sorun aciklamasi.
        severity: Sorun siddeti.
        line: Satir numarasi.
        column: Sutun numarasi.
        rule: Ihlal edilen kural.
        suggestion: Duzeltme onerisi.
    """

    message: str = ""
    severity: AnalysisSeverity = AnalysisSeverity.INFO
    line: int = 0
    column: int = 0
    rule: str = ""
    suggestion: str = ""


class DependencyInfo(BaseModel):
    """Kod bagimliligi bilgisi.

    Attributes:
        module: Modul adi.
        names: Import edilen isimler.
        is_stdlib: Standart kutuphane mi.
        is_local: Yerel modul mu.
    """

    module: str = ""
    names: list[str] = Field(default_factory=list)
    is_stdlib: bool = False
    is_local: bool = False


class ComplexityMetrics(BaseModel):
    """Kod karmasiklik metrikleri.

    Attributes:
        cyclomatic: Siklomatik karmasiklik.
        cognitive: Bilissel karmasiklik.
        halstead_volume: Halstead hacmi.
        lines_of_code: Satir sayisi.
        maintainability_index: Bakim endeksi (0-100).
    """

    cyclomatic: int = 0
    cognitive: int = 0
    halstead_volume: float = 0.0
    lines_of_code: int = 0
    maintainability_index: float = 100.0


class CodeAnalysisReport(BaseModel):
    """Kod analiz raporu.

    Attributes:
        file_path: Analiz edilen dosya.
        issues: Bulunan sorunlar.
        dependencies: Cikartilan bagimliliklar.
        complexity: Karmasiklik metrikleri.
        code_smells: Kod kokulari.
        security_issues: Guvenlik sorunlari.
        score: Genel kalite puani (0-100).
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    file_path: str = ""
    issues: list[AnalysisIssue] = Field(default_factory=list)
    dependencies: list[DependencyInfo] = Field(default_factory=list)
    complexity: ComplexityMetrics = Field(default_factory=ComplexityMetrics)
    code_smells: list[CodeSmellType] = Field(default_factory=list)
    security_issues: list[AnalysisIssue] = Field(default_factory=list)
    score: float = 100.0
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class TestCase(BaseModel):
    """Test vakasi.

    Attributes:
        name: Test fonksiyonu adi.
        test_type: Test tipi.
        code: Test kodu.
        description: Test aciklamasi.
        target_function: Hedef fonksiyon adi.
        mocks: Mock gereksinimleri.
        fixtures: Fixture gereksinimleri.
    """

    name: str = ""
    test_type: TestType = TestType.UNIT
    code: str = ""
    description: str = ""
    target_function: str = ""
    mocks: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)


class TestSuite(BaseModel):
    """Test grubu.

    Attributes:
        name: Test sinif/modul adi.
        tests: Test vakalari.
        imports: Gerekli importlar.
        fixtures_code: Fixture tanimlari.
        coverage_target: Hedef kapsama yuzdesi.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str = ""
    tests: list[TestCase] = Field(default_factory=list)
    imports: list[str] = Field(default_factory=list)
    fixtures_code: str = ""
    coverage_target: float = 80.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class FixSuggestion(BaseModel):
    """Duzeltme onerisi.

    Attributes:
        description: Duzeltme aciklamasi.
        confidence: Guvence duzeyi.
        code_before: Hata oncesi kod.
        code_after: Duzeltilmis kod.
        line: Hedef satir numarasi.
        auto_fixable: Otomatik duzeltilebilir mi.
    """

    description: str = ""
    confidence: FixConfidence = FixConfidence.MEDIUM
    code_before: str = ""
    code_after: str = ""
    line: int = 0
    auto_fixable: bool = False


class DebugReport(BaseModel):
    """Hata ayiklama raporu.

    Attributes:
        error_type: Hata tipi.
        error_message: Hata mesaji.
        file_path: Hata dosyasi.
        line_number: Satir numarasi.
        stack_trace: Stack trace.
        root_cause: Kok neden analizi.
        suggestions: Duzeltme onerileri.
        auto_fixed: Otomatik duzeltildi mi.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    error_type: str = ""
    error_message: str = ""
    file_path: str = ""
    line_number: int = 0
    stack_trace: str = ""
    root_cause: str = ""
    suggestions: list[FixSuggestion] = Field(default_factory=list)
    auto_fixed: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RefactorPlan(BaseModel):
    """Yeniden duzenleme plani.

    Attributes:
        refactor_type: Duzenleme tipi.
        target: Hedef (fonksiyon, sinif, degisken adi).
        file_path: Hedef dosya.
        description: Aciklama.
        estimated_impact: Tahmini etki (0-1).
        breaking: Kirilici degisiklik mi.
        reversible: Geri alinabilir mi.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    refactor_type: RefactorType = RefactorType.SIMPLIFY
    target: str = ""
    file_path: str = ""
    description: str = ""
    estimated_impact: float = 0.0
    breaking: bool = False
    reversible: bool = True


class RefactorResult(BaseModel):
    """Yeniden duzenleme sonucu.

    Attributes:
        plan_id: Plan kimligi.
        success: Basarili mi.
        original_code: Orijinal kod.
        refactored_code: Duzenlenmis kod.
        changes_count: Degisiklik sayisi.
        lines_added: Eklenen satir sayisi.
        lines_removed: Silinen satir sayisi.
    """

    plan_id: str = ""
    success: bool = True
    original_code: str = ""
    refactored_code: str = ""
    changes_count: int = 0
    lines_added: int = 0
    lines_removed: int = 0


class ExecutionConfig(BaseModel):
    """Guvenli calistirma yapilandirmasi.

    Attributes:
        timeout: Zaman asimi (saniye).
        max_memory_mb: Maks bellek (MB).
        max_output_lines: Maks cikti satiri.
        allow_network: Ag erisimi izni.
        allow_filesystem: Dosya sistemi erisimi.
        working_dir: Calisma dizini.
    """

    timeout: float = 30.0
    max_memory_mb: int = 256
    max_output_lines: int = 1000
    allow_network: bool = False
    allow_filesystem: bool = False
    working_dir: str = ""


class ExecutionResult(BaseModel):
    """Calistirma sonucu.

    Attributes:
        status: Calistirma durumu.
        stdout: Standart cikti.
        stderr: Hata ciktisi.
        exit_code: Cikis kodu.
        duration: Gecen sure (saniye).
        memory_used_mb: Kullanilan bellek (MB).
        timed_out: Zaman asimina ugradi mi.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    status: ExecutionStatus = ExecutionStatus.PENDING
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration: float = 0.0
    memory_used_mb: float = 0.0
    timed_out: bool = False


class AgentBlueprint(BaseModel):
    """Agent fabrikasi sablonu.

    Attributes:
        name: Agent adi.
        description: Agent aciklamasi.
        capabilities: Yetenek listesi.
        tools: Arac baglantilari.
        base_class: Temel sinif.
        auto_register: Otomatik kayit.
        config: Ek yapilandirma.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str = ""
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    base_class: str = "BaseAgent"
    auto_register: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class APIEndpointSpec(BaseModel):
    """API endpoint spesifikasyonu.

    Attributes:
        path: Endpoint yolu.
        method: HTTP metodu.
        parameters: Parametreler.
        request_body: Istek govdesi.
        response_model: Yanit modeli.
        description: Aciklama.
    """

    path: str = ""
    method: str = "GET"
    parameters: dict[str, str] = Field(default_factory=dict)
    request_body: dict[str, Any] = Field(default_factory=dict)
    response_model: str = ""
    description: str = ""


class APISpec(BaseModel):
    """API spesifikasyonu.

    Attributes:
        title: API basligi.
        base_url: Temel URL.
        version: API surumu.
        auth_type: Kimlik dogrulama tipi.
        endpoints: Endpoint listesi.
        headers: Varsayilan basliklar.
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str = ""
    base_url: str = ""
    version: str = "1.0.0"
    auth_type: APIAuthType = APIAuthType.NONE
    endpoints: list[APIEndpointSpec] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)


class APIClientConfig(BaseModel):
    """Uretilen API istemci yapilandirmasi.

    Attributes:
        spec_id: API spec kimligi.
        client_code: Uretilen istemci kodu.
        auth_code: Kimlik dogrulama kodu.
        rate_limit: Saniyedeki istek limiti.
        retry_count: Yeniden deneme sayisi.
        timeout: Zaman asimi (saniye).
    """

    spec_id: str = ""
    client_code: str = ""
    auth_code: str = ""
    rate_limit: int = 10
    retry_count: int = 3
    timeout: float = 30.0


class PipelineResult(BaseModel):
    """Meta agent pipeline sonucu.

    Attributes:
        stages_completed: Tamamlanan asamalar.
        total_stages: Toplam asama.
        success: Pipeline basarili mi.
        artifacts: Uretilen ciktiler.
        errors: Hata listesi.
        duration: Toplam sure (saniye).
    """

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    stages_completed: list[PipelineStage] = Field(default_factory=list)
    total_stages: int = 0
    success: bool = True
    artifacts: dict[str, str] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    duration: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
