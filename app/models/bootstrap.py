"""Self-bootstrapping ve auto-provisioning veri modelleri.

Ortam tespiti, paket yonetimi, servis provizyon, bagimlilik cozumleme,
gorev analizi, oto-kurulum, kendi kendini guncelleme ve yetenek
olusturma modelleri.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class OSType(str, Enum):
    """Isletim sistemi tipi."""

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class PackageManagerType(str, Enum):
    """Paket yoneticisi tipi."""

    PIP = "pip"
    NPM = "npm"
    APT = "apt"
    BREW = "brew"
    CHOCO = "choco"
    DOCKER = "docker"


class PackageStatus(str, Enum):
    """Paket durumu."""

    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"


class InstallationStatus(str, Enum):
    """Kurulum islem durumu."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ServiceType(str, Enum):
    """Servis tipi."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNREACHABLE = "unreachable"
    NOT_INSTALLED = "not_installed"
    HEALTHY = "healthy"
    DEGRADED = "degraded"


class DependencyRelation(str, Enum):
    """Bagimlilik iliskisi."""

    REQUIRES = "requires"
    OPTIONAL = "optional"
    CONFLICTS = "conflicts"


class CapabilityCategory(str, Enum):
    """Yetenek kategorisi."""

    AGENT = "agent"
    TOOL = "tool"
    MONITOR = "monitor"
    API_CLIENT = "api_client"
    PLUGIN = "plugin"


class UpgradeStatus(str, Enum):
    """Guncelleme durumu."""

    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    DOWNLOADING = "downloading"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class GapSeverity(str, Enum):
    """Yetenek eksikligi siddeti."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# === Ortam Tespiti Modelleri ===


class SoftwareInfo(BaseModel):
    """Tespit edilen yazilim bilgisi.

    Attributes:
        name: Yazilim adi.
        path: Calistirilabilir dosya yolu.
        version: Tespit edilen surum.
        available: Kullanilabilir mi.
    """

    name: str
    path: str | None = None
    version: str | None = None
    available: bool = False


class ResourceInfo(BaseModel):
    """Sistem kaynak bilgisi.

    Attributes:
        cpu_cores: CPU cekirdek sayisi.
        total_ram_mb: Toplam RAM (MB).
        available_ram_mb: Kullanilabilir RAM (MB).
        total_disk_mb: Toplam disk alani (MB).
        available_disk_mb: Kullanilabilir disk alani (MB).
    """

    cpu_cores: int = 0
    total_ram_mb: float = 0.0
    available_ram_mb: float = 0.0
    total_disk_mb: float = 0.0
    available_disk_mb: float = 0.0


class NetworkInfo(BaseModel):
    """Ag yetenekleri bilgisi.

    Attributes:
        internet_access: Internet erisimi var mi.
        dns_available: DNS cozumleme calisiyor mu.
        available_ports: Kullanilabilir portlar listesi.
        checked_ports: Kontrol edilen portlar.
    """

    internet_access: bool = False
    dns_available: bool = False
    available_ports: list[int] = Field(default_factory=list)
    checked_ports: dict[int, bool] = Field(default_factory=dict)


class EnvironmentInfo(BaseModel):
    """Tam ortam bilgisi.

    Attributes:
        id: Benzersiz tarama kimlik numarasi.
        os_type: Isletim sistemi tipi.
        os_version: Isletim sistemi surumu.
        python_version: Python surumu.
        software: Tespit edilen yazilimlar.
        resources: Sistem kaynaklari.
        network: Ag yetenekleri.
        missing_dependencies: Eksik bagimliliklar.
        scanned_at: Tarama zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    os_type: OSType = OSType.UNKNOWN
    os_version: str = ""
    python_version: str = ""
    software: list[SoftwareInfo] = Field(default_factory=list)
    resources: ResourceInfo = Field(default_factory=ResourceInfo)
    network: NetworkInfo = Field(default_factory=NetworkInfo)
    missing_dependencies: list[str] = Field(default_factory=list)
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# === Paket Yonetimi Modelleri ===


class PackageInfo(BaseModel):
    """Paket bilgisi.

    Attributes:
        name: Paket adi.
        version: Mevcut surum.
        latest_version: En son surum.
        manager: Paket yoneticisi.
        status: Paket durumu.
    """

    name: str
    version: str | None = None
    latest_version: str | None = None
    manager: PackageManagerType = PackageManagerType.PIP
    status: PackageStatus = PackageStatus.UNKNOWN


class InstallationRecord(BaseModel):
    """Kurulum kaydi.

    Attributes:
        id: Benzersiz kayit kimlik numarasi.
        package_name: Paket adi.
        manager: Kullanilan paket yoneticisi.
        version: Kurulan surum.
        status: Kurulum durumu.
        dry_run: Kuru calistirma mi.
        started_at: Baslangic zamani.
        completed_at: Bitis zamani.
        error_message: Hata mesaji.
        rollback_info: Geri alma bilgisi.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    package_name: str
    manager: PackageManagerType = PackageManagerType.PIP
    version: str | None = None
    status: InstallationStatus = InstallationStatus.PENDING
    dry_run: bool = False
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: datetime | None = None
    error_message: str | None = None
    rollback_info: dict[str, Any] = Field(default_factory=dict)


# === Servis Provizyon Modelleri ===


class ServiceCheck(BaseModel):
    """Servis saglik kontrolu sonucu.

    Attributes:
        name: Servis adi.
        status: Servis durumu.
        host: Servis adresi.
        port: Servis portu.
        response_time_ms: Yanit suresi (ms).
        details: Ek detaylar.
        checked_at: Kontrol zamani.
    """

    name: str
    status: ServiceType = ServiceType.UNREACHABLE
    host: str = "localhost"
    port: int = 0
    response_time_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class PortCheck(BaseModel):
    """Port kullanilabilirlik kontrolu.

    Attributes:
        port: Port numarasi.
        available: Kullanilabilir mi.
        process_name: Portu kullanan islem adi.
    """

    port: int
    available: bool = True
    process_name: str | None = None


class SSLInfo(BaseModel):
    """SSL sertifika bilgisi.

    Attributes:
        domain: Alan adi.
        valid: Gecerli mi.
        expires_at: Son gecerlilik tarihi.
        issuer: Sertifika yetkilisi.
        days_until_expiry: Son kullanma gunu sayisi.
    """

    domain: str
    valid: bool = False
    expires_at: datetime | None = None
    issuer: str = ""
    days_until_expiry: int = 0


# === Bagimlilik Cozumleme Modelleri ===


class DependencyNode(BaseModel):
    """Bagimlilik graf dugumu.

    Attributes:
        name: Paket/bagimlilik adi.
        version_spec: Surum kisiti (orn: '>=1.0').
        relation: Bagimlilik iliskisi.
        dependencies: Alt bagimlilik adlari.
        resolved_version: Cozumlenmis surum.
    """

    name: str
    version_spec: str = ""
    relation: DependencyRelation = DependencyRelation.REQUIRES
    dependencies: list[str] = Field(default_factory=list)
    resolved_version: str | None = None


class DependencyGraph(BaseModel):
    """Bagimlilik grafi.

    Attributes:
        nodes: Dugum sozlugu (ad -> DependencyNode).
        install_order: Topolojik sirali kurulum listesi.
        has_cycles: Dongusel bagimlilik var mi.
        conflicts: Surum catismalari.
    """

    nodes: dict[str, DependencyNode] = Field(default_factory=dict)
    install_order: list[str] = Field(default_factory=list)
    has_cycles: bool = False
    conflicts: list[str] = Field(default_factory=list)


# === Gorev Analizi Modelleri ===


class ToolRequirement(BaseModel):
    """Gorev icin gerekli arac.

    Attributes:
        name: Arac adi.
        category: Arac kategorisi (yazilim, kutuphane, servis).
        available: Sistemde mevcut mu.
        install_suggestion: Kurulum onerisi.
    """

    name: str
    category: str = "software"
    available: bool = False
    install_suggestion: str = ""


class SkillGap(BaseModel):
    """Yetenek eksikligi.

    Attributes:
        capability: Eksik yetenek adi.
        severity: Eksiklik siddeti.
        description: Aciklama.
        resolution_options: Cozum secenekleri.
    """

    capability: str
    severity: GapSeverity = GapSeverity.MEDIUM
    description: str = ""
    resolution_options: list[str] = Field(default_factory=list)


class TaskAnalysis(BaseModel):
    """Gorev analiz sonucu.

    Attributes:
        id: Benzersiz analiz kimlik numarasi.
        task_description: Gorev aciklamasi.
        required_tools: Gerekli araclar.
        available_tools: Mevcut araclar.
        missing_tools: Eksik araclar.
        skill_gaps: Yetenek eksiklikleri.
        feasible: Gorev gerceklestirilebilir mi.
        confidence: Guven skoru (0.0-1.0).
        analyzed_at: Analiz zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_description: str = ""
    required_tools: list[ToolRequirement] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    missing_tools: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    feasible: bool = True
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    analyzed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# === Oto-Kurulum Modelleri ===


class InstallationPlan(BaseModel):
    """Kurulum plani.

    Attributes:
        id: Benzersiz plan kimlik numarasi.
        packages: Kurulacak paketler (sirali).
        total_packages: Toplam paket sayisi.
        requires_approval: Onay gerektirir mi.
        dry_run: Kuru calistirma mi.
        estimated_duration: Tahmini sure (saniye).
        status: Plan durumu.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    packages: list[InstallationRecord] = Field(default_factory=list)
    total_packages: int = 0
    requires_approval: bool = True
    dry_run: bool = False
    estimated_duration: float = 0.0
    status: InstallationStatus = InstallationStatus.PENDING


class InstallationResult(BaseModel):
    """Kurulum sonucu.

    Attributes:
        plan_id: Kurulum plan ID.
        success: Basarili mi.
        installed: Basariyla kurulan paketler.
        failed: Basarisiz paketler.
        rolled_back: Geri alinan paketler.
        total_duration: Toplam sure (saniye).
    """

    plan_id: str
    success: bool = True
    installed: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    rolled_back: list[str] = Field(default_factory=list)
    total_duration: float = 0.0


# === Guncelleme Modelleri ===


class VersionInfo(BaseModel):
    """Surum bilgisi.

    Attributes:
        current_version: Mevcut surum.
        latest_version: En son surum.
        update_available: Guncelleme mevcut mu.
        release_notes: Surum notlari.
        breaking_changes: Kirilici degisiklikler.
    """

    current_version: str = ""
    latest_version: str = ""
    update_available: bool = False
    release_notes: str = ""
    breaking_changes: list[str] = Field(default_factory=list)


class UpgradeRecord(BaseModel):
    """Guncelleme kaydi.

    Attributes:
        id: Benzersiz kayit kimlik numarasi.
        from_version: Onceki surum.
        to_version: Hedef surum.
        status: Guncelleme durumu.
        migration_steps: Migrasyon adimlari.
        started_at: Baslangic zamani.
        completed_at: Bitis zamani.
        rollback_available: Geri alma mumkun mu.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_version: str = ""
    to_version: str = ""
    status: UpgradeStatus = UpgradeStatus.UP_TO_DATE
    migration_steps: list[str] = Field(default_factory=list)
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    completed_at: datetime | None = None
    rollback_available: bool = True


class MigrationPlan(BaseModel):
    """Migrasyon plani.

    Attributes:
        db_migrations: Veritabani migrasyonlari.
        config_changes: Yapilandirma degisiklikleri.
        estimated_downtime: Tahmini kesinti suresi (saniye).
        reversible: Geri alinabilir mi.
    """

    db_migrations: list[str] = Field(default_factory=list)
    config_changes: dict[str, Any] = Field(default_factory=dict)
    estimated_downtime: float = 0.0
    reversible: bool = True


# === Yetenek Olusturma Modelleri ===


class CapabilityTemplate(BaseModel):
    """Yetenek sablonu.

    Attributes:
        id: Benzersiz sablon kimlik numarasi.
        name: Sablon adi.
        category: Yetenek kategorisi.
        description: Sablon aciklamasi.
        base_class: Temel sinif adi.
        methods: Metot tanimlari.
        dependencies: Gereken paketler.
        generated_at: Olusturma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: CapabilityCategory = CapabilityCategory.TOOL
    description: str = ""
    base_class: str = ""
    methods: list[dict[str, Any]] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class ScaffoldResult(BaseModel):
    """Scaffold uretim sonucu.

    Attributes:
        template_id: Kullanilan sablon ID.
        files_generated: Uretilen dosya yollari.
        total_loc: Toplam satir sayisi.
        success: Basarili mi.
    """

    template_id: str
    files_generated: list[str] = Field(default_factory=list)
    total_loc: int = 0
    success: bool = True
