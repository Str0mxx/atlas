"""
ZT token dogrulayici modulu.

Token dogrulama, imza kontrolu,
talep dogrulama, sure yonetimi,
iptal kontrolu.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ZTTokenValidator:
    """ZT token dogrulayici.

    Attributes:
        _tokens: Token kayitlari.
        _revoked: Iptal edilen tokenler.
        _signing_keys: Imza anahtarlari.
        _stats: Istatistikler.
    """

    TOKEN_TYPES: list[str] = [
        "access",
        "refresh",
        "api_key",
        "service",
        "temporary",
    ]

    def __init__(
        self,
        default_ttl_min: int = 60,
    ) -> None:
        """Dogrulayiciyi baslatir.

        Args:
            default_ttl_min: Varsayilan TTL.
        """
        self._tokens: dict[
            str, dict
        ] = {}
        self._revoked: set[str] = set()
        self._signing_keys: dict[
            str, str
        ] = {}
        self._default_ttl = default_ttl_min
        self._stats: dict[str, int] = {
            "tokens_issued": 0,
            "tokens_validated": 0,
            "tokens_revoked": 0,
            "validation_failures": 0,
            "expired_tokens": 0,
        }
        self._init_signing_key()
        logger.info(
            "ZTTokenValidator baslatildi"
        )

    def _init_signing_key(self) -> None:
        """Varsayilan imza anahtari."""
        kid = "key_default"
        key = hashlib.sha256(
            f"atlas_zt_{uuid4()}".encode()
        ).hexdigest()
        self._signing_keys[kid] = key

    @property
    def token_count(self) -> int:
        """Aktif token sayisi."""
        return sum(
            1
            for t in self._tokens.values()
            if t["active"]
            and t["token_id"]
            not in self._revoked
        )

    def issue_token(
        self,
        user_id: str = "",
        token_type: str = "access",
        claims: dict | None = None,
        ttl_min: int = 0,
        scope: str = "",
    ) -> dict[str, Any]:
        """Token uretir.

        Args:
            user_id: Kullanici ID.
            token_type: Token tipi.
            claims: Talepler.
            ttl_min: Gecerlilik suresi.
            scope: Kapsam.

        Returns:
            Uretim bilgisi.
        """
        try:
            if (
                token_type
                not in self.TOKEN_TYPES
            ):
                return {
                    "issued": False,
                    "error": (
                        f"Gecersiz tip: "
                        f"{token_type}"
                    ),
                }

            tid = f"tk_{uuid4()!s:.8}"
            ttl = (
                ttl_min or self._default_ttl
            )
            token_value = hashlib.sha256(
                f"{tid}{user_id}{uuid4()}"
                .encode()
            ).hexdigest()

            kid = list(
                self._signing_keys.keys()
            )[0]
            key = self._signing_keys[kid]
            signature = hashlib.sha256(
                f"{token_value}{key}".encode()
            ).hexdigest()[:16]

            now = datetime.now(
                timezone.utc
            ).isoformat()
            self._tokens[tid] = {
                "token_id": tid,
                "user_id": user_id,
                "token_type": token_type,
                "token_value": token_value,
                "signature": signature,
                "signing_key_id": kid,
                "claims": claims or {},
                "scope": scope,
                "ttl_min": ttl,
                "active": True,
                "issued_at": now,
            }
            self._stats[
                "tokens_issued"
            ] += 1

            return {
                "token_id": tid,
                "token_value": token_value,
                "signature": signature,
                "token_type": token_type,
                "ttl_min": ttl,
                "issued": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "issued": False,
                "error": str(e),
            }

    def validate_token(
        self,
        token_id: str = "",
        token_value: str = "",
        required_claims: (
            dict | None
        ) = None,
        required_scope: str = "",
    ) -> dict[str, Any]:
        """Token dogrular.

        Args:
            token_id: Token ID.
            token_value: Token degeri.
            required_claims: Gereken talepler.
            required_scope: Gereken kapsam.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            self._stats[
                "tokens_validated"
            ] += 1
            tok = self._tokens.get(
                token_id
            )
            if not tok:
                self._stats[
                    "validation_failures"
                ] += 1
                return {
                    "valid": False,
                    "error": (
                        "Token bulunamadi"
                    ),
                }

            issues: list[str] = []

            if token_id in self._revoked:
                issues.append("revoked")

            if not tok["active"]:
                issues.append("inactive")

            if (
                token_value
                and token_value
                != tok["token_value"]
            ):
                issues.append(
                    "value_mismatch"
                )

            sig_valid = (
                self._verify_signature(
                    token_id
                )
            )
            if not sig_valid:
                issues.append(
                    "invalid_signature"
                )

            if required_claims:
                for k, v in (
                    required_claims.items()
                ):
                    if (
                        tok["claims"].get(k)
                        != v
                    ):
                        issues.append(
                            f"claim_{k}_mismatch"
                        )

            if required_scope and (
                required_scope
                != tok["scope"]
            ):
                issues.append(
                    "scope_mismatch"
                )

            valid = len(issues) == 0
            if not valid:
                self._stats[
                    "validation_failures"
                ] += 1

            return {
                "token_id": token_id,
                "valid": valid,
                "issues": issues,
                "token_type": tok[
                    "token_type"
                ],
                "user_id": tok["user_id"],
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._stats[
                "validation_failures"
            ] += 1
            return {
                "valid": False,
                "error": str(e),
            }

    def _verify_signature(
        self,
        token_id: str,
    ) -> bool:
        """Imza dogrular."""
        tok = self._tokens.get(token_id)
        if not tok:
            return False

        kid = tok["signing_key_id"]
        key = self._signing_keys.get(kid)
        if not key:
            return False

        expected = hashlib.sha256(
            f"{tok['token_value']}{key}"
            .encode()
        ).hexdigest()[:16]
        return expected == tok["signature"]

    def revoke_token(
        self,
        token_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Token iptal eder.

        Args:
            token_id: Token ID.
            reason: Iptal sebebi.

        Returns:
            Iptal bilgisi.
        """
        try:
            tok = self._tokens.get(
                token_id
            )
            if not tok:
                return {
                    "revoked": False,
                    "error": (
                        "Token bulunamadi"
                    ),
                }

            self._revoked.add(token_id)
            tok["active"] = False
            tok["revoked_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            tok["revoke_reason"] = reason
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
        reason: str = "security",
    ) -> dict[str, Any]:
        """Kullanici tokenlerini iptal eder.

        Args:
            user_id: Kullanici ID.
            reason: Iptal sebebi.

        Returns:
            Iptal bilgisi.
        """
        try:
            count = 0
            for tid, tok in (
                self._tokens.items()
            ):
                if (
                    tok["user_id"] == user_id
                    and tok["active"]
                ):
                    self._revoked.add(tid)
                    tok["active"] = False
                    tok["revoked_at"] = (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    )
                    tok["revoke_reason"] = (
                        reason
                    )
                    count += 1

            self._stats[
                "tokens_revoked"
            ] += count

            return {
                "user_id": user_id,
                "revoked_count": count,
                "reason": reason,
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def rotate_signing_key(
        self,
    ) -> dict[str, Any]:
        """Imza anahtari rotasyonu.

        Returns:
            Rotasyon bilgisi.
        """
        try:
            kid = f"key_{uuid4()!s:.8}"
            key = hashlib.sha256(
                f"atlas_zt_{uuid4()}"
                .encode()
            ).hexdigest()
            self._signing_keys[kid] = key

            return {
                "key_id": kid,
                "total_keys": len(
                    self._signing_keys
                ),
                "rotated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rotated": False,
                "error": str(e),
            }

    def is_revoked(
        self,
        token_id: str = "",
    ) -> dict[str, Any]:
        """Token iptal edilmis mi.

        Args:
            token_id: Token ID.

        Returns:
            Kontrol bilgisi.
        """
        try:
            return {
                "token_id": token_id,
                "revoked": (
                    token_id in self._revoked
                ),
                "checked": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_tokens": len(
                    self._tokens
                ),
                "active_tokens": (
                    self.token_count
                ),
                "revoked_tokens": len(
                    self._revoked
                ),
                "signing_keys": len(
                    self._signing_keys
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
