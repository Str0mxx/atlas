"""
Insan eskalasyon tetikleyici modulu.

Eskalasyon kurallari, esik tespiti,
yonlendirme mantigi, oncelik yonetimi,
yanit takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HumanEscalationTrigger:
    """Insan eskalasyon tetikleyici.

    Attributes:
        _escalations: Eskalasyonlar.
        _rules: Kurallar.
        _stats: Istatistikler.
    """

    PRIORITY_LEVELS: list[str] = [
        "low",
        "medium",
        "high",
        "critical",
        "emergency",
    ]

    ESCALATION_REASONS: list[str] = [
        "low_confidence",
        "high_risk",
        "safety_concern",
        "hallucination_detected",
        "user_request",
        "policy_violation",
        "ambiguous_input",
        "critical_decision",
    ]

    STATUS_TYPES: list[str] = [
        "pending",
        "acknowledged",
        "in_progress",
        "resolved",
        "expired",
    ]

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        risk_threshold: float = 0.7,
        auto_escalate: bool = True,
        timeout_seconds: int = 3600,
    ) -> None:
        """Tetikleyiciyi baslatir.

        Args:
            confidence_threshold: Esik.
            risk_threshold: Risk esigi.
            auto_escalate: Otomatik.
            timeout_seconds: Zaman asimi.
        """
        self._confidence_threshold = (
            confidence_threshold
        )
        self._risk_threshold = (
            risk_threshold
        )
        self._auto_escalate = auto_escalate
        self._timeout_seconds = (
            timeout_seconds
        )
        self._escalations: dict[
            str, dict
        ] = {}
        self._rules: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "escalations_created": 0,
            "escalations_resolved": 0,
            "auto_escalations": 0,
            "manual_escalations": 0,
        }
        logger.info(
            "HumanEscalationTrigger "
            "baslatildi"
        )

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayisi."""
        return len(self._escalations)

    def add_rule(
        self,
        name: str = "",
        condition_type: str = "",
        threshold: float = 0.5,
        priority: str = "medium",
        route_to: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Eskalasyon kurali ekler.

        Args:
            name: Kural adi.
            condition_type: Kosul tipi.
            threshold: Esik degeri.
            priority: Oncelik.
            route_to: Yonlendirme.
            metadata: Ek veri.

        Returns:
            Ekleme bilgisi.
        """
        try:
            rid = f"rul_{uuid4()!s:.8}"
            self._rules[rid] = {
                "rule_id": rid,
                "name": name,
                "condition_type": (
                    condition_type
                ),
                "threshold": threshold,
                "priority": priority,
                "route_to": route_to,
                "active": True,
                "metadata": metadata or {},
            }
            return {
                "rule_id": rid,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def check_escalation(
        self,
        confidence: float = 1.0,
        risk_score: float = 0.0,
        has_hallucination: bool = False,
        safety_concern: bool = False,
        context: str = "",
    ) -> dict[str, Any]:
        """Eskalasyon gerekli mi kontrol.

        Args:
            confidence: Guven degeri.
            risk_score: Risk puani.
            has_hallucination: Halusinasyon.
            safety_concern: Guvenlik.
            context: Baglam.

        Returns:
            Kontrol bilgisi.
        """
        try:
            reasons: list[str] = []
            priority = "low"

            # Dusuk guven
            if (
                confidence
                < self._confidence_threshold
            ):
                reasons.append(
                    "low_confidence"
                )
                priority = "medium"

            # Yuksek risk
            if (
                risk_score
                > self._risk_threshold
            ):
                reasons.append("high_risk")
                priority = "high"

            # Halusinasyon
            if has_hallucination:
                reasons.append(
                    "hallucination_detected"
                )
                priority = "high"

            # Guvenlik endisesi
            if safety_concern:
                reasons.append(
                    "safety_concern"
                )
                priority = "critical"

            # Kural kontrolu
            for rule in (
                self._rules.values()
            ):
                if not rule["active"]:
                    continue
                ct = rule["condition_type"]
                th = rule["threshold"]
                if (
                    ct == "confidence"
                    and confidence < th
                ):
                    reasons.append(
                        "low_confidence"
                    )
                    priority = max(
                        priority,
                        rule["priority"],
                        key=lambda p: (
                            self.PRIORITY_LEVELS.index(
                                p
                            )
                            if p
                            in self.PRIORITY_LEVELS
                            else 0
                        ),
                    )
                elif (
                    ct == "risk"
                    and risk_score > th
                ):
                    reasons.append(
                        "high_risk"
                    )

            # Tekrarlari kaldir
            reasons = list(set(reasons))
            needs_escalation = (
                len(reasons) > 0
            )

            return {
                "needs_escalation": (
                    needs_escalation
                ),
                "reasons": reasons,
                "priority": priority,
                "confidence": confidence,
                "risk_score": risk_score,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def create_escalation(
        self,
        reason: str = "",
        priority: str = "medium",
        description: str = "",
        route_to: str = "",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Eskalasyon olusturur.

        Args:
            reason: Neden.
            priority: Oncelik.
            description: Aciklama.
            route_to: Yonlendirme.
            context: Baglam.

        Returns:
            Olusturma bilgisi.
        """
        try:
            eid = f"esc_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            )

            self._escalations[eid] = {
                "escalation_id": eid,
                "reason": reason,
                "priority": priority,
                "description": description,
                "route_to": route_to,
                "status": "pending",
                "context": context or {},
                "created_at": (
                    now.isoformat()
                ),
                "acknowledged_at": None,
                "resolved_at": None,
                "resolution": None,
            }

            self._stats[
                "escalations_created"
            ] += 1
            if self._auto_escalate:
                self._stats[
                    "auto_escalations"
                ] += 1
            else:
                self._stats[
                    "manual_escalations"
                ] += 1

            return {
                "escalation_id": eid,
                "priority": priority,
                "status": "pending",
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def acknowledge_escalation(
        self,
        escalation_id: str = "",
        acknowledged_by: str = "",
    ) -> dict[str, Any]:
        """Eskalasyonu onayla.

        Args:
            escalation_id: ID.
            acknowledged_by: Onaylayan.

        Returns:
            Onay bilgisi.
        """
        try:
            esc = self._escalations.get(
                escalation_id
            )
            if not esc:
                return {
                    "acknowledged": False,
                    "error": (
                        "Eskalasyon "
                        "bulunamadi"
                    ),
                }

            esc["status"] = "acknowledged"
            esc["acknowledged_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            esc["acknowledged_by"] = (
                acknowledged_by
            )

            return {
                "escalation_id": (
                    escalation_id
                ),
                "status": "acknowledged",
                "acknowledged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "acknowledged": False,
                "error": str(e),
            }

    def resolve_escalation(
        self,
        escalation_id: str = "",
        resolution: str = "",
        resolved_by: str = "",
    ) -> dict[str, Any]:
        """Eskalasyonu cozumle.

        Args:
            escalation_id: ID.
            resolution: Cozum.
            resolved_by: Cozen.

        Returns:
            Cozum bilgisi.
        """
        try:
            esc = self._escalations.get(
                escalation_id
            )
            if not esc:
                return {
                    "resolved": False,
                    "error": (
                        "Eskalasyon "
                        "bulunamadi"
                    ),
                }

            esc["status"] = "resolved"
            esc["resolved_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            esc["resolution"] = resolution
            esc["resolved_by"] = (
                resolved_by
            )

            self._stats[
                "escalations_resolved"
            ] += 1

            return {
                "escalation_id": (
                    escalation_id
                ),
                "status": "resolved",
                "resolved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def get_pending(
        self,
    ) -> dict[str, Any]:
        """Bekleyen eskalasyonlari getirir."""
        try:
            pending = [
                e
                for e in (
                    self._escalations.values()
                )
                if e["status"]
                in ("pending", "acknowledged")
            ]

            # Oncelik siralamasi
            order = {
                p: i
                for i, p in enumerate(
                    self.PRIORITY_LEVELS
                )
            }
            pending.sort(
                key=lambda x: order.get(
                    x["priority"], 0
                ),
                reverse=True,
            )

            return {
                "pending": [
                    {
                        "escalation_id": e[
                            "escalation_id"
                        ],
                        "reason": e[
                            "reason"
                        ],
                        "priority": e[
                            "priority"
                        ],
                        "status": e[
                            "status"
                        ],
                        "description": e[
                            "description"
                        ],
                    }
                    for e in pending
                ],
                "count": len(pending),
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
        """Ozet getirir."""
        try:
            return {
                "total_escalations": len(
                    self._escalations
                ),
                "total_rules": len(
                    self._rules
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
