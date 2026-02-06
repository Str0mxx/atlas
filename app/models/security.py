"""Guvenlik agent'i veri modelleri.

Guvenlik taramasi sonuclarini, basarisiz giris girisimlerini,
engellenen IP'leri, acik portlari, SSL sertifika bilgilerini
ve supehli process'leri modellar.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecurityCheckType(str, Enum):
    """Guvenlik kontrol tipleri."""

    AUTH_LOG = "auth_log"
    FAIL2BAN = "fail2ban"
    OPEN_PORTS = "open_ports"
    SSL_CERT = "ssl_cert"
    SUSPICIOUS_PROCESS = "suspicious_process"


class ThreatLevel(str, Enum):
    """Tehdit seviyesi."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityScanConfig(BaseModel):
    """Guvenlik taramasi yapilandirmasi.

    Attributes:
        checks: Calistirilacak kontrol tipleri.
        auth_log_path: auth.log dosya yolu.
        syslog_path: syslog dosya yolu.
        failed_login_threshold: Uyari icin basarisiz giris esigi.
        ssl_domains: SSL kontrolu yapilacak domain listesi.
        allowed_ports: Beklenen acik portlar (bunlar disindakiler supehli).
        suspicious_commands: Supehli kabul edilecek process isimleri.
    """

    checks: list[SecurityCheckType] = Field(
        default_factory=lambda: list(SecurityCheckType),
    )
    auth_log_path: str = "/var/log/auth.log"
    syslog_path: str = "/var/log/syslog"
    failed_login_threshold: int = 5
    ssl_domains: list[str] = Field(default_factory=list)
    allowed_ports: list[int] = Field(
        default_factory=lambda: [22, 80, 443],
    )
    suspicious_commands: list[str] = Field(
        default_factory=lambda: [
            "nc", "ncat", "nmap", "masscan", "hydra", "john",
            "hashcat", "msfconsole", "cryptominer", "xmrig",
        ],
    )


class FailedLoginEntry(BaseModel):
    """Basarisiz giris girisimleri kaydi.

    Attributes:
        ip: Kaynak IP adresi.
        username: Denenen kullanici adi.
        count: Basarisiz giris sayisi.
        last_attempt: Son girisim zamani (log'dan ayristirilan).
        service: Hedef servis (sshd, vb.).
    """

    ip: str
    username: str = "unknown"
    count: int = 1
    last_attempt: str = ""
    service: str = "sshd"


class BannedIPEntry(BaseModel):
    """Fail2ban tarafindan engellenen IP kaydi.

    Attributes:
        ip: Engellenen IP adresi.
        jail: Fail2ban jail adi.
        ban_time: Engelleme zamani.
    """

    ip: str
    jail: str = "sshd"
    ban_time: str = ""


class OpenPort(BaseModel):
    """Acik port bilgisi.

    Attributes:
        port: Port numarasi.
        protocol: Protokol (tcp/udp).
        process: Portu kullanan process adi.
        pid: Process ID.
        is_expected: Beklenen bir port mu.
    """

    port: int
    protocol: str = "tcp"
    process: str = ""
    pid: int = 0
    is_expected: bool = True


class SSLCertInfo(BaseModel):
    """SSL sertifika bilgisi.

    Attributes:
        domain: Domain adi.
        issuer: Sertifika saglayicisi.
        expiry_date: Son kullanma tarihi.
        days_remaining: Kalan gun sayisi.
        is_valid: Sertifika gecerli mi.
    """

    domain: str
    issuer: str = ""
    expiry_date: str = ""
    days_remaining: int = 0
    is_valid: bool = True


class SuspiciousProcess(BaseModel):
    """Supehli process bilgisi.

    Attributes:
        pid: Process ID.
        user: Process sahibi kullanici.
        command: Calistirilan komut.
        cpu_percent: CPU kullanim yuzdesi.
        mem_percent: Bellek kullanim yuzdesi.
        reason: Neden supehli kabul edildi.
    """

    pid: int
    user: str = ""
    command: str = ""
    cpu_percent: float = 0.0
    mem_percent: float = 0.0
    reason: str = ""


class SecurityScanResult(BaseModel):
    """Guvenlik taramasi genel sonucu.

    Attributes:
        threat_level: Genel tehdit seviyesi.
        failed_logins: Basarisiz giris kayitlari.
        total_failed_attempts: Toplam basarisiz giris sayisi.
        banned_ips: Engellenen IP'ler.
        fail2ban_active: Fail2ban aktif mi.
        open_ports: Tespit edilen acik portlar.
        unexpected_ports: Beklenmeyen acik portlar.
        ssl_certs: SSL sertifika bilgileri.
        suspicious_processes: Supehli process'ler.
        summary: Tarama ozeti.
    """

    threat_level: ThreatLevel = ThreatLevel.NONE
    failed_logins: list[FailedLoginEntry] = Field(default_factory=list)
    total_failed_attempts: int = 0
    banned_ips: list[BannedIPEntry] = Field(default_factory=list)
    fail2ban_active: bool = False
    open_ports: list[OpenPort] = Field(default_factory=list)
    unexpected_ports: list[OpenPort] = Field(default_factory=list)
    ssl_certs: list[SSLCertInfo] = Field(default_factory=list)
    suspicious_processes: list[SuspiciousProcess] = Field(default_factory=list)
    summary: str = ""
