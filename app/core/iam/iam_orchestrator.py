"""ATLAS IAM Orkestrator modulu.

Tam IAM pipeline, politika zorlama,
izleme ve analitik.
"""

import logging
import time
from typing import Any

from app.core.iam.audit_log import IAMAuditLog
from app.core.iam.group_manager import GroupManager
from app.core.iam.identity_provider import (
    IdentityProvider,
)
from app.core.iam.oauth_provider import OAuthProvider
from app.core.iam.permission_manager import (
    PermissionManager,
)
from app.core.iam.policy_engine import (
    IAMPolicyEngine,
)
from app.core.iam.role_manager import RoleManager
from app.core.iam.session_manager import (
    IAMSessionManager,
)

logger = logging.getLogger(__name__)


class IAMOrchestrator:
    """IAM orkestrator.

    Tum IAM bilesenleri koordine eder.

    Attributes:
        identity: Kimlik saglayici.
        roles: Rol yoneticisi.
        permissions: Izin yoneticisi.
        policies: Politika motoru.
        groups: Grup yoneticisi.
        sessions: Oturum yoneticisi.
        oauth: OAuth saglayici.
        audit: Denetim gunlugu.
    """

    def __init__(
        self,
        max_failed_attempts: int = 5,
        session_timeout: int = 1800,
        password_min_length: int = 8,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            max_failed_attempts: Maks basarisiz giris.
            session_timeout: Oturum suresi (sn).
            password_min_length: Min parola uzunlugu.
        """
        self.identity = IdentityProvider(
            max_failed_attempts=max_failed_attempts,
            password_min_length=password_min_length,
        )
        self.roles = RoleManager()
        self.permissions = PermissionManager()
        self.policies = IAMPolicyEngine()
        self.groups = GroupManager()
        self.sessions = IAMSessionManager(
            session_timeout=session_timeout,
        )
        self.oauth = OAuthProvider()
        self.audit = IAMAuditLog()

        self._stats = {
            "registrations": 0,
            "authentications": 0,
            "authorizations": 0,
        }

        logger.info(
            "IAMOrchestrator baslatildi",
        )

    def register_user(
        self,
        user_id: str,
        username: str,
        password: str,
        email: str = "",
        roles: list[str] | None = None,
        groups: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kullanici kaydeder (tam pipeline).

        Args:
            user_id: Kullanici ID.
            username: Kullanici adi.
            password: Parola.
            email: E-posta.
            roles: Roller.
            groups: Gruplar.

        Returns:
            Kayit sonucu.
        """
        # Kullanici olustur
        result = self.identity.create_user(
            user_id, username, password,
            email=email,
            roles=roles,
        )

        if "error" in result:
            return result

        # Gruplara ekle
        if groups:
            for gid in groups:
                self.groups.add_member(
                    gid, user_id,
                )

        # Varsayilan rolleri ata
        defaults = self.roles.get_defaults()
        user_roles = list(roles or [])
        for role_id in defaults:
            if role_id not in user_roles:
                user_roles.append(role_id)

        if user_roles:
            self.identity.update_user(
                user_id, roles=user_roles,
            )

        # Denetim logu
        self.audit.log_change(
            user_id,
            "user",
            user_id,
            "create",
            new_value={"username": username},
        )

        self._stats["registrations"] += 1

        return {
            "user_id": user_id,
            "username": username,
            "roles": user_roles,
            "status": "registered",
        }

    def login(
        self,
        user_id: str,
        password: str,
        mfa_code: str | None = None,
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict[str, Any]:
        """Giris yapar (kimlik dogrulama + oturum).

        Args:
            user_id: Kullanici ID.
            password: Parola.
            mfa_code: MFA kodu.
            ip_address: IP adresi.
            user_agent: Kullanici agenti.

        Returns:
            Giris sonucu.
        """
        # Kimlik dogrulama
        auth = self.identity.authenticate(
            user_id, password, mfa_code,
        )

        # Denetim logu
        self.audit.log_login(
            user_id,
            success=auth["authenticated"],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        if not auth["authenticated"]:
            return auth

        # Oturum olustur
        session = self.sessions.create_session(
            user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self._stats["authentications"] += 1

        return {
            "authenticated": True,
            "user_id": user_id,
            "roles": auth.get("roles", []),
            "session_id": session["session_id"],
            "access_token": session["access_token"],
            "refresh_token": session.get(
                "refresh_token",
            ),
        }

    def authorize(
        self,
        token: str,
        resource: str,
        action: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yetkilendirme yapar (token + politika).

        Args:
            token: Erisim tokeni.
            resource: Kaynak.
            action: Aksiyon.
            context: Baglam.

        Returns:
            Yetkilendirme sonucu.
        """
        # Token dogrula
        validation = self.sessions.validate_token(
            token,
        )
        if not validation["valid"]:
            return {
                "authorized": False,
                "reason": validation["reason"],
            }

        user_id = validation["user_id"]

        # Politika degerlendirmesi
        policy_result = self.policies.evaluate(
            user_id, resource, action,
            context=context,
        )

        # Izin kontrolu (politika yoksa perm check)
        allowed = policy_result["allowed"]
        if not allowed and policy_result[
            "reason"
        ] == "no_matching_policy":
            # Dogrudan izin kontrolu
            user = self.identity.get_user(user_id)
            if user:
                for role_id in user.get(
                    "roles", [],
                ):
                    perms = (
                        self.roles
                        .get_effective_permissions(
                            role_id,
                        )
                    )
                    for perm_id in perms:
                        if self.permissions.check(
                            perm_id,
                            resource,
                            action,
                        ):
                            allowed = True
                            break
                    if allowed:
                        break

        # Denetim logu
        self.audit.log_access(
            user_id, resource, action,
            allowed=allowed,
        )

        self._stats["authorizations"] += 1

        return {
            "authorized": allowed,
            "user_id": user_id,
            "resource": resource,
            "action": action,
        }

    def logout(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Cikis yapar.

        Args:
            session_id: Oturum ID.

        Returns:
            Cikis sonucu.
        """
        session = self.sessions.get_session(
            session_id,
        )
        user_id = (
            session["user_id"] if session else ""
        )

        result = self.sessions.revoke_session(
            session_id,
        )

        if user_id:
            self.audit.log_login(
                user_id,
                success=True,
                method="logout",
            )

        return result

    def get_user_permissions(
        self,
        user_id: str,
    ) -> list[str]:
        """Kullanici izinlerini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Izin listesi.
        """
        user = self.identity.get_user(user_id)
        if not user:
            return []

        all_perms: set[str] = set()
        for role_id in user.get("roles", []):
            perms = (
                self.roles
                .get_effective_permissions(role_id)
            )
            all_perms.update(perms)

        return sorted(all_perms)

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "users": self.identity.user_count,
            "roles": self.roles.role_count,
            "permissions": (
                self.permissions.permission_count
            ),
            "policies": (
                self.policies.policy_count
            ),
            "groups": self.groups.group_count,
            "active_sessions": (
                self.sessions.active_session_count
            ),
            "oauth_clients": (
                self.oauth.client_count
            ),
            "audit_entries": (
                self.audit.entry_count
            ),
            "stats": dict(self._stats),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik bilgisi.

        Returns:
            Analitik verileri.
        """
        return {
            "registrations": (
                self._stats["registrations"]
            ),
            "authentications": (
                self._stats["authentications"]
            ),
            "authorizations": (
                self._stats["authorizations"]
            ),
            "locked_users": (
                self.identity.locked_count
            ),
            "mfa_users": (
                self.identity.mfa_enabled_count
            ),
            "compliance": (
                self.audit.get_compliance_report()
            ),
            "timestamp": time.time(),
        }

    @property
    def user_count(self) -> int:
        """Kullanici sayisi."""
        return self.identity.user_count

    @property
    def session_count(self) -> int:
        """Oturum sayisi."""
        return self.sessions.session_count

    @property
    def auth_count(self) -> int:
        """Kimlik dogrulama sayisi."""
        return self._stats["authentications"]
