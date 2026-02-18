"""
Onay yoneticisi modulu.

Onay toplama, amac takibi,
geri cekme yonetimi, tercih merkezi,
denetim izi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ComplianceConsentManager:
    """Onay yoneticisi.

    Attributes:
        _consents: Onay kayitlari.
        _purposes: Amac kayitlari.
        _withdrawals: Geri cekme kayit.
        _audit_trail: Denetim izi.
        _stats: Istatistikler.
    """

    CONSENT_STATUSES: list[str] = [
        "granted",
        "denied",
        "withdrawn",
        "expired",
    ]

    def __init__(self) -> None:
        """Yoneticiyi baslatir."""
        self._consents: dict[
            str, dict
        ] = {}
        self._purposes: dict[
            str, dict
        ] = {}
        self._withdrawals: list[dict] = []
        self._audit_trail: list[dict] = []
        self._stats: dict[str, int] = {
            "consents_collected": 0,
            "consents_withdrawn": 0,
            "purposes_defined": 0,
            "audit_entries": 0,
        }
        logger.info(
            "ComplianceConsentManager "
            "baslatildi"
        )

    @property
    def consent_count(self) -> int:
        """Aktif onay sayisi."""
        return sum(
            1
            for c in self._consents.values()
            if c["status"] == "granted"
        )

    def define_purpose(
        self,
        name: str = "",
        description: str = "",
        legal_basis: str = "consent",
        is_required: bool = False,
        data_categories: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Amac tanimlar.

        Args:
            name: Amac adi.
            description: Aciklama.
            legal_basis: Hukuki dayanak.
            is_required: Zorunlu mu.
            data_categories: Kategoriler.

        Returns:
            Amac bilgisi.
        """
        try:
            pid = f"pp_{uuid4()!s:.8}"
            self._purposes[pid] = {
                "purpose_id": pid,
                "name": name,
                "description": description,
                "legal_basis": legal_basis,
                "is_required": is_required,
                "data_categories": (
                    data_categories or []
                ),
                "is_active": True,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "purposes_defined"
            ] += 1

            return {
                "purpose_id": pid,
                "name": name,
                "defined": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "defined": False,
                "error": str(e),
            }

    def collect_consent(
        self,
        user_id: str = "",
        purpose_id: str = "",
        granted: bool = True,
        source: str = "",
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Onay toplar.

        Args:
            user_id: Kullanici ID.
            purpose_id: Amac ID.
            granted: Onay verildi mi.
            source: Kaynak.
            ip_address: IP adresi.

        Returns:
            Onay bilgisi.
        """
        try:
            purpose = self._purposes.get(
                purpose_id
            )
            if not purpose:
                return {
                    "collected": False,
                    "error": (
                        "Amac bulunamadi"
                    ),
                }

            cid = f"cn_{uuid4()!s:.8}"
            consent_key = (
                f"{user_id}_{purpose_id}"
            )
            status = (
                "granted"
                if granted
                else "denied"
            )

            self._consents[consent_key] = {
                "consent_id": cid,
                "user_id": user_id,
                "purpose_id": purpose_id,
                "purpose_name": purpose[
                    "name"
                ],
                "status": status,
                "source": source,
                "ip_address": ip_address,
                "collected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "consents_collected"
            ] += 1

            self._log_audit(
                user_id,
                "consent_collected",
                f"Onay: {status} "
                f"amac={purpose['name']}",
            )

            return {
                "consent_id": cid,
                "status": status,
                "collected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "collected": False,
                "error": str(e),
            }

    def withdraw_consent(
        self,
        user_id: str = "",
        purpose_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Onayi geri ceker.

        Args:
            user_id: Kullanici ID.
            purpose_id: Amac ID.
            reason: Sebep.

        Returns:
            Geri cekme bilgisi.
        """
        try:
            consent_key = (
                f"{user_id}_{purpose_id}"
            )
            consent = self._consents.get(
                consent_key
            )
            if not consent:
                return {
                    "withdrawn": False,
                    "error": (
                        "Onay bulunamadi"
                    ),
                }

            if consent["status"] != (
                "granted"
            ):
                return {
                    "withdrawn": False,
                    "error": (
                        "Onay aktif degil"
                    ),
                }

            consent["status"] = "withdrawn"
            consent["withdrawn_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            self._withdrawals.append({
                "user_id": user_id,
                "purpose_id": purpose_id,
                "reason": reason,
                "withdrawn_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })
            self._stats[
                "consents_withdrawn"
            ] += 1

            self._log_audit(
                user_id,
                "consent_withdrawn",
                f"Geri cekildi: "
                f"{purpose_id}",
            )

            return {
                "user_id": user_id,
                "purpose_id": purpose_id,
                "withdrawn": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "withdrawn": False,
                "error": str(e),
            }

    def get_user_consents(
        self,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Kullanici onaylarini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Onay listesi.
        """
        try:
            user_consents = [
                c
                for c in (
                    self._consents.values()
                )
                if c["user_id"] == user_id
            ]

            return {
                "user_id": user_id,
                "consents": user_consents,
                "count": len(
                    user_consents
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def check_consent(
        self,
        user_id: str = "",
        purpose_id: str = "",
    ) -> dict[str, Any]:
        """Onay durumunu kontrol eder.

        Args:
            user_id: Kullanici ID.
            purpose_id: Amac ID.

        Returns:
            Onay durumu.
        """
        try:
            consent_key = (
                f"{user_id}_{purpose_id}"
            )
            consent = self._consents.get(
                consent_key
            )

            has_consent = (
                consent is not None
                and consent["status"]
                == "granted"
            )

            return {
                "user_id": user_id,
                "purpose_id": purpose_id,
                "has_consent": has_consent,
                "status": (
                    consent["status"]
                    if consent
                    else "none"
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _log_audit(
        self,
        user_id: str,
        action: str,
        detail: str,
    ) -> None:
        """Denetim izi loglar."""
        self._audit_trail.append({
            "audit_id": (
                f"ca_{uuid4()!s:.8}"
            ),
            "user_id": user_id,
            "action": action,
            "detail": detail,
            "logged_at": datetime.now(
                timezone.utc
            ).isoformat(),
        })
        self._stats[
            "audit_entries"
        ] += 1

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            active = sum(
                1
                for c in (
                    self._consents.values()
                )
                if c["status"] == "granted"
            )
            return {
                "total_consents": len(
                    self._consents
                ),
                "active_consents": active,
                "total_purposes": len(
                    self._purposes
                ),
                "withdrawals": len(
                    self._withdrawals
                ),
                "audit_entries": len(
                    self._audit_trail
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
