"""
Politika uygulayici modulu.

Politika uygulama, kural degerlendirme,
ihlal tespiti, otomatik duzeltme,
istisna yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CompliancePolicyEnforcer:
    """Politika uygulayici.

    Attributes:
        _policies: Politika kayitlari.
        _violations: Ihlal kayitlari.
        _exceptions: Istisna kayitlari.
        _remediations: Duzeltme kayitlari.
        _stats: Istatistikler.
    """

    POLICY_TYPES: list[str] = [
        "data_protection",
        "access_control",
        "encryption",
        "retention",
        "consent",
        "breach_response",
        "audit",
        "training",
    ]

    SEVERITY_LEVELS: list[str] = [
        "info",
        "low",
        "medium",
        "high",
        "critical",
    ]

    def __init__(
        self,
        auto_remediate: bool = False,
    ) -> None:
        """Uygulayiciyi baslatir.

        Args:
            auto_remediate: Otomatik duzelt.
        """
        self._auto_remediate = (
            auto_remediate
        )
        self._policies: dict[
            str, dict
        ] = {}
        self._violations: list[dict] = []
        self._exceptions: dict[
            str, dict
        ] = {}
        self._remediations: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "policies_created": 0,
            "evaluations_run": 0,
            "violations_found": 0,
            "auto_remediations": 0,
            "exceptions_granted": 0,
        }
        logger.info(
            "CompliancePolicyEnforcer "
            "baslatildi"
        )

    @property
    def violation_count(self) -> int:
        """Ihlal sayisi."""
        return len(self._violations)

    def create_policy(
        self,
        name: str = "",
        policy_type: str = (
            "data_protection"
        ),
        framework_key: str = "",
        rules: list[dict] | None = None,
        description: str = "",
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Politika olusturur.

        Args:
            name: Politika adi.
            policy_type: Politika tipi.
            framework_key: Cerceve.
            rules: Kurallar.
            description: Aciklama.
            severity: Ciddiyet.

        Returns:
            Politika bilgisi.
        """
        try:
            if (
                policy_type
                not in self.POLICY_TYPES
            ):
                return {
                    "created": False,
                    "error": (
                        f"Gecersiz: "
                        f"{policy_type}"
                    ),
                }

            pid = f"pl_{uuid4()!s:.8}"
            self._policies[pid] = {
                "policy_id": pid,
                "name": name,
                "policy_type": policy_type,
                "framework_key": (
                    framework_key
                ),
                "rules": rules or [],
                "description": description,
                "severity": severity,
                "is_active": True,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "policies_created"
            ] += 1

            return {
                "policy_id": pid,
                "name": name,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def evaluate(
        self,
        policy_id: str = "",
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Politika degerlendirir.

        Args:
            policy_id: Politika ID.
            context: Degerlendirme baglami.

        Returns:
            Degerlendirme sonucu.
        """
        try:
            policy = self._policies.get(
                policy_id
            )
            if not policy:
                return {
                    "evaluated": False,
                    "error": (
                        "Politika bulunamadi"
                    ),
                }

            ctx = context or {}
            self._stats[
                "evaluations_run"
            ] += 1

            violations = []
            for rule in policy.get(
                "rules", []
            ):
                field = rule.get("field", "")
                op = rule.get(
                    "operator", "exists"
                )
                expected = rule.get(
                    "value"
                )
                actual = ctx.get(field)

                violated = False
                if op == "exists":
                    violated = (
                        actual is None
                    )
                elif op == "equals":
                    violated = (
                        actual != expected
                    )
                elif op == "not_equals":
                    violated = (
                        actual == expected
                    )
                elif op == "min":
                    violated = (
                        actual is not None
                        and actual < expected
                    )
                elif op == "max":
                    violated = (
                        actual is not None
                        and actual > expected
                    )

                if violated:
                    violations.append({
                        "rule": rule,
                        "actual": actual,
                    })

            # Ihlalleri kaydet
            if violations:
                for v in violations:
                    vid = (
                        f"vl_{uuid4()!s:.8}"
                    )
                    record = {
                        "violation_id": vid,
                        "policy_id": (
                            policy_id
                        ),
                        "policy_name": (
                            policy["name"]
                        ),
                        "severity": policy[
                            "severity"
                        ],
                        "rule": v["rule"],
                        "actual": v[
                            "actual"
                        ],
                        "detected_at": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    }
                    self._violations.append(
                        record
                    )
                    self._stats[
                        "violations_found"
                    ] += 1

                # Otomatik duzeltme
                if self._auto_remediate:
                    self._auto_fix(
                        policy_id,
                        violations,
                    )

            return {
                "policy_id": policy_id,
                "compliant": (
                    len(violations) == 0
                ),
                "violations": len(
                    violations
                ),
                "evaluated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "evaluated": False,
                "error": str(e),
            }

    def _auto_fix(
        self,
        policy_id: str,
        violations: list[dict],
    ) -> None:
        """Otomatik duzeltme."""
        for v in violations:
            self._remediations.append({
                "remediation_id": (
                    f"rm_{uuid4()!s:.8}"
                ),
                "policy_id": policy_id,
                "rule": v["rule"],
                "action": "auto_remediated",
                "remediated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })
            self._stats[
                "auto_remediations"
            ] += 1

    def grant_exception(
        self,
        policy_id: str = "",
        reason: str = "",
        approved_by: str = "",
        expiry_days: int = 30,
    ) -> dict[str, Any]:
        """Istisna verir.

        Args:
            policy_id: Politika ID.
            reason: Sebep.
            approved_by: Onaylayan.
            expiry_days: Sure (gun).

        Returns:
            Istisna bilgisi.
        """
        try:
            policy = self._policies.get(
                policy_id
            )
            if not policy:
                return {
                    "granted": False,
                    "error": (
                        "Politika bulunamadi"
                    ),
                }

            eid = f"ex_{uuid4()!s:.8}"
            self._exceptions[eid] = {
                "exception_id": eid,
                "policy_id": policy_id,
                "reason": reason,
                "approved_by": approved_by,
                "expiry_days": expiry_days,
                "status": "active",
                "granted_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "exceptions_granted"
            ] += 1

            return {
                "exception_id": eid,
                "policy_id": policy_id,
                "granted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "granted": False,
                "error": str(e),
            }

    def get_violations(
        self,
        severity: str = "",
    ) -> dict[str, Any]:
        """Ihlalleri getirir.

        Args:
            severity: Ciddiyet filtresi.

        Returns:
            Ihlal listesi.
        """
        try:
            if severity:
                filtered = [
                    v
                    for v in self._violations
                    if v["severity"]
                    == severity
                ]
            else:
                filtered = list(
                    self._violations
                )

            return {
                "violations": filtered,
                "count": len(filtered),
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
                "total_policies": len(
                    self._policies
                ),
                "total_violations": len(
                    self._violations
                ),
                "total_exceptions": len(
                    self._exceptions
                ),
                "total_remediations": len(
                    self._remediations
                ),
                "auto_remediate": (
                    self._auto_remediate
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
