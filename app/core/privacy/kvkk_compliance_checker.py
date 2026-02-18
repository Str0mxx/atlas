"""
KVKK uyumluluk kontrolcu modulu.

KVKK gereksinimleri, veri envanteri,
isleme amaclari, aktarim kurallari,
raporlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class KVKKComplianceChecker:
    """KVKK uyumluluk kontrolcusu.

    Attributes:
        _inventory: Veri envanteri.
        _purposes: Isleme amaclari.
        _transfers: Aktarim kayitlari.
        _reports: Raporlar.
        _stats: Istatistikler.
    """

    KVKK_ARTICLES: dict[str, str] = {
        "md4": "Genel ilkeler",
        "md5": "Kisisel veri isleme",
        "md6": "Ozel nitelikli veri",
        "md7": "Acik riza",
        "md8": "Aktarim sartlari",
        "md9": "Yurt disi aktarim",
        "md10": "Aydinlatma yukumlulugu",
        "md11": "Ilgili kisi haklari",
        "md12": "Basvuru usulu",
        "md15": "Kurul yetkileri",
    }

    SPECIAL_CATEGORIES: list[str] = [
        "health",
        "biometric",
        "genetic",
        "race_ethnicity",
        "political",
        "religion",
        "criminal",
        "trade_union",
    ]

    def __init__(self) -> None:
        """Kontrolcuyu baslatir."""
        self._inventory: list[dict] = []
        self._purposes: dict[
            str, dict
        ] = {}
        self._transfers: list[dict] = []
        self._reports: list[dict] = []
        self._stats: dict[str, int] = {
            "inventory_items": 0,
            "purposes_registered": 0,
            "transfers_recorded": 0,
            "reports_generated": 0,
            "checks_performed": 0,
        }
        logger.info(
            "KVKKComplianceChecker "
            "baslatildi"
        )

    @property
    def inventory_count(self) -> int:
        """Envanter sayisi."""
        return len(self._inventory)

    def add_inventory_item(
        self,
        data_category: str = "",
        data_owner: str = "",
        storage_location: str = "",
        retention_days: int = 365,
        is_special: bool = False,
    ) -> dict[str, Any]:
        """Envanter ogeleri ekler.

        Args:
            data_category: Veri kategorisi.
            data_owner: Veri sorumlusu.
            storage_location: Depolama.
            retention_days: Saklama suresi.
            is_special: Ozel nitelikli mi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            iid = f"vi_{uuid4()!s:.8}"
            item = {
                "item_id": iid,
                "data_category": (
                    data_category
                ),
                "data_owner": data_owner,
                "storage_location": (
                    storage_location
                ),
                "retention_days": (
                    retention_days
                ),
                "is_special": is_special,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._inventory.append(item)
            self._stats[
                "inventory_items"
            ] += 1

            return {
                "item_id": iid,
                "data_category": (
                    data_category
                ),
                "is_special": is_special,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def register_purpose(
        self,
        name: str = "",
        description: str = "",
        legal_basis: str = "consent",
        data_categories: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Isleme amaci kaydeder.

        Args:
            name: Amac adi.
            description: Aciklama.
            legal_basis: Hukuki dayanak.
            data_categories: Kategoriler.

        Returns:
            Kayit bilgisi.
        """
        try:
            pid = f"pp_{uuid4()!s:.8}"
            self._purposes[name] = {
                "purpose_id": pid,
                "name": name,
                "description": description,
                "legal_basis": legal_basis,
                "data_categories": (
                    data_categories or []
                ),
                "active": True,
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "purposes_registered"
            ] += 1

            return {
                "purpose_id": pid,
                "name": name,
                "legal_basis": legal_basis,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def record_transfer(
        self,
        data_category: str = "",
        recipient: str = "",
        destination: str = "domestic",
        legal_basis: str = "",
        has_contract: bool = False,
    ) -> dict[str, Any]:
        """Aktarim kaydeder.

        Args:
            data_category: Veri kategorisi.
            recipient: Alici.
            destination: Hedef.
            legal_basis: Hukuki dayanak.
            has_contract: Sozlesme var mi.

        Returns:
            Kayit bilgisi.
        """
        try:
            tid = f"tr_{uuid4()!s:.8}"
            compliant = True
            issues: list[str] = []

            if (
                destination
                == "international"
            ):
                if not has_contract:
                    issues.append(
                        "no_contract_intl"
                    )
                    compliant = False
                if not legal_basis:
                    issues.append(
                        "no_legal_basis_intl"
                    )
                    compliant = False

            transfer = {
                "transfer_id": tid,
                "data_category": (
                    data_category
                ),
                "recipient": recipient,
                "destination": destination,
                "legal_basis": legal_basis,
                "has_contract": has_contract,
                "compliant": compliant,
                "issues": issues,
                "recorded_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._transfers.append(transfer)
            self._stats[
                "transfers_recorded"
            ] += 1

            return {
                "transfer_id": tid,
                "destination": destination,
                "compliant": compliant,
                "issues": issues,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def check_special_category(
        self,
        data_category: str = "",
        has_explicit_consent: bool = False,
    ) -> dict[str, Any]:
        """Ozel kategori kontrol eder.

        Args:
            data_category: Veri kategorisi.
            has_explicit_consent: Acik riza.

        Returns:
            Kontrol bilgisi.
        """
        try:
            self._stats[
                "checks_performed"
            ] += 1
            is_special = (
                data_category
                in self.SPECIAL_CATEGORIES
            )

            if not is_special:
                return {
                    "is_special": False,
                    "processing_allowed": (
                        True
                    ),
                    "checked": True,
                }

            return {
                "is_special": True,
                "category": data_category,
                "has_explicit_consent": (
                    has_explicit_consent
                ),
                "processing_allowed": (
                    has_explicit_consent
                ),
                "requirement": (
                    "Acik riza gerekli"
                    if not (
                        has_explicit_consent
                    )
                    else "Uygun"
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def generate_verbis_report(
        self,
    ) -> dict[str, Any]:
        """VERBiS raporu olusturur.

        Returns:
            Rapor bilgisi.
        """
        try:
            rid = f"vr_{uuid4()!s:.8}"
            special_items = [
                i
                for i in self._inventory
                if i.get("is_special")
            ]
            intl_transfers = [
                t
                for t in self._transfers
                if t.get("destination")
                == "international"
            ]

            report = {
                "report_id": rid,
                "inventory_count": len(
                    self._inventory
                ),
                "special_data_count": len(
                    special_items
                ),
                "purposes_count": len(
                    self._purposes
                ),
                "transfer_count": len(
                    self._transfers
                ),
                "intl_transfer_count": len(
                    intl_transfers
                ),
                "generated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._reports.append(report)
            self._stats[
                "reports_generated"
            ] += 1

            return {
                "report_id": rid,
                "inventory_count": len(
                    self._inventory
                ),
                "special_data_count": len(
                    special_items
                ),
                "purposes_count": len(
                    self._purposes
                ),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def check_compliance(
        self,
    ) -> dict[str, Any]:
        """Uyumluluk kontrol eder.

        Returns:
            Uyumluluk bilgisi.
        """
        try:
            self._stats[
                "checks_performed"
            ] += 1
            issues: list[str] = []

            if not self._inventory:
                issues.append(
                    "no_data_inventory"
                )
            if not self._purposes:
                issues.append(
                    "no_processing_purposes"
                )

            non_compliant = [
                t
                for t in self._transfers
                if not t.get("compliant")
            ]
            if non_compliant:
                issues.append(
                    "non_compliant_transfers"
                )

            special_no_consent = [
                i
                for i in self._inventory
                if i.get("is_special")
            ]
            if special_no_consent:
                has_purpose = any(
                    p.get("legal_basis")
                    == "explicit_consent"
                    for p in (
                        self._purposes.values()
                    )
                )
                if not has_purpose:
                    issues.append(
                        "special_data_no_"
                        "explicit_consent"
                    )

            score = max(
                0.0,
                1.0 - len(issues) * 0.2,
            )

            return {
                "compliant": (
                    len(issues) == 0
                ),
                "score": round(score, 2),
                "issues": issues,
                "inventory": len(
                    self._inventory
                ),
                "purposes": len(
                    self._purposes
                ),
                "transfers": len(
                    self._transfers
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
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
                "total_inventory": len(
                    self._inventory
                ),
                "total_purposes": len(
                    self._purposes
                ),
                "total_transfers": len(
                    self._transfers
                ),
                "total_reports": len(
                    self._reports
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
