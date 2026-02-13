"""ATLAS Kimlik Yonetimi modulu.

API anahtari isteme, guvenli depolama, anahtar rotasyonu,
OAuth akis yonetimi ve token yenileme.
"""

import hashlib
import logging
import time
from typing import Any

from app.models.jit import AuthMethod, CredentialEntry

logger = logging.getLogger(__name__)


class CredentialManager:
    """Kimlik yonetim sistemi.

    API anahtarlarini guvenli yonetir, rotasyon yapar,
    OAuth akislarini yonetir ve token yeniler.

    Attributes:
        _credentials: Kimlik bilgileri (service -> CredentialEntry).
        _secrets: Sifreli degerler (service -> hash).
        _pending_requests: Bekleyen anahtar istekleri.
        _oauth_states: OAuth durum bilgileri.
    """

    def __init__(self) -> None:
        """Kimlik yonetim sistemini baslatir."""
        self._credentials: dict[str, CredentialEntry] = {}
        self._secrets: dict[str, str] = {}
        self._pending_requests: list[dict[str, Any]] = []
        self._oauth_states: dict[str, dict[str, Any]] = {}

        logger.info("CredentialManager baslatildi")

    def request_api_key(self, service_name: str, key_name: str = "api_key") -> dict[str, Any]:
        """Kullanicidan API anahtari ister.

        Args:
            service_name: Servis adi.
            key_name: Anahtar adi.

        Returns:
            Istek bilgisi.
        """
        request = {
            "service": service_name,
            "key_name": key_name,
            "requested_at": time.time(),
            "status": "pending",
        }
        self._pending_requests.append(request)

        # CredentialEntry olustur
        if service_name not in self._credentials:
            self._credentials[service_name] = CredentialEntry(
                service_name=service_name,
                key_name=key_name,
                auth_method=AuthMethod.API_KEY,
                is_set=False,
            )

        logger.info("API anahtari istendi: %s.%s", service_name, key_name)
        return request

    def store_credential(self, service_name: str, value: str, key_name: str = "api_key") -> bool:
        """Kimlik bilgisini guvenli depolar.

        Args:
            service_name: Servis adi.
            value: Anahtar degeri.
            key_name: Anahtar adi.

        Returns:
            Basarili mi.
        """
        # Hash olarak depola (gercek uygulamada vault kullanilir)
        hashed = hashlib.sha256(value.encode()).hexdigest()
        self._secrets[service_name] = hashed

        # Credential entry guncelle
        if service_name not in self._credentials:
            self._credentials[service_name] = CredentialEntry(
                service_name=service_name,
                key_name=key_name,
            )

        self._credentials[service_name].is_set = True
        self._credentials[service_name].key_name = key_name

        # Pending istegi temizle
        self._pending_requests = [
            r for r in self._pending_requests
            if r["service"] != service_name
        ]

        logger.info("Kimlik bilgisi depolandi: %s", service_name)
        return True

    def has_credential(self, service_name: str) -> bool:
        """Servisin kimlik bilgisi var mi kontrol eder.

        Args:
            service_name: Servis adi.

        Returns:
            Mevcut mu.
        """
        cred = self._credentials.get(service_name)
        return cred is not None and cred.is_set

    def rotate_key(self, service_name: str, new_value: str) -> bool:
        """Anahtar rotasyonu yapar.

        Args:
            service_name: Servis adi.
            new_value: Yeni anahtar degeri.

        Returns:
            Basarili mi.
        """
        if service_name not in self._credentials:
            return False

        from datetime import datetime, timezone

        # Yeni degeri depola
        hashed = hashlib.sha256(new_value.encode()).hexdigest()
        self._secrets[service_name] = hashed
        self._credentials[service_name].last_rotated = datetime.now(timezone.utc)

        logger.info("Anahtar rotate edildi: %s", service_name)
        return True

    def init_oauth_flow(self, service_name: str, client_id: str, scopes: list[str] | None = None) -> dict[str, Any]:
        """OAuth akisini baslatir.

        Args:
            service_name: Servis adi.
            client_id: Client ID.
            scopes: Yetki kapsamlari.

        Returns:
            OAuth durum bilgisi.
        """
        import uuid
        state = str(uuid.uuid4())

        self._oauth_states[service_name] = {
            "state": state,
            "client_id": client_id,
            "scopes": scopes or [],
            "initiated_at": time.time(),
            "status": "initiated",
        }

        # CredentialEntry olustur/guncelle
        if service_name not in self._credentials:
            self._credentials[service_name] = CredentialEntry(
                service_name=service_name,
                auth_method=AuthMethod.OAUTH2,
            )
        self._credentials[service_name].auth_method = AuthMethod.OAUTH2

        logger.info("OAuth akisi baslatildi: %s", service_name)
        return {"state": state, "service": service_name}

    def complete_oauth(self, service_name: str, access_token: str, refresh_token: str = "") -> bool:
        """OAuth akisini tamamlar.

        Args:
            service_name: Servis adi.
            access_token: Erisim tokeni.
            refresh_token: Yenileme tokeni.

        Returns:
            Basarili mi.
        """
        if service_name not in self._oauth_states:
            return False

        self._oauth_states[service_name]["status"] = "completed"
        self._oauth_states[service_name]["has_refresh"] = bool(refresh_token)

        # Tokenlari depola
        self.store_credential(service_name, access_token, "access_token")
        if refresh_token:
            self._secrets[f"{service_name}_refresh"] = hashlib.sha256(
                refresh_token.encode()
            ).hexdigest()

        logger.info("OAuth tamamlandi: %s", service_name)
        return True

    def refresh_token(self, service_name: str) -> bool:
        """Token yenileme yapar.

        Args:
            service_name: Servis adi.

        Returns:
            Basarili mi (refresh token varsa).
        """
        oauth_state = self._oauth_states.get(service_name)
        if not oauth_state:
            return False

        if not oauth_state.get("has_refresh", False):
            return False

        # Gercek uygulamada burada token yenileme API cagrisi yapilir
        oauth_state["last_refresh"] = time.time()
        logger.info("Token yenilendi: %s", service_name)
        return True

    def get_credential_info(self, service_name: str) -> CredentialEntry | None:
        """Kimlik bilgisi detayini getirir."""
        return self._credentials.get(service_name)

    def remove_credential(self, service_name: str) -> bool:
        """Kimlik bilgisini siler.

        Args:
            service_name: Servis adi.

        Returns:
            Basarili mi.
        """
        removed = False
        if service_name in self._credentials:
            del self._credentials[service_name]
            removed = True
        if service_name in self._secrets:
            del self._secrets[service_name]
            removed = True
        self._oauth_states.pop(service_name, None)
        return removed

    @property
    def credential_count(self) -> int:
        """Kayitli kimlik sayisi."""
        return len(self._credentials)

    @property
    def pending_count(self) -> int:
        """Bekleyen istek sayisi."""
        return len(self._pending_requests)

    @property
    def services_with_credentials(self) -> list[str]:
        """Kimlik bilgisi olan servisler."""
        return [name for name, cred in self._credentials.items() if cred.is_set]
