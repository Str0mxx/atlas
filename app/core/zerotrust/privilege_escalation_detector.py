"""
Yetki yukseltme tespit modulu.

Yetki yukseltme tespiti, kalip analizi,
uyari uretimi, otomatik engelleme,
sorusturma.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PrivilegeEscalationDetector:
    """Yetki yukseltme tespitcisi.

    Attributes:
        _rules: Tespit kurallari.
        _alerts: Uyarilar.
        _blocked: Engellenen islemler.
        _investigations: Sorusturmalar.
        _patterns: Kalip kayitlari.
        _stats: Istatistikler.
    """

    ALERT_SEVERITIES: list[str] = [
        "info",
        "warning",
        "critical",
        "emergency",
    ]

    ESCALATION_TYPES: list[str] = [
        "horizontal",
        "vertical",
        "lateral",
        "role_abuse",
        "permission_creep",
    ]

    def __init__(
        self,
        auto_block: bool = True,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            auto_block: Otomatik engelleme.
        """
        self._rules: dict[
            str, dict
        ] = {}
        self._alerts: list[dict] = []
        self._blocked: list[dict] = []
        self._investigations: dict[
            str, dict
        ] = {}
        self._patterns: list[dict] = []
        self._auto_block = auto_block
        self._stats: dict[str, int] = {
            "checks_performed": 0,
            "escalations_detected": 0,
            "alerts_generated": 0,
            "auto_blocked": 0,
            "investigations_opened": 0,
        }
        self._init_default_rules()
        logger.info(
            "PrivilegeEscalationDetector "
            "baslatildi"
        )

    def _init_default_rules(self) -> None:
        """Varsayilan kurallar."""
        defaults = [
            {
                "name": "rapid_perm_change",
                "description": (
                    "Hizli izin degisikligi"
                ),
                "severity": "critical",
                "type": "vertical",
            },
            {
                "name": "cross_role_access",
                "description": (
                    "Rol disi erisim"
                ),
                "severity": "warning",
                "type": "horizontal",
            },
            {
                "name": "admin_escalation",
                "description": (
                    "Admin yukseltme"
                ),
                "severity": "emergency",
                "type": "vertical",
            },
            {
                "name": "unusual_time_access",
                "description": (
                    "Olagan disi saat"
                ),
                "severity": "info",
                "type": "lateral",
            },
        ]
        for rule in defaults:
            rid = f"pr_{uuid4()!s:.8}"
            self._rules[rule["name"]] = {
                "rule_id": rid,
                "active": True,
                **rule,
            }

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    def add_rule(
        self,
        name: str = "",
        description: str = "",
        severity: str = "warning",
        escalation_type: str = "vertical",
        conditions: dict | None = None,
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            name: Kural adi.
            description: Aciklama.
            severity: Ciddiyet.
            escalation_type: Yukseltme tipi.
            conditions: Kosullar.

        Returns:
            Ekleme bilgisi.
        """
        try:
            if (
                severity
                not in self.ALERT_SEVERITIES
            ):
                return {
                    "added": False,
                    "error": (
                        f"Gecersiz: {severity}"
                    ),
                }

            rid = f"pr_{uuid4()!s:.8}"
            self._rules[name] = {
                "rule_id": rid,
                "name": name,
                "description": description,
                "severity": severity,
                "type": escalation_type,
                "conditions": (
                    conditions or {}
                ),
                "active": True,
            }

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

    def check_escalation(
        self,
        user_id: str = "",
        action: str = "",
        current_role: str = "",
        target_resource: str = "",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Yetki yukseltme kontrol eder.

        Args:
            user_id: Kullanici ID.
            action: Eylem.
            current_role: Mevcut rol.
            target_resource: Hedef kaynak.
            context: Baglam.

        Returns:
            Kontrol bilgisi.
        """
        try:
            self._stats[
                "checks_performed"
            ] += 1
            ctx = context or {}
            detections: list[dict] = []
            risk_score = 0.0

            for rule in (
                self._rules.values()
            ):
                if not rule["active"]:
                    continue

                matched = (
                    self._evaluate_rule(
                        rule,
                        user_id,
                        action,
                        current_role,
                        target_resource,
                        ctx,
                    )
                )
                if matched:
                    detections.append({
                        "rule": rule["name"],
                        "severity": rule[
                            "severity"
                        ],
                        "type": rule["type"],
                    })
                    sev = rule["severity"]
                    if sev == "emergency":
                        risk_score += 0.5
                    elif sev == "critical":
                        risk_score += 0.3
                    elif sev == "warning":
                        risk_score += 0.2
                    else:
                        risk_score += 0.1

            risk_score = min(
                1.0, risk_score
            )
            escalation_detected = (
                len(detections) > 0
            )

            if escalation_detected:
                self._stats[
                    "escalations_detected"
                ] += 1
                self._record_pattern(
                    user_id,
                    action,
                    detections,
                )

                alert = self._generate_alert(
                    user_id,
                    action,
                    detections,
                    risk_score,
                )

                if (
                    self._auto_block
                    and risk_score >= 0.5
                ):
                    self._block_action(
                        user_id,
                        action,
                        target_resource,
                        alert[
                            "alert_id"
                        ],
                    )

            return {
                "user_id": user_id,
                "action": action,
                "escalation_detected": (
                    escalation_detected
                ),
                "detections": detections,
                "risk_score": round(
                    risk_score, 2
                ),
                "blocked": (
                    escalation_detected
                    and self._auto_block
                    and risk_score >= 0.5
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _evaluate_rule(
        self,
        rule: dict,
        user_id: str,
        action: str,
        current_role: str,
        target_resource: str,
        context: dict,
    ) -> bool:
        """Kural degerlendirir."""
        name = rule["name"]

        if name == "rapid_perm_change":
            return context.get(
                "rapid_change", False
            )
        if name == "cross_role_access":
            return context.get(
                "cross_role", False
            )
        if name == "admin_escalation":
            return (
                "admin" in action.lower()
                or context.get(
                    "admin_attempt", False
                )
            )
        if name == "unusual_time_access":
            return context.get(
                "unusual_time", False
            )

        conds = rule.get("conditions", {})
        if conds.get("action_pattern"):
            return conds[
                "action_pattern"
            ] in action
        return False

    def _generate_alert(
        self,
        user_id: str,
        action: str,
        detections: list[dict],
        risk_score: float,
    ) -> dict:
        """Uyari uretir."""
        aid = f"al_{uuid4()!s:.8}"
        severities = [
            d["severity"]
            for d in detections
        ]
        if "emergency" in severities:
            sev = "emergency"
        elif "critical" in severities:
            sev = "critical"
        elif "warning" in severities:
            sev = "warning"
        else:
            sev = "info"

        alert = {
            "alert_id": aid,
            "user_id": user_id,
            "action": action,
            "severity": sev,
            "risk_score": round(
                risk_score, 2
            ),
            "detections": detections,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "acknowledged": False,
        }
        self._alerts.append(alert)
        self._stats[
            "alerts_generated"
        ] += 1
        return alert

    def _block_action(
        self,
        user_id: str,
        action: str,
        target: str,
        alert_id: str,
    ) -> None:
        """Eylem engeller."""
        self._blocked.append({
            "user_id": user_id,
            "action": action,
            "target": target,
            "alert_id": alert_id,
            "blocked_at": datetime.now(
                timezone.utc
            ).isoformat(),
        })
        self._stats["auto_blocked"] += 1

    def _record_pattern(
        self,
        user_id: str,
        action: str,
        detections: list[dict],
    ) -> None:
        """Kalip kaydeder."""
        self._patterns.append({
            "user_id": user_id,
            "action": action,
            "types": [
                d["type"]
                for d in detections
            ],
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    def acknowledge_alert(
        self,
        alert_id: str = "",
        analyst: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Uyariyi onaylar.

        Args:
            alert_id: Uyari ID.
            analyst: Analizci.
            notes: Notlar.

        Returns:
            Onay bilgisi.
        """
        try:
            for alert in self._alerts:
                if (
                    alert["alert_id"]
                    == alert_id
                ):
                    alert[
                        "acknowledged"
                    ] = True
                    alert["analyst"] = analyst
                    alert["notes"] = notes
                    alert[
                        "acknowledged_at"
                    ] = (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    )
                    return {
                        "alert_id": alert_id,
                        "acknowledged": True,
                    }

            return {
                "acknowledged": False,
                "error": (
                    "Uyari bulunamadi"
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "acknowledged": False,
                "error": str(e),
            }

    def open_investigation(
        self,
        alert_id: str = "",
        user_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Sorusturma acar.

        Args:
            alert_id: Uyari ID.
            user_id: Hedef kullanici.
            description: Aciklama.

        Returns:
            Sorusturma bilgisi.
        """
        try:
            iid = f"iv_{uuid4()!s:.8}"
            user_patterns = [
                p
                for p in self._patterns
                if p["user_id"] == user_id
            ]
            user_alerts = [
                a
                for a in self._alerts
                if a["user_id"] == user_id
            ]
            user_blocks = [
                b
                for b in self._blocked
                if b["user_id"] == user_id
            ]

            self._investigations[iid] = {
                "investigation_id": iid,
                "alert_id": alert_id,
                "user_id": user_id,
                "description": description,
                "status": "open",
                "patterns": user_patterns,
                "related_alerts": len(
                    user_alerts
                ),
                "blocked_actions": len(
                    user_blocks
                ),
                "findings": [],
                "opened_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "investigations_opened"
            ] += 1

            return {
                "investigation_id": iid,
                "user_id": user_id,
                "patterns_found": len(
                    user_patterns
                ),
                "related_alerts": len(
                    user_alerts
                ),
                "opened": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "opened": False,
                "error": str(e),
            }

    def add_finding(
        self,
        investigation_id: str = "",
        finding: str = "",
        severity: str = "info",
    ) -> dict[str, Any]:
        """Bulgu ekler.

        Args:
            investigation_id: Sorusturma ID.
            finding: Bulgu.
            severity: Ciddiyet.

        Returns:
            Ekleme bilgisi.
        """
        try:
            inv = (
                self._investigations.get(
                    investigation_id
                )
            )
            if not inv:
                return {
                    "added": False,
                    "error": (
                        "Sorusturma bulunamadi"
                    ),
                }

            inv["findings"].append({
                "finding": finding,
                "severity": severity,
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })

            return {
                "investigation_id": (
                    investigation_id
                ),
                "findings_count": len(
                    inv["findings"]
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def close_investigation(
        self,
        investigation_id: str = "",
        resolution: str = "",
    ) -> dict[str, Any]:
        """Sorusturma kapatir.

        Args:
            investigation_id: Sorusturma ID.
            resolution: Cozum.

        Returns:
            Kapatma bilgisi.
        """
        try:
            inv = (
                self._investigations.get(
                    investigation_id
                )
            )
            if not inv:
                return {
                    "closed": False,
                    "error": (
                        "Sorusturma bulunamadi"
                    ),
                }

            inv["status"] = "closed"
            inv["resolution"] = resolution
            inv["closed_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            return {
                "investigation_id": (
                    investigation_id
                ),
                "resolution": resolution,
                "findings_count": len(
                    inv["findings"]
                ),
                "closed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "closed": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_rules": len(
                    self._rules
                ),
                "total_alerts": len(
                    self._alerts
                ),
                "total_blocked": len(
                    self._blocked
                ),
                "total_investigations": len(
                    self._investigations
                ),
                "total_patterns": len(
                    self._patterns
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
