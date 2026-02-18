"""
Asiri yetki tespitcisi modulu.

Yetki analizi, en az yetki kontrolu,
kapsam daraltma, risk puanlama,
duzeltme onerileri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class OverPermissionDetector:
    """Asiri yetki tespitcisi.

    Attributes:
        _policies: Yetki politikalari.
        _scans: Tarama kayitlari.
        _violations: Ihlal kayitlari.
        _recommendations: Oneriler.
        _stats: Istatistikler.
    """

    RISK_LEVELS: list[str] = [
        "low",
        "medium",
        "high",
        "critical",
    ]

    SCOPE_CATEGORIES: list[str] = [
        "read",
        "write",
        "delete",
        "admin",
        "execute",
    ]

    def __init__(self) -> None:
        """Tespitciyi baslatir."""
        self._policies: dict[
            str, dict
        ] = {}
        self._scans: list[dict] = []
        self._violations: list[dict] = []
        self._recommendations: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "policies_created": 0,
            "scans_run": 0,
            "violations_found": 0,
            "recommendations_made": 0,
            "remediations_applied": 0,
        }
        logger.info(
            "OverPermissionDetector "
            "baslatildi"
        )

    @property
    def violation_count(self) -> int:
        """Ihlal sayisi."""
        return len(self._violations)

    def create_policy(
        self,
        name: str = "",
        service: str = "",
        required_scopes: (
            list[str] | None
        ) = None,
        max_scopes: int = 5,
        forbidden_scopes: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Yetki politikasi olusturur.

        Args:
            name: Politika adi.
            service: Servis adi.
            required_scopes: Gerekli kapsamlar.
            max_scopes: Max kapsam sayisi.
            forbidden_scopes: Yasakli kapsamlar.

        Returns:
            Olusturma bilgisi.
        """
        try:
            pid = f"op_{uuid4()!s:.8}"
            self._policies[name] = {
                "policy_id": pid,
                "name": name,
                "service": service,
                "required_scopes": (
                    required_scopes or []
                ),
                "max_scopes": max_scopes,
                "forbidden_scopes": (
                    forbidden_scopes or []
                ),
                "active": True,
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

    def scan_key_permissions(
        self,
        key_id: str = "",
        current_scopes: (
            list[str] | None
        ) = None,
        used_scopes: (
            list[str] | None
        ) = None,
        policy_name: str = "",
        service: str = "",
    ) -> dict[str, Any]:
        """Anahtar yetkilerini tarar.

        Args:
            key_id: Anahtar ID.
            current_scopes: Mevcut kapsamlar.
            used_scopes: Kullanilan kapsamlar.
            policy_name: Politika adi.
            service: Servis adi.

        Returns:
            Tarama sonucu.
        """
        try:
            self._stats["scans_run"] += 1
            curr = current_scopes or []
            used = used_scopes or []
            violations: list[dict] = []

            # Kullanilmayan kapsam
            unused = [
                s for s in curr
                if s not in used
            ]
            if unused:
                violations.append({
                    "type": "unused_scopes",
                    "detail": (
                        f"{len(unused)} "
                        f"kullanilmayan kapsam"
                    ),
                    "scopes": unused,
                    "risk": (
                        "high"
                        if len(unused) > 3
                        else "medium"
                    ),
                })

            # Admin kapsami kontrolu
            admin_scopes = [
                s for s in curr
                if "admin" in s.lower()
                or "delete" in s.lower()
            ]
            if admin_scopes:
                admin_used = [
                    s for s in admin_scopes
                    if s in used
                ]
                if not admin_used:
                    violations.append({
                        "type": (
                            "unused_admin"
                        ),
                        "detail": (
                            "Admin yetkileri "
                            "kullanilmiyor"
                        ),
                        "scopes": admin_scopes,
                        "risk": "critical",
                    })

            # Politika kontrolu
            policy = self._policies.get(
                policy_name
            )
            if policy:
                # Max kapsam
                if (
                    len(curr)
                    > policy["max_scopes"]
                ):
                    violations.append({
                        "type": (
                            "exceeds_max_scopes"
                        ),
                        "detail": (
                            f"{len(curr)} > "
                            f"{policy['max_scopes']}"
                        ),
                        "risk": "high",
                    })

                # Yasakli kapsam
                forbidden = [
                    s for s in curr
                    if s in policy[
                        "forbidden_scopes"
                    ]
                ]
                if forbidden:
                    violations.append({
                        "type": (
                            "forbidden_scopes"
                        ),
                        "detail": (
                            f"Yasakli: "
                            f"{forbidden}"
                        ),
                        "scopes": forbidden,
                        "risk": "critical",
                    })

            # Risk puani
            risk_score = 0.0
            for v in violations:
                if v["risk"] == "critical":
                    risk_score += 0.4
                elif v["risk"] == "high":
                    risk_score += 0.3
                elif v["risk"] == "medium":
                    risk_score += 0.2
                else:
                    risk_score += 0.1
            risk_score = min(
                risk_score, 1.0
            )

            # Ihlalleri kaydet
            for v in violations:
                vid = f"vl_{uuid4()!s:.8}"
                v["violation_id"] = vid
                v["key_id"] = key_id
                v["detected_at"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )
                self._violations.append(v)

            self._stats[
                "violations_found"
            ] += len(violations)

            scan = {
                "key_id": key_id,
                "current_scopes": len(curr),
                "used_scopes": len(used),
                "unused_scopes": len(unused),
                "violations": len(
                    violations
                ),
                "risk_score": round(
                    risk_score, 2
                ),
                "scanned": True,
            }
            self._scans.append(scan)

            return {
                **scan,
                "violation_details": (
                    violations
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scanned": False,
                "error": str(e),
            }

    def get_remediation(
        self,
        key_id: str = "",
        current_scopes: (
            list[str] | None
        ) = None,
        used_scopes: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Duzeltme onerileri getirir.

        Args:
            key_id: Anahtar ID.
            current_scopes: Mevcut kapsamlar.
            used_scopes: Kullanilan kapsamlar.

        Returns:
            Oneri listesi.
        """
        try:
            curr = current_scopes or []
            used = used_scopes or []
            recs: list[dict] = []

            unused = [
                s for s in curr
                if s not in used
            ]
            if unused:
                recs.append({
                    "type": "remove_scopes",
                    "detail": (
                        "Kullanilmayan "
                        "kapsamlari kaldirin"
                    ),
                    "scopes_to_remove": (
                        unused
                    ),
                    "priority": (
                        "high"
                        if len(unused) > 3
                        else "medium"
                    ),
                })

            recommended = list(used)
            if recommended != curr:
                recs.append({
                    "type": (
                        "scope_reduction"
                    ),
                    "detail": (
                        "Kapsamlari "
                        "daraltın"
                    ),
                    "recommended_scopes": (
                        recommended
                    ),
                    "reduction": (
                        len(curr)
                        - len(recommended)
                    ),
                    "priority": "medium",
                })

            for r in recs:
                r["key_id"] = key_id
                self._recommendations.append(
                    r
                )
            self._stats[
                "recommendations_made"
            ] += len(recs)

            return {
                "key_id": key_id,
                "recommendations": recs,
                "count": len(recs),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def apply_remediation(
        self,
        key_id: str = "",
        scopes_to_remove: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Duzeltme uygular.

        Args:
            key_id: Anahtar ID.
            scopes_to_remove: Kaldirilacak.

        Returns:
            Uygulama bilgisi.
        """
        try:
            remove = scopes_to_remove or []
            self._stats[
                "remediations_applied"
            ] += 1

            return {
                "key_id": key_id,
                "removed_scopes": remove,
                "count": len(remove),
                "applied": True,
                "applied_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "applied": False,
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
                "total_scans": len(
                    self._scans
                ),
                "total_violations": len(
                    self._violations
                ),
                "total_recommendations": (
                    len(self._recommendations)
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
