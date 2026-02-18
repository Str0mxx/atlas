"""
Erisim token yoneticisi modulu.

Token uretimi, sure yonetimi,
kapsam yonetimi, iptal,
kullanim takibi.
"""

import logging
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AccessTokenManager:
    """Erisim token yoneticisi.

    Attributes:
        _tokens: Token kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Yoneticiyi baslatir."""
        self._tokens: dict[str, dict] = {}
        self._stats: dict[str, int] = {
            "tokens_generated": 0,
            "tokens_revoked": 0,
            "tokens_expired": 0,
        }
        logger.info(
            "AccessTokenManager baslatildi"
        )

    @property
    def token_count(self) -> int:
        """Token sayisi."""
        return len(self._tokens)

    def generate_token(
        self,
        user_id: str = "",
        scopes: list[str] | None = None,
        ttl_hours: int = 24,
        description: str = "",
    ) -> dict[str, Any]:
        """Token uretir.

        Args:
            user_id: Kullanici ID.
            scopes: Kapsam listesi.
            ttl_hours: Gecerlilik suresi (saat).
            description: Aciklama.

        Returns:
            Token bilgisi.
        """
        try:
            tid = f"tk_{uuid4()!s:.8}"
            token_value = secrets.token_urlsafe(
                32
            )
            now = datetime.now(
                timezone.utc
            ).isoformat()

            self._tokens[tid] = {
                "token_id": tid,
                "token_value": token_value,
                "user_id": user_id,
                "scopes": scopes or ["read"],
                "ttl_hours": ttl_hours,
                "description": description,
                "created_at": now,
                "last_used": None,
                "usage_count": 0,
                "active": True,
                "revoked": False,
            }

            self._stats[
                "tokens_generated"
            ] += 1

            return {
                "token_id": tid,
                "token_value": token_value,
                "scopes": scopes or ["read"],
                "ttl_hours": ttl_hours,
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def validate_token(
        self,
        token_id: str = "",
        required_scope: str = "",
    ) -> dict[str, Any]:
        """Token dogrular.

        Args:
            token_id: Token ID.
            required_scope: Gerekli kapsam.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            if token_id not in self._tokens:
                return {
                    "valid": False,
                    "reason": "not_found",
                }

            token = self._tokens[token_id]

            if token["revoked"]:
                return {
                    "valid": False,
                    "reason": "revoked",
                }

            if not token["active"]:
                return {
                    "valid": False,
                    "reason": "inactive",
                }

            if (
                required_scope
                and required_scope
                not in token["scopes"]
            ):
                return {
                    "valid": False,
                    "reason": "scope_denied",
                }

            token["usage_count"] += 1
            token[
                "last_used"
            ] = datetime.now(
                timezone.utc
            ).isoformat()

            return {
                "valid": True,
                "user_id": token["user_id"],
                "scopes": token["scopes"],
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "valid": False,
                "error": str(e),
            }

    def revoke_token(
        self,
        token_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Token iptal eder.

        Args:
            token_id: Token ID.
            reason: Neden.

        Returns:
            Iptal bilgisi.
        """
        try:
            if token_id not in self._tokens:
                return {
                    "revoked": False,
                    "error": "Bulunamadi",
                }

            token = self._tokens[token_id]
            token["revoked"] = True
            token["active"] = False
            token[
                "revoked_at"
            ] = datetime.now(
                timezone.utc
            ).isoformat()
            token["revoke_reason"] = reason

            self._stats[
                "tokens_revoked"
            ] += 1

            return {
                "token_id": token_id,
                "reason": reason,
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def revoke_user_tokens(
        self,
        user_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Kullanici tokenlarini iptal eder.

        Args:
            user_id: Kullanici ID.
            reason: Neden.

        Returns:
            Iptal bilgisi.
        """
        try:
            revoked = 0
            for token in self._tokens.values():
                if (
                    token["user_id"] == user_id
                    and token["active"]
                ):
                    token["revoked"] = True
                    token["active"] = False
                    token[
                        "revoked_at"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    token[
                        "revoke_reason"
                    ] = reason
                    revoked += 1

            self._stats[
                "tokens_revoked"
            ] += revoked

            return {
                "user_id": user_id,
                "revoked_count": revoked,
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def update_scopes(
        self,
        token_id: str = "",
        scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kapsam gunceller.

        Args:
            token_id: Token ID.
            scopes: Yeni kapsamlar.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            if token_id not in self._tokens:
                return {
                    "updated": False,
                    "error": "Bulunamadi",
                }

            token = self._tokens[token_id]
            old_scopes = token["scopes"]
            token["scopes"] = scopes or []

            return {
                "token_id": token_id,
                "old_scopes": old_scopes,
                "new_scopes": token["scopes"],
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def get_usage_stats(
        self,
        token_id: str = "",
    ) -> dict[str, Any]:
        """Kullanim istatistikleri getirir.

        Args:
            token_id: Token ID.

        Returns:
            Istatistik bilgisi.
        """
        try:
            if token_id not in self._tokens:
                return {
                    "found": False,
                    "retrieved": True,
                }

            token = self._tokens[token_id]

            return {
                "token_id": token_id,
                "user_id": token["user_id"],
                "usage_count": token[
                    "usage_count"
                ],
                "last_used": token[
                    "last_used"
                ],
                "active": token["active"],
                "scopes": token["scopes"],
                "found": True,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def list_active_tokens(
        self,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Aktif tokenlari listeler.

        Args:
            user_id: Kullanici filtresi.

        Returns:
            Liste bilgisi.
        """
        try:
            active = [
                {
                    "token_id": t["token_id"],
                    "user_id": t["user_id"],
                    "scopes": t["scopes"],
                    "usage_count": t[
                        "usage_count"
                    ],
                    "created_at": t[
                        "created_at"
                    ],
                }
                for t in self._tokens.values()
                if t["active"]
                and (
                    not user_id
                    or t["user_id"] == user_id
                )
            ]

            return {
                "tokens": active,
                "count": len(active),
                "listed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "listed": False,
                "error": str(e),
            }
