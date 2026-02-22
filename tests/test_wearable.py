"""Wearable Companion test modulu.

Apple Watch / akilli saat / giyilebilir cihaz
eslik sistemi testleri.
"""

import pytest
import time

from app.models.wearable_models import (
    APNsPayload,
    CommandSurface,
    NotificationPriority,
    WatchInboxItem,
    WearableConfig,
    WearableDevice,
    WearableType,
)

from app.core.wearable.watch_companion import WatchCompanion
from app.core.wearable.apns_manager import APNsManager
from app.core.wearable.notification_relay import NotificationRelay
from app.core.wearable.command_surface import WearableCommandSurface


class TestWearableModels:
    """Wearable model testleri."""

    def test_wearable_type_values(self) -> None:
        assert WearableType.APPLE_WATCH == "apple_watch"
        assert WearableType.ANDROID_WEAR == "android_wear"
        assert WearableType.FITBIT == "fitbit"
        assert WearableType.GENERIC == "generic"

    def test_notification_priority_values(self) -> None:
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.NORMAL == "normal"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.CRITICAL == "critical"

    def test_wearable_device_defaults(self) -> None:
        device = WearableDevice()
        assert device.device_id == ""
        assert device.device_type == WearableType.GENERIC
        assert device.is_connected is False
        assert device.capabilities == []

    def test_watch_inbox_item_defaults(self) -> None:
        item = WatchInboxItem()
        assert item.item_id == ""
        assert item.is_read is False
        assert item.priority == NotificationPriority.NORMAL

    def test_apns_payload_defaults(self) -> None:
        payload = APNsPayload()
        assert payload.sound == "default"
        assert payload.is_silent is False
        assert payload.expiry == 3600

    def test_command_surface_defaults(self) -> None:
        surface = CommandSurface()
        assert surface.status == "pending"
        assert surface.result == {}

    def test_wearable_config_defaults(self) -> None:
        config = WearableConfig()
        assert config.apns_use_sandbox is True
        assert config.max_inbox_items == 100
        assert config.notification_ttl == 86400
        assert config.auto_reconnect is True

class TestWatchCompanion:
    """Akilli saat eslik testleri."""

    def test_register_device(self) -> None:
        wc = WatchCompanion()
        device = wc.register_device("d1", WearableType.APPLE_WATCH, "My Watch")
        assert device.device_id == "d1"
        assert device.device_type == WearableType.APPLE_WATCH
        assert device.is_connected is True

    def test_unregister_device(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        assert wc.unregister_device("d1") is True

    def test_unregister_nonexistent(self) -> None:
        wc = WatchCompanion()
        assert wc.unregister_device("nonexistent") is False

    def test_get_device(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        device = wc.get_device("d1")
        assert device is not None
        assert device.device_id == "d1"

    def test_get_device_nonexistent(self) -> None:
        wc = WatchCompanion()
        assert wc.get_device("nonexistent") is None

    def test_list_devices(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        wc.register_device("d2")
        assert len(wc.list_devices()) == 2

    def test_add_inbox_item(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        item = wc.add_inbox_item("d1", "Test", "Body")
        assert item is not None
        assert item.title == "Test"
        assert item.is_read is False

    def test_add_inbox_item_nonexistent_device(self) -> None:
        wc = WatchCompanion()
        assert wc.add_inbox_item("nonexistent", "T", "B") is None

    def test_get_inbox(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        wc.add_inbox_item("d1", "T1", "B1")
        wc.add_inbox_item("d1", "T2", "B2")
        inbox = wc.get_inbox("d1")
        assert len(inbox) == 2

    def test_get_inbox_unread_only(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        item = wc.add_inbox_item("d1", "T1", "B1")
        wc.add_inbox_item("d1", "T2", "B2")
        wc.mark_read("d1", item.item_id)
        unread = wc.get_inbox("d1", unread_only=True)
        assert len(unread) == 1

    def test_mark_read(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        item = wc.add_inbox_item("d1", "T", "B")
        assert wc.mark_read("d1", item.item_id) is True

    def test_mark_read_nonexistent(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        assert wc.mark_read("d1", "nonexistent") is False

    def test_clear_inbox(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        wc.add_inbox_item("d1", "T1", "B1")
        wc.add_inbox_item("d1", "T2", "B2")
        count = wc.clear_inbox("d1")
        assert count == 2
        assert len(wc.get_inbox("d1")) == 0

    def test_max_inbox_items(self) -> None:
        config = WearableConfig(max_inbox_items=2)
        wc = WatchCompanion(config=config)
        wc.register_device("d1")
        wc.add_inbox_item("d1", "T1", "B1")
        wc.add_inbox_item("d1", "T2", "B2")
        wc.add_inbox_item("d1", "T3", "B3")
        assert len(wc.get_inbox("d1")) == 2

    def test_get_stats(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        stats = wc.get_stats()
        assert stats["total_devices"] == 1
        assert stats["connected_devices"] == 1

    def test_get_history(self) -> None:
        wc = WatchCompanion()
        wc.register_device("d1")
        assert len(wc.get_history()) >= 1

class TestAPNsManager:
    """APNs yonetimi testleri."""

    def test_register_token(self) -> None:
        mgr = APNsManager()
        assert mgr.register_token("d1", "abcdef1234567890") is True

    def test_register_invalid_token(self) -> None:
        mgr = APNsManager()
        assert mgr.register_token("d1", "short") is False

    def test_send_notification(self) -> None:
        mgr = APNsManager()
        mgr.register_token("d1", "abcdef1234567890")
        nid = mgr.send_notification("d1", "Test", "Body")
        assert nid is not None

    def test_send_notification_no_token(self) -> None:
        mgr = APNsManager()
        assert mgr.send_notification("d1", "Test", "Body") is None

    def test_send_silent_push(self) -> None:
        mgr = APNsManager()
        mgr.register_token("d1", "abcdef1234567890")
        nid = mgr.send_silent_push("d1", {"wake": True})
        assert nid is not None

    def test_send_silent_push_no_token(self) -> None:
        mgr = APNsManager()
        assert mgr.send_silent_push("d1") is None

    def test_validate_token_valid(self) -> None:
        mgr = APNsManager()
        assert mgr.validate_token("abcdef1234567890") is True

    def test_validate_token_invalid(self) -> None:
        mgr = APNsManager()
        assert mgr.validate_token("") is False
        assert mgr.validate_token("short") is False

    def test_get_delivery_stats(self) -> None:
        mgr = APNsManager()
        mgr.register_token("d1", "abcdef1234567890")
        mgr.send_notification("d1", "T", "B")
        stats = mgr.get_delivery_stats()
        assert stats["total_sent"] == 1
        assert stats["delivered"] == 1

    def test_test_push(self) -> None:
        mgr = APNsManager()
        mgr.register_token("d1", "abcdef1234567890")
        nid = mgr.test_push("d1")
        assert nid is not None

    def test_get_stats(self) -> None:
        mgr = APNsManager()
        stats = mgr.get_stats()
        assert "total_sent" in stats
        assert "history_count" in stats

    def test_get_history(self) -> None:
        mgr = APNsManager()
        mgr.register_token("d1", "abcdef1234567890")
        assert len(mgr.get_history()) >= 1

class TestNotificationRelay:
    """Bildirim aktarim testleri."""

    def test_relay(self) -> None:
        relay = NotificationRelay()
        result = relay.relay({"title": "Test"}, ["d1", "d2"])
        assert result["d1"] is True
        assert result["d2"] is True

    def test_relay_with_priority_rules(self) -> None:
        relay = NotificationRelay()
        relay.set_relay_rules("d1", {"min_priority": NotificationPriority.HIGH})
        result = relay.relay({"title": "T", "priority": NotificationPriority.LOW}, ["d1"])
        assert result["d1"] is False

    def test_filter_by_priority(self) -> None:
        relay = NotificationRelay()
        notifications = [
            {"title": "Low", "priority": NotificationPriority.LOW},
            {"title": "High", "priority": NotificationPriority.HIGH},
        ]
        filtered = relay.filter_by_priority(notifications, NotificationPriority.HIGH)
        assert len(filtered) == 1

    def test_batch_relay(self) -> None:
        relay = NotificationRelay()
        notifications = [{"title": "T1"}, {"title": "T2"}]
        result = relay.batch_relay(notifications, ["d1"])
        assert result["total_sent"] == 2

    def test_get_relay_history(self) -> None:
        relay = NotificationRelay()
        relay.relay({"title": "T"}, ["d1"])
        history = relay.get_relay_history("d1")
        assert len(history) == 1

    def test_get_relay_history_all(self) -> None:
        relay = NotificationRelay()
        relay.relay({"title": "T"}, ["d1", "d2"])
        history = relay.get_relay_history()
        assert len(history) == 2

    def test_set_relay_rules(self) -> None:
        relay = NotificationRelay()
        relay.set_relay_rules("d1", {"min_priority": NotificationPriority.HIGH})
        assert len(relay.get_history()) >= 1

    def test_get_stats(self) -> None:
        relay = NotificationRelay()
        relay.relay({"title": "T"}, ["d1"])
        stats = relay.get_stats()
        assert stats["total_relayed"] == 1


class TestCommandSurface:
    """Komut yuzeyi testleri."""

    def test_execute_command(self) -> None:
        cs = WearableCommandSurface()
        surface = cs.execute_command("d1", "test_cmd", {"key": "val"})
        assert surface.device_id == "d1"
        assert surface.command_type == "test_cmd"
        assert surface.status == "pending"

    def test_status_check(self) -> None:
        cs = WearableCommandSurface()
        result = cs.status_check("d1")
        assert result["status"] == "online"
        assert "battery" in result

    def test_quick_reply(self) -> None:
        cs = WearableCommandSurface()
        surface = cs.quick_reply("d1", "Hello!")
        assert surface.command_type == "quick_reply"

    def test_get_pending_commands(self) -> None:
        cs = WearableCommandSurface()
        cs.execute_command("d1", "cmd1")
        cs.execute_command("d1", "cmd2")
        pending = cs.get_pending_commands("d1")
        assert len(pending) >= 1

    def test_complete_command(self) -> None:
        cs = WearableCommandSurface()
        surface = cs.execute_command("d1", "cmd1")
        assert cs.complete_command(surface.surface_id, {"ok": True}) is True

    def test_complete_nonexistent(self) -> None:
        cs = WearableCommandSurface()
        assert cs.complete_command("nonexistent") is False

    def test_get_stats(self) -> None:
        cs = WearableCommandSurface()
        cs.execute_command("d1", "cmd1")
        stats = cs.get_stats()
        assert stats["total_commands"] == 1
        assert stats["pending_commands"] >= 0

    def test_get_history(self) -> None:
        cs = WearableCommandSurface()
        cs.execute_command("d1", "cmd1")
        assert len(cs.get_history()) >= 1