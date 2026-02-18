"""
Data Encryption & Privacy Engine modelleri.

Siralama, veri modelleri ve
yapilandirma siniflari.
"""

from enum import Enum

from pydantic import BaseModel, Field


class EncryptionAlgorithm(str, Enum):
    """Sifreleme algoritmasi."""

    AES_256_GCM = "AES-256-GCM"
    AES_256_CBC = "AES-256-CBC"
    AES_128_GCM = "AES-128-GCM"
    CHACHA20 = "ChaCha20-Poly1305"


class MaskType(str, Enum):
    """Maskeleme turu."""

    FULL = "full"
    PARTIAL = "partial"
    EMAIL = "email"
    REVERSIBLE = "reversible"


class PIIType(str, Enum):
    """PII turu."""

    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"


class LawfulBasis(str, Enum):
    """Hukuki dayanak."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTEREST = "vital_interest"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTEREST = (
        "legitimate_interest"
    )


class DeletionStatus(str, Enum):
    """Silme durumu."""

    PENDING = "pending"
    VERIFYING = "verifying"
    DISCOVERING = "discovering"
    DELETING = "deleting"
    COMPLETED = "completed"
    REJECTED = "rejected"


class PrivacyRiskLevel(str, Enum):
    """Gizlilik risk seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EncryptionKeyRecord(BaseModel):
    """Sifreleme anahtar kaydi."""

    key_id: str = ""
    name: str = ""
    algorithm: EncryptionAlgorithm = (
        EncryptionAlgorithm.AES_256_GCM
    )
    purpose: str = "general"
    version: int = 1
    active: bool = True


class EncryptedDataRecord(BaseModel):
    """Sifreli veri kaydi."""

    encryption_id: str = ""
    key_id: str = ""
    algorithm: str = ""
    ciphertext: str = ""
    context: str = ""
    original_size: int = 0


class MaskingRuleRecord(BaseModel):
    """Maskeleme kural kaydi."""

    rule_id: str = ""
    name: str = ""
    field: str = ""
    mask_type: MaskType = MaskType.FULL
    pattern: str = ""
    replacement: str = "***"
    active: bool = True


class ConsentRecord(BaseModel):
    """Rizalik kaydi."""

    consent_id: str = ""
    data_subject: str = ""
    purpose: str = ""
    lawful_basis: LawfulBasis = (
        LawfulBasis.CONSENT
    )
    granted: bool = True
    expiry_days: int = 365


class DeletionRequestRecord(BaseModel):
    """Silme talep kaydi."""

    request_id: str = ""
    data_subject: str = ""
    reason: str = ""
    scope: str = "all"
    status: DeletionStatus = (
        DeletionStatus.PENDING
    )
    verified: bool = False


class BreachRecord(BaseModel):
    """Ihlal kaydi."""

    breach_id: str = ""
    description: str = ""
    affected_count: int = 0
    severity: str = "medium"
    notify_authority: bool = False
    deadline_hours: int = 72


class PrivacyStatusRecord(BaseModel):
    """Gizlilik durum kaydi."""

    transit_channels: int = 0
    encryption_keys: int = 0
    encrypted_fields: int = 0
    masks_applied: int = 0
    records_anonymized: int = 0
    gdpr_consents: int = 0
    kvkk_inventory: int = 0
    deletion_requests: int = 0
    overall_compliant: bool = False
    overall_score: float = Field(
        default=0.0, ge=0.0, le=1.0
    )
