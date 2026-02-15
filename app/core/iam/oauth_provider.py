"""ATLAS OAuth Saglayici modulu.

Auth code, client credentials,
token degisimi, scope yonetimi.
"""

import hashlib
import logging
import time
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class OAuthProvider:
    """OAuth saglayici.

    OAuth 2.0 akislarini yonetir.

    Attributes:
        _clients: OAuth istemcileri.
        _auth_codes: Yetki kodlari.
    """

    def __init__(
        self,
        token_ttl: int = 3600,
        auth_code_ttl: int = 600,
    ) -> None:
        """OAuth saglayiciyi baslatir.

        Args:
            token_ttl: Token suresi (sn).
            auth_code_ttl: Yetki kodu suresi (sn).
        """
        self._clients: dict[
            str, dict[str, Any]
        ] = {}
        self._auth_codes: dict[
            str, dict[str, Any]
        ] = {}
        self._tokens: dict[
            str, dict[str, Any]
        ] = {}
        self._scopes: dict[
            str, dict[str, Any]
        ] = {}
        self._token_ttl = token_ttl
        self._auth_code_ttl = auth_code_ttl
        self._stats = {
            "clients": 0,
            "codes_issued": 0,
            "tokens_issued": 0,
            "tokens_revoked": 0,
        }

        logger.info(
            "OAuthProvider baslatildi",
        )

    def register_client(
        self,
        client_id: str,
        client_secret: str,
        name: str = "",
        redirect_uris: list[str] | None = None,
        allowed_scopes: list[str] | None = None,
        grant_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """OAuth istemci kaydeder.

        Args:
            client_id: Istemci ID.
            client_secret: Istemci sirri.
            name: Istemci adi.
            redirect_uris: Yonlendirme URI'lari.
            allowed_scopes: Izin verilen scope'lar.
            grant_types: Izin verilen hibe tipleri.

        Returns:
            Istemci bilgisi.
        """
        if client_id in self._clients:
            return {"error": "client_exists"}

        secret_hash = hashlib.sha256(
            client_secret.encode(),
        ).hexdigest()

        self._clients[client_id] = {
            "client_id": client_id,
            "secret_hash": secret_hash,
            "name": name,
            "redirect_uris": redirect_uris or [],
            "allowed_scopes": (
                allowed_scopes or ["read"]
            ),
            "grant_types": grant_types or [
                "authorization_code",
            ],
            "active": True,
            "created_at": time.time(),
        }

        self._stats["clients"] += 1

        return {
            "client_id": client_id,
            "name": name,
            "status": "registered",
        }

    def authorize(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str = "",
        scopes: list[str] | None = None,
        state: str = "",
    ) -> dict[str, Any]:
        """Yetki kodu olusturur (auth code flow).

        Args:
            client_id: Istemci ID.
            user_id: Kullanici ID.
            redirect_uri: Yonlendirme URI.
            scopes: Talep edilen scope'lar.
            state: Durum parametresi.

        Returns:
            Yetki kodu bilgisi.
        """
        client = self._clients.get(client_id)
        if not client or not client["active"]:
            return {"error": "invalid_client"}

        if "authorization_code" not in client[
            "grant_types"
        ]:
            return {
                "error": "unsupported_grant_type",
            }

        # Scope kontrolu
        requested = scopes or ["read"]
        allowed = client["allowed_scopes"]
        invalid = [
            s for s in requested
            if s not in allowed
        ]
        if invalid:
            return {
                "error": "invalid_scope",
                "invalid_scopes": invalid,
            }

        code = str(uuid4())[:16]
        now = time.time()

        self._auth_codes[code] = {
            "code": code,
            "client_id": client_id,
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "scopes": requested,
            "state": state,
            "created_at": now,
            "expires_at": now + self._auth_code_ttl,
            "used": False,
        }

        self._stats["codes_issued"] += 1

        return {
            "code": code,
            "state": state,
            "redirect_uri": redirect_uri,
        }

    def exchange_code(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "",
    ) -> dict[str, Any]:
        """Yetki kodunu token ile degistirir.

        Args:
            code: Yetki kodu.
            client_id: Istemci ID.
            client_secret: Istemci sirri.
            redirect_uri: Yonlendirme URI.

        Returns:
            Token bilgisi.
        """
        auth_code = self._auth_codes.get(code)
        if not auth_code:
            return {"error": "invalid_code"}

        if auth_code["used"]:
            return {"error": "code_already_used"}

        if time.time() > auth_code["expires_at"]:
            return {"error": "code_expired"}

        if auth_code["client_id"] != client_id:
            return {"error": "client_mismatch"}

        # Client secret dogrula
        if not self._verify_client(
            client_id, client_secret,
        ):
            return {
                "error": "invalid_client_secret",
            }

        if (
            redirect_uri
            and auth_code["redirect_uri"]
            and redirect_uri
            != auth_code["redirect_uri"]
        ):
            return {"error": "redirect_mismatch"}

        # Kodu kullanildi olarak isaretle
        auth_code["used"] = True

        # Token olustur
        return self._issue_token(
            client_id,
            auth_code["user_id"],
            auth_code["scopes"],
            "authorization_code",
        )

    def client_credentials(
        self,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Client credentials flow.

        Args:
            client_id: Istemci ID.
            client_secret: Istemci sirri.
            scopes: Talep edilen scope'lar.

        Returns:
            Token bilgisi.
        """
        client = self._clients.get(client_id)
        if not client or not client["active"]:
            return {"error": "invalid_client"}

        if "client_credentials" not in client[
            "grant_types"
        ]:
            return {
                "error": "unsupported_grant_type",
            }

        if not self._verify_client(
            client_id, client_secret,
        ):
            return {
                "error": "invalid_client_secret",
            }

        requested = scopes or ["read"]
        return self._issue_token(
            client_id,
            client_id,
            requested,
            "client_credentials",
        )

    def refresh_token(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        """Token yeniler.

        Args:
            refresh_token: Yenileme tokeni.
            client_id: Istemci ID.
            client_secret: Istemci sirri.

        Returns:
            Yeni token bilgisi.
        """
        token_info = self._tokens.get(
            refresh_token,
        )
        if not token_info:
            return {"error": "invalid_token"}

        if token_info["type"] != "refresh":
            return {"error": "not_refresh_token"}

        if token_info["client_id"] != client_id:
            return {"error": "client_mismatch"}

        if not self._verify_client(
            client_id, client_secret,
        ):
            return {
                "error": "invalid_client_secret",
            }

        # Eski tokenlari iptal et
        self._revoke_access_for_refresh(
            refresh_token,
        )

        return self._issue_token(
            client_id,
            token_info["user_id"],
            token_info["scopes"],
            "refresh_token",
        )

    def revoke_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        """Token iptal eder.

        Args:
            token: Token degeri.

        Returns:
            Iptal sonucu.
        """
        token_info = self._tokens.pop(token, None)
        if not token_info:
            return {"error": "token_not_found"}

        self._stats["tokens_revoked"] += 1

        return {
            "token": token[:8] + "...",
            "status": "revoked",
        }

    def validate_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        """Token dogrular.

        Args:
            token: Token degeri.

        Returns:
            Dogrulama sonucu.
        """
        token_info = self._tokens.get(token)
        if not token_info:
            return {
                "valid": False,
                "reason": "token_not_found",
            }

        if time.time() > token_info["expires_at"]:
            return {
                "valid": False,
                "reason": "token_expired",
            }

        return {
            "valid": True,
            "client_id": token_info["client_id"],
            "user_id": token_info["user_id"],
            "scopes": token_info["scopes"],
            "type": token_info["type"],
        }

    def register_scope(
        self,
        scope_id: str,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Scope kaydeder.

        Args:
            scope_id: Scope ID.
            name: Scope adi.
            description: Aciklama.

        Returns:
            Scope bilgisi.
        """
        self._scopes[scope_id] = {
            "scope_id": scope_id,
            "name": name,
            "description": description,
        }

        return {
            "scope_id": scope_id,
            "status": "registered",
        }

    def get_client(
        self,
        client_id: str,
    ) -> dict[str, Any] | None:
        """Istemci getirir.

        Args:
            client_id: Istemci ID.

        Returns:
            Istemci bilgisi veya None.
        """
        client = self._clients.get(client_id)
        if not client:
            return None
        result = dict(client)
        result.pop("secret_hash", None)
        return result

    def list_clients(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Istemcileri listeler.

        Args:
            limit: Limit.

        Returns:
            Istemci listesi.
        """
        result = []
        for client in self._clients.values():
            c = dict(client)
            c.pop("secret_hash", None)
            result.append(c)
        return result[-limit:]

    def _verify_client(
        self,
        client_id: str,
        client_secret: str,
    ) -> bool:
        """Istemci dogrular.

        Args:
            client_id: Istemci ID.
            client_secret: Istemci sirri.

        Returns:
            Gecerli mi.
        """
        client = self._clients.get(client_id)
        if not client:
            return False
        secret_hash = hashlib.sha256(
            client_secret.encode(),
        ).hexdigest()
        return secret_hash == client["secret_hash"]

    def _issue_token(
        self,
        client_id: str,
        user_id: str,
        scopes: list[str],
        grant_type: str,
    ) -> dict[str, Any]:
        """Token olusturur.

        Args:
            client_id: Istemci ID.
            user_id: Kullanici ID.
            scopes: Scope'lar.
            grant_type: Hibe tipi.

        Returns:
            Token bilgisi.
        """
        now = time.time()
        access = hashlib.sha256(
            f"{uuid4()}{now}".encode(),
        ).hexdigest()[:32]
        refresh = hashlib.sha256(
            f"{uuid4()}{now}r".encode(),
        ).hexdigest()[:32]

        self._tokens[access] = {
            "type": "access",
            "client_id": client_id,
            "user_id": user_id,
            "scopes": scopes,
            "grant_type": grant_type,
            "created_at": now,
            "expires_at": now + self._token_ttl,
            "refresh_token": refresh,
        }

        self._tokens[refresh] = {
            "type": "refresh",
            "client_id": client_id,
            "user_id": user_id,
            "scopes": scopes,
            "grant_type": grant_type,
            "created_at": now,
            "expires_at": now + self._token_ttl * 24,
            "access_token": access,
        }

        self._stats["tokens_issued"] += 1

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "expires_in": self._token_ttl,
            "scope": " ".join(scopes),
        }

    def _revoke_access_for_refresh(
        self,
        refresh_token: str,
    ) -> None:
        """Refresh token'a ait access token'i iptal eder.

        Args:
            refresh_token: Yenileme tokeni.
        """
        token_info = self._tokens.get(
            refresh_token,
        )
        if token_info and "access_token" in token_info:
            self._tokens.pop(
                token_info["access_token"], None,
            )

    @property
    def client_count(self) -> int:
        """Istemci sayisi."""
        return len(self._clients)

    @property
    def token_count(self) -> int:
        """Token sayisi."""
        return len(self._tokens)

    @property
    def scope_count(self) -> int:
        """Scope sayisi."""
        return len(self._scopes)

    @property
    def auth_code_count(self) -> int:
        """Yetki kodu sayisi."""
        return len(self._auth_codes)
