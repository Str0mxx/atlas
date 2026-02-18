"""
Veri maskeleme modulu.

PII maskeleme, dinamik maskeleme,
rol tabanli maskeleme, geri donusturulur
maskeleme, log maskeleme.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DataMasker:
    """Veri maskeleyici.

    Attributes:
        _rules: Maskeleme kurallari.
        _masked: Maskelenmis kayitlar.
        _role_rules: Rol kurallari.
        _reversible: Geri donusturulur.
        _stats: Istatistikler.
    """

    PII_PATTERNS: dict[str, str] = {
        "email": (
            r"[a-zA-Z0-9._%+-]+"
            r"@[a-zA-Z0-9.-]+"
            r"\.[a-zA-Z]{2,}"
        ),
        "phone": (
            r"\b\d{3}[-.]?\d{3}"
            r"[-.]?\d{4}\b"
        ),
        "ssn": (
            r"\b\d{3}-\d{2}-\d{4}\b"
        ),
        "credit_card": (
            r"\b\d{4}[-\s]?\d{4}"
            r"[-\s]?\d{4}[-\s]?\d{4}\b"
        ),
        "ip_address": (
            r"\b\d{1,3}\.\d{1,3}"
            r"\.\d{1,3}\.\d{1,3}\b"
        ),
    }

    def __init__(self) -> None:
        """Maskeleyiciyi baslatir."""
        self._rules: list[dict] = []
        self._masked: list[dict] = []
        self._role_rules: dict[
            str, list[str]
        ] = {}
        self._reversible: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "masks_applied": 0,
            "pii_detected": 0,
            "reversals": 0,
            "log_masks": 0,
        }
        logger.info(
            "DataMasker baslatildi"
        )

    @property
    def mask_count(self) -> int:
        """Maskeleme sayisi."""
        return self._stats["masks_applied"]

    def add_rule(
        self,
        name: str = "",
        field: str = "",
        mask_type: str = "full",
        pattern: str = "",
        replacement: str = "***",
    ) -> dict[str, Any]:
        """Maskeleme kurali ekler.

        Args:
            name: Kural adi.
            field: Alan adi.
            mask_type: Maskeleme turu.
            pattern: Desen.
            replacement: Degistirme.

        Returns:
            Ekleme bilgisi.
        """
        try:
            rid = f"mr_{uuid4()!s:.8}"
            rule = {
                "rule_id": rid,
                "name": name,
                "field": field,
                "mask_type": mask_type,
                "pattern": pattern,
                "replacement": replacement,
                "active": True,
            }
            self._rules.append(rule)

            return {
                "rule_id": rid,
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def mask_value(
        self,
        value: str = "",
        mask_type: str = "partial",
        visible_chars: int = 4,
    ) -> dict[str, Any]:
        """Degeri maskeler.

        Args:
            value: Deger.
            mask_type: Maskeleme turu.
            visible_chars: Gorunur karakter.

        Returns:
            Maskeleme bilgisi.
        """
        try:
            if mask_type == "full":
                masked = "*" * len(value)
            elif mask_type == "partial":
                if len(value) <= visible_chars:
                    masked = (
                        "*" * len(value)
                    )
                else:
                    masked = (
                        "*"
                        * (
                            len(value)
                            - visible_chars
                        )
                        + value[
                            -visible_chars:
                        ]
                    )
            elif mask_type == "email":
                parts = value.split("@")
                if len(parts) == 2:
                    name = parts[0]
                    if len(name) > 2:
                        masked = (
                            name[0]
                            + "*"
                            * (len(name) - 2)
                            + name[-1]
                            + "@"
                            + parts[1]
                        )
                    else:
                        masked = (
                            "**@" + parts[1]
                        )
                else:
                    masked = (
                        "*" * len(value)
                    )
            else:
                masked = "*" * len(value)

            self._stats[
                "masks_applied"
            ] += 1

            return {
                "original_length": len(
                    value
                ),
                "masked": masked,
                "mask_type": mask_type,
                "masked_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "masked_ok": False,
                "error": str(e),
            }

    def detect_pii(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """PII tespit eder.

        Args:
            text: Metin.

        Returns:
            Tespit bilgisi.
        """
        try:
            found: list[dict] = []
            for (
                pii_type,
                pattern,
            ) in self.PII_PATTERNS.items():
                matches = re.findall(
                    pattern, text
                )
                for m in matches:
                    found.append({
                        "type": pii_type,
                        "value": m,
                    })

            self._stats[
                "pii_detected"
            ] += len(found)

            return {
                "pii_found": found,
                "pii_count": len(found),
                "has_pii": len(found) > 0,
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def mask_pii(
        self,
        text: str = "",
    ) -> dict[str, Any]:
        """PII maskeler.

        Args:
            text: Metin.

        Returns:
            Maskeleme bilgisi.
        """
        try:
            masked = text
            count = 0
            for (
                pii_type,
                pattern,
            ) in self.PII_PATTERNS.items():
                matches = re.findall(
                    pattern, masked
                )
                for m in matches:
                    replacement = (
                        f"[{pii_type.upper()}]"
                    )
                    masked = masked.replace(
                        m, replacement, 1
                    )
                    count += 1

            self._stats[
                "masks_applied"
            ] += count

            return {
                "original": text,
                "masked": masked,
                "pii_masked": count,
                "masked_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "masked_ok": False,
                "error": str(e),
            }

    def set_role_access(
        self,
        role: str = "",
        visible_fields: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Rol erisimi ayarlar.

        Args:
            role: Rol adi.
            visible_fields: Gorunur alanlar.

        Returns:
            Ayar bilgisi.
        """
        try:
            fields = visible_fields or []
            self._role_rules[role] = fields
            return {
                "role": role,
                "visible_fields": fields,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def apply_role_mask(
        self,
        data: dict | None = None,
        role: str = "",
    ) -> dict[str, Any]:
        """Rol bazli maskeleme uygular.

        Args:
            data: Veri.
            role: Rol.

        Returns:
            Maskeleme bilgisi.
        """
        try:
            src = data or {}
            visible = self._role_rules.get(
                role, []
            )
            masked_data: dict = {}
            masked_count = 0

            for k, v in src.items():
                if k in visible:
                    masked_data[k] = v
                else:
                    masked_data[k] = "***"
                    masked_count += 1

            self._stats[
                "masks_applied"
            ] += masked_count

            return {
                "role": role,
                "data": masked_data,
                "fields_masked": (
                    masked_count
                ),
                "masked_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "masked_ok": False,
                "error": str(e),
            }

    def mask_reversible(
        self,
        value: str = "",
        context: str = "",
    ) -> dict[str, Any]:
        """Geri donusturulur maskeler.

        Args:
            value: Deger.
            context: Baglam.

        Returns:
            Maskeleme bilgisi.
        """
        try:
            mid = f"rv_{uuid4()!s:.8}"
            masked = f"MASKED[{mid}]"
            self._reversible[mid] = {
                "original": value,
                "context": context,
                "masked_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "masks_applied"
            ] += 1

            return {
                "mask_id": mid,
                "masked": masked,
                "reversible": True,
                "masked_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "masked_ok": False,
                "error": str(e),
            }

    def unmask(
        self,
        mask_id: str = "",
    ) -> dict[str, Any]:
        """Maskeyi kaldirir.

        Args:
            mask_id: Maske ID.

        Returns:
            Kaldirma bilgisi.
        """
        try:
            rec = self._reversible.get(
                mask_id
            )
            if not rec:
                return {
                    "unmasked": False,
                    "error": (
                        "Maske bulunamadi"
                    ),
                }

            self._stats["reversals"] += 1
            return {
                "mask_id": mask_id,
                "original": rec["original"],
                "unmasked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "unmasked": False,
                "error": str(e),
            }

    def mask_log(
        self,
        log_line: str = "",
    ) -> dict[str, Any]:
        """Log maskeler.

        Args:
            log_line: Log satiri.

        Returns:
            Maskeleme bilgisi.
        """
        try:
            result = self.mask_pii(
                text=log_line
            )
            self._stats["log_masks"] += 1
            return {
                "original": log_line,
                "masked": result.get(
                    "masked", log_line
                ),
                "pii_masked": result.get(
                    "pii_masked", 0
                ),
                "masked_ok": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "masked_ok": False,
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
                "total_rules": len(
                    self._rules
                ),
                "role_rules": len(
                    self._role_rules
                ),
                "reversible_masks": len(
                    self._reversible
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
