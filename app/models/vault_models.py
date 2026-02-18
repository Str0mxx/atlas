"""Vault & Secret Manager modelleri."""

from enum import Enum

from pydantic import BaseModel, Field


class SecretCategory(str, Enum):
    """Gizli bilgi kategorisi."""

    GENERAL = "general"
    API_KEY = "api_key"
    DATABASE = "database"
    CREDENTIAL = "credential"
    CERTIFICATE = "certificate"
    TOKEN = "token"


class EncryptionAlgorithm(str, Enum):
    """Sifreleme algoritmasi."""

    AES256 = "aes256"
    AES128 = "aes128"
    RSA = "rsa"
    CHACHA20 = "chacha20"


class TokenScope(str, Enum):
    """Token kapsami."""

    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    DELETE = "delete"
    ROTATE = "rotate"


class ScanSeverity(str, Enum):
    """Tarama ciddiyeti."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RevocationStatus(str, Enum):
    """Iptal durumu."""

    PENDING = "pending"
    COMPLETED = "completed"
    RECOVERED = "recovered"
    FAILED = "failed"


class AuditAction(str, Enum):
    """Denetim aksiyonu."""

    STORE = "store"
    ACCESS = "access"
    UPDATE = "update"
    DELETE = "delete"
    ROTATE = "rotate"
    REVOKE = "revoke"
    SCAN = "scan"


class SecretRecord(BaseModel):
    """Gizli bilgi kaydi."""

    name: str = ""
    category: str = "general"
    owner: str = ""
    encrypted: bool = True
    version: int = 1


class KeyRecord(BaseModel):
    """Anahtar kaydi."""

    key_name: str = ""
    algorithm: str = "aes256"
    rotation_days: int = 90
    owner: str = ""
    version: int = 1


class TokenRecord(BaseModel):
    """Token kaydi."""

    user_id: str = ""
    scopes: list[str] = Field(
        default_factory=list
    )
    ttl_hours: int = 24
    description: str = ""


class ScanResult(BaseModel):
    """Tarama sonucu."""

    source: str = ""
    source_type: str = "code"
    leak_detected: bool = False
    findings_count: int = 0


class RevocationRecord(BaseModel):
    """Iptal kaydi."""

    target_type: str = "secret"
    target_id: str = ""
    reason: str = ""
    severity: str = "high"
    recovered: bool = False


class AuditEntry(BaseModel):
    """Denetim kaydi."""

    action: str = ""
    resource: str = ""
    user_id: str = ""
    result: str = "success"
    details: str = ""
