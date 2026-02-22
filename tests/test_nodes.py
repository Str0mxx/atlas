"""Device Nodes system test suite."""

import time
import pytest

from app.models.nodes_models import (
    CameraCapture, DeviceNode, LocationData, NodeHealthCheck,
    NodeNotification, NodeStatus, NodeType, NodesConfig, ScreenCapture,
)
from app.core.nodes.node_registry import NodeRegistry
from app.core.nodes.camera_node import CameraNode
from app.core.nodes.screen_node import ScreenNode
from app.core.nodes.location_node import LocationNode
from app.core.nodes.notification_node import NotificationNode
from app.core.nodes.node_health import NodeHealthMonitor


class TestNodesModels:
    def test_node_type_values(self) -> None:
        assert NodeType.CAMERA == "camera"
        assert NodeType.SCREEN == "screen"
        assert NodeType.SYSTEM == "system"

    def test_node_status_values(self) -> None:
        assert NodeStatus.ONLINE == "online"
        assert NodeStatus.OFFLINE == "offline"

    def test_device_node_defaults(self) -> None:
        n = DeviceNode()
        assert n.node_id == ""
        assert n.status == NodeStatus.OFFLINE
        assert n.is_paired is False

    def test_camera_capture_defaults(self) -> None:
        c = CameraCapture()
        assert c.format == "jpg"
        assert c.capture_type == "snap"

    def test_screen_capture_defaults(self) -> None:
        s = ScreenCapture()
        assert s.format == "png"

    def test_location_data_defaults(self) -> None:
        l = LocationData()
        assert l.source == "gps"

    def test_notification_defaults(self) -> None:
        n = NodeNotification()
        assert n.priority == "normal"
        assert n.delivered is False

    def test_health_check_defaults(self) -> None:
        h = NodeHealthCheck()
        assert h.auto_reconnect is True

    def test_config_defaults(self) -> None:
        c = NodesConfig()
        assert c.max_nodes == 50
        assert c.heartbeat_interval == 30


class TestNodeRegistry:
    def test_register(self) -> None:
        r = NodeRegistry()
        n = r.register("n1", NodeType.CAMERA, "Cam1")
        assert n.node_id == "n1"
        assert n.name == "Cam1"
        assert n.node_type == NodeType.CAMERA

    def test_register_auto_id(self) -> None:
        r = NodeRegistry()
        n = r.register("", NodeType.SYSTEM)
        assert n.node_id != ""

    def test_unregister(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        assert r.unregister("n1") is True
        assert r.get("n1") is None

    def test_unregister_missing(self) -> None:
        assert NodeRegistry().unregister("x") is False

    def test_pair_unpair(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        assert r.pair("n1") is True
        node = r.get("n1")
        assert node.is_paired is True
        assert node.status == NodeStatus.ONLINE
        assert r.unpair("n1") is True
        assert r.get("n1").is_paired is False

    def test_pair_missing(self) -> None:
        assert NodeRegistry().pair("x") is False

    def test_list_nodes_all(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        r.register("n2", NodeType.SCREEN)
        assert len(r.list_nodes()) == 2

    def test_list_nodes_filter_type(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        r.register("n2", NodeType.SCREEN)
        assert len(r.list_nodes(node_type=NodeType.CAMERA)) == 1

    def test_update_heartbeat(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.SYSTEM)
        assert r.update_heartbeat("n1") is True
        assert r.get("n1").last_heartbeat > 0

    def test_update_heartbeat_missing(self) -> None:
        assert NodeRegistry().update_heartbeat("x") is False

    def test_clear_pending(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        r.register("n2", NodeType.SCREEN)
        r.pair("n1")
        assert r.clear_pending() == 1
        assert len(r.list_nodes()) == 1

    def test_remove_all_no_confirm(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        assert r.remove_all() is False

    def test_remove_all_confirmed(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        assert r.remove_all(confirm=True) is True
        assert len(r.list_nodes()) == 0

    def test_registry_stats(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        r.pair("n1")
        s = r.get_stats()
        assert s["total_nodes"] == 1
        assert s["online"] == 1
        assert s["paired"] == 1

    def test_registry_history(self) -> None:
        r = NodeRegistry()
        r.register("n1", NodeType.CAMERA)
        assert len(r.get_history()) >= 1


class TestCameraNode:
    def test_snap(self) -> None:
        cn = CameraNode()
        c = cn.snap("n1")
        assert c.capture_type == "snap"
        assert c.node_id == "n1"
        assert c.format == "jpg"

    def test_snap_custom_format(self) -> None:
        cn = CameraNode()
        c = cn.snap("n1", format="png")
        assert c.format == "png"

    def test_clip(self) -> None:
        cn = CameraNode()
        c = cn.clip("n1", duration=5.0)
        assert c.capture_type == "clip"
        assert c.duration == 5.0

    def test_get_captures(self) -> None:
        cn = CameraNode()
        cn.snap("n1")
        cn.snap("n1")
        assert len(cn.get_captures("n1")) == 2

    def test_get_captures_limit(self) -> None:
        cn = CameraNode()
        for _ in range(5): cn.snap("n1")
        assert len(cn.get_captures("n1", limit=3)) == 3

    def test_delete_capture(self) -> None:
        cn = CameraNode()
        c = cn.snap("n1")
        assert cn.delete_capture(c.capture_id) is True
        assert len(cn.get_captures("n1")) == 0

    def test_delete_capture_missing(self) -> None:
        assert CameraNode().delete_capture("x") is False

    def test_configure(self) -> None:
        cn = CameraNode()
        r = cn.configure("n1", {"resolution": "4k"})
        assert r["applied"]["resolution"] == "4k"

    def test_camera_stats(self) -> None:
        cn = CameraNode()
        cn.snap("n1")
        assert cn.get_stats()["total_captures"] == 1


class TestScreenNode:
    def test_screenshot(self) -> None:
        sn = ScreenNode()
        c = sn.screenshot("n1")
        assert c.capture_type == "screenshot"
        assert c.format == "png"

    def test_screenshot_format(self) -> None:
        sn = ScreenNode()
        c = sn.screenshot("n1", format="jpg")
        assert c.format == "jpg"

    def test_record(self) -> None:
        sn = ScreenNode()
        c = sn.record("n1", duration=10.0)
        assert c.capture_type == "recording"
        assert c.duration == 10.0

    def test_get_recordings(self) -> None:
        sn = ScreenNode()
        sn.record("n1")
        assert len(sn.get_recordings("n1")) == 1

    def test_stop_recording(self) -> None:
        sn = ScreenNode()
        sn.record("n1")
        assert sn.stop_recording("n1") is True

    def test_stop_recording_none(self) -> None:
        assert ScreenNode().stop_recording("n1") is False

    def test_screen_stats(self) -> None:
        sn = ScreenNode()
        sn.record("n1")
        s = sn.get_stats()
        assert s["total_captures"] == 1
        assert s["active_recordings"] == 1


class TestLocationNode:
    def test_get_location_empty(self) -> None:
        ln = LocationNode()
        assert ln.get_location("n1") is None

    def test_update_and_get(self) -> None:
        ln = LocationNode()
        data = LocationData(node_id="n1", latitude=41.0, longitude=29.0)
        ln.update_location(data)
        loc = ln.get_location("n1")
        assert loc is not None
        assert loc.latitude == 41.0

    def test_location_history(self) -> None:
        ln = LocationNode()
        for i in range(5):
            ln.update_location(LocationData(node_id="n1", latitude=41.0+i*0.01, longitude=29.0))
        assert len(ln.get_location_history("n1", limit=3)) == 3

    def test_set_update_interval(self) -> None:
        ln = LocationNode()
        ln.set_update_interval("n1", 10)
        assert ln._intervals["n1"] == 10

    def test_get_address(self) -> None:
        ln = LocationNode()
        addr = ln.get_address(41.0, 29.0)
        assert "41.0000" in addr

    def test_location_stats(self) -> None:
        ln = LocationNode()
        ln.update_location(LocationData(node_id="n1", latitude=41.0, longitude=29.0))
        s = ln.get_stats()
        assert s["tracked_nodes"] == 1
        assert s["total_points"] == 1


class TestNotificationNode:
    def test_send(self) -> None:
        nn = NotificationNode()
        n = nn.send("n1", "Title", "Body")
        assert n.title == "Title"
        assert n.delivered is True

    def test_send_priority(self) -> None:
        nn = NotificationNode()
        n = nn.send("n1", "T", "B", priority="high")
        assert n.priority == "high"

    def test_send_batch(self) -> None:
        nn = NotificationNode()
        results = nn.send_batch(["n1", "n2"], "T", "B")
        assert len(results) == 2

    def test_delivery_status(self) -> None:
        nn = NotificationNode()
        n = nn.send("n1", "T", "B")
        assert nn.get_delivery_status(n.notification_id) is True

    def test_delivery_status_missing(self) -> None:
        assert NotificationNode().get_delivery_status("x") is None

    def test_get_sent(self) -> None:
        nn = NotificationNode()
        nn.send("n1", "T1", "B1")
        nn.send("n1", "T2", "B2")
        assert len(nn.get_sent("n1")) == 2

    def test_notification_stats(self) -> None:
        nn = NotificationNode()
        nn.send("n1", "T", "B")
        s = nn.get_stats()
        assert s["total_sent"] == 1
        assert s["delivered"] == 1


class TestNodeHealth:
    def test_check(self) -> None:
        m = NodeHealthMonitor()
        m._health["n1"] = NodeHealthCheck(node_id="n1")
        h = m.check("n1")
        assert h.status == NodeStatus.ONLINE

    def test_check_all(self) -> None:
        m = NodeHealthMonitor()
        m._health["n1"] = NodeHealthCheck(node_id="n1")
        m._health["n2"] = NodeHealthCheck(node_id="n2")
        results = m.check_all()
        assert len(results) == 2

    def test_get_status(self) -> None:
        m = NodeHealthMonitor()
        m.check("n1")
        assert m.get_status("n1") is not None

    def test_get_status_missing(self) -> None:
        assert NodeHealthMonitor().get_status("x") is None

    def test_set_auto_reconnect(self) -> None:
        m = NodeHealthMonitor()
        assert m.set_auto_reconnect("n1", False) is True
        assert m._health["n1"].auto_reconnect is False

    def test_get_unhealthy(self) -> None:
        m = NodeHealthMonitor()
        m.mark_failure("n1")
        assert len(m.get_unhealthy()) == 1

    def test_attempt_reconnect_success(self) -> None:
        m = NodeHealthMonitor()
        m.mark_failure("n1")
        assert m.attempt_reconnect("n1") is True
        assert m._health["n1"].status == NodeStatus.ONLINE

    def test_attempt_reconnect_missing(self) -> None:
        assert NodeHealthMonitor().attempt_reconnect("x") is False

    def test_attempt_reconnect_disabled(self) -> None:
        m = NodeHealthMonitor()
        m.mark_failure("n1")
        m._health["n1"].auto_reconnect = False
        assert m.attempt_reconnect("n1") is False

    def test_attempt_reconnect_max_retries(self) -> None:
        m = NodeHealthMonitor(config=NodesConfig(reconnect_max_retries=2))
        m.mark_failure("n1")
        m.mark_failure("n1")
        assert m.attempt_reconnect("n1") is False

    def test_mark_failure(self) -> None:
        m = NodeHealthMonitor()
        m.mark_failure("n1")
        assert m._health["n1"].consecutive_failures == 1
        assert m._health["n1"].status == NodeStatus.ERROR

    def test_health_stats(self) -> None:
        m = NodeHealthMonitor()
        m.check("n1")
        s = m.get_stats()
        assert s["monitored_nodes"] == 1
        assert s["online"] == 1

    def test_health_history(self) -> None:
        m = NodeHealthMonitor()
        m.check("n1")
        assert len(m.get_history()) >= 1
