"""ATLAS Varlık Gizlilik Yöneticisi modulu.

Veri saklama, erişim kontrolü,
anonimleştirme, onay takibi, GDPR uyumu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EntityPrivacyManager:
    """Varlık gizlilik yöneticisi.

    Varlık verisi gizliliğini yönetir.

    Attributes:
        _consent: Onay kayıtları.
        _access_log: Erişim günlüğü.
        _retention: Saklama politikaları.
    """

    def __init__(
        self,
        retention_days: int = 365,
        privacy_mode: str = "standard",
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            retention_days: Saklama süresi.
            privacy_mode: Gizlilik modu.
        """
        self._consent: dict[
            str, dict[str, Any]
        ] = {}
        self._access_log: list[
            dict[str, Any]
        ] = []
        self._retention_days = retention_days
        self._privacy_mode = privacy_mode
        self._anonymized: set[str] = set()
        self._stats = {
            "consents": 0,
            "access_checks": 0,
            "anonymizations": 0,
        }

        logger.info(
            "EntityPrivacyManager baslatildi",
        )

    def set_consent(
        self,
        entity_id: str,
        consent_type: str,
        status: str = "granted",
        expiry_days: int | None = None,
    ) -> dict[str, Any]:
        """Onay ayarlar.

        Args:
            entity_id: Varlık ID.
            consent_type: Onay tipi.
            status: Onay durumu.
            expiry_days: Geçerlilik süresi.

        Returns:
            Onay bilgisi.
        """
        if entity_id not in self._consent:
            self._consent[entity_id] = {}

        expiry = None
        if expiry_days:
            expiry = (
                time.time()
                + expiry_days * 86400
            )

        self._consent[entity_id][
            consent_type
        ] = {
            "status": status,
            "granted_at": time.time(),
            "expiry": expiry,
        }
        self._stats["consents"] += 1

        return {
            "entity_id": entity_id,
            "consent_type": consent_type,
            "status": status,
            "set": True,
        }

    def check_consent(
        self,
        entity_id: str,
        consent_type: str,
    ) -> dict[str, Any]:
        """Onay kontrolü yapar.

        Args:
            entity_id: Varlık ID.
            consent_type: Onay tipi.

        Returns:
            Kontrol bilgisi.
        """
        consents = self._consent.get(
            entity_id, {},
        )
        consent = consents.get(consent_type)

        if not consent:
            return {
                "entity_id": entity_id,
                "consent_type": consent_type,
                "has_consent": False,
                "reason": "no_consent_record",
            }

        # Süre kontrolü
        if (
            consent.get("expiry")
            and time.time() > consent["expiry"]
        ):
            return {
                "entity_id": entity_id,
                "consent_type": consent_type,
                "has_consent": False,
                "reason": "expired",
            }

        has = consent["status"] == "granted"
        return {
            "entity_id": entity_id,
            "consent_type": consent_type,
            "has_consent": has,
            "status": consent["status"],
        }

    def check_access(
        self,
        entity_id: str,
        accessor: str,
        purpose: str,
    ) -> dict[str, Any]:
        """Erişim kontrolü yapar.

        Args:
            entity_id: Varlık ID.
            accessor: Erişen.
            purpose: Amaç.

        Returns:
            Erişim bilgisi.
        """
        self._stats["access_checks"] += 1

        # Erişim logu
        self._access_log.append({
            "entity_id": entity_id,
            "accessor": accessor,
            "purpose": purpose,
            "timestamp": time.time(),
        })

        # Anonimleştirilmiş varlık
        if entity_id in self._anonymized:
            return {
                "entity_id": entity_id,
                "allowed": False,
                "reason": "anonymized",
            }

        # Gizlilik modu kontrolü
        if self._privacy_mode == "strict":
            consent = self.check_consent(
                entity_id, purpose,
            )
            if not consent["has_consent"]:
                return {
                    "entity_id": entity_id,
                    "allowed": False,
                    "reason": (
                        "no_consent_for_purpose"
                    ),
                }

        return {
            "entity_id": entity_id,
            "allowed": True,
            "accessor": accessor,
            "purpose": purpose,
        }

    def anonymize_entity(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Varlığı anonimleştirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Anonimleştirme bilgisi.
        """
        self._anonymized.add(entity_id)
        self._stats["anonymizations"] += 1

        return {
            "entity_id": entity_id,
            "anonymized": True,
        }

    def check_retention(
        self,
        entity_id: str,
        created_at: float,
    ) -> dict[str, Any]:
        """Saklama kontrolü yapar.

        Args:
            entity_id: Varlık ID.
            created_at: Oluşturma zamanı.

        Returns:
            Saklama bilgisi.
        """
        age_days = (
            (time.time() - created_at) / 86400
        )
        expired = (
            age_days > self._retention_days
        )

        return {
            "entity_id": entity_id,
            "age_days": round(age_days, 1),
            "retention_days": (
                self._retention_days
            ),
            "expired": expired,
            "action": (
                "delete" if expired else "keep"
            ),
        }

    def get_gdpr_report(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """GDPR raporu getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            GDPR raporu.
        """
        consents = self._consent.get(
            entity_id, {},
        )
        access_records = [
            a for a in self._access_log
            if a["entity_id"] == entity_id
        ]

        consent_summary = {
            ct: {
                "status": c["status"],
                "granted_at": c["granted_at"],
            }
            for ct, c in consents.items()
        }

        return {
            "entity_id": entity_id,
            "is_anonymized": (
                entity_id in self._anonymized
            ),
            "consents": consent_summary,
            "consent_count": len(consents),
            "access_log_count": len(
                access_records,
            ),
            "retention_days": (
                self._retention_days
            ),
            "privacy_mode": self._privacy_mode,
        }

    def withdraw_consent(
        self,
        entity_id: str,
        consent_type: str,
    ) -> dict[str, Any]:
        """Onay geri çeker.

        Args:
            entity_id: Varlık ID.
            consent_type: Onay tipi.

        Returns:
            Geri çekme bilgisi.
        """
        consents = self._consent.get(
            entity_id, {},
        )
        if consent_type not in consents:
            return {
                "error": "consent_not_found",
            }

        consents[consent_type]["status"] = (
            "withdrawn"
        )
        consents[consent_type][
            "withdrawn_at"
        ] = time.time()

        return {
            "entity_id": entity_id,
            "consent_type": consent_type,
            "withdrawn": True,
        }

    def get_access_log(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Erişim günlüğü getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Erişim kayıtları.
        """
        return [
            a for a in self._access_log
            if a["entity_id"] == entity_id
        ]

    @property
    def consent_count(self) -> int:
        """Onay sayısı."""
        return self._stats["consents"]

    @property
    def anonymization_count(self) -> int:
        """Anonimleştirme sayısı."""
        return self._stats["anonymizations"]
