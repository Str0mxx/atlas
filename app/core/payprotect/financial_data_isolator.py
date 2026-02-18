"""
Finansal veri izolasyoncusu modulu.

Veri izolasyonu, ag segmentasyonu,
erisim kisitlamasi, sifreleme zorlama,
izleme.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FinancialDataIsolator:
    """Finansal veri izolasyoncusu.

    Attributes:
        _zones: Izolasyon bolgeleri.
        _access_rules: Erisim kurallari.
        _access_log: Erisim kayitlari.
        _encryption: Sifreleme kayitlari.
        _stats: Istatistikler.
    """

    ZONE_TYPES: list[str] = [
        "pci",
        "pii",
        "financial",
        "general",
        "public",
    ]

    DATA_CLASSES: list[str] = [
        "card_data",
        "bank_account",
        "personal_info",
        "transaction",
        "financial_report",
        "general",
    ]

    def __init__(self) -> None:
        """Izolasyoncuyu baslatir."""
        self._zones: dict[
            str, dict
        ] = {}
        self._access_rules: dict[
            str, dict
        ] = {}
        self._access_log: list[dict] = []
        self._encryption: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "zones_created": 0,
            "rules_created": 0,
            "access_granted": 0,
            "access_denied": 0,
            "encryption_ops": 0,
        }
        self._init_default_zones()
        logger.info(
            "FinancialDataIsolator "
            "baslatildi"
        )

    def _init_default_zones(
        self,
    ) -> None:
        """Varsayilan bolgeler."""
        defaults = [
            {
                "name": "pci_zone",
                "zone_type": "pci",
                "encryption": "aes256",
                "min_clearance": "level_3",
            },
            {
                "name": "pii_zone",
                "zone_type": "pii",
                "encryption": "aes256",
                "min_clearance": "level_2",
            },
            {
                "name": "financial_zone",
                "zone_type": "financial",
                "encryption": "aes128",
                "min_clearance": "level_2",
            },
            {
                "name": "general_zone",
                "zone_type": "general",
                "encryption": "none",
                "min_clearance": "level_1",
            },
        ]
        for z in defaults:
            zid = f"zn_{uuid4()!s:.8}"
            z["zone_id"] = zid
            z["active"] = True
            self._zones[z["name"]] = z
            self._stats[
                "zones_created"
            ] += 1

    @property
    def zone_count(self) -> int:
        """Aktif bolge sayisi."""
        return sum(
            1
            for z in self._zones.values()
            if z["active"]
        )

    def create_zone(
        self,
        name: str = "",
        zone_type: str = "general",
        encryption: str = "aes256",
        min_clearance: str = "level_1",
        allowed_services: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Izolasyon bolgesi olusturur.

        Args:
            name: Bolge adi.
            zone_type: Bolge tipi.
            encryption: Sifreleme.
            min_clearance: Min yetki.
            allowed_services: Izinli servis.

        Returns:
            Olusturma bilgisi.
        """
        try:
            if (
                zone_type
                not in self.ZONE_TYPES
            ):
                return {
                    "created": False,
                    "error": (
                        f"Gecersiz: "
                        f"{zone_type}"
                    ),
                }

            zid = f"zn_{uuid4()!s:.8}"
            self._zones[name] = {
                "zone_id": zid,
                "name": name,
                "zone_type": zone_type,
                "encryption": encryption,
                "min_clearance": (
                    min_clearance
                ),
                "allowed_services": (
                    allowed_services or []
                ),
                "active": True,
            }
            self._stats[
                "zones_created"
            ] += 1

            return {
                "zone_id": zid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def create_access_rule(
        self,
        name: str = "",
        zone_name: str = "",
        role: str = "",
        data_class: str = "general",
        can_read: bool = False,
        can_write: bool = False,
        can_export: bool = False,
    ) -> dict[str, Any]:
        """Erisim kurali olusturur.

        Args:
            name: Kural adi.
            zone_name: Bolge adi.
            role: Rol.
            data_class: Veri sinifi.
            can_read: Okuma izni.
            can_write: Yazma izni.
            can_export: Disari aktarim.

        Returns:
            Kayit bilgisi.
        """
        try:
            rid = f"ar_{uuid4()!s:.8}"
            self._access_rules[name] = {
                "rule_id": rid,
                "name": name,
                "zone_name": zone_name,
                "role": role,
                "data_class": data_class,
                "can_read": can_read,
                "can_write": can_write,
                "can_export": can_export,
                "active": True,
            }
            self._stats[
                "rules_created"
            ] += 1

            return {
                "rule_id": rid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def check_access(
        self,
        user_id: str = "",
        role: str = "",
        zone_name: str = "",
        data_class: str = "general",
        operation: str = "read",
    ) -> dict[str, Any]:
        """Erisim kontrol eder.

        Args:
            user_id: Kullanici ID.
            role: Rol.
            zone_name: Bolge adi.
            data_class: Veri sinifi.
            operation: Islem.

        Returns:
            Erisim sonucu.
        """
        try:
            zone = self._zones.get(
                zone_name
            )
            if not zone:
                self._stats[
                    "access_denied"
                ] += 1
                return {
                    "allowed": False,
                    "reason": (
                        "Bolge bulunamadi"
                    ),
                    "checked": True,
                }

            # Kural eslestirme
            allowed = False
            for rule in (
                self._access_rules.values()
            ):
                if not rule["active"]:
                    continue
                if (
                    rule["zone_name"]
                    != zone_name
                ):
                    continue
                if rule["role"] != role:
                    continue
                if (
                    rule["data_class"]
                    != data_class
                    and rule["data_class"]
                    != "general"
                ):
                    continue

                if (
                    operation == "read"
                    and rule["can_read"]
                ):
                    allowed = True
                elif (
                    operation == "write"
                    and rule["can_write"]
                ):
                    allowed = True
                elif (
                    operation == "export"
                    and rule["can_export"]
                ):
                    allowed = True

            if allowed:
                self._stats[
                    "access_granted"
                ] += 1
            else:
                self._stats[
                    "access_denied"
                ] += 1

            self._access_log.append({
                "user_id": user_id,
                "role": role,
                "zone_name": zone_name,
                "data_class": data_class,
                "operation": operation,
                "allowed": allowed,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            })

            return {
                "user_id": user_id,
                "zone_name": zone_name,
                "operation": operation,
                "allowed": allowed,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def encrypt_data(
        self,
        data_id: str = "",
        data_class: str = "general",
        zone_name: str = "",
    ) -> dict[str, Any]:
        """Veriyi sifreler (simulasyon).

        Args:
            data_id: Veri ID.
            data_class: Veri sinifi.
            zone_name: Bolge adi.

        Returns:
            Sifreleme bilgisi.
        """
        try:
            zone = self._zones.get(
                zone_name
            )
            enc = "aes256"
            if zone:
                enc = zone.get(
                    "encryption", "aes256"
                )

            eid = f"en_{uuid4()!s:.8}"
            key_hash = hashlib.sha256(
                f"{data_id}_{eid}".encode()
            ).hexdigest()[:16]

            self._encryption[data_id] = {
                "encryption_id": eid,
                "data_id": data_id,
                "data_class": data_class,
                "zone_name": zone_name,
                "algorithm": enc,
                "key_hash": key_hash,
                "encrypted_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "encryption_ops"
            ] += 1

            return {
                "encryption_id": eid,
                "data_id": data_id,
                "algorithm": enc,
                "encrypted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "encrypted": False,
                "error": str(e),
            }

    def get_zone_info(
        self,
        zone_name: str = "",
    ) -> dict[str, Any]:
        """Bolge bilgisi getirir."""
        try:
            zone = self._zones.get(
                zone_name
            )
            if not zone:
                return {
                    "found": False,
                    "error": (
                        "Bolge bulunamadi"
                    ),
                }
            return {
                **zone,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_zones": len(
                    self._zones
                ),
                "active_zones": (
                    self.zone_count
                ),
                "total_rules": len(
                    self._access_rules
                ),
                "access_log_entries": len(
                    self._access_log
                ),
                "encrypted_items": len(
                    self._encryption
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
