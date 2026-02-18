"""
Gizlilik orkestratoru modulu.

Tam gizlilik yonetimi,
Sifrele -> Maskele -> Anonimles -> Uyumlu,
tasarimla gizlilik, analitik.
"""

import logging
from typing import Any

from .anonymization_engine import (
    AnonymizationEngine,
)
from .at_rest_encryptor import (
    AtRestEncryptor,
)
from .data_masker import DataMasker
from .field_level_encryption import (
    FieldLevelEncryption,
)
from .gdpr_compliance_checker import (
    GDPRComplianceChecker,
)
from .kvkk_compliance_checker import (
    KVKKComplianceChecker,
)
from .right_to_delete_handler import (
    RightToDeleteHandler,
)
from .transit_encryptor import (
    TransitEncryptor,
)

logger = logging.getLogger(__name__)


class PrivacyOrchestrator:
    """Gizlilik orkestratoru.

    Attributes:
        transit: Transfer sifreleme.
        at_rest: Duraganlik sifreleme.
        field_enc: Alan sifreleme.
        masker: Veri maskeleme.
        anonymizer: Anonimlestime.
        gdpr: GDPR kontrolcu.
        kvkk: KVKK kontrolcu.
        delete_handler: Silme isleyici.
    """

    def __init__(self) -> None:
        """Orkestratoru baslatir."""
        self.transit = TransitEncryptor()
        self.at_rest = AtRestEncryptor()
        self.field_enc = (
            FieldLevelEncryption()
        )
        self.masker = DataMasker()
        self.anonymizer = (
            AnonymizationEngine()
        )
        self.gdpr = GDPRComplianceChecker()
        self.kvkk = KVKKComplianceChecker()
        self.delete_handler = (
            RightToDeleteHandler()
        )
        logger.info(
            "PrivacyOrchestrator "
            "baslatildi"
        )

    def protect_data(
        self,
        data: dict | None = None,
        encrypt_fields: (
            list[str] | None
        ) = None,
        mask_fields: (
            list[str] | None
        ) = None,
        anonymize_fields: (
            list[str] | None
        ) = None,
        record_id: str = "",
    ) -> dict[str, Any]:
        """Veriyi korur.

        Args:
            data: Veri.
            encrypt_fields: Sifrelenecek.
            mask_fields: Maskelenecek.
            anonymize_fields: Anonimlesecek.
            record_id: Kayit ID.

        Returns:
            Koruma bilgisi.
        """
        try:
            src = data or {}
            enc = encrypt_fields or []
            msk = mask_fields or []
            anon = anonymize_fields or []
            result: dict = {}
            actions: list[str] = []

            for k, v in src.items():
                val = str(v)
                if k in enc:
                    r = self.masker.mask_value(
                        value=val,
                        mask_type="full",
                    )
                    result[k] = r.get(
                        "masked", val
                    )
                    actions.append(
                        f"encrypted:{k}"
                    )
                elif k in msk:
                    r = self.masker.mask_value(
                        value=val,
                        mask_type="partial",
                    )
                    result[k] = r.get(
                        "masked", val
                    )
                    actions.append(
                        f"masked:{k}"
                    )
                elif k in anon:
                    result[k] = (
                        "[ANONYMIZED]"
                    )
                    actions.append(
                        f"anonymized:{k}"
                    )
                else:
                    result[k] = v

            return {
                "record_id": record_id,
                "protected_data": result,
                "actions": actions,
                "fields_protected": len(
                    actions
                ),
                "protected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "protected": False,
                "error": str(e),
            }

    def scan_pii(
        self,
        text: str = "",
        auto_mask: bool = False,
    ) -> dict[str, Any]:
        """PII tarar.

        Args:
            text: Metin.
            auto_mask: Oto maskeleme.

        Returns:
            Tarama bilgisi.
        """
        try:
            detect = (
                self.masker.detect_pii(
                    text=text
                )
            )

            masked_text = text
            if (
                auto_mask
                and detect.get("has_pii")
            ):
                mask_result = (
                    self.masker.mask_pii(
                        text=text
                    )
                )
                masked_text = (
                    mask_result.get(
                        "masked", text
                    )
                )

            return {
                "pii_found": detect.get(
                    "pii_found", []
                ),
                "pii_count": detect.get(
                    "pii_count", 0
                ),
                "has_pii": detect.get(
                    "has_pii", False
                ),
                "masked_text": (
                    masked_text
                    if auto_mask
                    else None
                ),
                "scanned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def handle_deletion_request(
        self,
        data_subject: str = "",
        reason: str = "",
        verified: bool = False,
        auto_execute: bool = False,
    ) -> dict[str, Any]:
        """Silme talebi isler.

        Args:
            data_subject: Veri sahibi.
            reason: Sebep.
            verified: Dogrulanmis mi.
            auto_execute: Oto islem.

        Returns:
            Islem bilgisi.
        """
        try:
            submit = (
                self.delete_handler
                .submit_request(
                    data_subject=(
                        data_subject
                    ),
                    reason=reason,
                    verified=verified,
                )
            )
            if not submit.get("submitted"):
                return submit

            rid = submit["request_id"]

            if auto_execute and verified:
                self.delete_handler\
                    .discover_data(
                        request_id=rid
                    )
                delete = (
                    self.delete_handler
                    .execute_deletion(
                        request_id=rid,
                        cascade=True,
                    )
                )
                return {
                    "request_id": rid,
                    "auto_executed": True,
                    "records_deleted": (
                        delete.get(
                            "records_deleted",
                            0,
                        )
                    ),
                    "handled": True,
                }

            return {
                "request_id": rid,
                "status": submit.get(
                    "status", "pending"
                ),
                "auto_executed": False,
                "handled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "handled": False,
                "error": str(e),
            }

    def compliance_status(
        self,
    ) -> dict[str, Any]:
        """Uyumluluk durumu getirir.

        Returns:
            Durum bilgisi.
        """
        try:
            gdpr = (
                self.gdpr.check_compliance()
            )
            kvkk = (
                self.kvkk.check_compliance()
            )

            overall = (
                gdpr.get("compliant", False)
                and kvkk.get(
                    "compliant", False
                )
            )
            avg_score = (
                gdpr.get("score", 0.0)
                + kvkk.get("score", 0.0)
            ) / 2

            return {
                "overall_compliant": (
                    overall
                ),
                "overall_score": round(
                    avg_score, 2
                ),
                "gdpr": {
                    "compliant": gdpr.get(
                        "compliant", False
                    ),
                    "score": gdpr.get(
                        "score", 0.0
                    ),
                    "issues": gdpr.get(
                        "issues", []
                    ),
                },
                "kvkk": {
                    "compliant": kvkk.get(
                        "compliant", False
                    ),
                    "score": kvkk.get(
                        "score", 0.0
                    ),
                    "issues": kvkk.get(
                        "issues", []
                    ),
                },
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir.

        Returns:
            Analitik bilgisi.
        """
        try:
            return {
                "transit_channels": (
                    self.transit
                    .channel_count
                ),
                "encryption_keys": (
                    self.at_rest.key_count
                ),
                "encrypted_fields": (
                    self.field_enc
                    .field_count
                ),
                "masks_applied": (
                    self.masker.mask_count
                ),
                "records_anonymized": (
                    self.anonymizer
                    .anonymized_count
                ),
                "gdpr_consents": (
                    self.gdpr.consent_count
                ),
                "kvkk_inventory": (
                    self.kvkk
                    .inventory_count
                ),
                "deletion_requests": (
                    self.delete_handler
                    .request_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            return {
                "transit": (
                    self.transit
                    .get_summary()
                ),
                "at_rest": (
                    self.at_rest
                    .get_summary()
                ),
                "field_encryption": (
                    self.field_enc
                    .get_summary()
                ),
                "masking": (
                    self.masker
                    .get_summary()
                ),
                "anonymization": (
                    self.anonymizer
                    .get_summary()
                ),
                "gdpr": (
                    self.gdpr
                    .get_summary()
                ),
                "kvkk": (
                    self.kvkk
                    .get_summary()
                ),
                "deletion": (
                    self.delete_handler
                    .get_summary()
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
