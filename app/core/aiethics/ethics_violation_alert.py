"""
Etik ihlal uyari modulu.

Ihlal tespiti, uyari olusturma,
ciddiyet siniflandirma, eskalasyon
yonlendirme, cozum takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EthicsViolationAlert:
    """Etik ihlal uyari sistemi.

    Attributes:
        _alerts: Uyarilar.
        _rules: Uyari kurallari.
        _escalations: Eskalasyonlar.
        _stats: Istatistikler.
    """

    SEVERITY_LEVELS: list[str] = [
        "info",
        "low",
        "medium",
        "high",
        "critical",
    ]

    ALERT_STATUS: list[str] = [
        "open",
        "acknowledged",
        "investigating",
        "resolved",
        "dismissed",
    ]

    VIOLATION_TYPES: list[str] = [
        "bias_detected",
        "fairness_violation",
        "rule_violation",
        "disparity_alert",
        "transparency_gap",
        "compliance_issue",
    ]

    def __init__(
        self,
        auto_escalate: bool = True,
        escalation_threshold: str = "high",
    ) -> None:
        """Uyari sistemini baslatir.

        Args:
            auto_escalate: Oto eskalasyon.
            escalation_threshold: Esik.
        """
        self._auto_escalate = (
            auto_escalate
        )
        self._escalation_threshold = (
            escalation_threshold
        )
        self._alerts: dict[
            str, dict
        ] = {}
        self._rules: dict[
            str, dict
        ] = {}
        self._escalations: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "alerts_raised": 0,
            "alerts_resolved": 0,
            "escalations_made": 0,
            "critical_alerts": 0,
        }
        logger.info(
            "EthicsViolationAlert "
            "baslatildi"
        )

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    def add_alert_rule(
        self,
        name: str = "",
        violation_type: str = "",
        severity: str = "medium",
        condition: str = "",
        threshold: float = 0.0,
        auto_escalate: bool = False,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Uyari kurali ekler.

        Args:
            name: Ad.
            violation_type: Ihlal tipi.
            severity: Ciddiyet.
            condition: Kosul.
            threshold: Esik.
            auto_escalate: Oto eskalasyon.
            metadata: Ek veri.

        Returns:
            Kural bilgisi.
        """
        try:
            rid = f"arule_{uuid4()!s:.8}"
            self._rules[rid] = {
                "rule_id": rid,
                "name": name,
                "violation_type": (
                    violation_type
                ),
                "severity": severity,
                "condition": condition,
                "threshold": threshold,
                "auto_escalate": (
                    auto_escalate
                ),
                "active": True,
                "metadata": metadata or {},
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
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

    def raise_alert(
        self,
        violation_type: str = "",
        severity: str = "medium",
        title: str = "",
        description: str = "",
        source: str = "",
        evidence: dict | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Uyari olusturur.

        Args:
            violation_type: Ihlal tipi.
            severity: Ciddiyet.
            title: Baslik.
            description: Aciklama.
            source: Kaynak.
            evidence: Kanit.
            metadata: Ek veri.

        Returns:
            Uyari bilgisi.
        """
        try:
            aid = f"valr_{uuid4()!s:.8}"

            alert = {
                "alert_id": aid,
                "violation_type": (
                    violation_type
                ),
                "severity": severity,
                "title": title,
                "description": description,
                "source": source,
                "evidence": evidence or {},
                "status": "open",
                "metadata": metadata or {},
                "raised_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._alerts[aid] = alert
            self._stats[
                "alerts_raised"
            ] += 1

            if severity == "critical":
                self._stats[
                    "critical_alerts"
                ] += 1

            # Oto eskalasyon
            escalation_id = None
            sev_idx = (
                self.SEVERITY_LEVELS.index(
                    severity
                )
                if severity
                in self.SEVERITY_LEVELS
                else 0
            )
            thresh_idx = (
                self.SEVERITY_LEVELS.index(
                    self._escalation_threshold
                )
                if self._escalation_threshold
                in self.SEVERITY_LEVELS
                else 3
            )

            if (
                self._auto_escalate
                and sev_idx >= thresh_idx
            ):
                esc = self._escalate(
                    aid, severity
                )
                escalation_id = esc.get(
                    "escalation_id"
                )

            return {
                "alert_id": aid,
                "severity": severity,
                "escalation_id": (
                    escalation_id
                ),
                "raised": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "raised": False,
                "error": str(e),
            }

    def check_violations(
        self,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Ihlal kontrolu yapar.

        Args:
            context: Baglam verisi.

        Returns:
            Kontrol bilgisi.
        """
        try:
            ctx = context or {}
            violations: list[dict] = []

            for rule in (
                self._rules.values()
            ):
                if not rule["active"]:
                    continue

                cond = rule.get(
                    "condition", ""
                )
                threshold = rule.get(
                    "threshold", 0.0
                )

                val = ctx.get(cond)
                if val is None:
                    continue

                violated = False
                if isinstance(
                    val, (int, float)
                ):
                    if val > threshold:
                        violated = True
                elif isinstance(val, bool):
                    if val:
                        violated = True

                if violated:
                    result = (
                        self.raise_alert(
                            violation_type=rule[
                                "violation_type"
                            ],
                            severity=rule[
                                "severity"
                            ],
                            title=rule[
                                "name"
                            ],
                            description=(
                                f"{cond}="
                                f"{val} > "
                                f"{threshold}"
                            ),
                            source=(
                                "auto_check"
                            ),
                            evidence={
                                "rule_id": rule[
                                    "rule_id"
                                ],
                                "value": val,
                                "threshold": (
                                    threshold
                                ),
                            },
                        )
                    )
                    violations.append(
                        result
                    )

            return {
                "violations": violations,
                "violation_count": len(
                    violations
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _escalate(
        self,
        alert_id: str,
        severity: str,
    ) -> dict[str, Any]:
        """Eskalasyon yapar."""
        eid = f"esc_{uuid4()!s:.8}"
        self._escalations[eid] = {
            "escalation_id": eid,
            "alert_id": alert_id,
            "severity": severity,
            "status": "pending",
            "escalated_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        }
        self._stats[
            "escalations_made"
        ] += 1
        return {"escalation_id": eid}

    def acknowledge_alert(
        self,
        alert_id: str = "",
        acknowledged_by: str = "",
    ) -> dict[str, Any]:
        """Uyariyi kabul eder.

        Args:
            alert_id: Uyari ID.
            acknowledged_by: Kabul eden.

        Returns:
            Kabul bilgisi.
        """
        try:
            alert = self._alerts.get(
                alert_id
            )
            if not alert:
                return {
                    "acknowledged": False,
                    "error": (
                        "Uyari bulunamadi"
                    ),
                }
            alert["status"] = (
                "acknowledged"
            )
            alert["acknowledged_by"] = (
                acknowledged_by
            )
            alert["acknowledged_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            return {
                "alert_id": alert_id,
                "acknowledged": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "acknowledged": False,
                "error": str(e),
            }

    def resolve_alert(
        self,
        alert_id: str = "",
        resolution: str = "",
        resolved_by: str = "",
    ) -> dict[str, Any]:
        """Uyariyi cozer.

        Args:
            alert_id: Uyari ID.
            resolution: Cozum.
            resolved_by: Cozen.

        Returns:
            Cozum bilgisi.
        """
        try:
            alert = self._alerts.get(
                alert_id
            )
            if not alert:
                return {
                    "resolved": False,
                    "error": (
                        "Uyari bulunamadi"
                    ),
                }
            alert["status"] = "resolved"
            alert["resolution"] = (
                resolution
            )
            alert["resolved_by"] = (
                resolved_by
            )
            alert["resolved_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._stats[
                "alerts_resolved"
            ] += 1
            return {
                "alert_id": alert_id,
                "resolved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def get_open_alerts(
        self,
    ) -> dict[str, Any]:
        """Acik uyarilari getirir."""
        try:
            open_alerts = [
                a
                for a in (
                    self._alerts.values()
                )
                if a["status"]
                in ("open", "acknowledged")
            ]
            return {
                "alerts": open_alerts,
                "count": len(open_alerts),
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
            severity_dist: dict[
                str, int
            ] = {}
            for a in (
                self._alerts.values()
            ):
                s = a.get(
                    "severity", "unknown"
                )
                severity_dist[s] = (
                    severity_dist.get(s, 0)
                    + 1
                )

            return {
                "total_alerts": len(
                    self._alerts
                ),
                "total_rules": len(
                    self._rules
                ),
                "total_escalations": len(
                    self._escalations
                ),
                "severity_distribution": (
                    severity_dist
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
