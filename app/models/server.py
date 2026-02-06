"""Sunucu izleme veri modelleri.

ServerMonitorAgent tarafindan kullanilan tum metrik ve yapilandirma modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class MetricStatus(str, Enum):
    """Metrik durum seviyeleri."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class ServerConfig(BaseModel):
    """Sunucu baglanti yapilandirmasi.

    Attributes:
        host: Sunucu IP adresi veya hostname.
        user: SSH kullanici adi.
        key_path: SSH ozel anahtar dosya yolu.
        port: SSH port numarasi.
        services: Kontrol edilecek systemd servis listesi.
    """

    host: str
    user: str = "root"
    key_path: str = "~/.ssh/id_rsa"
    port: int = 22
    services: list[str] = Field(default_factory=list)


class MetricThresholds(BaseModel):
    """Metrik esik degerleri (yuzde olarak).

    Attributes:
        cpu_warning: CPU uyari esigi.
        cpu_critical: CPU kritik esigi.
        ram_warning: RAM uyari esigi.
        ram_critical: RAM kritik esigi.
        disk_warning: Disk uyari esigi.
        disk_critical: Disk kritik esigi.
    """

    cpu_warning: float = 70.0
    cpu_critical: float = 90.0
    ram_warning: float = 75.0
    ram_critical: float = 90.0
    disk_warning: float = 80.0
    disk_critical: float = 90.0


class CpuMetrics(BaseModel):
    """CPU metrik verileri.

    Attributes:
        usage_percent: CPU kullanim yuzdesi.
        load_1m: 1 dakikalik load average.
        load_5m: 5 dakikalik load average.
        load_15m: 15 dakikalik load average.
        status: Metrik durumu.
    """

    usage_percent: float = 0.0
    load_1m: float = 0.0
    load_5m: float = 0.0
    load_15m: float = 0.0
    status: MetricStatus = MetricStatus.NORMAL


class RamMetrics(BaseModel):
    """RAM metrik verileri.

    Attributes:
        total_mb: Toplam RAM (MB).
        used_mb: Kullanilan RAM (MB).
        available_mb: Kullanilabilir RAM (MB).
        usage_percent: RAM kullanim yuzdesi.
        status: Metrik durumu.
    """

    total_mb: int = 0
    used_mb: int = 0
    available_mb: int = 0
    usage_percent: float = 0.0
    status: MetricStatus = MetricStatus.NORMAL


class DiskMetrics(BaseModel):
    """Tek bir disk bolumu metrik verileri.

    Attributes:
        mount_point: Baglama noktasi.
        total_gb: Toplam kapasite (GB).
        used_gb: Kullanilan alan (GB).
        available_gb: Kullanilabilir alan (GB).
        usage_percent: Disk kullanim yuzdesi.
        status: Metrik durumu.
    """

    mount_point: str = "/"
    total_gb: float = 0.0
    used_gb: float = 0.0
    available_gb: float = 0.0
    usage_percent: float = 0.0
    status: MetricStatus = MetricStatus.NORMAL


class ServiceStatus(BaseModel):
    """Systemd servis durum bilgisi.

    Attributes:
        name: Servis adi.
        is_active: Servis calisiyor mu.
        status: Metrik durumu.
    """

    name: str
    is_active: bool = False
    status: MetricStatus = MetricStatus.NORMAL


class ServerMetrics(BaseModel):
    """Bir sunucunun tum metriklerini birlestiren ana model.

    Attributes:
        host: Sunucu adresi.
        reachable: Sunucuya erisilebilir mi.
        cpu: CPU metrikleri.
        ram: RAM metrikleri.
        disks: Disk metrikleri listesi.
        services: Servis durumlari listesi.
        overall_status: Genel durum (en kotu metrik baz alinir).
    """

    host: str
    reachable: bool = True
    cpu: CpuMetrics = Field(default_factory=CpuMetrics)
    ram: RamMetrics = Field(default_factory=RamMetrics)
    disks: list[DiskMetrics] = Field(default_factory=list)
    services: list[ServiceStatus] = Field(default_factory=list)
    overall_status: MetricStatus = MetricStatus.NORMAL
