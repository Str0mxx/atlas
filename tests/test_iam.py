"""ATLAS Identity & Access Management testleri.

Kimlik ve erisim yonetimi bilesenleri icin
kapsamli test suite.
"""

import hashlib
import time
from unittest.mock import patch

import pytest


# ── Models ────────────────────────────────────

class TestIAMModels:
    """IAM model testleri."""

    def test_auth_method_enum(self):
        from app.models.iam_models import AuthMethod
        assert AuthMethod.PASSWORD == "password"
        assert AuthMethod.MFA == "mfa"
        assert AuthMethod.OAUTH == "oauth"
        assert AuthMethod.API_KEY == "api_key"
        assert AuthMethod.CERTIFICATE == "certificate"
        assert AuthMethod.SSO == "sso"

    def test_user_status_enum(self):
        from app.models.iam_models import UserStatus
        assert UserStatus.ACTIVE == "active"
        assert UserStatus.INACTIVE == "inactive"
        assert UserStatus.LOCKED == "locked"
        assert UserStatus.SUSPENDED == "suspended"
        assert UserStatus.PENDING == "pending"
        assert UserStatus.DELETED == "deleted"

    def test_permission_effect_enum(self):
        from app.models.iam_models import PermissionEffect
        assert PermissionEffect.ALLOW == "allow"
        assert PermissionEffect.DENY == "deny"
        assert PermissionEffect.CONDITIONAL == "conditional"

    def test_token_type_enum(self):
        from app.models.iam_models import TokenType
        assert TokenType.ACCESS == "access"
        assert TokenType.REFRESH == "refresh"
        assert TokenType.API_KEY == "api_key"
        assert TokenType.AUTH_CODE == "auth_code"
        assert TokenType.ID_TOKEN == "id_token"

    def test_audit_action_enum(self):
        from app.models.iam_models import AuditAction
        assert AuditAction.LOGIN == "login"
        assert AuditAction.LOGOUT == "logout"
        assert AuditAction.CREATE == "create"
        assert AuditAction.UPDATE == "update"
        assert AuditAction.DELETE == "delete"
        assert AuditAction.ACCESS == "access"
        assert AuditAction.DENY == "deny"
        assert AuditAction.GRANT == "grant"
        assert AuditAction.REVOKE == "revoke"

    def test_oauth_grant_type_enum(self):
        from app.models.iam_models import OAuthGrantType
        assert OAuthGrantType.AUTHORIZATION_CODE == "authorization_code"
        assert OAuthGrantType.CLIENT_CREDENTIALS == "client_credentials"
        assert OAuthGrantType.REFRESH_TOKEN == "refresh_token"
        assert OAuthGrantType.IMPLICIT == "implicit"
        assert OAuthGrantType.DEVICE_CODE == "device_code"

    def test_identity_record(self):
        from app.models.iam_models import IdentityRecord
        r = IdentityRecord(username="test", email="t@e.com")
        assert r.username == "test"
        assert r.email == "t@e.com"
        assert r.status.value == "active"
        assert r.mfa_enabled is False
        assert isinstance(r.roles, list)
        assert isinstance(r.identity_id, str)

    def test_role_record(self):
        from app.models.iam_models import RoleRecord
        r = RoleRecord(name="admin")
        assert r.name == "admin"
        assert r.parent_role is None
        assert r.is_default is False
        assert isinstance(r.permissions, list)

    def test_policy_record(self):
        from app.models.iam_models import PolicyRecord
        r = PolicyRecord(name="pol1")
        assert r.name == "pol1"
        assert r.effect.value == "allow"
        assert r.priority == 0
        assert r.enabled is True

    def test_iam_snapshot(self):
        from app.models.iam_models import IAMSnapshot
        s = IAMSnapshot(users=10, roles=5)
        assert s.users == 10
        assert s.roles == 5
        assert s.policies == 0
        assert isinstance(s.snapshot_id, str)


# ── IdentityProvider ──────────────────────────

class TestIdentityProvider:
    """IdentityProvider testleri."""

    def setup_method(self):
        from app.core.iam.identity_provider import IdentityProvider
        self.provider = IdentityProvider(
            max_failed_attempts=3,
            password_min_length=6,
        )

    def test_create_user(self):
        r = self.provider.create_user("u1", "user1", "pass123")
        assert r["status"] == "created"
        assert r["user_id"] == "u1"
        assert self.provider.user_count == 1

    def test_create_duplicate(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.create_user("u1", "dup", "pass123")
        assert r.get("error") == "user_exists"

    def test_create_short_password(self):
        r = self.provider.create_user("u1", "user1", "ab")
        assert r.get("error") == "password_too_short"

    def test_authenticate_success(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.authenticate("u1", "pass123")
        assert r["authenticated"] is True

    def test_authenticate_wrong_password(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.authenticate("u1", "wrong")
        assert r["authenticated"] is False
        assert r["reason"] == "invalid_password"

    def test_authenticate_not_found(self):
        r = self.provider.authenticate("none", "pass")
        assert r["authenticated"] is False
        assert r["reason"] == "user_not_found"

    def test_authenticate_inactive(self):
        self.provider.create_user("u1", "user1", "pass123")
        self.provider.update_user("u1", status="suspended")
        r = self.provider.authenticate("u1", "pass123")
        assert r["authenticated"] is False
        assert r["reason"] == "account_inactive"

    def test_mfa_enable_disable(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.enable_mfa("u1", "secret")
        assert r["mfa_enabled"] is True
        assert self.provider.mfa_enabled_count == 1

        r = self.provider.disable_mfa("u1")
        assert r["mfa_enabled"] is False
        assert self.provider.mfa_enabled_count == 0

    def test_mfa_authentication(self):
        self.provider.create_user("u1", "user1", "pass123")
        self.provider.enable_mfa("u1", "secret")

        # MFA kodu olmadan
        r = self.provider.authenticate("u1", "pass123")
        assert r["reason"] == "mfa_required"

        # Yanlis MFA kodu
        r = self.provider.authenticate("u1", "pass123", mfa_code="000000")
        assert r["reason"] == "invalid_mfa"

        # Dogru MFA kodu
        expected = hashlib.md5(b"secret").hexdigest()[:6]
        r = self.provider.authenticate("u1", "pass123", mfa_code=expected)
        assert r["authenticated"] is True

    def test_account_lockout(self):
        self.provider.create_user("u1", "user1", "pass123")
        for _ in range(3):
            self.provider.authenticate("u1", "wrong")
        r = self.provider.authenticate("u1", "pass123")
        assert r["reason"] == "account_locked"
        assert self.provider.locked_count == 1

    def test_unlock_user(self):
        self.provider.create_user("u1", "user1", "pass123")
        for _ in range(3):
            self.provider.authenticate("u1", "wrong")
        self.provider.unlock_user("u1")
        r = self.provider.authenticate("u1", "pass123")
        assert r["authenticated"] is True

    def test_change_password(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.change_password("u1", "pass123", "newpass")
        assert r["status"] == "password_changed"
        r = self.provider.authenticate("u1", "newpass")
        assert r["authenticated"] is True

    def test_change_password_wrong_old(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.change_password("u1", "wrong", "newpass")
        assert r.get("error") == "invalid_password"

    def test_change_password_too_short(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.change_password("u1", "pass123", "ab")
        assert r.get("error") == "password_too_short"

    def test_update_user(self):
        self.provider.create_user("u1", "user1", "pass123")
        r = self.provider.update_user("u1", email="new@e.com")
        assert r["status"] == "updated"
        user = self.provider.get_user("u1")
        assert user["email"] == "new@e.com"

    def test_delete_user(self):
        self.provider.create_user("u1", "user1", "pass123")
        assert self.provider.delete_user("u1") is True
        assert self.provider.user_count == 0

    def test_delete_nonexistent(self):
        assert self.provider.delete_user("none") is False

    def test_get_user_excludes_hash(self):
        self.provider.create_user("u1", "user1", "pass123")
        user = self.provider.get_user("u1")
        assert "password_hash" not in user

    def test_list_users(self):
        self.provider.create_user("u1", "user1", "pass123")
        self.provider.create_user("u2", "user2", "pass456")
        users = self.provider.list_users()
        assert len(users) == 2

    def test_list_users_with_status_filter(self):
        self.provider.create_user("u1", "user1", "pass123")
        self.provider.create_user("u2", "user2", "pass456")
        self.provider.update_user("u2", status="suspended")
        users = self.provider.list_users(status="active")
        assert len(users) == 1

    def test_enable_mfa_not_found(self):
        r = self.provider.enable_mfa("none")
        assert r.get("error") == "user_not_found"

    def test_disable_mfa_not_found(self):
        r = self.provider.disable_mfa("none")
        assert r.get("error") == "user_not_found"

    def test_change_password_not_found(self):
        r = self.provider.change_password("none", "a", "b")
        assert r.get("error") == "user_not_found"

    def test_update_not_found(self):
        r = self.provider.update_user("none", email="x")
        assert r.get("error") == "user_not_found"

    def test_lockout_expires(self):
        self.provider._lockout_duration = 0
        self.provider.create_user("u1", "user1", "pass123")
        for _ in range(3):
            self.provider.authenticate("u1", "wrong")
        # Lockout suresi dolmus
        r = self.provider.authenticate("u1", "pass123")
        assert r["authenticated"] is True


# ── RoleManager ───────────────────────────────

class TestRoleManager:
    """RoleManager testleri."""

    def setup_method(self):
        from app.core.iam.role_manager import RoleManager
        self.mgr = RoleManager()

    def test_create_role(self):
        r = self.mgr.create_role("r1", "Admin", permissions=["read", "write"])
        assert r["status"] == "created"
        assert self.mgr.role_count == 1

    def test_create_duplicate(self):
        self.mgr.create_role("r1", "Admin")
        r = self.mgr.create_role("r1", "Dup")
        assert r.get("error") == "role_exists"

    def test_create_with_parent(self):
        self.mgr.create_role("parent", "Parent")
        r = self.mgr.create_role("child", "Child", parent_role="parent")
        assert r["status"] == "created"

    def test_create_invalid_parent(self):
        r = self.mgr.create_role("r1", "R1", parent_role="none")
        assert r.get("error") == "parent_not_found"

    def test_delete_role(self):
        self.mgr.create_role("r1", "Admin")
        assert self.mgr.delete_role("r1") is True
        assert self.mgr.role_count == 0

    def test_delete_clears_children_parent(self):
        self.mgr.create_role("p", "Parent")
        self.mgr.create_role("c", "Child", parent_role="p")
        self.mgr.delete_role("p")
        role = self.mgr.get_role("c")
        assert role["parent_role"] is None

    def test_get_role(self):
        self.mgr.create_role("r1", "Admin")
        role = self.mgr.get_role("r1")
        assert role["name"] == "Admin"

    def test_update_role(self):
        self.mgr.create_role("r1", "Admin")
        r = self.mgr.update_role("r1", name="SuperAdmin")
        assert r["status"] == "updated"
        assert self.mgr.get_role("r1")["name"] == "SuperAdmin"

    def test_update_not_found(self):
        r = self.mgr.update_role("none", name="x")
        assert r.get("error") == "role_not_found"

    def test_add_permission(self):
        self.mgr.create_role("r1", "Admin")
        r = self.mgr.add_permission("r1", "delete")
        assert r["status"] == "added"

    def test_add_permission_not_found(self):
        r = self.mgr.add_permission("none", "x")
        assert r.get("error") == "role_not_found"

    def test_remove_permission(self):
        self.mgr.create_role("r1", "Admin", permissions=["read", "write"])
        self.mgr.remove_permission("r1", "write")
        role = self.mgr.get_role("r1")
        assert "write" not in role["permissions"]

    def test_remove_permission_not_found(self):
        r = self.mgr.remove_permission("none", "x")
        assert r.get("error") == "role_not_found"

    def test_effective_permissions_inheritance(self):
        self.mgr.create_role("p", "Parent", permissions=["read"])
        self.mgr.create_role("c", "Child", permissions=["write"], parent_role="p")
        perms = self.mgr.get_effective_permissions("c")
        assert "read" in perms
        assert "write" in perms

    def test_get_children(self):
        self.mgr.create_role("p", "Parent")
        self.mgr.create_role("c1", "C1", parent_role="p")
        self.mgr.create_role("c2", "C2", parent_role="p")
        children = self.mgr.get_children("p")
        assert len(children) == 2

    def test_get_ancestors(self):
        self.mgr.create_role("gp", "Grandparent")
        self.mgr.create_role("p", "Parent", parent_role="gp")
        self.mgr.create_role("c", "Child", parent_role="p")
        ancestors = self.mgr.get_ancestors("c")
        assert "p" in ancestors
        assert "gp" in ancestors

    def test_defaults(self):
        self.mgr.create_role("r1", "Default", is_default=True)
        defaults = self.mgr.get_defaults()
        assert "r1" in defaults
        assert self.mgr.default_count == 1

    def test_list_roles(self):
        self.mgr.create_role("r1", "R1")
        self.mgr.create_role("r2", "R2")
        roles = self.mgr.list_roles()
        assert len(roles) == 2


# ── PermissionManager ─────────────────────────

class TestPermissionManager:
    """PermissionManager testleri."""

    def setup_method(self):
        from app.core.iam.permission_manager import PermissionManager
        self.mgr = PermissionManager()

    def test_create_permission(self):
        r = self.mgr.create_permission("p1", "users", "read")
        assert r["status"] == "created"
        assert self.mgr.permission_count == 1

    def test_create_duplicate(self):
        self.mgr.create_permission("p1", "users", "read")
        r = self.mgr.create_permission("p1", "users", "write")
        assert r.get("error") == "permission_exists"

    def test_delete_permission(self):
        self.mgr.create_permission("p1", "users", "read")
        assert self.mgr.delete_permission("p1") is True
        assert self.mgr.permission_count == 0

    def test_delete_cleans_assignments(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.assign("u1", "p1")
        self.mgr.delete_permission("p1")
        assert self.mgr.get_permissions("u1") == []

    def test_assign_permission(self):
        self.mgr.create_permission("p1", "users", "read")
        r = self.mgr.assign("u1", "p1")
        assert r["status"] == "assigned"
        assert self.mgr.assignment_count == 1

    def test_revoke_permission(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.assign("u1", "p1")
        r = self.mgr.revoke("u1", "p1")
        assert r["status"] == "revoked"

    def test_check_allowed(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.assign("u1", "p1")
        assert self.mgr.check("u1", "users", "read") is True

    def test_check_denied(self):
        assert self.mgr.check("u1", "users", "read") is False

    def test_check_wildcard(self):
        self.mgr.create_permission("p1", "*", "*")
        self.mgr.assign("u1", "p1")
        assert self.mgr.check("u1", "anything", "any_action") is True

    def test_check_negation(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.create_permission("p2", "users", "read")
        self.mgr.assign("u1", "p1")
        self.mgr.negate("u1", "p2")
        assert self.mgr.check("u1", "users", "read") is False
        assert self.mgr.negation_count == 1

    def test_get_permissions(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.assign("u1", "p1")
        perms = self.mgr.get_permissions("u1")
        assert "p1" in perms

    def test_get_permission(self):
        self.mgr.create_permission("p1", "users", "read")
        perm = self.mgr.get_permission("p1")
        assert perm["resource"] == "users"

    def test_find_by_resource(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.create_permission("p2", "orders", "write")
        results = self.mgr.find_by_resource("users")
        assert len(results) == 1

    def test_list_permissions(self):
        self.mgr.create_permission("p1", "users", "read")
        self.mgr.create_permission("p2", "orders", "write")
        perms = self.mgr.list_permissions()
        assert len(perms) == 2

    def test_wildcard_pattern(self):
        self.mgr.create_permission("p1", "users.*", "read")
        self.mgr.assign("u1", "p1")
        assert self.mgr.check("u1", "users.profile", "read") is True
        assert self.mgr.check("u1", "orders", "read") is False


# ── IAMPolicyEngine ───────────────────────────

class TestIAMPolicyEngine:
    """IAMPolicyEngine testleri."""

    def setup_method(self):
        from app.core.iam.policy_engine import IAMPolicyEngine
        self.engine = IAMPolicyEngine(cache_enabled=True)

    def test_create_policy(self):
        r = self.engine.create_policy("pol1", "Test Policy", effect="allow")
        assert r["status"] == "created"
        assert self.engine.policy_count == 1

    def test_create_duplicate(self):
        self.engine.create_policy("pol1", "P1")
        r = self.engine.create_policy("pol1", "P2")
        assert r.get("error") == "policy_exists"

    def test_delete_policy(self):
        self.engine.create_policy("pol1", "P1")
        assert self.engine.delete_policy("pol1") is True
        assert self.engine.policy_count == 0

    def test_update_policy(self):
        self.engine.create_policy("pol1", "P1")
        r = self.engine.update_policy("pol1", name="Updated")
        assert r["status"] == "updated"

    def test_update_not_found(self):
        r = self.engine.update_policy("none", name="x")
        assert r.get("error") == "policy_not_found"

    def test_evaluate_allow(self):
        self.engine.create_policy(
            "pol1", "Allow All",
            effect="allow",
            subjects=["user1"],
            resources=["*"],
            actions=["*"],
        )
        r = self.engine.evaluate("user1", "data", "read")
        assert r["allowed"] is True
        assert r["reason"] == "explicit_allow"

    def test_evaluate_deny(self):
        self.engine.create_policy(
            "pol1", "Deny",
            effect="deny",
            subjects=["user1"],
            resources=["*"],
            actions=["*"],
        )
        r = self.engine.evaluate("user1", "data", "read")
        assert r["allowed"] is False
        assert r["reason"] == "explicit_deny"

    def test_deny_overrides_allow(self):
        self.engine.create_policy(
            "pol1", "Allow",
            effect="allow",
            subjects=["*"],
            resources=["*"],
            actions=["*"],
        )
        self.engine.create_policy(
            "pol2", "Deny",
            effect="deny",
            subjects=["user1"],
            resources=["*"],
            actions=["delete"],
        )
        r = self.engine.evaluate("user1", "data", "delete")
        assert r["allowed"] is False

    def test_evaluate_no_matching(self):
        r = self.engine.evaluate("user1", "data", "read")
        assert r["allowed"] is False
        assert r["reason"] == "no_matching_policy"

    def test_evaluate_with_conditions(self):
        self.engine.create_policy(
            "pol1", "Conditional",
            effect="allow",
            subjects=["*"],
            resources=["*"],
            actions=["*"],
            conditions={"ip": "192.168.1.1"},
        )
        r = self.engine.evaluate(
            "user1", "data", "read",
            context={"ip": "192.168.1.1"},
        )
        assert r["allowed"] is True

        r = self.engine.evaluate(
            "user1", "data", "read",
            context={"ip": "10.0.0.1"},
        )
        assert r["allowed"] is False
        assert r["reason"] == "conditions_not_met"

    def test_evaluate_conditions_list(self):
        self.engine.create_policy(
            "pol1", "Conditional",
            effect="allow",
            subjects=["*"],
            resources=["*"],
            actions=["*"],
            conditions={"role": ["admin", "editor"]},
        )
        r = self.engine.evaluate(
            "user1", "data", "read",
            context={"role": "admin"},
        )
        assert r["allowed"] is True

    def test_cache_hit(self):
        self.engine.create_policy(
            "pol1", "Allow",
            effect="allow",
            subjects=["*"],
            resources=["*"],
            actions=["*"],
        )
        self.engine.evaluate("user1", "data", "read")
        self.engine.evaluate("user1", "data", "read")
        assert self.engine._stats["cache_hits"] == 1

    def test_cache_invalidation(self):
        self.engine.create_policy(
            "pol1", "Allow",
            effect="allow",
            subjects=["*"],
            resources=["*"],
            actions=["*"],
        )
        self.engine.evaluate("user1", "data", "read")
        assert self.engine.cache_size > 0
        self.engine.create_policy("pol2", "New")
        assert self.engine.cache_size == 0

    def test_prefix_pattern(self):
        self.engine.create_policy(
            "pol1", "Prefix",
            effect="allow",
            subjects=["admin*"],
            resources=["*"],
            actions=["*"],
        )
        r = self.engine.evaluate("admin_user", "data", "read")
        assert r["allowed"] is True
        r = self.engine.evaluate("user", "data", "read")
        assert r["allowed"] is False

    def test_list_policies(self):
        self.engine.create_policy("p1", "P1", effect="allow")
        self.engine.create_policy("p2", "P2", effect="deny")
        all_p = self.engine.list_policies()
        assert len(all_p) == 2
        allow_p = self.engine.list_policies(effect="allow")
        assert len(allow_p) == 1

    def test_get_policy(self):
        self.engine.create_policy("p1", "Test")
        p = self.engine.get_policy("p1")
        assert p["name"] == "Test"

    def test_disabled_policy_ignored(self):
        self.engine.create_policy("p1", "P1", effect="allow", subjects=["*"], resources=["*"], actions=["*"])
        self.engine.update_policy("p1", enabled=False)
        r = self.engine.evaluate("user1", "data", "read")
        assert r["allowed"] is False

    def test_priority_ordering(self):
        self.engine.create_policy(
            "p1", "Low",
            effect="allow",
            subjects=["*"], resources=["*"], actions=["*"],
            priority=1,
        )
        self.engine.create_policy(
            "p2", "High",
            effect="allow",
            subjects=["*"], resources=["*"], actions=["*"],
            priority=10,
        )
        r = self.engine.evaluate("user1", "data", "read")
        assert r["policy_id"] == "p2"


# ── GroupManager ──────────────────────────────

class TestGroupManager:
    """GroupManager testleri."""

    def setup_method(self):
        from app.core.iam.group_manager import GroupManager
        self.mgr = GroupManager()

    def test_create_group(self):
        r = self.mgr.create_group("g1", "Engineers")
        assert r["status"] == "created"
        assert self.mgr.group_count == 1

    def test_create_duplicate(self):
        self.mgr.create_group("g1", "Engineers")
        r = self.mgr.create_group("g1", "Dup")
        assert r.get("error") == "group_exists"

    def test_create_with_parent(self):
        self.mgr.create_group("parent", "Parent")
        r = self.mgr.create_group("child", "Child", parent_group="parent")
        assert r["status"] == "created"
        assert self.mgr.nested_count == 1

    def test_create_invalid_parent(self):
        r = self.mgr.create_group("g1", "G1", parent_group="none")
        assert r.get("error") == "parent_not_found"

    def test_delete_group(self):
        self.mgr.create_group("g1", "Engineers")
        assert self.mgr.delete_group("g1") is True
        assert self.mgr.group_count == 0

    def test_delete_clears_children(self):
        self.mgr.create_group("p", "Parent")
        self.mgr.create_group("c", "Child", parent_group="p")
        self.mgr.delete_group("p")
        group = self.mgr.get_group("c")
        assert group["parent_group"] is None

    def test_add_member(self):
        self.mgr.create_group("g1", "Engineers")
        r = self.mgr.add_member("g1", "u1")
        assert r["status"] == "added"
        assert self.mgr.total_members == 1

    def test_add_member_not_found(self):
        r = self.mgr.add_member("none", "u1")
        assert r.get("error") == "group_not_found"

    def test_remove_member(self):
        self.mgr.create_group("g1", "Engineers")
        self.mgr.add_member("g1", "u1")
        r = self.mgr.remove_member("g1", "u1")
        assert r["status"] == "removed"
        assert self.mgr.total_members == 0

    def test_remove_member_not_found(self):
        r = self.mgr.remove_member("none", "u1")
        assert r.get("error") == "group_not_found"

    def test_get_members(self):
        self.mgr.create_group("g1", "Engineers")
        self.mgr.add_member("g1", "u1")
        self.mgr.add_member("g1", "u2")
        members = self.mgr.get_members("g1")
        assert len(members) == 2

    def test_get_members_nested(self):
        self.mgr.create_group("p", "Parent")
        self.mgr.create_group("c", "Child", parent_group="p")
        self.mgr.add_member("p", "u1")
        self.mgr.add_member("c", "u2")
        members = self.mgr.get_members("p", include_nested=True)
        assert "u1" in members
        assert "u2" in members

    def test_get_user_groups(self):
        self.mgr.create_group("g1", "G1")
        self.mgr.create_group("g2", "G2")
        self.mgr.add_member("g1", "u1")
        self.mgr.add_member("g2", "u1")
        groups = self.mgr.get_user_groups("u1")
        assert len(groups) == 2

    def test_is_member(self):
        self.mgr.create_group("g1", "G1")
        self.mgr.add_member("g1", "u1")
        assert self.mgr.is_member("g1", "u1") is True
        assert self.mgr.is_member("g1", "u2") is False

    def test_is_member_nested(self):
        self.mgr.create_group("p", "Parent")
        self.mgr.create_group("c", "Child", parent_group="p")
        self.mgr.add_member("c", "u1")
        assert self.mgr.is_member("p", "u1", check_nested=True) is True
        assert self.mgr.is_member("p", "u1", check_nested=False) is False

    def test_get_nested_groups(self):
        self.mgr.create_group("p", "Parent")
        self.mgr.create_group("c1", "C1", parent_group="p")
        self.mgr.create_group("c2", "C2", parent_group="p")
        nested = self.mgr.get_nested_groups("p")
        assert len(nested) == 2

    def test_sync_roles(self):
        self.mgr.create_group("g1", "G1", roles=["viewer"])
        r = self.mgr.sync_roles("g1", ["admin", "editor"])
        assert r["status"] == "synced"
        assert r["new_roles"] == ["admin", "editor"]

    def test_sync_roles_not_found(self):
        r = self.mgr.sync_roles("none", ["admin"])
        assert r.get("error") == "group_not_found"

    def test_list_groups(self):
        self.mgr.create_group("g1", "G1")
        self.mgr.create_group("g2", "G2")
        groups = self.mgr.list_groups()
        assert len(groups) == 2
        assert "member_count" in groups[0]


# ── IAMSessionManager ─────────────────────────

class TestIAMSessionManager:
    """IAMSessionManager testleri."""

    def setup_method(self):
        from app.core.iam.session_manager import IAMSessionManager
        self.mgr = IAMSessionManager(
            session_timeout=3600,
            max_concurrent=3,
        )

    def test_create_session(self):
        r = self.mgr.create_session("u1", ip_address="1.2.3.4")
        assert "session_id" in r
        assert "access_token" in r
        assert "refresh_token" in r
        assert self.mgr.session_count == 1

    def test_validate_token(self):
        session = self.mgr.create_session("u1")
        r = self.mgr.validate_token(session["access_token"])
        assert r["valid"] is True
        assert r["user_id"] == "u1"

    def test_validate_invalid_token(self):
        r = self.mgr.validate_token("invalid")
        assert r["valid"] is False

    def test_validate_expired_session(self):
        session = self.mgr.create_session("u1")
        # Expire the session
        sid = session["session_id"]
        self.mgr._sessions[sid]["expires_at"] = time.time() - 1
        r = self.mgr.validate_token(session["access_token"])
        assert r["valid"] is False
        assert r["reason"] == "session_expired"

    def test_refresh_session(self):
        session = self.mgr.create_session("u1")
        r = self.mgr.refresh_session(session["refresh_token"])
        assert "access_token" in r
        assert r["access_token"] != session["access_token"]

    def test_refresh_with_access_token_fails(self):
        session = self.mgr.create_session("u1")
        r = self.mgr.refresh_session(session["access_token"])
        assert r.get("error") == "not_refresh_token"

    def test_refresh_invalid_token(self):
        r = self.mgr.refresh_session("invalid")
        assert r.get("error") == "token_not_found"

    def test_revoke_session(self):
        session = self.mgr.create_session("u1")
        r = self.mgr.revoke_session(session["session_id"])
        assert r["status"] == "revoked"
        r = self.mgr.validate_token(session["access_token"])
        assert r["valid"] is False

    def test_revoke_not_found(self):
        r = self.mgr.revoke_session("none")
        assert r.get("error") == "session_not_found"

    def test_revoke_user_sessions(self):
        self.mgr.create_session("u1")
        self.mgr.create_session("u1")
        r = self.mgr.revoke_user_sessions("u1")
        assert r["revoked"] == 2

    def test_max_concurrent(self):
        s1 = self.mgr.create_session("u1")
        self.mgr.create_session("u1")
        self.mgr.create_session("u1")
        # 4th session should revoke oldest
        self.mgr.create_session("u1")
        r = self.mgr.validate_token(s1["access_token"])
        assert r["valid"] is False

    def test_get_session(self):
        session = self.mgr.create_session("u1")
        s = self.mgr.get_session(session["session_id"])
        assert s["user_id"] == "u1"

    def test_get_user_sessions(self):
        self.mgr.create_session("u1")
        self.mgr.create_session("u1")
        sessions = self.mgr.get_user_sessions("u1")
        assert len(sessions) == 2

    def test_get_user_sessions_active_only(self):
        s1 = self.mgr.create_session("u1")
        self.mgr.create_session("u1")
        self.mgr.revoke_session(s1["session_id"])
        active = self.mgr.get_user_sessions("u1", active_only=True)
        assert len(active) == 1

    def test_cleanup_expired(self):
        session = self.mgr.create_session("u1")
        sid = session["session_id"]
        self.mgr._sessions[sid]["expires_at"] = time.time() - 1
        cleaned = self.mgr.cleanup_expired()
        assert cleaned == 1

    def test_active_session_count(self):
        self.mgr.create_session("u1")
        self.mgr.create_session("u2")
        assert self.mgr.active_session_count == 2

    def test_token_count(self):
        self.mgr.create_session("u1")
        assert self.mgr.token_count >= 2  # access + refresh

    def test_refresh_disabled(self):
        from app.core.iam.session_manager import IAMSessionManager
        mgr = IAMSessionManager(refresh_enabled=False)
        session = mgr.create_session("u1")
        assert session["refresh_token"] is None
        r = mgr.refresh_session("any")
        assert r.get("error") == "refresh_disabled"

    def test_validate_revoked_session(self):
        session = self.mgr.create_session("u1")
        self.mgr.revoke_session(session["session_id"])
        # Recreate token entry to test active check
        r = self.mgr.validate_token(session["access_token"])
        assert r["valid"] is False


# ── OAuthProvider ─────────────────────────────

class TestOAuthProvider:
    """OAuthProvider testleri."""

    def setup_method(self):
        from app.core.iam.oauth_provider import OAuthProvider
        self.oauth = OAuthProvider(token_ttl=3600)

    def test_register_client(self):
        r = self.oauth.register_client(
            "c1", "secret", name="App1",
            allowed_scopes=["read", "write"],
            grant_types=["authorization_code", "client_credentials"],
        )
        assert r["status"] == "registered"
        assert self.oauth.client_count == 1

    def test_register_duplicate(self):
        self.oauth.register_client("c1", "secret")
        r = self.oauth.register_client("c1", "secret2")
        assert r.get("error") == "client_exists"

    def test_authorize_code_flow(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        r = self.oauth.authorize("c1", "u1", scopes=["read"])
        assert "code" in r

    def test_authorize_invalid_client(self):
        r = self.oauth.authorize("none", "u1")
        assert r.get("error") == "invalid_client"

    def test_authorize_invalid_scope(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        r = self.oauth.authorize("c1", "u1", scopes=["admin"])
        assert r.get("error") == "invalid_scope"

    def test_authorize_unsupported_grant(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        r = self.oauth.authorize("c1", "u1")
        assert r.get("error") == "unsupported_grant_type"

    def test_exchange_code(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        auth = self.oauth.authorize("c1", "u1", scopes=["read"])
        r = self.oauth.exchange_code(auth["code"], "c1", "secret")
        assert "access_token" in r
        assert "refresh_token" in r

    def test_exchange_invalid_code(self):
        r = self.oauth.exchange_code("invalid", "c1", "secret")
        assert r.get("error") == "invalid_code"

    def test_exchange_used_code(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        auth = self.oauth.authorize("c1", "u1", scopes=["read"])
        self.oauth.exchange_code(auth["code"], "c1", "secret")
        r = self.oauth.exchange_code(auth["code"], "c1", "secret")
        assert r.get("error") == "code_already_used"

    def test_exchange_expired_code(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        auth = self.oauth.authorize("c1", "u1", scopes=["read"])
        self.oauth._auth_codes[auth["code"]]["expires_at"] = time.time() - 1
        r = self.oauth.exchange_code(auth["code"], "c1", "secret")
        assert r.get("error") == "code_expired"

    def test_exchange_wrong_client(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        auth = self.oauth.authorize("c1", "u1", scopes=["read"])
        r = self.oauth.exchange_code(auth["code"], "c2", "secret")
        assert r.get("error") == "client_mismatch"

    def test_exchange_wrong_secret(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        auth = self.oauth.authorize("c1", "u1", scopes=["read"])
        r = self.oauth.exchange_code(auth["code"], "c1", "wrong")
        assert r.get("error") == "invalid_client_secret"

    def test_exchange_redirect_mismatch(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["authorization_code"],
        )
        auth = self.oauth.authorize(
            "c1", "u1", scopes=["read"],
            redirect_uri="http://localhost/cb",
        )
        r = self.oauth.exchange_code(
            auth["code"], "c1", "secret",
            redirect_uri="http://other/cb",
        )
        assert r.get("error") == "redirect_mismatch"

    def test_client_credentials(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["client_credentials"],
        )
        r = self.oauth.client_credentials("c1", "secret")
        assert "access_token" in r

    def test_client_credentials_invalid(self):
        r = self.oauth.client_credentials("none", "secret")
        assert r.get("error") == "invalid_client"

    def test_client_credentials_unsupported(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["authorization_code"],
        )
        r = self.oauth.client_credentials("c1", "secret")
        assert r.get("error") == "unsupported_grant_type"

    def test_client_credentials_wrong_secret(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        r = self.oauth.client_credentials("c1", "wrong")
        assert r.get("error") == "invalid_client_secret"

    def test_refresh_token(self):
        self.oauth.register_client(
            "c1", "secret",
            allowed_scopes=["read"],
            grant_types=["client_credentials"],
        )
        tokens = self.oauth.client_credentials("c1", "secret")
        r = self.oauth.refresh_token(
            tokens["refresh_token"], "c1", "secret",
        )
        assert "access_token" in r

    def test_refresh_invalid_token(self):
        r = self.oauth.refresh_token("invalid", "c1", "secret")
        assert r.get("error") == "invalid_token"

    def test_refresh_not_refresh_type(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        tokens = self.oauth.client_credentials("c1", "secret")
        r = self.oauth.refresh_token(
            tokens["access_token"], "c1", "secret",
        )
        assert r.get("error") == "not_refresh_token"

    def test_refresh_wrong_client(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        tokens = self.oauth.client_credentials("c1", "secret")
        r = self.oauth.refresh_token(
            tokens["refresh_token"], "c2", "secret",
        )
        assert r.get("error") == "client_mismatch"

    def test_revoke_token(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        tokens = self.oauth.client_credentials("c1", "secret")
        r = self.oauth.revoke_token(tokens["access_token"])
        assert r["status"] == "revoked"

    def test_revoke_not_found(self):
        r = self.oauth.revoke_token("invalid")
        assert r.get("error") == "token_not_found"

    def test_validate_token(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        tokens = self.oauth.client_credentials("c1", "secret")
        r = self.oauth.validate_token(tokens["access_token"])
        assert r["valid"] is True

    def test_validate_expired_token(self):
        self.oauth.register_client(
            "c1", "secret",
            grant_types=["client_credentials"],
        )
        tokens = self.oauth.client_credentials("c1", "secret")
        self.oauth._tokens[tokens["access_token"]]["expires_at"] = time.time() - 1
        r = self.oauth.validate_token(tokens["access_token"])
        assert r["valid"] is False

    def test_register_scope(self):
        r = self.oauth.register_scope("read", "Read", "Read access")
        assert r["status"] == "registered"
        assert self.oauth.scope_count == 1

    def test_get_client(self):
        self.oauth.register_client("c1", "secret", name="App")
        c = self.oauth.get_client("c1")
        assert c["name"] == "App"
        assert "secret_hash" not in c

    def test_get_client_not_found(self):
        assert self.oauth.get_client("none") is None

    def test_list_clients(self):
        self.oauth.register_client("c1", "s1")
        self.oauth.register_client("c2", "s2")
        clients = self.oauth.list_clients()
        assert len(clients) == 2


# ── IAMAuditLog ───────────────────────────────

class TestIAMAuditLog:
    """IAMAuditLog testleri."""

    def setup_method(self):
        from app.core.iam.audit_log import IAMAuditLog
        self.log = IAMAuditLog(max_entries=100)

    def test_log_access(self):
        r = self.log.log_access("u1", "data", "read", allowed=True)
        assert r["logged"] is True
        assert self.log.entry_count == 1

    def test_log_access_denied(self):
        self.log.log_access("u1", "data", "read", allowed=False)
        assert self.log.failure_count == 1

    def test_log_login(self):
        r = self.log.log_login("u1", success=True)
        assert r["logged"] is True
        assert self.log.login_count == 1

    def test_log_failed_login(self):
        self.log.log_login("u1", success=False)
        assert self.log.failure_count == 1

    def test_log_change(self):
        r = self.log.log_change(
            "admin", "user", "u1", "update",
            old_value={"name": "old"}, new_value={"name": "new"},
        )
        assert r["logged"] is True
        assert self.log.change_count == 1

    def test_get_login_history(self):
        self.log.log_login("u1", success=True)
        self.log.log_login("u1", success=False)
        history = self.log.get_login_history("u1")
        assert len(history) == 2

    def test_get_changes(self):
        self.log.log_change("admin", "user", "u1", "update")
        self.log.log_change("admin", "role", "r1", "create")
        changes = self.log.get_changes(entity_type="user")
        assert len(changes) == 1

    def test_get_changes_by_entity_id(self):
        self.log.log_change("admin", "user", "u1", "update")
        self.log.log_change("admin", "user", "u2", "update")
        changes = self.log.get_changes(entity_id="u1")
        assert len(changes) == 1

    def test_get_entries(self):
        self.log.log_access("u1", "data", "read")
        self.log.log_login("u1")
        entries = self.log.get_entries()
        assert len(entries) == 2

    def test_get_entries_by_type(self):
        self.log.log_access("u1", "data", "read")
        self.log.log_login("u1")
        entries = self.log.get_entries(entry_type="login")
        assert len(entries) == 1

    def test_get_entries_by_user(self):
        self.log.log_access("u1", "data", "read")
        self.log.log_access("u2", "data", "read")
        entries = self.log.get_entries(user_id="u1")
        assert len(entries) == 1

    def test_get_failed_logins(self):
        self.log.log_login("u1", success=True)
        self.log.log_login("u1", success=False)
        self.log.log_login("u2", success=False)
        failed = self.log.get_failed_logins()
        assert len(failed) == 2
        failed_u1 = self.log.get_failed_logins(user_id="u1")
        assert len(failed_u1) == 1

    def test_compliance_report(self):
        self.log.log_login("u1")
        self.log.log_access("u1", "data", "read", allowed=False)
        report = self.log.get_compliance_report()
        assert report["total_entries"] == 2
        assert report["login_events"] == 1
        assert "failure_rate" in report

    def test_search(self):
        self.log.log_access("u1", "secret_data", "read")
        self.log.log_access("u2", "public_data", "read")
        results = self.log.search("secret")
        assert len(results) == 1

    def test_cleanup(self):
        self.log.log_access("u1", "data", "read")
        # Make entry old
        self.log._entries[0]["timestamp"] = 0
        cleaned = self.log.cleanup(max_age_days=1)
        assert cleaned == 1
        assert self.log.entry_count == 0

    def test_max_entries_limit(self):
        for i in range(150):
            self.log.log_access(f"u{i}", "data", "read")
        assert self.log.entry_count <= 100


# ── IAMOrchestrator ───────────────────────────

class TestIAMOrchestrator:
    """IAMOrchestrator testleri."""

    def setup_method(self):
        from app.core.iam.iam_orchestrator import IAMOrchestrator
        self.orch = IAMOrchestrator(
            max_failed_attempts=3,
            session_timeout=3600,
            password_min_length=6,
        )

    def test_register_user(self):
        r = self.orch.register_user("u1", "user1", "pass123")
        assert r["status"] == "registered"
        assert self.orch.user_count == 1

    def test_register_with_roles(self):
        self.orch.roles.create_role("admin", "Admin")
        r = self.orch.register_user("u1", "user1", "pass123", roles=["admin"])
        assert "admin" in r["roles"]

    def test_register_with_groups(self):
        self.orch.groups.create_group("g1", "Engineers")
        r = self.orch.register_user("u1", "user1", "pass123", groups=["g1"])
        assert r["status"] == "registered"
        assert self.orch.groups.is_member("g1", "u1")

    def test_register_default_roles(self):
        self.orch.roles.create_role("viewer", "Viewer", is_default=True)
        r = self.orch.register_user("u1", "user1", "pass123")
        assert "viewer" in r["roles"]

    def test_register_error(self):
        self.orch.register_user("u1", "user1", "pass123")
        r = self.orch.register_user("u1", "dup", "pass123")
        assert "error" in r

    def test_login(self):
        self.orch.register_user("u1", "user1", "pass123")
        r = self.orch.login("u1", "pass123")
        assert r["authenticated"] is True
        assert "access_token" in r
        assert "session_id" in r

    def test_login_failed(self):
        self.orch.register_user("u1", "user1", "pass123")
        r = self.orch.login("u1", "wrong")
        assert r["authenticated"] is False

    def test_login_creates_audit_log(self):
        self.orch.register_user("u1", "user1", "pass123")
        self.orch.login("u1", "pass123")
        history = self.orch.audit.get_login_history("u1")
        assert len(history) >= 1

    def test_authorize_with_policy(self):
        self.orch.register_user("u1", "user1", "pass123")
        self.orch.policies.create_policy(
            "pol1", "Allow Read",
            effect="allow",
            subjects=["u1"],
            resources=["*"],
            actions=["read"],
        )
        login = self.orch.login("u1", "pass123")
        r = self.orch.authorize(login["access_token"], "data", "read")
        assert r["authorized"] is True

    def test_authorize_denied(self):
        self.orch.register_user("u1", "user1", "pass123")
        login = self.orch.login("u1", "pass123")
        r = self.orch.authorize(login["access_token"], "data", "read")
        assert r["authorized"] is False

    def test_authorize_invalid_token(self):
        r = self.orch.authorize("invalid", "data", "read")
        assert r["authorized"] is False

    def test_logout(self):
        self.orch.register_user("u1", "user1", "pass123")
        login = self.orch.login("u1", "pass123")
        r = self.orch.logout(login["session_id"])
        assert r["status"] == "revoked"

    def test_get_user_permissions(self):
        self.orch.roles.create_role("admin", "Admin", permissions=["read", "write"])
        self.orch.register_user("u1", "user1", "pass123", roles=["admin"])
        perms = self.orch.get_user_permissions("u1")
        assert "read" in perms
        assert "write" in perms

    def test_get_user_permissions_not_found(self):
        perms = self.orch.get_user_permissions("none")
        assert perms == []

    def test_get_status(self):
        self.orch.register_user("u1", "user1", "pass123")
        status = self.orch.get_status()
        assert status["users"] == 1
        assert "roles" in status
        assert "stats" in status

    def test_get_analytics(self):
        self.orch.register_user("u1", "user1", "pass123")
        self.orch.login("u1", "pass123")
        analytics = self.orch.get_analytics()
        assert analytics["registrations"] == 1
        assert analytics["authentications"] == 1
        assert "compliance" in analytics

    def test_full_pipeline(self):
        # Rol olustur
        self.orch.roles.create_role("editor", "Editor", permissions=["read", "write"])
        # Grup olustur
        self.orch.groups.create_group("team1", "Team 1")
        # Politika olustur
        self.orch.policies.create_policy(
            "pol1", "Editor Access",
            effect="allow",
            subjects=["u1"],
            resources=["docs*"],
            actions=["read", "write"],
        )
        # Kullanici kaydet
        self.orch.register_user(
            "u1", "user1", "pass123",
            roles=["editor"],
            groups=["team1"],
        )
        # Giris yap
        login = self.orch.login("u1", "pass123")
        assert login["authenticated"] is True
        # Yetkilendir
        r = self.orch.authorize(
            login["access_token"], "docs_main", "read",
        )
        assert r["authorized"] is True
        # Cikis yap
        self.orch.logout(login["session_id"])

    def test_session_count(self):
        self.orch.register_user("u1", "user1", "pass123")
        self.orch.login("u1", "pass123")
        assert self.orch.session_count >= 1

    def test_auth_count(self):
        self.orch.register_user("u1", "user1", "pass123")
        self.orch.login("u1", "pass123")
        assert self.orch.auth_count == 1


# ── Config ────────────────────────────────────

class TestIAMConfig:
    """IAM config testleri."""

    def test_iam_enabled(self):
        from app.config import settings
        assert hasattr(settings, "iam_enabled")
        assert isinstance(settings.iam_enabled, bool)

    def test_iam_session_timeout_minutes(self):
        from app.config import settings
        assert hasattr(settings, "iam_session_timeout_minutes")
        assert settings.iam_session_timeout_minutes == 30

    def test_iam_max_failed_attempts(self):
        from app.config import settings
        assert hasattr(settings, "iam_max_failed_attempts")
        assert settings.iam_max_failed_attempts == 5

    def test_iam_mfa_required(self):
        from app.config import settings
        assert hasattr(settings, "iam_mfa_required")
        assert settings.iam_mfa_required is False

    def test_iam_password_min_length(self):
        from app.config import settings
        assert hasattr(settings, "iam_password_min_length")
        assert settings.iam_password_min_length == 8


# ── Imports ───────────────────────────────────

class TestIAMImports:
    """IAM import testleri."""

    def test_import_identity_provider(self):
        from app.core.iam import IdentityProvider
        assert IdentityProvider is not None

    def test_import_role_manager(self):
        from app.core.iam import RoleManager
        assert RoleManager is not None

    def test_import_permission_manager(self):
        from app.core.iam import PermissionManager
        assert PermissionManager is not None

    def test_import_policy_engine(self):
        from app.core.iam import IAMPolicyEngine
        assert IAMPolicyEngine is not None

    def test_import_group_manager(self):
        from app.core.iam import GroupManager
        assert GroupManager is not None

    def test_import_session_manager(self):
        from app.core.iam import IAMSessionManager
        assert IAMSessionManager is not None

    def test_import_oauth_provider(self):
        from app.core.iam import OAuthProvider
        assert OAuthProvider is not None

    def test_import_audit_log(self):
        from app.core.iam import IAMAuditLog
        assert IAMAuditLog is not None

    def test_import_orchestrator(self):
        from app.core.iam import IAMOrchestrator
        assert IAMOrchestrator is not None

    def test_import_models(self):
        from app.models.iam_models import (
            AuthMethod,
            UserStatus,
            PermissionEffect,
            TokenType,
            AuditAction,
            OAuthGrantType,
            IdentityRecord,
            RoleRecord,
            PolicyRecord,
            IAMSnapshot,
        )
        assert all([
            AuthMethod, UserStatus, PermissionEffect,
            TokenType, AuditAction, OAuthGrantType,
            IdentityRecord, RoleRecord, PolicyRecord,
            IAMSnapshot,
        ])
