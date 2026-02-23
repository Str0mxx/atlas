"""BOLUM 4: Gateway & Infrastructure testleri.

GatewayConfigManager, GatewayAuthManager,
GatewayPairingManager, GatewayDaemon,
GatewayDoctor, ChannelHealthManager,
GatewayUpdateManager modulleri.
~120 test.
"""

import json
import os
import tempfile
import time

import pytest

from app.models.gateway_models import (
    AuthMode,
    ChannelHealthStatus,
    ChannelStatus,
    ConfigDiff,
    DiagnosticResult,
    GatewayToken,
    PairedDevice,
    UpdateResult,
)
from app.core.gateway.config_manager import (
    GatewayConfigManager,
)
from app.core.gateway.auth_manager import (
    GatewayAuthManager,
)
from app.core.gateway.pairing_manager import (
    GatewayPairingManager,
)
from app.core.gateway.daemon import GatewayDaemon
from app.core.gateway.doctor import GatewayDoctor
from app.core.gateway.channel_health import (
    ChannelHealthManager,
)
from app.core.gateway.update_manager import (
    GatewayUpdateManager,
)


# -- Model Tests --


class TestGatewayModels:

    def test_auth_mode_enum(self):
        assert AuthMode.TOKEN == "token"
        assert AuthMode.NONE == "none"
        assert AuthMode.BASIC == "basic"

    def test_channel_status_enum(self):
        assert ChannelStatus.HEALTHY == "healthy"
        assert ChannelStatus.CRASH_LOOP == "crash_loop"
        assert ChannelStatus.DOWN == "down"

    def test_channel_status_degraded(self):
        assert ChannelStatus.DEGRADED == "degraded"

    def test_channel_status_restarting(self):
        assert ChannelStatus.RESTARTING == "restarting"

    def test_gateway_token_defaults(self):
        t = GatewayToken()
        assert t.token
        assert t.scope == "operator.*"
        assert t.device_id == ""
        assert t.created_at == 0.0

    def test_gateway_token_custom(self):
        t = GatewayToken(token="abc", scope="admin", device_id="dev1", created_at=100.0)
        assert t.token == "abc"
        assert t.scope == "admin"

    def test_gateway_token_expires(self):
        t = GatewayToken(expires_at=9999.0)
        assert t.expires_at == 9999.0

    def test_paired_device_defaults(self):
        d = PairedDevice()
        assert d.device_id == ""
        assert d.scopes == []

    def test_paired_device_custom(self):
        d = PairedDevice(device_id="d1", scopes=["op.*"], paired_at=1.0)
        assert d.device_id == "d1"
        assert len(d.scopes) == 1

    def test_paired_device_name(self):
        d = PairedDevice(name="My Phone")
        assert d.name == "My Phone"

    def test_channel_health_status_defaults(self):
        s = ChannelHealthStatus()
        assert s.status == ChannelStatus.HEALTHY
        assert s.check_interval_minutes == 5

    def test_channel_health_status_custom(self):
        s = ChannelHealthStatus(channel="telegram", status=ChannelStatus.DOWN)
        assert s.channel == "telegram"

    def test_channel_health_status_error_message(self):
        s = ChannelHealthStatus(error_message="connection lost")
        assert s.error_message == "connection lost"

    def test_diagnostic_result_defaults(self):
        r = DiagnosticResult()
        assert r.severity == "warning"
        assert r.auto_fixable is False

    def test_diagnostic_result_model_dump(self):
        r = DiagnosticResult(category="config", issue="test")
        d = r.model_dump()
        assert d["category"] == "config"

    def test_diagnostic_result_details(self):
        r = DiagnosticResult(details="extra info")
        assert r.details == "extra info"

    def test_update_result_defaults(self):
        u = UpdateResult()
        assert u.success is False
        assert u.restart_required is False

    def test_update_result_custom(self):
        u = UpdateResult(version="2.0", success=True)
        assert u.version == "2.0"

    def test_update_result_error(self):
        u = UpdateResult(error="failed")
        assert u.error == "failed"

    def test_config_diff_defaults(self):
        d = ConfigDiff()
        assert d.action == "changed"

    def test_config_diff_custom(self):
        d = ConfigDiff(key="auth.mode", old_value="none", new_value="token", action="changed")
        assert d.key == "auth.mode"


# -- ConfigManager Tests --


class TestGatewayConfigManager:

    def test_init_defaults(self):
        mgr = GatewayConfigManager()
        assert mgr._bindings == {}

    def test_refresh_no_path(self):
        mgr = GatewayConfigManager()
        assert mgr.refresh_bindings() is False

    def test_refresh_with_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "val"}, f)
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager(config_path=path)
            assert mgr.refresh_bindings() is True
            assert mgr.get("key") == "val"
        finally:
            os.unlink(path)

    def test_refresh_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager(config_path=path)
            assert mgr.refresh_bindings() is False
        finally:
            os.unlink(path)

    def test_refresh_updates_last_refresh(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"k": 1}, f)
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager(config_path=path)
            assert mgr._last_refresh == 0.0
            mgr.refresh_bindings()
            assert mgr._last_refresh > 0
        finally:
            os.unlink(path)

    def test_prevent_object_array_merge_dicts(self):
        result = GatewayConfigManager.prevent_object_array_merge({"a": 1, "b": 2}, {"b": 3, "c": 4})
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_prevent_object_array_merge_dict_list(self):
        result = GatewayConfigManager.prevent_object_array_merge({"a": 1}, [1, 2, 3])
        assert result == {"a": 1}

    def test_prevent_object_array_merge_list_dict(self):
        result = GatewayConfigManager.prevent_object_array_merge([1, 2], {"a": 1})
        assert result == [1, 2]

    def test_prevent_object_array_merge_scalar(self):
        result = GatewayConfigManager.prevent_object_array_merge("old", "new")
        assert result == "new"

    def test_prevent_object_array_merge_nested(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = GatewayConfigManager.prevent_object_array_merge(base, override)
        assert result["a"] == {"x": 1, "y": 3, "z": 4}

    def test_prevent_object_array_merge_int_override(self):
        result = GatewayConfigManager.prevent_object_array_merge(10, 20)
        assert result == 20

    def test_trim_proxy_whitespace(self):
        entries = [" 10.0.0.1 ", "10.0.0.2", "  ", ""]
        result = GatewayConfigManager.trim_proxy_whitespace(entries)
        assert result == ["10.0.0.1", "10.0.0.2"]

    def test_trim_proxy_empty(self):
        assert GatewayConfigManager.trim_proxy_whitespace([]) == []

    def test_trim_proxy_all_blank(self):
        result = GatewayConfigManager.trim_proxy_whitespace(["  ", "", "   "])
        assert result == []

    def test_hot_reload(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"port": 8080}, f)
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager(config_path=path)
            mgr._bindings = {"port": 3000}
            diffs = mgr.hot_reload()
            assert len(diffs) == 1
            assert diffs[0]["key"] == "port"
        finally:
            os.unlink(path)

    def test_hot_reload_no_path(self):
        mgr = GatewayConfigManager()
        assert mgr.hot_reload() == []

    def test_hot_reload_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{bad")
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager()
            assert mgr.hot_reload(path) == []
        finally:
            os.unlink(path)

    def test_hot_reload_added_key(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"a": 1, "b": 2}, f)
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager(config_path=path)
            mgr._bindings = {"a": 1}
            diffs = mgr.hot_reload()
            added = [d for d in diffs if d["action"] == "added"]
            assert len(added) == 1
            assert added[0]["key"] == "b"
        finally:
            os.unlink(path)

    def test_hot_reload_no_changes(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"a": 1}, f)
            f.flush()
            path = f.name
        try:
            mgr = GatewayConfigManager(config_path=path)
            mgr._bindings = {"a": 1}
            diffs = mgr.hot_reload()
            assert diffs == []
        finally:
            os.unlink(path)

    def test_get_dot_notation(self):
        mgr = GatewayConfigManager()
        mgr._bindings = {"auth": {"mode": "token"}}
        assert mgr.get("auth.mode") == "token"
        assert mgr.get("auth.missing", "def") == "def"

    def test_get_missing_key(self):
        mgr = GatewayConfigManager()
        assert mgr.get("missing") is None
        assert mgr.get("missing", 42) == 42

    def test_get_deep_dot_notation(self):
        mgr = GatewayConfigManager()
        mgr._bindings = {"a": {"b": {"c": 99}}}
        assert mgr.get("a.b.c") == 99

    def test_get_non_dict_intermediate(self):
        mgr = GatewayConfigManager()
        mgr._bindings = {"a": "string"}
        assert mgr.get("a.b", "fallback") == "fallback"

    def test_set_simple(self):
        mgr = GatewayConfigManager()
        mgr.set("key", "val")
        assert mgr.get("key") == "val"

    def test_set_dot_notation(self):
        mgr = GatewayConfigManager()
        mgr.set("auth.mode", "token")
        assert mgr.get("auth.mode") == "token"

    def test_set_creates_intermediate_dicts(self):
        mgr = GatewayConfigManager()
        mgr.set("a.b.c", 42)
        assert mgr.get("a.b.c") == 42

    def test_validate_empty(self):
        mgr = GatewayConfigManager()
        warnings = mgr.validate()
        assert any("bos" in w for w in warnings)

    def test_validate_bad_auth_mode(self):
        mgr = GatewayConfigManager()
        mgr.set("auth.mode", "invalid")
        warnings = mgr.validate()
        assert any("auth" in w.lower() for w in warnings)

    def test_validate_proxy_whitespace(self):
        mgr = GatewayConfigManager()
        mgr._bindings = {"trusted_proxies": [" 10.0.0.1 "], "auth": {"mode": "token"}}
        warnings = mgr.validate()
        assert any("bosluk" in w for w in warnings)

    def test_validate_valid_config(self):
        mgr = GatewayConfigManager()
        mgr._bindings = {"auth": {"mode": "token"}, "trusted_proxies": ["10.0.0.1"]}
        warnings = mgr.validate()
        assert len(warnings) == 0

    def test_merge_configs(self):
        mgr = GatewayConfigManager()
        result = mgr._merge_configs({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_configs_override(self):
        mgr = GatewayConfigManager()
        result = mgr._merge_configs({"a": 1}, {"a": 2})
        assert result == {"a": 2}


# -- AuthManager Tests --


class TestGatewayAuthManager:

    def test_init_default_mode(self):
        mgr = GatewayAuthManager()
        assert mgr.mode == AuthMode.TOKEN

    def test_init_custom_mode(self):
        mgr = GatewayAuthManager(mode=AuthMode.NONE)
        assert mgr.mode == AuthMode.NONE

    def test_default_token_mode(self):
        mgr = GatewayAuthManager(mode=AuthMode.NONE)
        token = mgr.default_token_mode()
        assert token
        assert mgr.mode == AuthMode.TOKEN
        assert mgr.token_count == 1

    def test_allow_loopback_none_localhost(self):
        assert GatewayAuthManager.allow_loopback_none("localhost") is True

    def test_allow_loopback_none_ipv4(self):
        assert GatewayAuthManager.allow_loopback_none("127.0.0.1") is True

    def test_allow_loopback_none_ipv6(self):
        assert GatewayAuthManager.allow_loopback_none("::1") is True

    def test_allow_loopback_none_external(self):
        assert GatewayAuthManager.allow_loopback_none("10.0.0.1") is False

    def test_allow_loopback_whitespace(self):
        assert GatewayAuthManager.allow_loopback_none(" localhost ") is True

    def test_allow_loopback_case_insensitive(self):
        assert GatewayAuthManager.allow_loopback_none("LOCALHOST") is True

    def test_generate_token(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        assert token
        assert mgr.token_count == 1

    def test_generate_token_custom_scope(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token(scope="admin", device_id="dev1")
        assert token
        info = mgr.validate_token(token)
        assert info["scope"] == "admin"

    def test_generate_token_unique(self):
        mgr = GatewayAuthManager()
        t1 = mgr.generate_token()
        t2 = mgr.generate_token()
        assert t1 != t2
        assert mgr.token_count == 2

    def test_validate_token_valid(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        info = mgr.validate_token(token)
        assert info is not None
        assert info["valid"] is True

    def test_validate_token_invalid(self):
        mgr = GatewayAuthManager()
        assert mgr.validate_token("bad") is None

    def test_validate_token_none_mode(self):
        mgr = GatewayAuthManager(mode=AuthMode.NONE)
        info = mgr.validate_token("anything")
        assert info is not None
        assert info["valid"] is True

    def test_validate_token_expired(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        tok_obj = mgr._tokens[token]
        tok_obj.expires_at = time.time() - 100
        assert mgr.validate_token(token) is None

    def test_validate_token_updates_last_used(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        before = time.time()
        mgr.validate_token(token)
        tok_obj = mgr._tokens[token]
        assert tok_obj.last_used >= before

    def test_revoke_token(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        assert mgr.revoke_token(token) is True
        assert mgr.validate_token(token) is None

    def test_revoke_nonexistent(self):
        mgr = GatewayAuthManager()
        assert mgr.revoke_token("nope") is False

    def test_revoke_decrements_count(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        assert mgr.token_count == 1
        mgr.revoke_token(token)
        assert mgr.token_count == 0

    def test_clear_stale_tokens(self):
        mgr = GatewayAuthManager()
        token = mgr.generate_token()
        tok_obj = mgr._tokens[token]
        tok_obj.created_at = time.time() - 400000
        tok_obj.last_used = time.time() - 400000
        cleared = mgr.clear_stale_tokens(max_age_hours=72)
        assert cleared == 1
        assert mgr.token_count == 0

    def test_clear_stale_tokens_none(self):
        mgr = GatewayAuthManager()
        mgr.generate_token()
        cleared = mgr.clear_stale_tokens()
        assert cleared == 0

    def test_clear_stale_tokens_empty(self):
        mgr = GatewayAuthManager()
        cleared = mgr.clear_stale_tokens()
        assert cleared == 0

    def test_token_count(self):
        mgr = GatewayAuthManager()
        assert mgr.token_count == 0
        mgr.generate_token()
        mgr.generate_token()
        assert mgr.token_count == 2


# -- PairingManager Tests --


class TestGatewayPairingManager:

    def test_init(self):
        mgr = GatewayPairingManager()
        assert mgr.paired_count == 0

    def test_pair_device(self):
        mgr = GatewayPairingManager()
        assert mgr.pair_device("dev1", "tok1") is True
        assert mgr.paired_count == 1

    def test_pair_device_empty_id(self):
        mgr = GatewayPairingManager()
        assert mgr.pair_device("", "tok") is False

    def test_pair_device_empty_token(self):
        mgr = GatewayPairingManager()
        assert mgr.pair_device("d1", "") is False

    def test_pair_device_default_scopes(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1")
        device = mgr.get_paired("d1")
        assert "operator.*" in device.scopes

    def test_pair_device_custom_scopes(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1", scopes=["admin", "read"])
        device = mgr.get_paired("d1")
        assert device is not None
        assert "admin" in device.scopes

    def test_pair_device_overwrites(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1")
        mgr.pair_device("d1", "t2")
        assert mgr.paired_count == 1
        assert mgr.get_paired("d1").token == "t2"

    def test_unpair_device(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1")
        assert mgr.unpair_device("d1") is True
        assert mgr.paired_count == 0

    def test_unpair_nonexistent(self):
        mgr = GatewayPairingManager()
        assert mgr.unpair_device("d1") is False

    def test_get_paired(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1")
        dev = mgr.get_paired("d1")
        assert dev is not None
        assert dev.device_id == "d1"

    def test_get_paired_none(self):
        mgr = GatewayPairingManager()
        assert mgr.get_paired("missing") is None

    def test_check_operator_scope_exact(self):
        assert GatewayPairingManager.check_operator_scope("operator.admin", "operator.admin") is True

    def test_check_operator_scope_wildcard(self):
        assert GatewayPairingManager.check_operator_scope("operator.admin", "operator.*") is True

    def test_check_operator_scope_no_match(self):
        assert GatewayPairingManager.check_operator_scope("admin.write", "operator.*") is False

    def test_check_operator_scope_reverse_wildcard(self):
        assert GatewayPairingManager.check_operator_scope("operator.*", "operator.admin") is True

    def test_check_operator_scope_different(self):
        assert GatewayPairingManager.check_operator_scope("read", "write") is False

    def test_check_operator_scope_both_wildcard(self):
        assert GatewayPairingManager.check_operator_scope("operator.*", "operator.*") is True

    def test_preserve_scopes_on_repair(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1", scopes=["admin", "read"])
        scopes = mgr.preserve_scopes_on_repair("d1")
        assert "admin" in scopes

    def test_preserve_scopes_nonexistent(self):
        mgr = GatewayPairingManager()
        assert mgr.preserve_scopes_on_repair("d1") == []

    def test_preserve_scopes_returns_copy(self):
        mgr = GatewayPairingManager()
        mgr.pair_device("d1", "t1", scopes=["a"])
        scopes = mgr.preserve_scopes_on_repair("d1")
        scopes.append("b")
        assert "b" not in mgr.get_paired("d1").scopes


# -- Daemon Tests --


class TestGatewayDaemon:

    def test_init(self):
        daemon = GatewayDaemon()
        assert daemon._running is False

    def test_init_pid_file(self):
        daemon = GatewayDaemon()
        assert "atlas_gateway.pid" in daemon._pid_file

    def test_start(self):
        daemon = GatewayDaemon()
        assert daemon.start() is True
        assert daemon._running is True
        daemon.stop()

    def test_start_already_running(self):
        daemon = GatewayDaemon()
        daemon.start()
        assert daemon.start() is False
        daemon.stop()

    def test_stop(self):
        daemon = GatewayDaemon()
        daemon.start()
        assert daemon.stop() is True
        assert daemon._running is False

    def test_stop_not_running(self):
        daemon = GatewayDaemon()
        assert daemon.stop() is False

    def test_status(self):
        daemon = GatewayDaemon()
        s = daemon.status()
        assert "running" in s
        assert "pid" in s
        assert "platform" in s

    def test_status_not_running(self):
        daemon = GatewayDaemon()
        s = daemon.status()
        assert s["running"] is False
        assert s["pid"] == 0

    def test_status_running(self):
        daemon = GatewayDaemon()
        daemon.start()
        s = daemon.status()
        assert s["running"] is True
        assert s["pid"] > 0
        daemon.stop()

    def test_status_has_node(self):
        daemon = GatewayDaemon()
        s = daemon.status()
        assert "node" in s

    def test_forward_tmpdir(self):
        daemon = GatewayDaemon()
        result = daemon.forward_tmpdir()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_prefer_active_node(self):
        result = GatewayDaemon.prefer_active_node()
        assert isinstance(result, str)


# -- Doctor Tests --


class TestGatewayDoctor:

    def test_init(self):
        doctor = GatewayDoctor()
        assert doctor._issues == []

    def test_avoid_rewriting_invalid_empty(self):
        assert GatewayDoctor.avoid_rewriting_invalid({}) is False

    def test_avoid_rewriting_invalid_no_version(self):
        assert GatewayDoctor.avoid_rewriting_invalid({"key": "val"}) is False

    def test_avoid_rewriting_invalid_valid(self):
        assert GatewayDoctor.avoid_rewriting_invalid({"version": "1.0"}) is True

    def test_avoid_rewriting_invalid_non_dict(self):
        assert GatewayDoctor.avoid_rewriting_invalid("not a dict") is False

    def test_avoid_rewriting_invalid_none(self):
        assert GatewayDoctor.avoid_rewriting_invalid(None) is False

    def test_skip_embedding_warnings_qmd(self):
        assert GatewayDoctor.skip_embedding_warnings("qmd") is True

    def test_skip_embedding_warnings_quantized(self):
        assert GatewayDoctor.skip_embedding_warnings("quantized") is True

    def test_skip_embedding_warnings_other(self):
        assert GatewayDoctor.skip_embedding_warnings("openai") is False

    def test_skip_embedding_warnings_case(self):
        assert GatewayDoctor.skip_embedding_warnings("QMD") is True

    def test_auto_repair_dm_policy_open(self):
        result = GatewayDoctor.auto_repair_dm_policy({"dmPolicy": "open"})
        assert result["dmPolicy"] == "invite"

    def test_auto_repair_dm_policy_invite(self):
        result = GatewayDoctor.auto_repair_dm_policy({"dmPolicy": "invite"})
        assert result["dmPolicy"] == "invite"

    def test_auto_repair_dm_policy_no_key(self):
        result = GatewayDoctor.auto_repair_dm_policy({"other": "val"})
        assert "dmPolicy" not in result

    def test_auto_repair_dm_policy_preserves_other(self):
        result = GatewayDoctor.auto_repair_dm_policy({"dmPolicy": "open", "extra": 1})
        assert result["extra"] == 1

    def test_detect_token_drift_ok(self):
        config = {"service_token": "svc1", "tokens": {"dev1": {"token": "dev_tok"}}}
        issues = GatewayDoctor.detect_token_drift(config)
        assert len(issues) == 0

    def test_detect_token_drift_same_token(self):
        config = {"service_token": "same", "tokens": {"dev1": {"token": "same"}}}
        issues = GatewayDoctor.detect_token_drift(config)
        assert len(issues) == 1
        assert "sapmasi" in issues[0]

    def test_detect_token_drift_no_service_token(self):
        config = {"service_token": "", "tokens": {"dev1": {"token": "t1"}}}
        issues = GatewayDoctor.detect_token_drift(config)
        assert len(issues) == 1

    def test_detect_token_drift_empty(self):
        issues = GatewayDoctor.detect_token_drift({})
        assert len(issues) == 0

    def test_detect_token_drift_no_tokens(self):
        config = {"service_token": "svc"}
        issues = GatewayDoctor.detect_token_drift(config)
        assert len(issues) == 0

    def test_run_diagnostics_empty_config(self):
        doctor = GatewayDoctor()
        result = doctor.run_diagnostics()
        assert result["total_issues"] >= 1

    def test_run_diagnostics_valid_config(self):
        doctor = GatewayDoctor()
        result = doctor.run_diagnostics(config={"version": "1.0"})
        assert isinstance(result["issues"], list)

    def test_run_diagnostics_with_fix(self):
        doctor = GatewayDoctor()
        result = doctor.run_diagnostics(config={"version": "1.0", "dmPolicy": "open"}, fix=True)
        assert result["fixed"] >= 1
        assert result["config"]["dmPolicy"] == "invite"

    def test_run_diagnostics_no_fix(self):
        doctor = GatewayDoctor()
        result = doctor.run_diagnostics(config={"version": "1.0", "dmPolicy": "open"}, fix=False)
        assert result["fixed"] == 0

    def test_run_diagnostics_returns_config(self):
        doctor = GatewayDoctor()
        result = doctor.run_diagnostics(config={"version": "1.0"})
        assert "config" in result

    def test_run_diagnostics_clears_previous(self):
        doctor = GatewayDoctor()
        doctor.run_diagnostics()
        result = doctor.run_diagnostics(config={"version": "1.0"})
        assert result["total_issues"] == 0


# -- ChannelHealth Tests --


class TestChannelHealthManager:

    def test_init(self):
        mgr = ChannelHealthManager()
        assert mgr._channels == {}

    def test_wire_check_minutes(self):
        mgr = ChannelHealthManager()
        mgr.wire_check_minutes("telegram", 10)
        status = mgr._channels["telegram"]
        assert status.check_interval_minutes == 10

    def test_wire_check_minutes_min(self):
        mgr = ChannelHealthManager()
        mgr.wire_check_minutes("slack", 0)
        status = mgr._channels["slack"]
        assert status.check_interval_minutes == 1

    def test_wire_check_minutes_max(self):
        mgr = ChannelHealthManager()
        mgr.wire_check_minutes("discord", 100)
        status = mgr._channels["discord"]
        assert status.check_interval_minutes == 60

    def test_wire_check_minutes_negative(self):
        mgr = ChannelHealthManager()
        mgr.wire_check_minutes("ch", -5)
        status = mgr._channels["ch"]
        assert status.check_interval_minutes == 1

    def test_harden_auto_restart_ok(self):
        mgr = ChannelHealthManager()
        assert mgr.harden_auto_restart("ch1") is True

    def test_harden_auto_restart_crash_loop(self):
        mgr = ChannelHealthManager(max_crashes=3, crash_window=600)
        for _ in range(3):
            mgr.harden_auto_restart("ch1")
        assert mgr.harden_auto_restart("ch1") is False

    def test_crash_loop_status_set(self):
        mgr = ChannelHealthManager(max_crashes=2)
        mgr.harden_auto_restart("ch1")
        mgr.harden_auto_restart("ch1")
        status = mgr._channels.get("ch1")
        if status:
            assert status.status == ChannelStatus.CRASH_LOOP

    def test_check_health(self):
        mgr = ChannelHealthManager()
        result = mgr.check_health("telegram")
        assert "status" in result
        assert "channel" in result

    def test_check_health_creates_channel(self):
        mgr = ChannelHealthManager()
        mgr.check_health("new_ch")
        assert "new_ch" in mgr._channels

    def test_check_health_updates_last_check(self):
        mgr = ChannelHealthManager()
        before = time.time()
        result = mgr.check_health("ch1")
        assert result["last_check"] >= before

    def test_restart_channel(self):
        mgr = ChannelHealthManager()
        assert mgr.restart_channel("ch1") is True
        status = mgr._channels["ch1"]
        assert status.status == ChannelStatus.HEALTHY

    def test_restart_channel_crash_loop(self):
        mgr = ChannelHealthManager(max_crashes=1)
        mgr.harden_auto_restart("ch1")
        assert mgr.restart_channel("ch1") is False

    def test_restart_channel_increments_crash_count(self):
        mgr = ChannelHealthManager()
        mgr.restart_channel("ch1")
        status = mgr._channels["ch1"]
        assert status.crash_count == 1

    def test_mark_down(self):
        mgr = ChannelHealthManager()
        mgr.mark_down("ch1", "test error")
        status = mgr._channels["ch1"]
        assert status.status == ChannelStatus.DOWN
        assert status.error_message == "test error"

    def test_mark_down_no_error(self):
        mgr = ChannelHealthManager()
        mgr.mark_down("ch1")
        status = mgr._channels["ch1"]
        assert status.status == ChannelStatus.DOWN
        assert status.error_message == ""

    def test_get_all_status_empty(self):
        mgr = ChannelHealthManager()
        assert mgr.get_all_status() == {}

    def test_get_all_status(self):
        mgr = ChannelHealthManager()
        mgr.check_health("ch1")
        mgr.check_health("ch2")
        result = mgr.get_all_status()
        assert len(result) == 2
        assert "ch1" in result

    def test_get_all_status_serializable(self):
        mgr = ChannelHealthManager()
        mgr.check_health("ch1")
        result = mgr.get_all_status()
        assert isinstance(result["ch1"], dict)


# -- UpdateManager Tests --


class TestGatewayUpdateManager:

    def test_init(self):
        mgr = GatewayUpdateManager()
        assert mgr._context_file

    def test_init_custom_path(self):
        mgr = GatewayUpdateManager(context_file="/tmp/custom.json")
        assert mgr._context_file == "/tmp/custom.json"

    def test_restart_only_on_success_true(self):
        assert GatewayUpdateManager.restart_only_on_success({"success": True, "restart_required": True}) is True

    def test_restart_only_on_success_failed(self):
        assert GatewayUpdateManager.restart_only_on_success({"success": False, "restart_required": True}) is False

    def test_restart_only_on_success_no_restart(self):
        assert GatewayUpdateManager.restart_only_on_success({"success": True, "restart_required": False}) is False

    def test_restart_only_on_success_both_false(self):
        assert GatewayUpdateManager.restart_only_on_success({"success": False, "restart_required": False}) is False

    def test_restart_only_on_success_empty(self):
        assert GatewayUpdateManager.restart_only_on_success({}) is False

    def test_preserve_restart_context(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            result = mgr.preserve_restart_context({"key": "value"})
            assert result == path
            assert os.path.isfile(path)
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_preserve_restart_context_content(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            mgr.preserve_restart_context({"a": 1})
            with open(path) as fh:
                data = json.load(fh)
            assert data["context"]["a"] == 1
            assert "saved_at" in data
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_restore_restart_context(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            mgr.preserve_restart_context({"restore": "test"})
            ctx = mgr.restore_restart_context()
            assert ctx is not None
            assert ctx["restore"] == "test"
            assert not os.path.isfile(path)
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_restore_no_file(self):
        mgr = GatewayUpdateManager(context_file="/tmp/no_such_file_xyz.json")
        assert mgr.restore_restart_context() is None

    def test_restore_cleans_up(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            mgr.preserve_restart_context({"x": 1})
            mgr.restore_restart_context()
            assert not os.path.isfile(path)
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_perform_update(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            result = mgr.perform_update("2.0", config={"key": "val"})
            assert result.success is True
            assert result.version == "2.0"
            assert result.restart_required is True
            assert result.context_preserved is True
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_perform_update_no_config(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            result = mgr.perform_update("1.5")
            assert result.success is True
            assert result.context_preserved is False
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_perform_update_has_doctor_result(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = GatewayUpdateManager(context_file=path)
            result = mgr.perform_update("3.0")
            assert isinstance(result.doctor_result, dict)
            assert "total_issues" in result.doctor_result
        finally:
            if os.path.isfile(path):
                os.unlink(path)

    def test_run_doctor_during_update(self):
        result = GatewayUpdateManager.run_doctor_during_update()
        assert isinstance(result, dict)
        assert "total_issues" in result
