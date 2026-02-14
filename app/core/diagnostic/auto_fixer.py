"""ATLAS Otomatik Duzeltici modulu.

Bilinen duzeltmeleri uygulama, yapilandirma
duzeltmesi, onbellek temizleme, servis
yeniden baslatma ve veri onarimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import FixRecord, FixType

logger = logging.getLogger(__name__)


class AutoFixer:
    """Otomatik duzeltici.

    Tespit edilen sorunlara bilinen
    duzeltmeleri otomatik uygular.

    Attributes:
        _fixes: Uygulanan duzeltmeler.
        _known_fixes: Bilinen duzeltme veritabani.
        _fix_history: Duzeltme gecmisi.
        _auto_approve: Otomatik onay.
    """

    def __init__(self, auto_approve: bool = False) -> None:
        """Otomatik duzelticiyi baslatir.

        Args:
            auto_approve: Otomatik onay.
        """
        self._fixes: list[FixRecord] = []
        self._known_fixes: dict[str, dict[str, Any]] = {
            "cache_overflow": {
                "fix_type": FixType.CACHE_CLEAR,
                "description": "Onbellek temizleme",
                "auto_safe": True,
            },
            "config_invalid": {
                "fix_type": FixType.CONFIG,
                "description": "Yapilandirma duzeltmesi",
                "auto_safe": True,
            },
            "service_down": {
                "fix_type": FixType.RESTART,
                "description": "Servis yeniden baslatma",
                "auto_safe": False,
            },
            "data_corruption": {
                "fix_type": FixType.DATA_REPAIR,
                "description": "Veri onarimi",
                "auto_safe": False,
            },
            "dependency_missing": {
                "fix_type": FixType.DEPENDENCY,
                "description": "Eksik bagimlilik kurulumu",
                "auto_safe": False,
            },
        }
        self._fix_history: list[dict[str, Any]] = []
        self._auto_approve = auto_approve

        logger.info(
            "AutoFixer baslatildi (auto_approve=%s)", auto_approve,
        )

    def find_fix(
        self,
        issue_type: str,
    ) -> dict[str, Any] | None:
        """Sorun icin duzeltme bulur.

        Args:
            issue_type: Sorun turu.

        Returns:
            Duzeltme bilgisi veya None.
        """
        # Tam eslesme
        if issue_type in self._known_fixes:
            return dict(self._known_fixes[issue_type])

        # Kısmi eslesme
        issue_lower = issue_type.lower()
        for key, fix in self._known_fixes.items():
            if key in issue_lower or issue_lower in key:
                return dict(fix)

        return None

    def apply_fix(
        self,
        target: str,
        fix_type: FixType,
        description: str = "",
    ) -> FixRecord:
        """Duzeltme uygular.

        Args:
            target: Hedef bilesen.
            fix_type: Duzeltme turu.
            description: Aciklama.

        Returns:
            FixRecord nesnesi.
        """
        # Simule edilmis duzeltme
        success = True
        rollback = True

        if fix_type == FixType.RESTART:
            rollback = False

        record = FixRecord(
            fix_type=fix_type,
            target=target,
            description=description or f"{fix_type.value} duzeltmesi",
            success=success,
            rollback_available=rollback,
        )
        self._fixes.append(record)

        self._fix_history.append({
            "fix_id": record.fix_id,
            "target": target,
            "fix_type": fix_type.value,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info(
            "Duzeltme uygulandi: %s -> %s (basari=%s)",
            fix_type.value, target, success,
        )
        return record

    def auto_fix(
        self,
        issue_type: str,
        target: str,
    ) -> dict[str, Any]:
        """Otomatik duzeltme yapar.

        Args:
            issue_type: Sorun turu.
            target: Hedef bilesen.

        Returns:
            Duzeltme sonucu.
        """
        fix_info = self.find_fix(issue_type)
        if not fix_info:
            return {
                "fixed": False,
                "reason": "Bilinen duzeltme bulunamadi",
            }

        # Guvenlik kontrolu
        if not fix_info.get("auto_safe", False) and not self._auto_approve:
            return {
                "fixed": False,
                "reason": "Onay gerekiyor",
                "fix_type": fix_info["fix_type"].value,
                "requires_approval": True,
            }

        record = self.apply_fix(
            target,
            fix_info["fix_type"],
            fix_info.get("description", ""),
        )

        return {
            "fixed": record.success,
            "fix_id": record.fix_id,
            "fix_type": record.fix_type.value,
            "target": target,
        }

    def clear_cache(self, target: str) -> FixRecord:
        """Onbellek temizler.

        Args:
            target: Hedef.

        Returns:
            FixRecord nesnesi.
        """
        return self.apply_fix(
            target, FixType.CACHE_CLEAR, "Onbellek temizlendi",
        )

    def fix_config(
        self,
        target: str,
        corrections: dict[str, Any] | None = None,
    ) -> FixRecord:
        """Yapilandirma duzeltir.

        Args:
            target: Hedef.
            corrections: Duzeltmeler.

        Returns:
            FixRecord nesnesi.
        """
        desc = "Yapilandirma duzeltildi"
        if corrections:
            desc += f": {list(corrections.keys())}"
        return self.apply_fix(target, FixType.CONFIG, desc)

    def restart_service(self, target: str) -> FixRecord:
        """Servis yeniden baslatir.

        Args:
            target: Hedef servis.

        Returns:
            FixRecord nesnesi.
        """
        return self.apply_fix(
            target, FixType.RESTART, "Servis yeniden baslatildi",
        )

    def repair_data(
        self,
        target: str,
        description: str = "",
    ) -> FixRecord:
        """Veri onarir.

        Args:
            target: Hedef.
            description: Aciklama.

        Returns:
            FixRecord nesnesi.
        """
        return self.apply_fix(
            target, FixType.DATA_REPAIR,
            description or "Veri onarildi",
        )

    def add_known_fix(
        self,
        issue_type: str,
        fix_type: FixType,
        description: str,
        auto_safe: bool = False,
    ) -> None:
        """Bilinen duzeltme ekler.

        Args:
            issue_type: Sorun turu.
            fix_type: Duzeltme turu.
            description: Aciklama.
            auto_safe: Otomatik guvenli mi.
        """
        self._known_fixes[issue_type] = {
            "fix_type": fix_type,
            "description": description,
            "auto_safe": auto_safe,
        }

    def get_fix_history(
        self,
        target: str = "",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Duzeltme gecmisini getirir.

        Args:
            target: Hedef filtre.
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        if target:
            filtered = [
                f for f in self._fix_history
                if f["target"] == target
            ]
        else:
            filtered = self._fix_history

        return filtered[-limit:]

    def get_success_rate(self) -> float:
        """Basari oranini getirir.

        Returns:
            Basari orani (0-1).
        """
        if not self._fixes:
            return 0.0
        successful = sum(1 for f in self._fixes if f.success)
        return round(successful / len(self._fixes), 3)

    @property
    def fix_count(self) -> int:
        """Duzeltme sayisi."""
        return len(self._fixes)

    @property
    def known_fix_count(self) -> int:
        """Bilinen duzeltme sayisi."""
        return len(self._known_fixes)

    @property
    def successful_fixes(self) -> int:
        """Basarili duzeltme sayisi."""
        return sum(1 for f in self._fixes if f.success)
