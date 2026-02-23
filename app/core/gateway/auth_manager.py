"""Gateway kimlik dogrulama yoneticisi.

Token tabanli auth, loopback izni
ve eski jeton temizligi.
"""

import logging
import time
from uuid import uuid4

from app.models.gateway_models import (
    AuthMode,
    GatewayToken,
)

logger = logging.getLogger(__name__)

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


class GatewayAuthManager:
    """Gateway kimlik dogrulama yoneticisi.

    Attributes:
        _tokens: Kayitli jetonlar.
        _mode: Aktif auth modu.
    """

    def __init__(
        self,
        mode: AuthMode = AuthMode.TOKEN,
    ) -> None:
        """GatewayAuthManager baslatir."""
        self._tokens: dict[str, GatewayToken] = {}
        self._mode = mode

    @property
    def mode(self) -> AuthMode:
        """Aktif auth modunu dondurur."""
        return self._mode

    def default_token_mode(self) -> str:
        """Token moduna gecis ve otomatik jeton uretimi.

        Returns:
            Uretilen jeton degeri.
        """
        self._mode = AuthMode.TOKEN
        token = self.generate_token()
        logger.info("Varsayilan token modu etkinlestirildi")
        return token

    @staticmethod
    def allow_loopback_none(host: str) -> bool:
        """Loopback icin 'none' moduna izin verir.

        Args:
            host: Istemci hostu.

        Returns:
            Loopback ise True.
        """
        return host.strip().lower() in _LOOPBACK

    def clear_stale_tokens(
        self,
        max_age_hours: int = 72,
    ) -> int:
        """Eski device-auth jetonlarini temizler.

        Args:
            max_age_hours: Maksimum yasam suresi (saat).

        Returns:
            Temizlenen jeton sayisi.
        """
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        stale: list[str] = []

        for tok_val, tok in self._tokens.items():
            if tok.created_at > 0 and tok.created_at < cutoff:
                if tok.last_used < cutoff:
                    stale.append(tok_val)

        for tok_val in stale:
            del self._tokens[tok_val]

        if stale:
            logger.info(
                "%d eski jeton temizlendi", len(stale),
            )
        return len(stale)

    def generate_token(
        self,
        scope: str = "operator.*",
        device_id: str = "",
    ) -> str:
        """Yeni auth jetonu uretir.

        Args:
            scope: Yetki kapsami.
            device_id: Cihaz tanimlayici.

        Returns:
            Uretilen jeton degeri.
        """
        token = GatewayToken(
            token=str(uuid4()),
            scope=scope,
            device_id=device_id,
            created_at=time.time(),
        )
        self._tokens[token.token] = token
        return token.token

    def validate_token(
        self,
        token: str,
    ) -> dict | None:
        """Jetonu dogrular ve bilgi dondurur.

        Args:
            token: Jeton degeri.

        Returns:
            Jeton bilgisi veya None.
        """
        if self._mode == AuthMode.NONE:
            return {"scope": "operator.*", "valid": True}

        tok = self._tokens.get(token)
        if not tok:
            return None

        now = time.time()
        if tok.expires_at > 0 and now > tok.expires_at:
            return None

        tok.last_used = now
        return {
            "scope": tok.scope,
            "device_id": tok.device_id,
            "valid": True,
        }

    def revoke_token(self, token: str) -> bool:
        """Jetonu iptal eder.

        Args:
            token: Jeton degeri.

        Returns:
            Basarili ise True.
        """
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False

    @property
    def token_count(self) -> int:
        """Kayitli jeton sayisi."""
        return len(self._tokens)
