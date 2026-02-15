"""ATLAS Aciliyet Geçersiz Kılma modülü.

Acil durum tespiti, geçersiz kılma kriterleri,
eskalasyon tetikleyicileri, kullanıcı onayı,
denetim kayıtları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UrgencyOverride:
    """Aciliyet geçersiz kılma yöneticisi.

    Acil durumlarda sessiz saatleri ve
    tamponları geçersiz kılar.

    Attributes:
        _criteria: Geçersiz kılma kriterleri.
        _overrides: Geçersiz kılma kayıtları.
    """

    def __init__(
        self,
        emergency_threshold: float = 0.9,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            emergency_threshold: Acil durum eşiği.
        """
        self._criteria: list[
            dict[str, Any]
        ] = []
        self._overrides: list[
            dict[str, Any]
        ] = []
        self._escalations: list[
            dict[str, Any]
        ] = []
        self._confirmations: dict[
            str, dict[str, Any]
        ] = {}
        self._audit_log: list[
            dict[str, Any]
        ] = []
        self._emergency_threshold = (
            emergency_threshold
        )
        self._counter = 0
        self._stats = {
            "overrides": 0,
            "emergencies_detected": 0,
            "escalations_triggered": 0,
            "confirmations_requested": 0,
        }

        # Varsayılan kriterler
        self._default_criteria = [
            {
                "name": "security_breach",
                "keywords": [
                    "security", "breach",
                    "attack", "intrusion",
                ],
                "auto_override": True,
            },
            {
                "name": "system_down",
                "keywords": [
                    "down", "crash", "outage",
                    "unreachable",
                ],
                "auto_override": True,
            },
            {
                "name": "financial_loss",
                "keywords": [
                    "payment", "fraud",
                    "financial", "transaction",
                ],
                "auto_override": False,
            },
        ]

        logger.info(
            "UrgencyOverride baslatildi",
        )

    def detect_emergency(
        self,
        message: str,
        priority_score: float = 0.5,
        source: str = "system",
    ) -> dict[str, Any]:
        """Acil durum tespit eder.

        Args:
            message: Mesaj metni.
            priority_score: Öncelik puanı.
            source: Kaynak.

        Returns:
            Tespit bilgisi.
        """
        is_emergency = (
            priority_score
            >= self._emergency_threshold
        )
        matched_criteria = []

        # Kriter kontrolü
        msg_lower = message.lower()
        all_criteria = (
            self._default_criteria
            + self._criteria
        )
        for criterion in all_criteria:
            keywords = criterion.get(
                "keywords", [],
            )
            if any(
                kw in msg_lower
                for kw in keywords
            ):
                matched_criteria.append(
                    criterion["name"],
                )
                if criterion.get("auto_override"):
                    is_emergency = True

        if is_emergency:
            self._stats[
                "emergencies_detected"
            ] += 1

        self._audit(
            "emergency_detection",
            {
                "message": message[:100],
                "is_emergency": is_emergency,
                "priority_score": priority_score,
                "matched_criteria": (
                    matched_criteria
                ),
            },
        )

        return {
            "is_emergency": is_emergency,
            "priority_score": priority_score,
            "matched_criteria": matched_criteria,
            "source": source,
        }

    def override(
        self,
        reason: str,
        source: str = "system",
        requires_confirmation: bool = False,
    ) -> dict[str, Any]:
        """Geçersiz kılma uygular.

        Args:
            reason: Neden.
            source: Kaynak.
            requires_confirmation: Onay gerekli mi.

        Returns:
            Geçersiz kılma bilgisi.
        """
        self._counter += 1
        oid = f"ovr_{self._counter}"

        override_record = {
            "override_id": oid,
            "reason": reason,
            "source": source,
            "requires_confirmation": (
                requires_confirmation
            ),
            "confirmed": (
                not requires_confirmation
            ),
            "timestamp": time.time(),
        }

        if requires_confirmation:
            self._confirmations[oid] = (
                override_record
            )
            self._stats[
                "confirmations_requested"
            ] += 1
        else:
            override_record["confirmed"] = True

        self._overrides.append(override_record)
        self._stats["overrides"] += 1

        self._audit(
            "override_applied",
            {
                "override_id": oid,
                "reason": reason,
                "confirmed": override_record[
                    "confirmed"
                ],
            },
        )

        return {
            "override_id": oid,
            "reason": reason,
            "confirmed": override_record[
                "confirmed"
            ],
            "requires_confirmation": (
                requires_confirmation
            ),
        }

    def confirm(
        self,
        override_id: str,
        approved: bool = True,
    ) -> dict[str, Any]:
        """Onay verir.

        Args:
            override_id: Geçersiz kılma ID.
            approved: Onaylandı mı.

        Returns:
            Onay bilgisi.
        """
        record = self._confirmations.get(
            override_id,
        )
        if not record:
            return {
                "error": "override_not_found",
            }

        record["confirmed"] = approved
        record["confirmed_at"] = time.time()

        self._audit(
            "override_confirmed",
            {
                "override_id": override_id,
                "approved": approved,
            },
        )

        return {
            "override_id": override_id,
            "approved": approved,
            "confirmed": True,
        }

    def add_criterion(
        self,
        name: str,
        keywords: list[str],
        auto_override: bool = False,
    ) -> dict[str, Any]:
        """Kriter ekler.

        Args:
            name: Kriter adı.
            keywords: Anahtar kelimeler.
            auto_override: Otomatik geçersiz kıl.

        Returns:
            Ekleme bilgisi.
        """
        criterion = {
            "name": name,
            "keywords": keywords,
            "auto_override": auto_override,
        }
        self._criteria.append(criterion)

        return {
            "name": name,
            "added": True,
            "auto_override": auto_override,
        }

    def escalate(
        self,
        override_id: str,
        target: str = "admin",
        reason: str = "",
    ) -> dict[str, Any]:
        """Eskalasyon tetikler.

        Args:
            override_id: Geçersiz kılma ID.
            target: Hedef.
            reason: Neden.

        Returns:
            Eskalasyon bilgisi.
        """
        escalation = {
            "override_id": override_id,
            "target": target,
            "reason": reason,
            "timestamp": time.time(),
        }
        self._escalations.append(escalation)
        self._stats[
            "escalations_triggered"
        ] += 1

        self._audit(
            "escalation_triggered",
            escalation,
        )

        return {
            "override_id": override_id,
            "escalated_to": target,
            "reason": reason,
            "escalated": True,
        }

    def _audit(
        self,
        action: str,
        details: dict[str, Any],
    ) -> None:
        """Denetim kaydı ekler."""
        self._audit_log.append({
            "action": action,
            "details": details,
            "timestamp": time.time(),
        })

    def get_audit_log(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Denetim kayıtlarını getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Kayıt listesi.
        """
        return list(self._audit_log[-limit:])

    def get_overrides(
        self,
        confirmed_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Geçersiz kılmaları getirir.

        Args:
            confirmed_only: Sadece onaylı.
            limit: Maks kayıt.

        Returns:
            Geçersiz kılma listesi.
        """
        results = self._overrides
        if confirmed_only:
            results = [
                o for o in results
                if o.get("confirmed")
            ]
        return list(results[-limit:])

    @property
    def override_count(self) -> int:
        """Geçersiz kılma sayısı."""
        return self._stats["overrides"]

    @property
    def emergency_count(self) -> int:
        """Acil durum sayısı."""
        return self._stats[
            "emergencies_detected"
        ]

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayısı."""
        return self._stats[
            "escalations_triggered"
        ]
