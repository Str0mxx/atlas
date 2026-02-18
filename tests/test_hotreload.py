"""
Hot Reload & Live Config sistem testleri.

FileWatcher, ConfigHotReloader,
TelegramConfigInterface, ValidationEngine.
"""

import os
import time

import pytest

from app.core.hotreload.config_hot_reloader import ConfigHotReloader
from app.core.hotreload.file_watcher import FileWatcher
from app.core.hotreload.telegram_config_interface import TelegramConfigInterface
from app.core.hotreload.validation_engine import ValidationEngine
from app.models.hotreload_models import (
    ChangeType,
    ConfigChange,
    ErrorMessage,
    FileEvent,
    FileEventType,
    FilterConfig,
    HistoryRecord,
    HotReloadConfig,
    PendingUpdate,
    ReloadRecord,
    ReloadResult,
    ReloadSource,
    ReloaderSummary,
    RollbackResult,
    RuleType,
    SchemaField,
    TelegramAction,
    TelegramInterfaceSummary,
    UpdateRequest,
    ValidationEngineSummary,
    ValidationError,
    ValidationErrorType,
    ValidationResult,
    ValidationRule,
    WatchEntry,
    WatcherSummary,
)


# ── FileWatcher Testleri ─────────────────────────────────────────────────────


class TestFileWatcher:
    """FileWatcher sinifi testleri."""

    def setup_method(self) -> None:
        """Her test icin taze ornek."""
        self.watcher = FileWatcher(debounce_ms=100)

    # Baslatma testleri
    def test_init_default(self) -> None:
        w = FileWatcher()
        assert w.watched_count == 0
        assert w.callback_count == 0

    def test_init_custom_debounce(self) -> None:
        w = FileWatcher(debounce_ms=200)
        summary = w.get_summary()
        assert summary["debounce_ms"] == 200

    def test_watched_count_property(self) -> None:
        assert self.watcher.watched_count == 0

    def test_callback_count_property(self) -> None:
        assert self.watcher.callback_count == 0

    # watch() testleri
    def test_watch_empty_path(self) -> None:
        result = self.watcher.watch("")
        assert result["watching"] is False
        assert "yol_gerekli" in result["error"]

    def test_watch_nonexistent_path(self) -> None:
        result = self.watcher.watch("/nonexistent/path/xyz")
        assert result["watching"] is True
        assert result["exists"] is False

    def test_watch_current_dir(self) -> None:
        result = self.watcher.watch(".")
        assert result["watching"] is True
        assert self.watcher.watched_count == 1

    def test_watch_recursive_flag(self) -> None:
        result = self.watcher.watch(".", recursive=True)
        assert result["recursive"] is True

    def test_watch_increments_count(self) -> None:
        self.watcher.watch(".")
        self.watcher.watch("app")
        assert self.watcher.watched_count == 2

    def test_watch_normalizes_path(self) -> None:
        result = self.watcher.watch("./.")
        assert result["watching"] is True

    # unwatch() testleri
    def test_unwatch_not_watched(self) -> None:
        result = self.watcher.unwatch("/not/watched")
        assert result["removed"] is False

    def test_unwatch_existing(self) -> None:
        self.watcher.watch(".")
        path = os.path.normpath(".")
        result = self.watcher.unwatch(path)
        assert result["removed"] is True

    def test_unwatch_empty_path(self) -> None:
        result = self.watcher.unwatch("")
        assert result["removed"] is False

    def test_unwatch_decrements_count(self) -> None:
        self.watcher.watch(".")
        assert self.watcher.watched_count == 1
        self.watcher.unwatch(os.path.normpath("."))
        assert self.watcher.watched_count == 0

    # add_filter() testleri
    def test_add_include_filter(self) -> None:
        result = self.watcher.add_filter("*.env", "include")
        assert result["added"] is True
        assert result["pattern"] == "*.env"

    def test_add_exclude_filter(self) -> None:
        result = self.watcher.add_filter("*.pyc", "exclude")
        assert result["added"] is True

    def test_add_filter_empty_pattern(self) -> None:
        result = self.watcher.add_filter("", "include")
        assert result["added"] is False

    def test_add_filter_invalid_type(self) -> None:
        result = self.watcher.add_filter("*.txt", "invalid")
        assert result["added"] is False

    def test_add_filter_no_duplicate(self) -> None:
        self.watcher.add_filter("*.env", "include")
        result = self.watcher.add_filter("*.env", "include")
        assert result["total"] == 1

    def test_add_multiple_filters(self) -> None:
        self.watcher.add_filter("*.env", "include")
        result = self.watcher.add_filter("*.yaml", "include")
        assert result["total"] == 2

    # remove_filter() testleri
    def test_remove_existing_filter(self) -> None:
        self.watcher.add_filter("*.env", "include")
        result = self.watcher.remove_filter("*.env", "include")
        assert result["removed"] is True

    def test_remove_nonexistent_filter(self) -> None:
        result = self.watcher.remove_filter("*.env", "include")
        assert result["removed"] is False

    def test_remove_filter_invalid_type(self) -> None:
        result = self.watcher.remove_filter("*.env", "bad")
        assert result["removed"] is False

    # register_callback() testleri
    def test_register_callback(self) -> None:
        called = []
        result = self.watcher.register_callback(lambda p, e: called.append((p, e)))
        assert result["registered"] is True
        assert self.watcher.callback_count == 1

    def test_register_none_callback(self) -> None:
        result = self.watcher.register_callback(None)
        assert result["registered"] is False

    def test_register_callback_no_duplicate(self) -> None:
        cb = lambda p, e: None
        self.watcher.register_callback(cb)
        result = self.watcher.register_callback(cb)
        assert result["total_callbacks"] == 1

    def test_unregister_callback(self) -> None:
        cb = lambda p, e: None
        self.watcher.register_callback(cb)
        result = self.watcher.unregister_callback(cb)
        assert result["unregistered"] is True
        assert self.watcher.callback_count == 0

    def test_unregister_nonregistered_callback(self) -> None:
        result = self.watcher.unregister_callback(lambda p, e: None)
        assert result["unregistered"] is False

    # emit() testleri
    def test_emit_fires_callbacks(self) -> None:
        events = []
        self.watcher.register_callback(lambda p, e: events.append((p, e)))
        self.watcher.emit("/some/file.env", "modified")
        assert len(events) == 1
        assert events[0] == ("/some/file.env", "modified")

    def test_emit_empty_path(self) -> None:
        result = self.watcher.emit("", "modified")
        assert result["emitted"] is False

    def test_emit_increments_stats(self) -> None:
        self.watcher.emit("/some/file.env", "created")
        summary = self.watcher.get_summary()
        assert summary["stats"]["events_emitted"] == 1

    def test_emit_multiple_callbacks(self) -> None:
        events1, events2 = [], []
        self.watcher.register_callback(lambda p, e: events1.append(e))
        self.watcher.register_callback(lambda p, e: events2.append(e))
        self.watcher.emit("/f", "deleted")
        assert len(events1) == 1
        assert len(events2) == 1

    # poll() testleri
    def test_poll_no_watched(self) -> None:
        result = self.watcher.poll()
        assert result["polled"] is True
        assert result["change_count"] == 0

    def test_poll_increments_stat(self) -> None:
        self.watcher.poll()
        summary = self.watcher.get_summary()
        assert summary["stats"]["polls_run"] == 1

    # get_watched_list() testleri
    def test_get_watched_list_empty(self) -> None:
        result = self.watcher.get_watched_list()
        assert result["retrieved"] is True
        assert result["count"] == 0

    def test_get_watched_list_with_entry(self) -> None:
        self.watcher.watch(".")
        result = self.watcher.get_watched_list()
        assert result["count"] == 1

    # get_summary() testleri
    def test_get_summary(self) -> None:
        result = self.watcher.get_summary()
        assert result["retrieved"] is True
        assert "watched_count" in result
        assert "callback_count" in result
        assert "stats" in result

    def test_summary_debounce(self) -> None:
        w = FileWatcher(debounce_ms=750)
        s = w.get_summary()
        assert s["debounce_ms"] == 750

    # Filter logic testleri
    def test_passes_filter_include(self) -> None:
        self.watcher.add_filter("*.env", "include")
        assert self.watcher._passes_filters(".env") is True
        assert self.watcher._passes_filters("test.py") is False

    def test_passes_filter_exclude(self) -> None:
        self.watcher.add_filter("*.pyc", "exclude")
        assert self.watcher._passes_filters("test.pyc") is False
        assert self.watcher._passes_filters("test.py") is True

    def test_passes_filter_no_filters(self) -> None:
        assert self.watcher._passes_filters("anything.txt") is True


# ── ConfigHotReloader Testleri ───────────────────────────────────────────────


class TestConfigHotReloader:
    """ConfigHotReloader sinifi testleri."""

    def setup_method(self) -> None:
        """Her test icin taze ornek."""
        self.reloader = ConfigHotReloader()
        self._base_config = {
            "debug": False,
            "log_level": "INFO",
            "max_workers": 4,
            "api_timeout": 30,
        }

    # Baslatma testleri
    def test_init(self) -> None:
        r = ConfigHotReloader()
        assert r.reload_count == 0
        assert r.has_previous is False

    def test_reload_count_property(self) -> None:
        assert self.reloader.reload_count == 0

    def test_has_previous_property(self) -> None:
        assert self.reloader.has_previous is False

    # load_initial() testleri
    def test_load_initial_success(self) -> None:
        result = self.reloader.load_initial(self._base_config)
        assert result["loaded"] is True
        assert result["key_count"] == 4

    def test_load_initial_none(self) -> None:
        result = self.reloader.load_initial(None)
        assert result["loaded"] is False

    def test_load_initial_empty(self) -> None:
        result = self.reloader.load_initial({})
        assert result["loaded"] is True
        assert result["key_count"] == 0

    # reload() testleri
    def test_reload_with_changes(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["log_level"] = "DEBUG"
        result = self.reloader.reload(new_cfg, source="file")
        assert result["reloaded"] is True
        assert result["changed"] is True
        assert len(result["changes"]) == 1

    def test_reload_no_changes(self) -> None:
        self.reloader.load_initial(self._base_config)
        result = self.reloader.reload(dict(self._base_config))
        assert result["reloaded"] is True
        assert result["changed"] is False

    def test_reload_none_config(self) -> None:
        result = self.reloader.reload(None)
        assert result["reloaded"] is False

    def test_reload_increments_count(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["debug"] = True
        self.reloader.reload(new_cfg)
        assert self.reloader.reload_count == 1

    def test_reload_sets_has_previous(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["debug"] = True
        self.reloader.reload(new_cfg)
        assert self.reloader.has_previous is True

    def test_reload_detects_add(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["new_key"] = "value"
        result = self.reloader.reload(new_cfg)
        changes = result["changes"]
        add_changes = [c for c in changes if c["type"] == "add"]
        assert len(add_changes) == 1

    def test_reload_detects_remove(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = {k: v for k, v in self._base_config.items() if k != "debug"}
        result = self.reloader.reload(new_cfg)
        changes = result["changes"]
        remove_changes = [c for c in changes if c["type"] == "remove"]
        assert len(remove_changes) == 1

    def test_reload_notifies_listeners(self) -> None:
        notified = []
        self.reloader.add_listener(lambda c, s: notified.append(s))
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["debug"] = True
        self.reloader.reload(new_cfg, source="api")
        assert "api" in notified

    # apply_change() testleri
    def test_apply_change_success(self) -> None:
        self.reloader.load_initial(self._base_config)
        result = self.reloader.apply_change("log_level", "DEBUG")
        assert result["applied"] is True
        assert result["new_value"] == "DEBUG"

    def test_apply_change_empty_key(self) -> None:
        result = self.reloader.apply_change("", "value")
        assert result["applied"] is False

    def test_apply_change_updates_value(self) -> None:
        self.reloader.load_initial(self._base_config)
        self.reloader.apply_change("max_workers", 8)
        val = self.reloader.get_value("max_workers")
        assert val["value"] == 8

    # rollback() testleri
    def test_rollback_no_previous(self) -> None:
        result = self.reloader.rollback()
        assert result["rolled_back"] is False

    def test_rollback_after_reload(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["debug"] = True
        self.reloader.reload(new_cfg)
        result = self.reloader.rollback()
        assert result["rolled_back"] is True

    def test_rollback_restores_value(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["log_level"] = "DEBUG"
        self.reloader.reload(new_cfg)
        self.reloader.rollback()
        val = self.reloader.get_value("log_level")
        assert val["value"] == "INFO"

    def test_rollback_increments_stat(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["debug"] = True
        self.reloader.reload(new_cfg)
        self.reloader.rollback()
        summary = self.reloader.get_summary()
        assert summary["stats"]["rollbacks_performed"] == 1

    # get_value() testleri
    def test_get_value_found(self) -> None:
        self.reloader.load_initial(self._base_config)
        result = self.reloader.get_value("log_level")
        assert result["found"] is True
        assert result["value"] == "INFO"

    def test_get_value_not_found(self) -> None:
        self.reloader.load_initial(self._base_config)
        result = self.reloader.get_value("nonexistent")
        assert result["found"] is False

    def test_get_value_empty_key(self) -> None:
        result = self.reloader.get_value("")
        assert result["found"] is False

    # get_all() testleri
    def test_get_all(self) -> None:
        self.reloader.load_initial(self._base_config)
        result = self.reloader.get_all()
        assert result["retrieved"] is True
        assert result["key_count"] == 4

    # add/remove listener testleri
    def test_add_listener(self) -> None:
        result = self.reloader.add_listener(lambda c, s: None)
        assert result["added"] is True

    def test_add_none_listener(self) -> None:
        result = self.reloader.add_listener(None)
        assert result["added"] is False

    def test_remove_listener(self) -> None:
        cb = lambda c, s: None
        self.reloader.add_listener(cb)
        result = self.reloader.remove_listener(cb)
        assert result["removed"] is True

    def test_remove_nonregistered_listener(self) -> None:
        result = self.reloader.remove_listener(lambda c, s: None)
        assert result["removed"] is False

    # get_history() testleri
    def test_get_history_empty(self) -> None:
        result = self.reloader.get_history()
        assert result["retrieved"] is True
        assert result["total"] == 0

    def test_get_history_after_reload(self) -> None:
        self.reloader.load_initial(self._base_config)
        new_cfg = dict(self._base_config)
        new_cfg["debug"] = True
        self.reloader.reload(new_cfg)
        result = self.reloader.get_history()
        assert result["total"] >= 1

    def test_get_history_limit(self) -> None:
        self.reloader.load_initial(self._base_config)
        for i in range(5):
            cfg = dict(self._base_config)
            cfg["max_workers"] = i + 1
            self.reloader.reload(cfg)
        result = self.reloader.get_history(limit=3)
        assert result["returned"] <= 3

    # get_diff() testleri
    def test_get_diff_with_changes(self) -> None:
        self.reloader.load_initial(self._base_config)
        other = dict(self._base_config)
        other["log_level"] = "WARNING"
        result = self.reloader.get_diff(other)
        assert result["compared"] is True
        assert result["has_changes"] is True

    def test_get_diff_no_changes(self) -> None:
        self.reloader.load_initial(self._base_config)
        result = self.reloader.get_diff(dict(self._base_config))
        assert result["has_changes"] is False

    def test_get_diff_none(self) -> None:
        result = self.reloader.get_diff(None)
        assert result["compared"] is False

    # get_summary() testleri
    def test_get_summary(self) -> None:
        result = self.reloader.get_summary()
        assert result["retrieved"] is True
        assert "key_count" in result
        assert "stats" in result


# ── TelegramConfigInterface Testleri ────────────────────────────────────────


class TestTelegramConfigInterface:
    """TelegramConfigInterface sinifi testleri."""

    def setup_method(self) -> None:
        """Her test icin taze ornek."""
        self.iface = TelegramConfigInterface()
        self._config = {
            "log_level": "INFO",
            "debug": False,
            "max_workers": 4,
            "api_key": "secret-key-123",
            "hotreload_enabled": True,
        }
        self.iface.load_config(self._config)
        self._chat = "chat_123"

    # Baslatma testleri
    def test_init(self) -> None:
        iface = TelegramConfigInterface()
        assert iface.pending_count == 0
        assert iface.history_count == 0

    def test_pending_count_property(self) -> None:
        assert self.iface.pending_count == 0

    def test_history_count_property(self) -> None:
        assert self.iface.history_count == 0

    # load_config() testleri
    def test_load_config_success(self) -> None:
        result = self.iface.load_config({"key": "val"})
        assert result["loaded"] is True
        assert result["key_count"] == 1

    def test_load_config_none(self) -> None:
        result = self.iface.load_config(None)
        assert result["loaded"] is False

    # handle_config_command() testleri
    def test_command_no_chat_id(self) -> None:
        result = self.iface.handle_config_command("", ["list"])
        assert result["handled"] is False

    def test_command_list(self) -> None:
        result = self.iface.handle_config_command(self._chat, ["list"])
        assert result["handled"] is True or "displayed" in result

    def test_command_get_known_key(self) -> None:
        result = self.iface.handle_config_command(
            self._chat, ["get", "log_level"]
        )
        assert result["handled"] is True

    def test_command_get_unknown_key(self) -> None:
        result = self.iface.handle_config_command(
            self._chat, ["get", "unknown_key"]
        )
        assert result["handled"] is True

    def test_command_set(self) -> None:
        result = self.iface.handle_config_command(
            self._chat, ["set", "log_level", "DEBUG"]
        )
        assert result["handled"] is True

    def test_command_history(self) -> None:
        result = self.iface.handle_config_command(self._chat, ["history"])
        assert result["handled"] is True

    def test_command_help(self) -> None:
        result = self.iface.handle_config_command(self._chat, ["help"])
        assert result["handled"] is True
        assert "ATLAS" in result.get("message", "")

    def test_command_no_args(self) -> None:
        result = self.iface.handle_config_command(self._chat, [])
        assert result["handled"] is True

    # display_settings() testleri
    def test_display_settings_no_chat(self) -> None:
        result = self.iface.display_settings("")
        assert result["displayed"] is False

    def test_display_settings_success(self) -> None:
        result = self.iface.display_settings(self._chat)
        assert result["displayed"] is True
        assert result["entry_count"] > 0

    def test_display_settings_masks_api_key(self) -> None:
        result = self.iface.display_settings(self._chat)
        assert result["displayed"] is True
        msg = result.get("message", "")
        assert "secret-key-123" not in msg

    def test_display_settings_with_filter(self) -> None:
        result = self.iface.display_settings(self._chat, filter_prefix="hot")
        assert result["displayed"] is True
        assert result["entry_count"] == 1

    # request_update() testleri
    def test_request_update_success(self) -> None:
        result = self.iface.request_update(self._chat, "log_level", "DEBUG")
        assert result["requested"] is True
        assert "request_id" in result

    def test_request_update_no_chat(self) -> None:
        result = self.iface.request_update("", "log_level", "DEBUG")
        assert result["requested"] is False

    def test_request_update_no_key(self) -> None:
        result = self.iface.request_update(self._chat, "", "DEBUG")
        assert result["requested"] is False

    def test_request_update_unknown_key(self) -> None:
        result = self.iface.request_update(self._chat, "no_such_key", "val")
        assert result["requested"] is False

    def test_request_update_increments_pending(self) -> None:
        self.iface.request_update(self._chat, "log_level", "DEBUG")
        assert self.iface.pending_count == 1

    def test_request_update_message_contains_key(self) -> None:
        result = self.iface.request_update(self._chat, "log_level", "DEBUG")
        assert "log_level" in result.get("message", "")

    # confirm_update() testleri
    def test_confirm_update_success(self) -> None:
        req = self.iface.request_update(self._chat, "log_level", "DEBUG")
        req_id = req["request_id"]
        result = self.iface.confirm_update(req_id)
        assert result["confirmed"] is True
        assert result["new_value"] == "DEBUG"

    def test_confirm_update_no_id(self) -> None:
        result = self.iface.confirm_update("")
        assert result["confirmed"] is False

    def test_confirm_update_nonexistent(self) -> None:
        result = self.iface.confirm_update("nonexistent_id")
        assert result["confirmed"] is False

    def test_confirm_decrements_pending(self) -> None:
        req = self.iface.request_update(self._chat, "log_level", "DEBUG")
        self.iface.confirm_update(req["request_id"])
        assert self.iface.pending_count == 0

    def test_confirm_adds_to_history(self) -> None:
        req = self.iface.request_update(self._chat, "log_level", "DEBUG")
        self.iface.confirm_update(req["request_id"])
        assert self.iface.history_count == 1

    def test_confirm_bool_conversion(self) -> None:
        req = self.iface.request_update(self._chat, "debug", "true")
        result = self.iface.confirm_update(req["request_id"])
        assert result["confirmed"] is True
        assert result["new_value"] is True

    def test_confirm_int_conversion(self) -> None:
        req = self.iface.request_update(self._chat, "max_workers", "8")
        result = self.iface.confirm_update(req["request_id"])
        assert result["confirmed"] is True
        assert result["new_value"] == 8

    # cancel_update() testleri
    def test_cancel_update_success(self) -> None:
        req = self.iface.request_update(self._chat, "log_level", "DEBUG")
        result = self.iface.cancel_update(req["request_id"])
        assert result["cancelled"] is True

    def test_cancel_update_no_id(self) -> None:
        result = self.iface.cancel_update("")
        assert result["cancelled"] is False

    def test_cancel_nonexistent(self) -> None:
        result = self.iface.cancel_update("no_such_id")
        assert result["cancelled"] is False

    def test_cancel_decrements_pending(self) -> None:
        req = self.iface.request_update(self._chat, "log_level", "DEBUG")
        self.iface.cancel_update(req["request_id"])
        assert self.iface.pending_count == 0

    # get_history() testleri
    def test_get_history_empty(self) -> None:
        result = self.iface.get_history()
        assert result["retrieved"] is True
        assert result["total"] == 0

    def test_get_history_after_confirm(self) -> None:
        req = self.iface.request_update(self._chat, "log_level", "DEBUG")
        self.iface.confirm_update(req["request_id"])
        result = self.iface.get_history()
        assert result["total"] == 1

    def test_get_history_limit(self) -> None:
        for _ in range(3):
            req = self.iface.request_update(self._chat, "log_level", "DEBUG")
            self.iface.confirm_update(req["request_id"])
        result = self.iface.get_history(limit=2)
        assert result["returned"] <= 2

    def test_get_history_by_chat(self) -> None:
        req = self.iface.request_update("other_chat", "log_level", "DEBUG")
        # other_chat icin onay - mevcut config'e gore
        self.iface.confirm_update(req["request_id"])
        result = self.iface.get_history(chat_id=self._chat)
        assert result["total"] == 0

    # mask_key() testleri
    def test_mask_key(self) -> None:
        result = self.iface.mask_key("my_secret")
        assert result["masked"] is True

    def test_mask_key_empty(self) -> None:
        result = self.iface.mask_key("")
        assert result["masked"] is False

    # get_summary() testleri
    def test_get_summary(self) -> None:
        result = self.iface.get_summary()
        assert result["retrieved"] is True
        assert "config_keys" in result
        assert "pending_count" in result
        assert "stats" in result


# ── ValidationEngine Testleri ────────────────────────────────────────────────


class TestValidationEngine:
    """ValidationEngine sinifi testleri."""

    def setup_method(self) -> None:
        """Her test icin taze ornek."""
        self.engine = ValidationEngine()

    # Baslatma testleri
    def test_init(self) -> None:
        e = ValidationEngine()
        assert e.schema_count == 0
        assert e.rule_count == 0

    def test_schema_count_property(self) -> None:
        assert self.engine.schema_count == 0

    def test_rule_count_property(self) -> None:
        assert self.engine.rule_count == 0

    # register_schema() testleri
    def test_register_schema_success(self) -> None:
        result = self.engine.register_schema(
            "log_level", {"type": "str", "required": True}
        )
        assert result["registered"] is True
        assert self.engine.schema_count == 1

    def test_register_schema_empty_key(self) -> None:
        result = self.engine.register_schema("", {"type": "str"})
        assert result["registered"] is False

    def test_register_schema_invalid_type(self) -> None:
        result = self.engine.register_schema("key", {"type": "unknowntype"})
        assert result["registered"] is False

    def test_register_schema_no_type(self) -> None:
        result = self.engine.register_schema("key", {})
        assert result["registered"] is True

    def test_register_multiple_schemas(self) -> None:
        self.engine.register_schema("a", {"type": "str"})
        self.engine.register_schema("b", {"type": "int"})
        assert self.engine.schema_count == 2

    def test_register_schema_all_types(self) -> None:
        for t in ["str", "int", "float", "bool", "list", "dict"]:
            result = self.engine.register_schema(f"key_{t}", {"type": t})
            assert result["registered"] is True

    # register_rule() testleri
    def test_register_rule_success(self) -> None:
        result = self.engine.register_rule(
            "dep_rule", "Bagimlilik", ["a", "b"], "dependency"
        )
        assert result["registered"] is True
        assert self.engine.rule_count == 1

    def test_register_rule_empty_name(self) -> None:
        result = self.engine.register_rule("")
        assert result["registered"] is False

    def test_register_rule_default_type(self) -> None:
        result = self.engine.register_rule("rule1", "desc", ["x"])
        assert result["registered"] is True
        assert result["type"] == "dependency"

    # validate_value() testleri
    def test_validate_value_str_ok(self) -> None:
        self.engine.register_schema("name", {"type": "str"})
        result = self.engine.validate_value("name", "hello")
        assert result["valid"] is True

    def test_validate_value_str_wrong_type(self) -> None:
        self.engine.register_schema("name", {"type": "str"})
        result = self.engine.validate_value("name", 123)
        assert result["valid"] is False

    def test_validate_value_int_ok(self) -> None:
        self.engine.register_schema("count", {"type": "int"})
        result = self.engine.validate_value("count", 42)
        assert result["valid"] is True

    def test_validate_value_bool_not_int(self) -> None:
        self.engine.register_schema("count", {"type": "int"})
        result = self.engine.validate_value("count", True)
        assert result["valid"] is False

    def test_validate_value_float_ok(self) -> None:
        self.engine.register_schema("rate", {"type": "float"})
        result = self.engine.validate_value("rate", 3.14)
        assert result["valid"] is True

    def test_validate_value_bool_ok(self) -> None:
        self.engine.register_schema("flag", {"type": "bool"})
        result = self.engine.validate_value("flag", True)
        assert result["valid"] is True

    def test_validate_value_list_ok(self) -> None:
        self.engine.register_schema("items", {"type": "list"})
        result = self.engine.validate_value("items", [1, 2, 3])
        assert result["valid"] is True

    def test_validate_value_dict_ok(self) -> None:
        self.engine.register_schema("cfg", {"type": "dict"})
        result = self.engine.validate_value("cfg", {"a": 1})
        assert result["valid"] is True

    def test_validate_value_min_ok(self) -> None:
        self.engine.register_schema("port", {"type": "int", "min": 1024})
        result = self.engine.validate_value("port", 8080)
        assert result["valid"] is True

    def test_validate_value_below_min(self) -> None:
        self.engine.register_schema("port", {"type": "int", "min": 1024})
        result = self.engine.validate_value("port", 80)
        assert result["valid"] is False

    def test_validate_value_max_ok(self) -> None:
        self.engine.register_schema("workers", {"type": "int", "max": 32})
        result = self.engine.validate_value("workers", 8)
        assert result["valid"] is True

    def test_validate_value_above_max(self) -> None:
        self.engine.register_schema("workers", {"type": "int", "max": 32})
        result = self.engine.validate_value("workers", 100)
        assert result["valid"] is False

    def test_validate_value_allowed_ok(self) -> None:
        self.engine.register_schema(
            "level", {"type": "str", "allowed": ["DEBUG", "INFO", "ERROR"]}
        )
        result = self.engine.validate_value("level", "INFO")
        assert result["valid"] is True

    def test_validate_value_not_allowed(self) -> None:
        self.engine.register_schema(
            "level", {"type": "str", "allowed": ["DEBUG", "INFO", "ERROR"]}
        )
        result = self.engine.validate_value("level", "VERBOSE")
        assert result["valid"] is False

    def test_validate_value_empty_key(self) -> None:
        result = self.engine.validate_value("", "val")
        assert result["valid"] is False

    def test_validate_value_no_schema(self) -> None:
        result = self.engine.validate_value("unknown", "val")
        assert result["valid"] is True

    # validate_config() testleri
    def test_validate_config_success(self) -> None:
        self.engine.register_schema("level", {"type": "str"})
        self.engine.register_schema("count", {"type": "int"})
        result = self.engine.validate_config({"level": "INFO", "count": 5})
        assert result["valid"] is True

    def test_validate_config_missing_required(self) -> None:
        self.engine.register_schema("level", {"type": "str", "required": True})
        result = self.engine.validate_config({"count": 5})
        assert result["valid"] is False
        assert result["error_count"] > 0

    def test_validate_config_none(self) -> None:
        result = self.engine.validate_config(None)
        assert result["valid"] is False

    def test_validate_config_empty(self) -> None:
        result = self.engine.validate_config({})
        assert result["valid"] is True

    def test_validate_config_multiple_errors(self) -> None:
        self.engine.register_schema("a", {"type": "str"})
        self.engine.register_schema("b", {"type": "int"})
        result = self.engine.validate_config({"a": 1, "b": "wrong"})
        assert result["error_count"] >= 2

    # check_type() testleri
    def test_check_type_str_ok(self) -> None:
        result = self.engine.check_type("k", "hello", "str")
        assert result["valid"] is True

    def test_check_type_int_wrong(self) -> None:
        result = self.engine.check_type("k", "not_int", "int")
        assert result["valid"] is False

    def test_check_type_no_type(self) -> None:
        result = self.engine.check_type("k", "val", "")
        assert result["valid"] is False

    def test_check_type_unknown_type(self) -> None:
        result = self.engine.check_type("k", "val", "set")
        assert result["valid"] is False

    # check_range() testleri
    def test_check_range_in_range(self) -> None:
        result = self.engine.check_range("port", 8080, min_val=1024, max_val=65535)
        assert result["valid"] is True

    def test_check_range_below_min(self) -> None:
        result = self.engine.check_range("port", 80, min_val=1024)
        assert result["valid"] is False

    def test_check_range_above_max(self) -> None:
        result = self.engine.check_range("port", 70000, max_val=65535)
        assert result["valid"] is False

    def test_check_range_non_numeric(self) -> None:
        result = self.engine.check_range("key", "string", min_val=0)
        assert result["valid"] is False

    def test_check_range_no_bounds(self) -> None:
        result = self.engine.check_range("key", 42)
        assert result["valid"] is True

    # check_dependency() testleri
    def test_check_dependency_condition_not_met(self) -> None:
        result = self.engine.check_dependency(
            {"debug": False}, "debug", True, "debug_host"
        )
        assert result["valid"] is True
        assert result["condition_met"] is False

    def test_check_dependency_condition_met_dep_present(self) -> None:
        result = self.engine.check_dependency(
            {"debug": True, "debug_host": "localhost"},
            "debug", True, "debug_host"
        )
        assert result["valid"] is True
        assert result["condition_met"] is True

    def test_check_dependency_condition_met_dep_missing(self) -> None:
        result = self.engine.check_dependency(
            {"debug": True}, "debug", True, "debug_host"
        )
        assert result["valid"] is False

    def test_check_dependency_none_config(self) -> None:
        result = self.engine.check_dependency(None, "a", True, "b")
        assert result["valid"] is False

    def test_check_dependency_empty_keys(self) -> None:
        result = self.engine.check_dependency({}, "", True, "")
        assert result["valid"] is False

    # get_error_messages() testleri
    def test_get_error_messages_empty(self) -> None:
        result = self.engine.get_error_messages([])
        assert result["retrieved"] is True
        assert result["count"] == 0

    def test_get_error_messages_with_errors(self) -> None:
        errors = [{"key": "port", "error": "minimum_altinda", "message": "Port cok kucuk"}]
        result = self.engine.get_error_messages(errors)
        assert result["count"] == 1

    def test_get_error_messages_en_lang(self) -> None:
        errors = [{"key": "k", "error": "yanlis_tip", "message": "yanlis_tip"}]
        result = self.engine.get_error_messages(errors, lang="en")
        assert result["lang"] == "en"

    def test_get_error_messages_no_arg_uses_last(self) -> None:
        self.engine.register_schema("x", {"type": "str", "required": True})
        self.engine.validate_config({})
        result = self.engine.get_error_messages()
        assert result["retrieved"] is True

    # get_summary() testleri
    def test_get_summary(self) -> None:
        result = self.engine.get_summary()
        assert result["retrieved"] is True
        assert "schema_count" in result
        assert "rule_count" in result
        assert "stats" in result

    def test_summary_increments_on_validation(self) -> None:
        self.engine.register_schema("k", {"type": "str"})
        self.engine.validate_value("k", "hello")
        summary = self.engine.get_summary()
        assert summary["stats"]["validations_run"] > 0


# ── Model Testleri ────────────────────────────────────────────────────────────


class TestHotReloadModels:
    """Pydantic model testleri."""

    def test_file_event_type_enum(self) -> None:
        assert FileEventType.CREATED == "created"
        assert FileEventType.MODIFIED == "modified"
        assert FileEventType.DELETED == "deleted"
        assert FileEventType.MOVED == "moved"

    def test_reload_source_enum(self) -> None:
        assert ReloadSource.FILE == "file"
        assert ReloadSource.API == "api"
        assert ReloadSource.TELEGRAM == "telegram"
        assert ReloadSource.MANUAL == "manual"
        assert ReloadSource.ROLLBACK == "rollback"

    def test_change_type_enum(self) -> None:
        assert ChangeType.ADD == "add"
        assert ChangeType.UPDATE == "update"
        assert ChangeType.REMOVE == "remove"

    def test_validation_error_type_enum(self) -> None:
        assert ValidationErrorType.WRONG_TYPE == "yanlis_tip"
        assert ValidationErrorType.REQUIRED_MISSING == "zorunlu_alan_eksik"
        assert ValidationErrorType.BELOW_MINIMUM == "minimum_altinda"

    def test_rule_type_enum(self) -> None:
        assert RuleType.DEPENDENCY == "dependency"
        assert RuleType.CONFLICT == "conflict"
        assert RuleType.REQUIRED_IF == "required_if"

    def test_telegram_action_enum(self) -> None:
        assert TelegramAction.CONFIRMED == "confirmed"
        assert TelegramAction.CANCELLED == "cancelled"
        assert TelegramAction.PENDING == "pending"

    def test_watch_entry_model(self) -> None:
        entry = WatchEntry(path="/some/path")
        assert entry.path == "/some/path"
        assert entry.recursive is False
        assert entry.exists is True

    def test_file_event_model(self) -> None:
        event = FileEvent(
            path="/file.env",
            event=FileEventType.MODIFIED,
            timestamp=1234567890.0,
        )
        assert event.path == "/file.env"
        assert event.event == FileEventType.MODIFIED

    def test_filter_config_model(self) -> None:
        fc = FilterConfig(include=["*.env"], exclude=["*.pyc"])
        assert len(fc.include) == 1
        assert len(fc.exclude) == 1

    def test_watcher_summary_model(self) -> None:
        ws = WatcherSummary(
            watched_count=3,
            callback_count=2,
            include_filters=1,
            exclude_filters=0,
            debounce_ms=500,
        )
        assert ws.watched_count == 3
        assert ws.debounce_ms == 500

    def test_config_change_model(self) -> None:
        change = ConfigChange(
            key="log_level", old="INFO", new="DEBUG",
            type=ChangeType.UPDATE
        )
        assert change.key == "log_level"
        assert change.type == ChangeType.UPDATE

    def test_reload_record_model(self) -> None:
        record = ReloadRecord(
            timestamp=time.time(),
            source="file",
            key_count=10,
        )
        assert record.key_count == 10

    def test_reload_result_model(self) -> None:
        result = ReloadResult(reloaded=True, changed=True)
        assert result.reloaded is True
        assert result.changed is True
        assert result.error is None

    def test_rollback_result_model(self) -> None:
        r = RollbackResult(rolled_back=True, changes_reverted=3)
        assert r.rolled_back is True
        assert r.changes_reverted == 3

    def test_reloader_summary_model(self) -> None:
        s = ReloaderSummary(
            key_count=5,
            has_previous=True,
            reload_count=2,
            history_count=3,
            listener_count=1,
        )
        assert s.has_previous is True

    def test_pending_update_model(self) -> None:
        p = PendingUpdate(
            chat_id="123",
            key="level",
            new_value="DEBUG",
            requested_at=time.time(),
        )
        assert p.key == "level"

    def test_update_request_model(self) -> None:
        ur = UpdateRequest(requested=True, request_id="r1", key="k")
        assert ur.requested is True

    def test_history_record_model(self) -> None:
        hr = HistoryRecord(
            key="level",
            old_value="INFO",
            new_value="DEBUG",
            timestamp=time.time(),
            action="confirmed",
        )
        assert hr.action == "confirmed"

    def test_telegram_interface_summary_model(self) -> None:
        s = TelegramInterfaceSummary(
            config_keys=10,
            pending_count=0,
            history_count=5,
            masked_keys=2,
        )
        assert s.masked_keys == 2

    def test_schema_field_model(self) -> None:
        sf = SchemaField(type="int", required=True, min=0.0, max=100.0)
        assert sf.type == "int"
        assert sf.required is True

    def test_validation_error_model(self) -> None:
        ve = ValidationError(
            key="port",
            error="minimum_altinda",
            message="Port cok kucuk",
        )
        assert ve.severity == "error"

    def test_validation_result_model(self) -> None:
        vr = ValidationResult(valid=False, error_count=2, checked_keys=5)
        assert vr.valid is False
        assert vr.error_count == 2

    def test_validation_rule_model(self) -> None:
        vr = ValidationRule(
            name="dep_rule",
            keys=["a", "b"],
            type=RuleType.DEPENDENCY,
        )
        assert len(vr.keys) == 2

    def test_error_message_model(self) -> None:
        em = ErrorMessage(key="k", message="Hata", severity="warning")
        assert em.severity == "warning"

    def test_validation_engine_summary_model(self) -> None:
        ves = ValidationEngineSummary(
            schema_count=5,
            rule_count=2,
            last_error_count=0,
        )
        assert ves.schema_count == 5

    def test_hot_reload_config_model(self) -> None:
        hrc = HotReloadConfig(enabled=True, watch_interval_ms=500)
        assert hrc.enabled is True
        assert hrc.watch_interval_ms == 500
        assert hrc.auto_validate is True

    def test_hot_reload_config_defaults(self) -> None:
        hrc = HotReloadConfig()
        assert hrc.enabled is True
        assert hrc.telegram_config is True
        assert hrc.watch_interval_ms == 1000


# ── Config Testleri ──────────────────────────────────────────────────────────


class TestHotReloadConfig:
    """Config.py hotreload ayarlari testleri."""

    def test_hotreload_enabled_default(self) -> None:
        from app.config import settings
        assert hasattr(settings, "hotreload_enabled")
        assert isinstance(settings.hotreload_enabled, bool)

    def test_watch_interval_ms_default(self) -> None:
        from app.config import settings
        assert hasattr(settings, "watch_interval_ms")
        assert settings.watch_interval_ms >= 100

    def test_telegram_config_default(self) -> None:
        from app.config import settings
        assert hasattr(settings, "telegram_config")
        assert isinstance(settings.telegram_config, bool)

    def test_auto_validate_default(self) -> None:
        from app.config import settings
        assert hasattr(settings, "auto_validate")
        assert isinstance(settings.auto_validate, bool)
