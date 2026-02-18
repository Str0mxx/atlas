"""
En az yetki uygulayici modulu.

Minimum izinler, rol analizi,
izin budama, erisim inceleme,
oneri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class LeastPrivilegeEnforcer:
    """En az yetki uygulayici.

    Attributes:
        _roles: Rol tanimlari.
        _user_perms: Kullanici izinleri.
        _access_history: Erisim gecmisi.
        _reviews: Inceleme kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Uygulayiciyi baslatir."""
        self._roles: dict[
            str, dict
        ] = {}
        self._user_perms: dict[
            str, dict
        ] = {}
        self._access_history: dict[
            str, list
        ] = {}
        self._reviews: list[dict] = []
        self._stats: dict[str, int] = {
            "roles_defined": 0,
            "permissions_assigned": 0,
            "permissions_pruned": 0,
            "reviews_completed": 0,
            "recommendations": 0,
        }
        logger.info(
            "LeastPrivilegeEnforcer "
            "baslatildi"
        )

    @property
    def role_count(self) -> int:
        """Rol sayisi."""
        return len(self._roles)

    def define_role(
        self,
        name: str = "",
        permissions: (
            list[str] | None
        ) = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Rol tanimlar.

        Args:
            name: Rol adi.
            permissions: Izinler.
            description: Aciklama.

        Returns:
            Tanimlama bilgisi.
        """
        try:
            rid = f"rl_{uuid4()!s:.8}"
            perms = permissions or []
            self._roles[name] = {
                "role_id": rid,
                "name": name,
                "permissions": perms,
                "description": description,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "roles_defined"
            ] += 1

            return {
                "role_id": rid,
                "name": name,
                "permissions_count": len(
                    perms
                ),
                "defined": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "defined": False,
                "error": str(e),
            }

    def assign_permissions(
        self,
        user_id: str = "",
        role: str = "",
        extra_permissions: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Izin atar.

        Args:
            user_id: Kullanici ID.
            role: Rol adi.
            extra_permissions: Ek izinler.

        Returns:
            Atama bilgisi.
        """
        try:
            role_def = self._roles.get(role)
            if not role_def:
                return {
                    "assigned": False,
                    "error": (
                        "Rol bulunamadi"
                    ),
                }

            perms = list(
                role_def["permissions"]
            )
            extra = extra_permissions or []
            perms.extend(extra)
            perms = list(set(perms))

            self._user_perms[user_id] = {
                "role": role,
                "permissions": perms,
                "extra_permissions": extra,
                "assigned_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "permissions_assigned"
            ] += len(perms)

            return {
                "user_id": user_id,
                "role": role,
                "total_permissions": len(
                    perms
                ),
                "assigned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assigned": False,
                "error": str(e),
            }

    def check_permission(
        self,
        user_id: str = "",
        permission: str = "",
    ) -> dict[str, Any]:
        """Izin kontrol eder.

        Args:
            user_id: Kullanici ID.
            permission: Izin adi.

        Returns:
            Kontrol bilgisi.
        """
        try:
            up = self._user_perms.get(
                user_id
            )
            if not up:
                return {
                    "has_permission": False,
                    "error": (
                        "Kullanici bulunamadi"
                    ),
                }

            has = (
                permission
                in up["permissions"]
            )

            if (
                user_id
                not in self._access_history
            ):
                self._access_history[
                    user_id
                ] = []
            self._access_history[
                user_id
            ].append({
                "permission": permission,
                "granted": has,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            })

            return {
                "user_id": user_id,
                "permission": permission,
                "has_permission": has,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def analyze_usage(
        self,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Kullanim analiz eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Analiz bilgisi.
        """
        try:
            up = self._user_perms.get(
                user_id
            )
            if not up:
                return {
                    "analyzed": False,
                    "error": (
                        "Kullanici bulunamadi"
                    ),
                }

            history = (
                self._access_history.get(
                    user_id, []
                )
            )
            used_perms = set(
                h["permission"]
                for h in history
                if h["granted"]
            )
            all_perms = set(
                up["permissions"]
            )
            unused = all_perms - used_perms

            return {
                "user_id": user_id,
                "total_permissions": len(
                    all_perms
                ),
                "used_permissions": len(
                    used_perms
                ),
                "unused_permissions": list(
                    unused
                ),
                "usage_ratio": round(
                    len(used_perms)
                    / max(len(all_perms), 1),
                    2,
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def prune_permissions(
        self,
        user_id: str = "",
        unused_only: bool = True,
    ) -> dict[str, Any]:
        """Izinleri budar.

        Args:
            user_id: Kullanici ID.
            unused_only: Sadece kullanilmayan.

        Returns:
            Budama bilgisi.
        """
        try:
            up = self._user_perms.get(
                user_id
            )
            if not up:
                return {
                    "pruned": False,
                    "error": (
                        "Kullanici bulunamadi"
                    ),
                }

            if unused_only:
                history = (
                    self._access_history.get(
                        user_id, []
                    )
                )
                used = set(
                    h["permission"]
                    for h in history
                    if h["granted"]
                )
                before = len(
                    up["permissions"]
                )
                up["permissions"] = [
                    p
                    for p in up["permissions"]
                    if p in used
                ]
                pruned = before - len(
                    up["permissions"]
                )
            else:
                pruned = len(
                    up.get(
                        "extra_permissions",
                        [],
                    )
                )
                role_def = self._roles.get(
                    up["role"], {}
                )
                up["permissions"] = list(
                    role_def.get(
                        "permissions", []
                    )
                )
                up["extra_permissions"] = []

            self._stats[
                "permissions_pruned"
            ] += pruned

            return {
                "user_id": user_id,
                "permissions_pruned": pruned,
                "remaining": len(
                    up["permissions"]
                ),
                "pruned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "pruned": False,
                "error": str(e),
            }

    def run_access_review(
        self,
    ) -> dict[str, Any]:
        """Erisim incelemesi yapar.

        Returns:
            Inceleme bilgisi.
        """
        try:
            findings: list[dict] = []
            for uid, up in (
                self._user_perms.items()
            ):
                analysis = (
                    self.analyze_usage(
                        user_id=uid
                    )
                )
                if analysis.get("analyzed"):
                    unused = analysis.get(
                        "unused_permissions",
                        [],
                    )
                    if unused:
                        findings.append({
                            "user_id": uid,
                            "unused_count": (
                                len(unused)
                            ),
                            "recommendation": (
                                "prune"
                            ),
                        })

            rid = f"rv_{uuid4()!s:.8}"
            self._reviews.append({
                "review_id": rid,
                "findings": findings,
                "reviewed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            self._stats[
                "reviews_completed"
            ] += 1
            self._stats[
                "recommendations"
            ] += len(findings)

            return {
                "review_id": rid,
                "users_reviewed": len(
                    self._user_perms
                ),
                "findings": len(findings),
                "reviewed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reviewed": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_roles": len(
                    self._roles
                ),
                "total_users": len(
                    self._user_perms
                ),
                "total_reviews": len(
                    self._reviews
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
