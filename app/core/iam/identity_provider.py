"""ATLAS Kimlik Saglayici modulu.

Kullanici olusturma, kimlik dogrulama,
parola hashleme, MFA, hesap kilitleme.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IdentityProvider:
    """Kimlik saglayici.

    Kullanici kimlik islemlerini yonetir.

    Attributes:
        _users: Kullanici kayitlari.
        _mfa_secrets: MFA sirlari.
    """

    def __init__(
        self,
        max_failed_attempts: int = 5,
        lockout_duration: int = 300,
        password_min_length: int = 8,
    ) -> None:
        """Kimlik saglayiciyi baslatir.

        Args:
            max_failed_attempts: Maks basarisiz giris.
            lockout_duration: Kilitleme suresi (sn).
            password_min_length: Min parola uzunlugu.
        """
        self._users: dict[
            str, dict[str, Any]
        ] = {}
        self._mfa_secrets: dict[str, str] = {}
        self._failed_attempts: dict[
            str, list[float]
        ] = {}
        self._lockouts: dict[str, float] = {}
        self._max_failed = max_failed_attempts
        self._lockout_duration = lockout_duration
        self._password_min_length = password_min_length
        self._stats = {
            "created": 0,
            "authenticated": 0,
            "failed": 0,
            "locked": 0,
        }

        logger.info(
            "IdentityProvider baslatildi",
        )

    def create_user(
        self,
        user_id: str,
        username: str,
        password: str,
        email: str = "",
        roles: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kullanici olusturur.

        Args:
            user_id: Kullanici ID.
            username: Kullanici adi.
            password: Parola.
            email: E-posta.
            roles: Roller.
            metadata: Ek bilgiler.

        Returns:
            Kullanici bilgisi.
        """
        if user_id in self._users:
            return {"error": "user_exists"}

        if len(password) < self._password_min_length:
            return {
                "error": "password_too_short",
                "min_length": self._password_min_length,
            }

        pw_hash = self._hash_password(password)

        self._users[user_id] = {
            "user_id": user_id,
            "username": username,
            "password_hash": pw_hash,
            "email": email,
            "status": "active",
            "roles": roles or [],
            "mfa_enabled": False,
            "metadata": metadata or {},
            "created_at": time.time(),
            "last_login": None,
        }

        self._stats["created"] += 1

        return {
            "user_id": user_id,
            "username": username,
            "status": "created",
        }

    def authenticate(
        self,
        user_id: str,
        password: str,
        mfa_code: str | None = None,
    ) -> dict[str, Any]:
        """Kimlik dogrulama yapar.

        Args:
            user_id: Kullanici ID.
            password: Parola.
            mfa_code: MFA kodu.

        Returns:
            Dogrulama sonucu.
        """
        # Kilitleme kontrolu
        if self._is_locked(user_id):
            return {
                "authenticated": False,
                "reason": "account_locked",
            }

        user = self._users.get(user_id)
        if not user:
            return {
                "authenticated": False,
                "reason": "user_not_found",
            }

        if user["status"] != "active":
            return {
                "authenticated": False,
                "reason": "account_inactive",
            }

        # Parola kontrolu
        pw_hash = self._hash_password(password)
        if pw_hash != user["password_hash"]:
            self._record_failed_attempt(user_id)
            self._stats["failed"] += 1
            return {
                "authenticated": False,
                "reason": "invalid_password",
            }

        # MFA kontrolu
        if user["mfa_enabled"]:
            if not mfa_code:
                return {
                    "authenticated": False,
                    "reason": "mfa_required",
                }
            if not self._verify_mfa(
                user_id, mfa_code,
            ):
                self._stats["failed"] += 1
                return {
                    "authenticated": False,
                    "reason": "invalid_mfa",
                }

        # Basarili
        user["last_login"] = time.time()
        self._clear_failed_attempts(user_id)
        self._stats["authenticated"] += 1

        return {
            "authenticated": True,
            "user_id": user_id,
            "roles": user["roles"],
        }

    def enable_mfa(
        self,
        user_id: str,
        secret: str = "",
    ) -> dict[str, Any]:
        """MFA etkinlestirir.

        Args:
            user_id: Kullanici ID.
            secret: MFA sirri.

        Returns:
            MFA durumu.
        """
        user = self._users.get(user_id)
        if not user:
            return {"error": "user_not_found"}

        mfa_secret = secret or f"mfa_{user_id}"
        self._mfa_secrets[user_id] = mfa_secret
        user["mfa_enabled"] = True

        return {
            "user_id": user_id,
            "mfa_enabled": True,
            "secret": mfa_secret,
        }

    def disable_mfa(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """MFA devre disi birakir.

        Args:
            user_id: Kullanici ID.

        Returns:
            MFA durumu.
        """
        user = self._users.get(user_id)
        if not user:
            return {"error": "user_not_found"}

        self._mfa_secrets.pop(user_id, None)
        user["mfa_enabled"] = False

        return {
            "user_id": user_id,
            "mfa_enabled": False,
        }

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> dict[str, Any]:
        """Parola degistirir.

        Args:
            user_id: Kullanici ID.
            old_password: Eski parola.
            new_password: Yeni parola.

        Returns:
            Degisiklik sonucu.
        """
        user = self._users.get(user_id)
        if not user:
            return {"error": "user_not_found"}

        old_hash = self._hash_password(old_password)
        if old_hash != user["password_hash"]:
            return {"error": "invalid_password"}

        if len(new_password) < self._password_min_length:
            return {
                "error": "password_too_short",
                "min_length": self._password_min_length,
            }

        user["password_hash"] = (
            self._hash_password(new_password)
        )

        return {
            "user_id": user_id,
            "status": "password_changed",
        }

    def update_user(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Kullanici gunceller.

        Args:
            user_id: Kullanici ID.
            **kwargs: Guncellenecek alanlar.

        Returns:
            Guncelleme sonucu.
        """
        user = self._users.get(user_id)
        if not user:
            return {"error": "user_not_found"}

        allowed = {
            "username", "email", "status",
            "roles", "metadata",
        }
        for key, value in kwargs.items():
            if key in allowed:
                user[key] = value

        return {
            "user_id": user_id,
            "status": "updated",
        }

    def delete_user(
        self,
        user_id: str,
    ) -> bool:
        """Kullanici siler.

        Args:
            user_id: Kullanici ID.

        Returns:
            Basarili mi.
        """
        if user_id not in self._users:
            return False

        del self._users[user_id]
        self._mfa_secrets.pop(user_id, None)
        self._failed_attempts.pop(user_id, None)
        self._lockouts.pop(user_id, None)
        return True

    def get_user(
        self,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Kullanici getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Kullanici bilgisi veya None.
        """
        user = self._users.get(user_id)
        if not user:
            return None
        result = dict(user)
        result.pop("password_hash", None)
        return result

    def list_users(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kullanicilari listeler.

        Args:
            status: Durum filtresi.
            limit: Limit.

        Returns:
            Kullanici listesi.
        """
        users = []
        for user in self._users.values():
            if status and user["status"] != status:
                continue
            u = dict(user)
            u.pop("password_hash", None)
            users.append(u)

        return users[-limit:]

    def unlock_user(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Kullanici kilidini acar.

        Args:
            user_id: Kullanici ID.

        Returns:
            Kilit durumu.
        """
        self._lockouts.pop(user_id, None)
        self._failed_attempts.pop(user_id, None)

        user = self._users.get(user_id)
        if user and user["status"] == "locked":
            user["status"] = "active"

        return {
            "user_id": user_id,
            "status": "unlocked",
        }

    def _hash_password(
        self, password: str,
    ) -> str:
        """Parola hashler.

        Args:
            password: Parola.

        Returns:
            Hash degeri.
        """
        return hashlib.sha256(
            password.encode(),
        ).hexdigest()

    def _verify_mfa(
        self,
        user_id: str,
        code: str,
    ) -> bool:
        """MFA dogrular.

        Args:
            user_id: Kullanici ID.
            code: MFA kodu.

        Returns:
            Gecerli mi.
        """
        secret = self._mfa_secrets.get(user_id)
        if not secret:
            return False
        expected = hashlib.md5(
            secret.encode(),
        ).hexdigest()[:6]
        return code == expected

    def _is_locked(
        self, user_id: str,
    ) -> bool:
        """Kilitli mi kontrol eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Kilitli mi.
        """
        lockout_time = self._lockouts.get(user_id)
        if not lockout_time:
            return False
        if time.time() - lockout_time > self._lockout_duration:
            self._lockouts.pop(user_id, None)
            self._failed_attempts.pop(
                user_id, None,
            )
            user = self._users.get(user_id)
            if user and user["status"] == "locked":
                user["status"] = "active"
            return False
        return True

    def _record_failed_attempt(
        self, user_id: str,
    ) -> None:
        """Basarisiz girisi kaydeder.

        Args:
            user_id: Kullanici ID.
        """
        if user_id not in self._failed_attempts:
            self._failed_attempts[user_id] = []
        self._failed_attempts[user_id].append(
            time.time(),
        )

        if (
            len(self._failed_attempts[user_id])
            >= self._max_failed
        ):
            self._lockouts[user_id] = time.time()
            user = self._users.get(user_id)
            if user:
                user["status"] = "locked"
            self._stats["locked"] += 1

    def _clear_failed_attempts(
        self, user_id: str,
    ) -> None:
        """Basarisiz girisleri temizler.

        Args:
            user_id: Kullanici ID.
        """
        self._failed_attempts.pop(user_id, None)

    @property
    def user_count(self) -> int:
        """Kullanici sayisi."""
        return len(self._users)

    @property
    def locked_count(self) -> int:
        """Kilitli kullanici sayisi."""
        return len(self._lockouts)

    @property
    def mfa_enabled_count(self) -> int:
        """MFA etkin kullanici sayisi."""
        return len(self._mfa_secrets)
