"""ATLAS Gizli Veri Yoneticisi modulu.

API key depolama, parola hashleme,
gizli veri rotasyonu, guvenli erisim
ve sure asimi yonetimi.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class SecretManager:
    """Gizli veri yoneticisi.

    Hassas verileri guvenli sekilde
    depolar ve yonetir.

    Attributes:
        _secrets: Gizli veri deposu.
        _password_hashes: Parola hashleri.
        _access_log: Erisim gecmisi.
    """

    def __init__(self) -> None:
        """Gizli veri yoneticisini baslatir."""
        self._secrets: dict[str, dict[str, Any]] = {}
        self._password_hashes: dict[str, dict[str, Any]] = {}
        self._access_log: list[dict[str, Any]] = []

        logger.info("SecretManager baslatildi")

    def store_secret(
        self,
        name: str,
        value: str,
        ttl_hours: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Gizli veri depolar.

        Args:
            name: Gizli ad.
            value: Deger.
            ttl_hours: Gecerlilik suresi (saat, 0=sinirsiz).
            metadata: Ek bilgi.

        Returns:
            Depolama bilgisi.
        """
        now = datetime.now(timezone.utc)
        expires_at = None
        if ttl_hours > 0:
            expires_at = (
                now + timedelta(hours=ttl_hours)
            ).isoformat()

        # Degeri hashle
        salt = os.urandom(16).hex()
        encrypted_value = hashlib.sha256(
            f"{salt}:{value}".encode(),
        ).hexdigest()

        self._secrets[name] = {
            "name": name,
            "value": value,  # Gercek uygulamada sifrelenir
            "encrypted": encrypted_value,
            "salt": salt,
            "metadata": metadata or {},
            "ttl_hours": ttl_hours,
            "expires_at": expires_at,
            "version": 1,
            "created_at": now.isoformat(),
            "accessed_at": None,
        }

        logger.info("Gizli veri depolandi: %s", name)
        return {
            "name": name,
            "ttl_hours": ttl_hours,
            "expires_at": expires_at,
        }

    def get_secret(
        self,
        name: str,
        accessor: str = "system",
    ) -> str | None:
        """Gizli veri getirir.

        Args:
            name: Gizli ad.
            accessor: Erisimci.

        Returns:
            Deger veya None.
        """
        secret = self._secrets.get(name)
        if not secret:
            return None

        # Sure asimi kontrolu
        if secret["expires_at"]:
            expires = datetime.fromisoformat(secret["expires_at"])
            if datetime.now(timezone.utc) > expires:
                del self._secrets[name]
                logger.info("Suresi dolmus gizli veri: %s", name)
                return None

        secret["accessed_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        self._access_log.append({
            "name": name,
            "accessor": accessor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return secret["value"]

    def rotate_secret(
        self,
        name: str,
        new_value: str,
    ) -> dict[str, Any]:
        """Gizli veri rotasyonu yapar.

        Args:
            name: Gizli ad.
            new_value: Yeni deger.

        Returns:
            Rotasyon sonucu.
        """
        old = self._secrets.get(name)
        if not old:
            return {"success": False, "error": "Bulunamadi"}

        version = old["version"] + 1
        ttl_hours = old["ttl_hours"]

        now = datetime.now(timezone.utc)
        expires_at = None
        if ttl_hours > 0:
            expires_at = (
                now + timedelta(hours=ttl_hours)
            ).isoformat()

        salt = os.urandom(16).hex()
        self._secrets[name] = {
            "name": name,
            "value": new_value,
            "encrypted": hashlib.sha256(
                f"{salt}:{new_value}".encode(),
            ).hexdigest(),
            "salt": salt,
            "metadata": old["metadata"],
            "ttl_hours": ttl_hours,
            "expires_at": expires_at,
            "version": version,
            "created_at": now.isoformat(),
            "accessed_at": None,
        }

        logger.info(
            "Gizli veri rotasyonu: %s (v%d)",
            name, version,
        )
        return {
            "success": True,
            "name": name,
            "version": version,
        }

    def delete_secret(
        self,
        name: str,
    ) -> bool:
        """Gizli veriyi siler.

        Args:
            name: Gizli ad.

        Returns:
            Basarili ise True.
        """
        if name in self._secrets:
            del self._secrets[name]
            return True
        return False

    def hash_password(
        self,
        user: str,
        password: str,
    ) -> str:
        """Parola hashler.

        Args:
            user: Kullanici.
            password: Parola.

        Returns:
            Hash degeri.
        """
        salt = os.urandom(16).hex()
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000,
        ).hex()

        self._password_hashes[user] = {
            "hash": hashed,
            "salt": salt,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        return hashed

    def verify_password(
        self,
        user: str,
        password: str,
    ) -> bool:
        """Parola dogrular.

        Args:
            user: Kullanici.
            password: Parola.

        Returns:
            Dogru ise True.
        """
        record = self._password_hashes.get(user)
        if not record:
            return False

        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            record["salt"].encode(),
            100000,
        ).hex()

        return computed == record["hash"]

    def list_secrets(self) -> list[dict[str, Any]]:
        """Gizli verileri listeler (degerler gizli).

        Returns:
            Gizli veri listesi.
        """
        return [
            {
                "name": s["name"],
                "version": s["version"],
                "ttl_hours": s["ttl_hours"],
                "expires_at": s["expires_at"],
                "has_metadata": bool(s["metadata"]),
            }
            for s in self._secrets.values()
        ]

    def cleanup_expired(self) -> int:
        """Suresi dolanlari temizler.

        Returns:
            Temizlenen sayisi.
        """
        now = datetime.now(timezone.utc)
        expired = [
            name for name, s in self._secrets.items()
            if s["expires_at"]
            and datetime.fromisoformat(s["expires_at"]) < now
        ]
        for name in expired:
            del self._secrets[name]
        return len(expired)

    @property
    def secret_count(self) -> int:
        """Gizli veri sayisi."""
        return len(self._secrets)

    @property
    def password_count(self) -> int:
        """Parola hash sayisi."""
        return len(self._password_hashes)

    @property
    def access_count(self) -> int:
        """Erisim sayisi."""
        return len(self._access_log)
