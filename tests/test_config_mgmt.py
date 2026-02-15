"""ATLAS Configuration Management testleri."""

import json

import pytest

from app.core.config_mgmt import (
    ConfigDiffer,
    ConfigLoader,
    ConfigOrchestrator,
    ConfigStore,
    ConfigValidator,
    DynamicConfig,
    EnvironmentManager,
    FeatureFlags,
    SecretVault,
)
from app.models.config_mgmt import (
    ConfigFormat,
    ConfigRecord,
    ConfigScope,
    ConfigSnapshot,
    EnvironmentType,
    FlagRecord,
    FlagStatus,
    SecretRecord,
    SecretType,
    ValidationLevel,
)


# ===================== Models =====================


class TestConfigModels:
    """Model testleri."""

    def test_config_format_enum(self):
        assert ConfigFormat.JSON == "json"
        assert ConfigFormat.YAML == "yaml"
        assert ConfigFormat.TOML == "toml"
        assert ConfigFormat.ENV == "env"
        assert ConfigFormat.INI == "ini"
        assert ConfigFormat.PROPERTIES == "properties"

    def test_config_scope_enum(self):
        assert ConfigScope.GLOBAL == "global"
        assert ConfigScope.ENVIRONMENT == "environment"
        assert ConfigScope.SERVICE == "service"
        assert ConfigScope.INSTANCE == "instance"
        assert ConfigScope.USER == "user"
        assert ConfigScope.TEMPORARY == "temporary"

    def test_validation_level_enum(self):
        assert ValidationLevel.STRICT == "strict"
        assert ValidationLevel.NORMAL == "normal"
        assert ValidationLevel.LENIENT == "lenient"
        assert ValidationLevel.WARN == "warn"
        assert ValidationLevel.SKIP == "skip"
        assert ValidationLevel.CUSTOM == "custom"

    def test_flag_status_enum(self):
        assert FlagStatus.ENABLED == "enabled"
        assert FlagStatus.DISABLED == "disabled"
        assert FlagStatus.GRADUAL == "gradual"
        assert FlagStatus.AB_TEST == "ab_test"
        assert FlagStatus.SCHEDULED == "scheduled"
        assert FlagStatus.KILLED == "killed"

    def test_secret_type_enum(self):
        assert SecretType.API_KEY == "api_key"
        assert SecretType.PASSWORD == "password"
        assert SecretType.CERTIFICATE == "certificate"
        assert SecretType.TOKEN == "token"
        assert SecretType.PRIVATE_KEY == "private_key"
        assert SecretType.CONNECTION_STRING == "connection_string"

    def test_environment_type_enum(self):
        assert EnvironmentType.DEVELOPMENT == "development"
        assert EnvironmentType.STAGING == "staging"
        assert EnvironmentType.PRODUCTION == "production"
        assert EnvironmentType.TESTING == "testing"
        assert EnvironmentType.CI == "ci"
        assert EnvironmentType.LOCAL == "local"

    def test_config_record(self):
        r = ConfigRecord(key="db_host", value="localhost")
        assert r.key == "db_host"
        assert r.value == "localhost"
        assert r.scope == ConfigScope.GLOBAL
        assert r.version == 1
        assert len(r.config_id) == 8

    def test_config_record_custom(self):
        r = ConfigRecord(
            key="port",
            value=8080,
            scope=ConfigScope.SERVICE,
            version=3,
        )
        assert r.scope == ConfigScope.SERVICE
        assert r.version == 3

    def test_flag_record(self):
        r = FlagRecord(name="dark_mode")
        assert r.name == "dark_mode"
        assert r.status == FlagStatus.DISABLED
        assert r.rollout_pct == 0.0
        assert len(r.flag_id) == 8

    def test_flag_record_custom(self):
        r = FlagRecord(
            name="beta",
            status=FlagStatus.GRADUAL,
            rollout_pct=50.0,
        )
        assert r.status == FlagStatus.GRADUAL
        assert r.rollout_pct == 50.0

    def test_secret_record(self):
        r = SecretRecord(name="api_key_1")
        assert r.name == "api_key_1"
        assert r.secret_type == SecretType.API_KEY
        assert r.access_count == 0
        assert len(r.secret_id) == 8

    def test_secret_record_custom(self):
        r = SecretRecord(
            name="db_pass",
            secret_type=SecretType.PASSWORD,
            access_count=5,
        )
        assert r.secret_type == SecretType.PASSWORD
        assert r.access_count == 5

    def test_config_snapshot(self):
        s = ConfigSnapshot(
            total_configs=10,
            total_secrets=3,
            total_flags=5,
        )
        assert s.total_configs == 10
        assert s.total_secrets == 3
        assert s.total_flags == 5
        assert s.environments == 0


# ===================== ConfigStore =====================


class TestConfigStore:
    """ConfigStore testleri."""

    def test_init(self):
        store = ConfigStore()
        assert store.config_count == 0
        assert store.namespace_count == 0

    def test_set_and_get(self):
        store = ConfigStore()
        store.set("host", "localhost")
        assert store.get("host") == "localhost"

    def test_set_returns_info(self):
        store = ConfigStore()
        r = store.set("port", 8080)
        assert r["key"] == "default.port"
        assert r["version"] == 1

    def test_version_increment(self):
        store = ConfigStore()
        store.set("val", 1)
        r = store.set("val", 2)
        assert r["version"] == 2

    def test_namespace(self):
        store = ConfigStore()
        store.set("host", "db1", namespace="db")
        store.set("port", 5432, namespace="db")
        assert store.get("host", namespace="db") == "db1"
        ns = store.get_namespace("db")
        assert "host" in ns
        assert "port" in ns

    def test_delete(self):
        store = ConfigStore()
        store.set("key1", "val1")
        assert store.delete("key1") is True
        assert store.get("key1") is None

    def test_delete_nonexistent(self):
        store = ConfigStore()
        assert store.delete("missing") is False

    def test_history(self):
        store = ConfigStore()
        store.set("val", 1)
        store.set("val", 2)
        store.set("val", 3)
        hist = store.get_history("val")
        assert len(hist) == 2  # ilk surum kayit yok

    def test_get_version(self):
        store = ConfigStore()
        assert store.get_version("missing") == 0
        store.set("x", 1)
        assert store.get_version("x") == 1
        store.set("x", 2)
        assert store.get_version("x") == 2

    def test_encrypted_set_get(self):
        store = ConfigStore()
        store.set("secret", "mypass", encrypt=True)
        assert store.get("secret") == "mypass"
        assert store.encrypted_count == 1

    def test_hierarchical(self):
        store = ConfigStore()
        store.set_hierarchical("db.host", "localhost")
        assert store.get_hierarchical("db.host") == "localhost"

    def test_hierarchical_children(self):
        store = ConfigStore()
        store.set("db.host", "localhost")
        store.set("db.port", 5432)
        children = store.get_hierarchical("db")
        assert children is not None

    def test_default_value(self):
        store = ConfigStore()
        assert store.get("missing", default="x") == "x"

    def test_list_namespaces(self):
        store = ConfigStore()
        store.set("a", 1, namespace="ns1")
        store.set("b", 2, namespace="ns2")
        ns_list = store.list_namespaces()
        assert "ns1" in ns_list
        assert "ns2" in ns_list


# ===================== ConfigLoader =====================


class TestConfigLoader:
    """ConfigLoader testleri."""

    def test_init(self):
        loader = ConfigLoader()
        assert loader.source_count == 0
        assert loader.loaded_count == 0

    def test_load_json(self):
        loader = ConfigLoader()
        data = loader.load_json('{"host": "localhost", "port": 8080}')
        assert data["host"] == "localhost"
        assert data["port"] == 8080
        assert loader.source_count == 1

    def test_load_json_invalid(self):
        loader = ConfigLoader()
        data = loader.load_json("not json")
        assert "error" in data

    def test_load_yaml(self):
        loader = ConfigLoader()
        content = "host: localhost\nport: 8080\ndebug: true"
        data = loader.load_yaml(content)
        assert data["host"] == "localhost"
        assert data["port"] == 8080
        assert data["debug"] is True

    def test_load_yaml_comments(self):
        loader = ConfigLoader()
        content = "# comment\nkey: value"
        data = loader.load_yaml(content)
        assert data["key"] == "value"

    def test_load_env(self):
        loader = ConfigLoader()
        env_vars = {
            "APP_HOST": "localhost",
            "APP_PORT": "8080",
            "OTHER": "skip",
        }
        data = loader.load_env(env_vars, prefix="APP")
        assert "host" in data
        assert "port" in data
        assert "other" not in data

    def test_load_env_no_prefix(self):
        loader = ConfigLoader()
        data = loader.load_env({"KEY": "val"})
        assert "key" in data

    def test_load_dict(self):
        loader = ConfigLoader()
        data = loader.load_dict({"a": 1, "b": 2})
        assert data["a"] == 1
        assert loader.loaded_count == 1

    def test_merge_override(self):
        loader = ConfigLoader()
        loader.load_dict({"a": 1, "b": 2}, "src1")
        loader.load_dict({"b": 3, "c": 4}, "src2")
        merged = loader.merge("override")
        assert merged["a"] == 1
        assert merged["b"] == 3
        assert merged["c"] == 4

    def test_merge_first_wins(self):
        loader = ConfigLoader()
        loader.load_dict({"a": 1, "b": 2}, "s1")
        loader.load_dict({"b": 3, "c": 4}, "s2")
        merged = loader.merge("first_wins")
        assert merged["b"] == 2  # ilk kazanir

    def test_merge_deep(self):
        loader = ConfigLoader()
        loader.load_dict(
            {"db": {"host": "a", "port": 5432}}, "s1",
        )
        loader.load_dict(
            {"db": {"host": "b", "name": "test"}}, "s2",
        )
        merged = loader.merge("deep_merge")
        assert merged["db"]["host"] == "b"
        assert merged["db"]["port"] == 5432
        assert merged["db"]["name"] == "test"

    def test_merge_empty(self):
        loader = ConfigLoader()
        assert loader.merge() == {}

    def test_get_source(self):
        loader = ConfigLoader()
        loader.load_dict({"x": 1}, "test")
        src = loader.get_source("test")
        assert src == {"x": 1}
        assert loader.get_source("missing") is None

    def test_clear(self):
        loader = ConfigLoader()
        loader.load_dict({"a": 1})
        count = loader.clear()
        assert count == 1
        assert loader.loaded_count == 0


# ===================== ConfigValidator =====================


class TestConfigValidator:
    """ConfigValidator testleri."""

    def test_init(self):
        v = ConfigValidator()
        assert v.schema_count == 0
        assert v.rule_count == 0

    def test_define_schema(self):
        v = ConfigValidator()
        r = v.define_schema("app", {
            "host": {"type": "string", "required": True},
            "port": {"type": "integer", "min": 1, "max": 65535},
        })
        assert r["name"] == "app"
        assert r["fields"] == 2

    def test_validate_valid(self):
        v = ConfigValidator()
        v.define_schema("app", {
            "host": {"type": "string", "required": True},
            "port": {"type": "integer"},
        })
        r = v.validate({"host": "localhost", "port": 8080}, "app")
        assert r["valid"] is True
        assert r["errors"] == []

    def test_validate_missing_required(self):
        v = ConfigValidator()
        v.define_schema("app", {
            "host": {"type": "string", "required": True},
        })
        r = v.validate({}, "app")
        assert r["valid"] is False
        assert any("required" in e for e in r["errors"])

    def test_validate_wrong_type(self):
        v = ConfigValidator()
        v.define_schema("app", {
            "port": {"type": "integer"},
        })
        r = v.validate({"port": "not_int"}, "app")
        assert r["valid"] is False

    def test_validate_range(self):
        v = ConfigValidator()
        v.define_schema("app", {
            "port": {"type": "integer", "min": 1, "max": 100},
        })
        r = v.validate({"port": 200}, "app")
        assert r["valid"] is False

    def test_validate_enum(self):
        v = ConfigValidator()
        v.define_schema("app", {
            "env": {"enum": ["dev", "prod"]},
        })
        r = v.validate({"env": "test"}, "app")
        assert r["valid"] is False

    def test_validate_nonexistent_schema(self):
        v = ConfigValidator()
        r = v.validate({}, "missing")
        assert r["valid"] is False
        assert "schema_not_found" in r["errors"]

    def test_validate_type_method(self):
        v = ConfigValidator()
        assert v.validate_type("hello", "string") is True
        assert v.validate_type(42, "integer") is True
        assert v.validate_type(3.14, "float") is True
        assert v.validate_type(True, "boolean") is True
        assert v.validate_type([], "list") is True
        assert v.validate_type({}, "dict") is True
        assert v.validate_type(42, "number") is True

    def test_validate_type_mismatch(self):
        v = ConfigValidator()
        assert v.validate_type("str", "integer") is False

    def test_validate_dependencies(self):
        v = ConfigValidator()
        r = v.validate_dependencies(
            {"ssl": True},
            {"ssl": ["ssl_cert", "ssl_key"]},
        )
        assert r["valid"] is False
        assert len(r["errors"]) == 2

    def test_validate_dependencies_satisfied(self):
        v = ConfigValidator()
        r = v.validate_dependencies(
            {"ssl": True, "ssl_cert": "c", "ssl_key": "k"},
            {"ssl": ["ssl_cert", "ssl_key"]},
        )
        assert r["valid"] is True

    def test_custom_rule(self):
        v = ConfigValidator()
        v.define_schema("app", {
            "port": {"type": "integer"},
        })
        v.add_rule("port_check", lambda d: d.get("port", 0) > 0)
        r = v.validate({"port": 0}, "app")
        assert r["valid"] is False

    def test_remove_rule(self):
        v = ConfigValidator()
        v.add_rule("test", lambda d: True)
        assert v.remove_rule("test") is True
        assert v.remove_rule("missing") is False

    def test_validation_count(self):
        v = ConfigValidator()
        v.define_schema("s", {"a": {"type": "string"}})
        v.validate({"a": "x"}, "s")
        v.validate({"a": "y"}, "s")
        assert v.validation_count == 2


# ===================== FeatureFlags =====================


class TestFeatureFlags:
    """FeatureFlags testleri."""

    def test_init(self):
        ff = FeatureFlags()
        assert ff.flag_count == 0
        assert ff.enabled_count == 0

    def test_create_flag(self):
        ff = FeatureFlags()
        r = ff.create_flag("dark_mode", enabled=True)
        assert r["name"] == "dark_mode"
        assert r["enabled"] is True
        assert ff.flag_count == 1

    def test_is_enabled(self):
        ff = FeatureFlags()
        ff.create_flag("feat1", enabled=True)
        assert ff.is_enabled("feat1") is True

    def test_is_disabled(self):
        ff = FeatureFlags()
        ff.create_flag("feat1", enabled=False)
        assert ff.is_enabled("feat1") is False

    def test_nonexistent_flag(self):
        ff = FeatureFlags()
        assert ff.is_enabled("missing") is False

    def test_enable_disable(self):
        ff = FeatureFlags()
        ff.create_flag("feat1")
        ff.enable("feat1")
        assert ff.is_enabled("feat1") is True
        ff.disable("feat1")
        assert ff.is_enabled("feat1") is False

    def test_enable_nonexistent(self):
        ff = FeatureFlags()
        assert ff.enable("missing") is False
        assert ff.disable("missing") is False

    def test_kill_switch(self):
        ff = FeatureFlags()
        ff.create_flag("feat1", enabled=True)
        ff.kill("feat1")
        assert ff.is_enabled("feat1") is False

    def test_kill_nonexistent(self):
        ff = FeatureFlags()
        assert ff.kill("missing") is False

    def test_rollout_percentage(self):
        ff = FeatureFlags()
        ff.create_flag("feat1", enabled=True, rollout_pct=50.0)
        # Deterministik sonuc icin user_id kullan
        results = set()
        for i in range(100):
            results.add(ff.is_enabled("feat1", f"user_{i}"))
        # 50% dagitimda True ve False olmali
        assert True in results
        assert False in results

    def test_set_rollout(self):
        ff = FeatureFlags()
        ff.create_flag("feat1")
        assert ff.set_rollout("feat1", 75.0) is True
        flag = ff.get_flag("feat1")
        assert flag["rollout_pct"] == 75.0

    def test_set_rollout_clamp(self):
        ff = FeatureFlags()
        ff.create_flag("feat1")
        ff.set_rollout("feat1", 150.0)
        assert ff.get_flag("feat1")["rollout_pct"] == 100.0
        ff.set_rollout("feat1", -10.0)
        assert ff.get_flag("feat1")["rollout_pct"] == 0.0

    def test_set_rollout_nonexistent(self):
        ff = FeatureFlags()
        assert ff.set_rollout("missing", 50.0) is False

    def test_user_override(self):
        ff = FeatureFlags()
        ff.create_flag("feat1", enabled=False)
        ff.set_override("feat1", "user1", True)
        assert ff.is_enabled("feat1", "user1") is True

    def test_remove_override(self):
        ff = FeatureFlags()
        ff.create_flag("feat1")
        ff.set_override("feat1", "user1", True)
        assert ff.remove_override("feat1", "user1") is True
        assert ff.remove_override("feat1", "user999") is False
        assert ff.remove_override("missing", "u1") is False

    def test_get_flag(self):
        ff = FeatureFlags()
        ff.create_flag("feat1", enabled=True)
        f = ff.get_flag("feat1")
        assert f["name"] == "feat1"
        assert f["enabled"] is True
        assert f["kill_switch"] is False

    def test_get_flag_nonexistent(self):
        ff = FeatureFlags()
        assert ff.get_flag("missing") is None

    def test_delete_flag(self):
        ff = FeatureFlags()
        ff.create_flag("feat1")
        assert ff.delete_flag("feat1") is True
        assert ff.flag_count == 0
        assert ff.delete_flag("missing") is False

    def test_enabled_count(self):
        ff = FeatureFlags()
        ff.create_flag("a", enabled=True)
        ff.create_flag("b", enabled=True)
        ff.create_flag("c", enabled=False)
        assert ff.enabled_count == 2

    def test_enabled_count_with_kill(self):
        ff = FeatureFlags()
        ff.create_flag("a", enabled=True)
        ff.kill("a")
        assert ff.enabled_count == 0

    def test_evaluation_count(self):
        ff = FeatureFlags()
        ff.create_flag("a", enabled=True)
        ff.is_enabled("a")
        ff.is_enabled("a")
        assert ff.evaluation_count == 2


# ===================== SecretVault =====================


class TestSecretVault:
    """SecretVault testleri."""

    def test_init(self):
        vault = SecretVault()
        assert vault.secret_count == 0
        assert vault.access_log_count == 0

    def test_store(self):
        vault = SecretVault()
        r = vault.store("api_key", "secret123")
        assert r["name"] == "api_key"
        assert r["version"] == 1
        assert vault.secret_count == 1

    def test_store_version_increment(self):
        vault = SecretVault()
        vault.store("key", "v1")
        r = vault.store("key", "v2")
        assert r["version"] == 2

    def test_retrieve(self):
        vault = SecretVault()
        vault.store("api_key", "secret123")
        r = vault.retrieve("api_key")
        assert r["found"] is True
        assert r["access"] == "granted"
        assert r["value"] == "secret123"

    def test_retrieve_not_found(self):
        vault = SecretVault()
        r = vault.retrieve("missing")
        assert r["found"] is False

    def test_acl_denied(self):
        vault = SecretVault()
        vault.store("key", "val", allowed_accessors=["admin"])
        r = vault.retrieve("key", accessor="user1")
        assert r["access"] == "denied"

    def test_acl_granted(self):
        vault = SecretVault()
        vault.store("key", "val", allowed_accessors=["admin"])
        r = vault.retrieve("key", accessor="admin")
        assert r["access"] == "granted"

    def test_delete(self):
        vault = SecretVault()
        vault.store("key", "val")
        assert vault.delete("key") is True
        assert vault.secret_count == 0
        assert vault.delete("missing") is False

    def test_rotate(self):
        vault = SecretVault()
        vault.store("key", "old_val")
        r = vault.rotate("key", "new_val")
        assert r["status"] == "rotated"
        assert r["version"] == 2
        ret = vault.retrieve("key")
        assert ret["value"] == "new_val"

    def test_rotate_not_found(self):
        vault = SecretVault()
        r = vault.rotate("missing", "val")
        assert r["status"] == "error"

    def test_rotation_schedule(self):
        vault = SecretVault()
        vault.store("key", "val")
        vault.set_rotation_schedule("key", 30)
        # Yeni olusturulan sirlarin rotasyonu gerekmez
        needed = vault.check_rotation_needed()
        assert isinstance(needed, list)

    def test_grant_access(self):
        vault = SecretVault()
        vault.store("key", "val")
        assert vault.grant_access("key", "user1") is True
        assert vault.grant_access("missing", "u1") is False

    def test_revoke_access(self):
        vault = SecretVault()
        vault.store("key", "val", allowed_accessors=["admin"])
        assert vault.revoke_access("key", "admin") is True
        assert vault.revoke_access("missing", "u") is False

    def test_access_log(self):
        vault = SecretVault()
        vault.store("key", "val")
        vault.retrieve("key", accessor="user1")
        log = vault.get_access_log()
        assert len(log) == 1
        assert log[0]["accessor"] == "user1"

    def test_access_log_filtered(self):
        vault = SecretVault()
        vault.store("k1", "v1")
        vault.store("k2", "v2")
        vault.retrieve("k1")
        vault.retrieve("k2")
        filtered = vault.get_access_log("k1")
        assert len(filtered) == 1


# ===================== EnvironmentManager =====================


class TestEnvironmentManager:
    """EnvironmentManager testleri."""

    def test_init(self):
        em = EnvironmentManager()
        assert em.current_env == "development"
        assert em.environment_count == 0

    def test_custom_env(self):
        em = EnvironmentManager("staging")
        assert em.current_env == "staging"

    def test_register_environment(self):
        em = EnvironmentManager()
        r = em.register_environment("dev", level=0)
        assert r["name"] == "dev"
        assert em.environment_count == 1

    def test_set_and_get_config(self):
        em = EnvironmentManager()
        em.register_environment("dev")
        em.set_config("dev", "debug", True)
        assert em.get_config("debug", env="dev") is True

    def test_get_config_default(self):
        em = EnvironmentManager()
        assert em.get_config("missing", default="x") == "x"

    def test_get_config_current_env(self):
        em = EnvironmentManager("dev")
        em.set_config("dev", "key", "val")
        assert em.get_config("key") == "val"

    def test_get_all_configs(self):
        em = EnvironmentManager()
        em.set_config("dev", "a", 1)
        em.set_config("dev", "b", 2)
        configs = em.get_all_configs(env="dev")
        assert configs["a"] == 1
        assert configs["b"] == 2

    def test_promotion_rule(self):
        em = EnvironmentManager()
        em.register_environment("dev")
        em.register_environment("prod")
        r = em.add_promotion_rule("dev", "prod")
        assert r["from_env"] == "dev"
        assert r["require_approval"] is True

    def test_promote(self):
        em = EnvironmentManager()
        em.register_environment("dev")
        em.register_environment("prod")
        em.add_promotion_rule("dev", "prod", require_approval=False)
        em.set_config("dev", "key", "val")
        r = em.promote("key", "dev", "prod")
        assert r["status"] == "promoted"
        assert em.get_config("key", env="prod") == "val"

    def test_promote_key_not_found(self):
        em = EnvironmentManager()
        em.add_promotion_rule("dev", "prod")
        r = em.promote("missing", "dev", "prod")
        assert r["status"] == "error"
        assert r["reason"] == "key_not_found"

    def test_promote_no_rule(self):
        em = EnvironmentManager()
        em.add_promotion_rule("dev", "staging")
        em.set_config("dev", "key", "val")
        r = em.promote("key", "dev", "prod")
        assert r["status"] == "error"
        assert r["reason"] == "no_promotion_rule"

    def test_promote_no_rules_at_all(self):
        em = EnvironmentManager()
        em.set_config("dev", "key", "val")
        r = em.promote("key", "dev", "prod")
        assert r["status"] == "promoted"

    def test_compare(self):
        em = EnvironmentManager()
        em.set_config("dev", "a", 1)
        em.set_config("dev", "b", 2)
        em.set_config("prod", "b", 3)
        em.set_config("prod", "c", 4)
        r = em.compare("dev", "prod")
        assert "a" in r["only_a"]
        assert "c" in r["only_b"]
        assert "b" in r["different"]

    def test_compare_same(self):
        em = EnvironmentManager()
        em.set_config("a", "key", "val")
        em.set_config("b", "key", "val")
        r = em.compare("a", "b")
        assert "key" in r["same"]

    def test_detect_environment(self):
        em = EnvironmentManager("production")
        assert em.detect_environment() == "production"

    def test_switch_environment(self):
        em = EnvironmentManager()
        em.register_environment("staging")
        assert em.switch_environment("staging") is True
        assert em.current_env == "staging"

    def test_switch_nonexistent(self):
        em = EnvironmentManager()
        assert em.switch_environment("missing") is False

    def test_promotion_count(self):
        em = EnvironmentManager()
        em.set_config("dev", "k", "v")
        em.promote("k", "dev", "prod")
        assert em.promotion_count == 1


# ===================== DynamicConfig =====================


class TestDynamicConfig:
    """DynamicConfig testleri."""

    def test_init(self):
        dc = DynamicConfig()
        assert dc.config_count == 0
        assert dc.watcher_count == 0

    def test_set_and_get(self):
        dc = DynamicConfig()
        dc.set("key", "value")
        assert dc.get("key") == "value"

    def test_get_default(self):
        dc = DynamicConfig()
        assert dc.get("missing", default="x") == "x"

    def test_set_returns_info(self):
        dc = DynamicConfig()
        r = dc.set("key", "val")
        assert r["key"] == "key"
        assert r["version"] == 1
        assert r["changed"] is True

    def test_version_increment(self):
        dc = DynamicConfig()
        dc.set("key", "v1")
        r = dc.set("key", "v2")
        assert r["version"] == 2

    def test_no_change(self):
        dc = DynamicConfig()
        dc.set("key", "same")
        r = dc.set("key", "same")
        assert r["changed"] is False

    def test_delete(self):
        dc = DynamicConfig()
        dc.set("key", "val")
        assert dc.delete("key") is True
        assert dc.get("key") is None
        assert dc.delete("missing") is False

    def test_watcher(self):
        dc = DynamicConfig()
        changes = []
        dc.watch("key", lambda k, n, o: changes.append((k, n, o)))
        dc.set("key", "val1")
        dc.set("key", "val2")
        assert len(changes) == 2
        assert changes[0] == ("key", "val1", None)
        assert changes[1] == ("key", "val2", "val1")

    def test_unwatch_all(self):
        dc = DynamicConfig()
        dc.watch("key", lambda k, n, o: None)
        assert dc.unwatch("key") is True
        assert dc.watcher_count == 0

    def test_unwatch_specific(self):
        dc = DynamicConfig()
        cb = lambda k, n, o: None
        dc.watch("key", cb)
        assert dc.unwatch("key", cb) is True

    def test_unwatch_nonexistent(self):
        dc = DynamicConfig()
        assert dc.unwatch("missing") is False

    def test_rollback(self):
        dc = DynamicConfig()
        dc.set("key", "v1")
        dc.set("key", "v2")
        r = dc.rollback("key")
        assert r["status"] == "rolled_back"
        assert r["restored"] == "v1"

    def test_rollback_no_history(self):
        dc = DynamicConfig()
        r = dc.rollback("missing")
        assert r["status"] == "error"

    def test_snapshot(self):
        dc = DynamicConfig()
        dc.set("a", 1)
        dc.set("b", 2)
        r = dc.create_snapshot("snap1")
        assert r["config_count"] == 2
        assert dc.snapshot_count == 1

    def test_restore_snapshot(self):
        dc = DynamicConfig()
        dc.set("a", 1)
        dc.set("b", 2)
        dc.create_snapshot("snap1")
        dc.set("a", 99)
        r = dc.restore_snapshot("snap1")
        assert r["status"] == "restored"
        assert r["restored_count"] == 2
        assert dc.get("a") == 1

    def test_restore_not_found(self):
        dc = DynamicConfig()
        r = dc.restore_snapshot("missing")
        assert r["status"] == "error"

    def test_change_history(self):
        dc = DynamicConfig()
        dc.set("a", 1)
        dc.set("b", 2)
        hist = dc.get_change_history()
        assert len(hist) == 2

    def test_change_history_filtered(self):
        dc = DynamicConfig()
        dc.set("a", 1)
        dc.set("b", 2)
        hist = dc.get_change_history(key="a")
        assert len(hist) == 1

    def test_hot_reload(self):
        dc = DynamicConfig()
        dc.set_hot_reload(False)
        assert dc._hot_reload_enabled is False

    def test_bulk_set(self):
        dc = DynamicConfig()
        r = dc.bulk_set({"a": 1, "b": 2, "c": 3})
        assert r["total"] == 3
        assert dc.config_count == 3

    def test_change_count(self):
        dc = DynamicConfig()
        dc.set("a", 1)
        dc.set("a", 2)
        assert dc.change_count == 2


# ===================== ConfigDiffer =====================


class TestConfigDiffer:
    """ConfigDiffer testleri."""

    def test_init(self):
        cd = ConfigDiffer()
        assert cd.diff_count == 0
        assert cd.migration_count == 0

    def test_diff_added(self):
        cd = ConfigDiffer()
        r = cd.diff({"a": 1}, {"a": 1, "b": 2})
        assert len(r["added"]) == 1
        assert r["added"][0]["key"] == "b"
        assert r["has_changes"] is True

    def test_diff_removed(self):
        cd = ConfigDiffer()
        r = cd.diff({"a": 1, "b": 2}, {"a": 1})
        assert len(r["removed"]) == 1
        assert r["removed"][0]["key"] == "b"

    def test_diff_modified(self):
        cd = ConfigDiffer()
        r = cd.diff({"a": 1}, {"a": 2})
        assert len(r["modified"]) == 1
        assert r["modified"][0]["old_value"] == 1
        assert r["modified"][0]["new_value"] == 2

    def test_diff_unchanged(self):
        cd = ConfigDiffer()
        r = cd.diff({"a": 1}, {"a": 1})
        assert "a" in r["unchanged"]
        assert r["has_changes"] is False
        assert r["total_changes"] == 0

    def test_diff_empty(self):
        cd = ConfigDiffer()
        r = cd.diff({}, {})
        assert r["total_changes"] == 0

    def test_deep_diff(self):
        cd = ConfigDiffer()
        source = {"db": {"host": "a", "port": 5432}}
        target = {"db": {"host": "b", "port": 5432}}
        changes = cd.deep_diff(source, target)
        assert len(changes) == 1
        assert changes[0]["path"] == "db.host"
        assert changes[0]["type"] == "modified"

    def test_deep_diff_added(self):
        cd = ConfigDiffer()
        changes = cd.deep_diff(
            {"a": 1}, {"a": 1, "b": 2},
        )
        assert any(c["type"] == "added" for c in changes)

    def test_deep_diff_removed(self):
        cd = ConfigDiffer()
        changes = cd.deep_diff(
            {"a": 1, "b": 2}, {"a": 1},
        )
        assert any(c["type"] == "removed" for c in changes)

    def test_deep_diff_nested(self):
        cd = ConfigDiffer()
        source = {"x": {"y": {"z": 1}}}
        target = {"x": {"y": {"z": 2}}}
        changes = cd.deep_diff(source, target)
        assert changes[0]["path"] == "x.y.z"

    def test_create_migration(self):
        cd = ConfigDiffer()
        m = cd.create_migration(
            {"a": 1}, {"a": 2, "b": 3}, "v1_to_v2",
        )
        assert m["name"] == "v1_to_v2"
        assert m["total_steps"] > 0
        assert cd.migration_count == 1

    def test_migration_steps(self):
        cd = ConfigDiffer()
        m = cd.create_migration(
            {"a": 1, "c": 3},
            {"a": 2, "b": 4},
        )
        actions = [s["action"] for s in m["steps"]]
        assert "add" in actions
        assert "update" in actions
        assert "remove" in actions

    def test_apply_migration(self):
        cd = ConfigDiffer()
        m = cd.create_migration(
            {"a": 1}, {"a": 2, "b": 3},
        )
        result = cd.apply_migration({"a": 1}, m)
        assert result["config"]["a"] == 2
        assert result["config"]["b"] == 3

    def test_impact_rules(self):
        cd = ConfigDiffer()
        cd.add_impact_rule("db", severity="critical", description="DB change")
        assert cd.impact_rule_count == 1

    def test_analyze_impact(self):
        cd = ConfigDiffer()
        cd.add_impact_rule("db", severity="critical", description="DB change")
        diff_result = cd.diff(
            {"db_host": "a"}, {"db_host": "b"},
        )
        impact = cd.analyze_impact(diff_result)
        assert impact["impact_count"] > 0
        assert impact["max_severity"] == "critical"
        assert impact["safe"] is False

    def test_analyze_impact_safe(self):
        cd = ConfigDiffer()
        diff_result = cd.diff({"a": 1}, {"a": 2})
        impact = cd.analyze_impact(diff_result)
        assert impact["safe"] is True

    def test_detect_breaking_removed(self):
        cd = ConfigDiffer()
        r = cd.detect_breaking(
            {"a": 1, "b": 2}, {"a": 1},
        )
        assert r["is_breaking"] is True
        assert any(
            b["reason"] == "key_removed"
            for b in r["breaking_changes"]
        )

    def test_detect_breaking_type_change(self):
        cd = ConfigDiffer()
        r = cd.detect_breaking(
            {"port": 8080}, {"port": "8080"},
        )
        assert r["is_breaking"] is True
        assert any(
            b["reason"] == "type_changed"
            for b in r["breaking_changes"]
        )

    def test_detect_breaking_required_missing(self):
        cd = ConfigDiffer()
        r = cd.detect_breaking(
            {"host": "a", "port": 8080},
            {"port": 8080},
            required_keys=["host"],
        )
        assert r["is_breaking"] is True

    def test_detect_breaking_safe(self):
        cd = ConfigDiffer()
        r = cd.detect_breaking(
            {"a": 1}, {"a": 1, "b": 2},
        )
        assert r["is_breaking"] is False

    def test_diff_history(self):
        cd = ConfigDiffer()
        cd.diff({"a": 1}, {"b": 2})
        cd.diff({"c": 3}, {"d": 4})
        hist = cd.get_diff_history()
        assert len(hist) == 2

    def test_diff_count(self):
        cd = ConfigDiffer()
        cd.diff({}, {})
        cd.diff({}, {})
        assert cd.diff_count == 2


# ===================== ConfigOrchestrator =====================


class TestConfigOrchestrator:
    """ConfigOrchestrator testleri."""

    def test_init(self):
        co = ConfigOrchestrator()
        assert co.is_initialized is False
        assert co.audit_count == 0

    def test_init_custom_env(self):
        co = ConfigOrchestrator("production")
        assert co.env_mgr.current_env == "production"

    def test_initialize(self):
        co = ConfigOrchestrator()
        r = co.initialize(
            config_data={"key": "val"},
            environments=["dev", "staging", "prod"],
        )
        assert r["status"] == "initialized"
        assert r["environments"] == 3
        assert r["configs_loaded"] == 1
        assert co.is_initialized is True

    def test_initialize_defaults(self):
        co = ConfigOrchestrator()
        r = co.initialize()
        assert r["environments"] == 3

    def test_load_and_validate(self):
        co = ConfigOrchestrator()
        r = co.load_and_validate('{"host": "localhost"}')
        assert r["status"] == "loaded"
        assert r["stored"] == 1

    def test_load_and_validate_with_schema(self):
        co = ConfigOrchestrator()
        co.validator.define_schema("app", {
            "host": {"type": "string", "required": True},
        })
        r = co.load_and_validate(
            '{"host": "localhost"}', "app",
        )
        assert r["status"] == "loaded"

    def test_load_and_validate_invalid_json(self):
        co = ConfigOrchestrator()
        r = co.load_and_validate("not json")
        assert r["status"] == "error"
        assert r["reason"] == "parse_error"

    def test_load_and_validate_validation_error(self):
        co = ConfigOrchestrator()
        co.validator.define_schema("app", {
            "host": {"type": "string", "required": True},
        })
        r = co.load_and_validate('{"port": 8080}', "app")
        assert r["status"] == "error"
        assert r["reason"] == "validation_error"

    def test_promote_config(self):
        co = ConfigOrchestrator()
        co.initialize(environments=["dev", "prod"])
        co.env_mgr.set_config("dev", "key", "val")
        r = co.promote_config("key", "dev", "prod")
        assert r["status"] == "promoted"

    def test_check_feature(self):
        co = ConfigOrchestrator()
        co.flags.create_flag("feat1", enabled=True)
        assert co.check_feature("feat1") is True
        assert co.check_feature("missing") is False

    def test_manage_secret_store(self):
        co = ConfigOrchestrator()
        r = co.manage_secret("store", "key", "secret")
        assert r["name"] == "key"

    def test_manage_secret_retrieve(self):
        co = ConfigOrchestrator()
        co.vault.store("key", "secret")
        r = co.manage_secret("retrieve", "key")
        assert r["found"] is True

    def test_manage_secret_rotate(self):
        co = ConfigOrchestrator()
        co.vault.store("key", "old")
        r = co.manage_secret("rotate", "key", "new")
        assert r["status"] == "rotated"

    def test_manage_secret_unknown(self):
        co = ConfigOrchestrator()
        r = co.manage_secret("unknown", "key")
        assert r["status"] == "error"

    def test_compare_environments(self):
        co = ConfigOrchestrator()
        co.env_mgr.set_config("dev", "a", 1)
        co.env_mgr.set_config("prod", "b", 2)
        r = co.compare_environments("dev", "prod")
        assert "only_a" in r
        assert "only_b" in r

    def test_diff_configs(self):
        co = ConfigOrchestrator()
        r = co.diff_configs({"a": 1}, {"a": 2})
        assert r["has_changes"] is True

    def test_get_snapshot(self):
        co = ConfigOrchestrator()
        co.initialize(config_data={"k": "v"})
        snap = co.get_snapshot()
        assert snap["total_configs"] >= 1
        assert snap["initialized"] is True
        assert "current_env" in snap

    def test_audit_log(self):
        co = ConfigOrchestrator()
        co.initialize()
        log = co.get_audit_log()
        assert len(log) >= 1
        assert log[0]["action"] == "initialize"

    def test_audit_count(self):
        co = ConfigOrchestrator()
        co.initialize()
        co.load_and_validate('{"a": 1}')
        assert co.audit_count >= 2


# ===================== Config Settings =====================


class TestConfigSettings:
    """Config ayarlari testleri."""

    def test_config_mgmt_settings(self):
        from app.config import settings
        assert hasattr(settings, "config_mgmt_enabled")
        assert hasattr(settings, "config_cache_ttl")
        assert hasattr(settings, "secret_rotation_days")
        assert hasattr(settings, "feature_flag_default")
        assert hasattr(settings, "hot_reload_enabled")

    def test_config_mgmt_defaults(self):
        from app.config import settings
        assert settings.config_mgmt_enabled is True
        assert settings.config_cache_ttl == 300
        assert settings.secret_rotation_days == 90
        assert settings.feature_flag_default is False
        assert settings.hot_reload_enabled is True
