"""ATLAS Location & Geofence Intelligence testleri."""

import pytest

from app.core.geolocation.geofence_manager import (
    GeofenceManager,
)
from app.core.geolocation.location_tracker import (
    LocationTracker,
)
from app.core.geolocation.proximity_trigger import (
    ProximityTrigger,
)
from app.core.geolocation.route_optimizer import (
    RouteOptimizer,
)
from app.core.geolocation.eta_calculator import (
    ETACalculator,
)
from app.core.geolocation.location_history import (
    LocationHistory,
)
from app.core.geolocation.geo_alert_engine import (
    GeoAlertEngine,
)
from app.core.geolocation.fleet_tracker import (
    FleetTracker,
)
from app.core.geolocation.geolocation_orchestrator import (
    GeolocationOrchestrator,
)


# ==================== GeofenceManager ====================


class TestDefineZone:
    """define_zone testleri."""

    def test_circle_zone(self):
        gm = GeofenceManager()
        r = gm.define_zone(
            name="Office",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=200.0,
        )
        assert r["created"] is True
        assert r["shape"] == "circle"
        assert r["name"] == "Office"

    def test_polygon_zone(self):
        gm = GeofenceManager()
        poly = [
            (41.0, 29.0),
            (41.1, 29.0),
            (41.1, 29.1),
            (41.0, 29.1),
        ]
        r = gm.define_zone(
            name="Area",
            shape="polygon",
            polygon=poly,
        )
        assert r["created"] is True
        assert r["shape"] == "polygon"

    def test_zone_counter(self):
        gm = GeofenceManager()
        gm.define_zone(name="Z1")
        gm.define_zone(name="Z2")
        assert gm.zone_count == 2


class TestCheckPointInZone:
    """check_point_in_zone testleri."""

    def test_inside_circle(self):
        gm = GeofenceManager()
        r = gm.define_zone(
            name="Test",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=5000.0,
        )
        c = gm.check_point_in_zone(
            r["zone_id"], 41.001, 29.001,
        )
        assert c["inside"] is True
        assert c["checked"] is True

    def test_outside_circle(self):
        gm = GeofenceManager()
        r = gm.define_zone(
            name="Small",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=10.0,
        )
        c = gm.check_point_in_zone(
            r["zone_id"], 42.0, 30.0,
        )
        assert c["inside"] is False

    def test_polygon_inside(self):
        gm = GeofenceManager()
        poly = [
            (40.0, 28.0),
            (42.0, 28.0),
            (42.0, 30.0),
            (40.0, 30.0),
        ]
        r = gm.define_zone(
            name="PolyZone",
            shape="polygon",
            polygon=poly,
        )
        c = gm.check_point_in_zone(
            r["zone_id"], 41.0, 29.0,
        )
        assert c["inside"] is True

    def test_unknown_zone(self):
        gm = GeofenceManager()
        c = gm.check_point_in_zone(
            "no_zone", 41.0, 29.0,
        )
        assert c["found"] is False


class TestDetectEntryExit:
    """detect_entry_exit testleri."""

    def test_entry_detected(self):
        gm = GeofenceManager()
        r = gm.define_zone(
            name="Gate",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=5000.0,
        )
        d = gm.detect_entry_exit(
            r["zone_id"],
            prev_lat=50.0,
            prev_lon=50.0,
            curr_lat=41.001,
            curr_lon=29.001,
        )
        assert d["event"] == "entry"
        assert d["detected"] is True

    def test_exit_detected(self):
        gm = GeofenceManager()
        r = gm.define_zone(
            name="Gate",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=5000.0,
        )
        d = gm.detect_entry_exit(
            r["zone_id"],
            prev_lat=41.001,
            prev_lon=29.001,
            curr_lat=50.0,
            curr_lon=50.0,
        )
        assert d["event"] == "exit"

    def test_stay_event(self):
        gm = GeofenceManager()
        r = gm.define_zone(
            name="Stay",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=5000.0,
        )
        d = gm.detect_entry_exit(
            r["zone_id"],
            prev_lat=41.001,
            prev_lon=29.001,
            curr_lat=41.002,
            curr_lon=29.002,
        )
        assert d["event"] == "stay"


class TestCheckOverlap:
    """check_overlap testleri."""

    def test_overlapping_circles(self):
        gm = GeofenceManager()
        z1 = gm.define_zone(
            name="Z1",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=5000.0,
        )
        z2 = gm.define_zone(
            name="Z2",
            center_lat=41.01,
            center_lon=29.01,
            radius_m=5000.0,
        )
        r = gm.check_overlap(
            z1["zone_id"],
            z2["zone_id"],
        )
        assert r["overlapping"] is True

    def test_non_overlapping(self):
        gm = GeofenceManager()
        z1 = gm.define_zone(
            name="Z1",
            center_lat=0.0,
            center_lon=0.0,
            radius_m=10.0,
        )
        z2 = gm.define_zone(
            name="Z2",
            center_lat=10.0,
            center_lon=10.0,
            radius_m=10.0,
        )
        r = gm.check_overlap(
            z1["zone_id"],
            z2["zone_id"],
        )
        assert r["overlapping"] is False


class TestManageGroup:
    """manage_group testleri."""

    def test_create_group(self):
        gm = GeofenceManager()
        r = gm.manage_group(
            "offices",
            zone_ids=["z1", "z2"],
            action="create",
        )
        assert r["managed"] is True
        assert r["zone_count"] == 2

    def test_delete_group(self):
        gm = GeofenceManager()
        gm.manage_group(
            "temp",
            zone_ids=["z1"],
            action="create",
        )
        r = gm.manage_group(
            "temp", action="delete",
        )
        assert r["managed"] is True


# ==================== LocationTracker ====================


class TestTrackRealtime:
    """track_realtime testleri."""

    def test_basic_track(self):
        lt = LocationTracker()
        r = lt.track_realtime(
            "dev1", 41.0, 29.0,
        )
        assert r["tracked"] is True
        assert r["device_id"] == "dev1"

    def test_device_count(self):
        lt = LocationTracker()
        lt.track_realtime("d1", 41.0, 29.0)
        lt.track_realtime("d2", 42.0, 30.0)
        lt.track_realtime("d1", 41.1, 29.1)
        assert lt.device_count == 2
        assert lt.update_count == 3


class TestGetDeviceLocation:
    """get_device_location testleri."""

    def test_found(self):
        lt = LocationTracker()
        lt.track_realtime("d1", 41.5, 29.5)
        r = lt.get_device_location("d1")
        assert r["found"] is True
        assert r["lat"] == 41.5

    def test_not_found(self):
        lt = LocationTracker()
        r = lt.get_device_location("nope")
        assert r["found"] is False


class TestLogHistory:
    """log_history testleri."""

    def test_retrieve_history(self):
        lt = LocationTracker()
        lt.track_realtime("d1", 41.0, 29.0)
        lt.track_realtime("d1", 41.1, 29.1)
        r = lt.log_history("d1")
        assert r["retrieved"] is True
        assert r["entries"] == 2


class TestHandleAccuracy:
    """handle_accuracy testleri."""

    def test_excellent(self):
        lt = LocationTracker()
        r = lt.handle_accuracy("d1", 3.0)
        assert r["quality"] == "excellent"

    def test_good(self):
        lt = LocationTracker()
        r = lt.handle_accuracy("d1", 10.0)
        assert r["quality"] == "good"

    def test_poor(self):
        lt = LocationTracker()
        r = lt.handle_accuracy("d1", 200.0)
        assert r["quality"] == "poor"
        assert r["usable"] is False


class TestOptimizeBattery:
    """optimize_battery testleri."""

    def test_low_battery(self):
        lt = LocationTracker()
        r = lt.optimize_battery(
            "d1", battery_pct=5.0,
        )
        assert r["mode"] == "ultra_saver"
        assert r["recommended_interval"] == 300

    def test_normal_moving(self):
        lt = LocationTracker()
        r = lt.optimize_battery(
            "d1",
            battery_pct=80.0,
            movement_detected=True,
        )
        assert r["mode"] == "normal"
        assert r["recommended_interval"] == 10

    def test_stationary(self):
        lt = LocationTracker()
        r = lt.optimize_battery(
            "d1",
            battery_pct=80.0,
            movement_detected=False,
        )
        assert r["mode"] == "stationary"


# ==================== ProximityTrigger ====================


class TestCalculateDistance:
    """calculate_distance testleri."""

    def test_known_distance(self):
        pt = ProximityTrigger()
        r = pt.calculate_distance(
            41.0, 29.0, 41.0, 29.01,
        )
        assert r["calculated"] is True
        assert r["distance_m"] > 0

    def test_zero_distance(self):
        pt = ProximityTrigger()
        r = pt.calculate_distance(
            41.0, 29.0, 41.0, 29.0,
        )
        assert r["distance_m"] == 0.0


class TestSetProximityAlert:
    """set_proximity_alert testleri."""

    def test_set_alert(self):
        pt = ProximityTrigger()
        r = pt.set_proximity_alert(
            "t1", 41.0, 29.0,
            range_m=500.0,
            action="notify",
        )
        assert r["alert_set"] is True
        assert r["range_m"] == 500.0


class TestCheckRange:
    """check_range testleri."""

    def test_in_range(self):
        pt = ProximityTrigger()
        pt.set_proximity_alert(
            "t1", 41.0, 29.0,
            range_m=5000.0,
        )
        r = pt.check_range(
            "t1", 41.001, 29.001,
        )
        assert r["in_range"] is True

    def test_out_of_range(self):
        pt = ProximityTrigger()
        pt.set_proximity_alert(
            "t1", 41.0, 29.0,
            range_m=10.0,
        )
        r = pt.check_range(
            "t1", 42.0, 30.0,
        )
        assert r["in_range"] is False

    def test_unknown_target(self):
        pt = ProximityTrigger()
        r = pt.check_range(
            "no", 41.0, 29.0,
        )
        assert r["found"] is False


class TestTrackMultiTarget:
    """track_multi_target testleri."""

    def test_multi_track(self):
        pt = ProximityTrigger()
        pt.set_proximity_alert(
            "t1", 41.0, 29.0,
            range_m=5000.0,
        )
        pt.set_proximity_alert(
            "t2", 50.0, 50.0,
            range_m=100.0,
        )
        r = pt.track_multi_target(
            41.001, 29.001,
        )
        assert r["tracked"] is True
        assert r["targets_checked"] == 2
        assert r["in_range_count"] == 1


class TestFireTrigger:
    """fire_trigger testleri."""

    def test_trigger_fired(self):
        pt = ProximityTrigger()
        pt.set_proximity_alert(
            "t1", 41.0, 29.0,
            range_m=5000.0,
            action="send_alert",
        )
        r = pt.fire_trigger(
            "t1", 41.001, 29.001,
        )
        assert r["fired"] is True
        assert r["action"] == "send_alert"
        assert pt.trigger_count == 1

    def test_trigger_not_fired(self):
        pt = ProximityTrigger()
        pt.set_proximity_alert(
            "t1", 41.0, 29.0,
            range_m=10.0,
        )
        r = pt.fire_trigger(
            "t1", 50.0, 50.0,
        )
        assert r["fired"] is False


# ==================== RouteOptimizer ====================


class TestOptimizePath:
    """optimize_path testleri."""

    def test_fastest_route(self):
        ro = RouteOptimizer()
        r = ro.optimize_path(
            41.0, 29.0, 41.5, 29.5,
            strategy="fastest",
        )
        assert r["optimized"] is True
        assert r["distance_km"] > 0
        assert r["duration_min"] > 0

    def test_economical_route(self):
        ro = RouteOptimizer()
        r = ro.optimize_path(
            41.0, 29.0, 42.0, 30.0,
            strategy="economical",
        )
        assert r["strategy"] == "economical"
        assert ro.route_count == 1


class TestMultiStopRoute:
    """multi_stop_route testleri."""

    def test_multi_stop(self):
        ro = RouteOptimizer()
        stops = [
            (41.0, 29.0),
            (41.1, 29.1),
            (41.2, 29.2),
        ]
        r = ro.multi_stop_route(stops)
        assert r["planned"] is True
        assert r["stop_count"] == 3
        assert r["segments"] == 2

    def test_insufficient_stops(self):
        ro = RouteOptimizer()
        r = ro.multi_stop_route(
            [(41.0, 29.0)],
        )
        assert r["planned"] is False


class TestConsiderTraffic:
    """consider_traffic testleri."""

    def test_clear_traffic(self):
        ro = RouteOptimizer()
        rt = ro.optimize_path(
            41.0, 29.0, 41.5, 29.5,
        )
        r = ro.consider_traffic(
            rt["route_id"],
            traffic_factor=0.9,
        )
        assert r["traffic_level"] == "clear"
        assert r["adjusted"] is True

    def test_heavy_traffic(self):
        ro = RouteOptimizer()
        rt = ro.optimize_path(
            41.0, 29.0, 41.5, 29.5,
        )
        r = ro.consider_traffic(
            rt["route_id"],
            traffic_factor=1.5,
        )
        assert r["traffic_level"] == "heavy"

    def test_unknown_route(self):
        ro = RouteOptimizer()
        r = ro.consider_traffic("no_route")
        assert r["found"] is False


class TestSetTimeWindow:
    """set_time_window testleri."""

    def test_set_window(self):
        ro = RouteOptimizer()
        rt = ro.optimize_path(
            41.0, 29.0, 41.5, 29.5,
        )
        r = ro.set_time_window(
            rt["route_id"],
            earliest="08:00",
            latest="18:00",
        )
        assert r["window_set"] is True


class TestAddConstraint:
    """add_constraint testleri."""

    def test_add(self):
        ro = RouteOptimizer()
        r = ro.add_constraint(
            "r1",
            constraint_type="max_weight",
            value=5000,
        )
        assert r["added"] is True


# ==================== ETACalculator ====================


class TestPredictEta:
    """predict_eta testleri."""

    def test_basic_prediction(self):
        ec = ETACalculator()
        r = ec.predict_eta(
            distance_km=100.0,
            speed_kmh=50.0,
        )
        assert r["predicted"] is True
        assert r["base_min"] == 120.0
        assert r["adjusted_min"] == 120.0

    def test_traffic_adjusted(self):
        ec = ETACalculator()
        r = ec.predict_eta(
            distance_km=100.0,
            speed_kmh=50.0,
            traffic_factor=1.5,
        )
        assert r["adjusted_min"] == 180.0
        assert r["confidence"] == 0.7

    def test_zero_speed(self):
        ec = ETACalculator()
        r = ec.predict_eta(
            distance_km=10.0,
            speed_kmh=0.0,
        )
        assert r["predicted"] is True


class TestUseHistorical:
    """use_historical testleri."""

    def test_no_patterns(self):
        ec = ETACalculator()
        r = ec.use_historical("route_a")
        assert r["historical"] is False

    def test_with_patterns(self):
        ec = ETACalculator()
        ec.add_pattern("r1", 30.0, 12)
        ec.add_pattern("r1", 40.0, 12)
        r = ec.use_historical("r1", 12)
        assert r["historical"] is True
        assert r["avg_min"] == 35.0

    def test_peak_hour(self):
        ec = ETACalculator()
        ec.add_pattern("r1", 30.0)
        r = ec.use_historical("r1", 8)
        assert r["peak_factor"] == 1.4


class TestUpdateRealtime:
    """update_realtime testleri."""

    def test_update(self):
        ec = ETACalculator()
        eta = ec.predict_eta(100.0, 50.0)
        r = ec.update_realtime(
            eta["eta_id"],
            remaining_km=50.0,
            current_speed_kmh=60.0,
        )
        assert r["updated"] is True
        assert r["new_eta_min"] == 50.0

    def test_unknown_eta(self):
        ec = ETACalculator()
        r = ec.update_realtime("no", 10.0)
        assert r["found"] is False


class TestDetectDelay:
    """detect_delay testleri."""

    def test_no_delay(self):
        ec = ETACalculator()
        eta = ec.predict_eta(100.0, 50.0)
        r = ec.detect_delay(
            eta["eta_id"],
            elapsed_min=60.0,
            progress_pct=50.0,
        )
        assert r["detected"] is True
        assert r["delayed"] is False

    def test_delay_detected(self):
        ec = ETACalculator()
        eta = ec.predict_eta(100.0, 100.0)
        r = ec.detect_delay(
            eta["eta_id"],
            elapsed_min=50.0,
            progress_pct=20.0,
        )
        assert r["delayed"] is True
        assert ec.delay_count == 1


# ==================== LocationHistory ====================


class TestStoreLocation:
    """store_location testleri."""

    def test_basic_store(self):
        lh = LocationHistory()
        r = lh.store_location(
            "d1", 41.0, 29.0,
        )
        assert r["stored"] is True
        assert r["total_records"] == 1

    def test_multiple_stores(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        lh.store_location("d1", 41.1, 29.1)
        assert lh.record_count == 2


class TestGetPath:
    """get_path testleri."""

    def test_get_path(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        lh.store_location("d1", 41.1, 29.1)
        r = lh.get_path("d1")
        assert r["retrieved"] is True
        assert r["point_count"] == 2

    def test_empty_path(self):
        lh = LocationHistory()
        r = lh.get_path("no_device")
        assert r["point_count"] == 0


class TestDetectDwell:
    """detect_dwell testleri."""

    def test_dwell_detected(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        lh.store_location(
            "d1", 41.0001, 29.0001,
        )
        lh.store_location(
            "d1", 41.0002, 29.0002,
        )
        r = lh.detect_dwell("d1")
        assert r["dwell_detected"] is True
        assert lh.dwell_count == 1

    def test_no_dwell(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        lh.store_location("d1", 42.0, 30.0)
        lh.store_location("d1", 43.0, 31.0)
        r = lh.detect_dwell("d1")
        assert r["dwell_detected"] is False

    def test_insufficient_data(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        r = lh.detect_dwell("d1")
        assert r["dwell_detected"] is False


class TestAnalyzePatterns:
    """analyze_patterns testleri."""

    def test_stationary(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        lh.store_location(
            "d1", 41.0001, 29.0001,
        )
        r = lh.analyze_patterns("d1")
        assert r["pattern"] == "stationary"

    def test_mobile(self):
        lh = LocationHistory()
        lh.store_location("d1", 41.0, 29.0)
        lh.store_location("d1", 42.0, 30.0)
        r = lh.analyze_patterns("d1")
        assert r["pattern"] == "mobile"

    def test_empty(self):
        lh = LocationHistory()
        r = lh.analyze_patterns("none")
        assert r["analyzed"] is False


class TestSetPrivacy:
    """set_privacy testleri."""

    def test_set_privacy(self):
        lh = LocationHistory()
        r = lh.set_privacy(
            "d1",
            retention_days=90,
            anonymize=True,
            share_enabled=False,
        )
        assert r["privacy_set"] is True
        assert r["retention_days"] == 90
        assert r["anonymize"] is True


# ==================== GeoAlertEngine ====================


class TestCreateLocationAlert:
    """create_location_alert testleri."""

    def test_create_alert(self):
        gae = GeoAlertEngine()
        r = gae.create_location_alert(
            device_id="d1",
            alert_type="entry",
            zone_id="z1",
            message="Entered zone",
        )
        assert r["generated"] is True
        assert r["alert_type"] == "entry"
        assert gae.alert_count == 1

    def test_multiple_alerts(self):
        gae = GeoAlertEngine()
        gae.create_location_alert("d1")
        gae.create_location_alert("d2")
        assert gae.alert_count == 2


class TestHandleGeofenceEvent:
    """handle_geofence_event testleri."""

    def test_handle_entry(self):
        gae = GeoAlertEngine()
        r = gae.handle_geofence_event(
            "d1", "z1", "entry",
        )
        assert r["handled"] is True
        assert r["event"] == "entry"

    def test_handle_exit(self):
        gae = GeoAlertEngine()
        r = gae.handle_geofence_event(
            "d1", "z1", "exit",
        )
        assert r["handled"] is True


class TestDefineCondition:
    """define_condition testleri."""

    def test_define(self):
        gae = GeoAlertEngine()
        r = gae.define_condition(
            "c1",
            condition_type="speed",
            threshold=120.0,
            action="warn",
        )
        assert r["defined"] is True


class TestNotifyChannels:
    """notify_channels testleri."""

    def test_notify(self):
        gae = GeoAlertEngine()
        a = gae.create_location_alert("d1")
        r = gae.notify_channels(
            a["alert_id"],
            channels=["telegram", "email"],
        )
        assert r["notified"] is True
        assert r["channels_notified"] == 2

    def test_unknown_alert(self):
        gae = GeoAlertEngine()
        r = gae.notify_channels("no_alert")
        assert r["found"] is False


class TestSuppressAlert:
    """suppress_alert testleri."""

    def test_suppress(self):
        gae = GeoAlertEngine()
        r = gae.suppress_alert(
            "zone_entry_*",
            duration_sec=7200,
        )
        assert r["suppressed"] is True


# ==================== FleetTracker ====================


class TestTrackVehicle:
    """track_vehicle testleri."""

    def test_basic_track(self):
        ft = FleetTracker()
        r = ft.track_vehicle(
            "v1", 41.0, 29.0,
            speed_kmh=60.0,
        )
        assert r["tracked"] is True
        assert r["status"] == "moving"

    def test_idle_vehicle(self):
        ft = FleetTracker()
        r = ft.track_vehicle(
            "v1", 41.0, 29.0,
            speed_kmh=0.0,
        )
        assert r["status"] == "idle"

    def test_vehicle_count(self):
        ft = FleetTracker()
        ft.track_vehicle("v1", 41.0, 29.0)
        ft.track_vehicle("v2", 42.0, 30.0)
        ft.track_vehicle("v1", 41.1, 29.1)
        assert ft.vehicle_count == 2


class TestAssignDriver:
    """assign_driver testleri."""

    def test_assign(self):
        ft = FleetTracker()
        ft.track_vehicle("v1", 41.0, 29.0)
        r = ft.assign_driver("v1", "drv1")
        assert r["assigned"] is True
        assert r["driver_id"] == "drv1"


class TestMonitorStatus:
    """monitor_status testleri."""

    def test_monitor(self):
        ft = FleetTracker()
        ft.track_vehicle(
            "v1", 41.0, 29.0,
            speed_kmh=80.0,
        )
        r = ft.monitor_status("v1")
        assert r["monitored"] is True
        assert r["status"] == "moving"
        assert r["connectivity"] == "strong"

    def test_unknown_vehicle(self):
        ft = FleetTracker()
        r = ft.monitor_status("nope")
        assert r["found"] is False


class TestGetPerformance:
    """get_performance testleri."""

    def test_excellent(self):
        ft = FleetTracker()
        r = ft.get_performance(
            "v1",
            total_km=300.0,
            fuel_liters=15.0,
            hours_driven=5.0,
        )
        assert r["calculated"] is True
        assert r["efficiency_rating"] == "excellent"
        assert r["fuel_efficiency_km_l"] == 20.0

    def test_poor(self):
        ft = FleetTracker()
        r = ft.get_performance(
            "v1",
            total_km=10.0,
            fuel_liters=5.0,
        )
        assert r["efficiency_rating"] == "poor"

    def test_zero_fuel(self):
        ft = FleetTracker()
        r = ft.get_performance(
            "v1",
            total_km=100.0,
            fuel_liters=0.0,
        )
        assert r["fuel_efficiency_km_l"] == 0.0


class TestDispatchVehicle:
    """dispatch_vehicle testleri."""

    def test_dispatch(self):
        ft = FleetTracker()
        ft.track_vehicle("v1", 41.0, 29.0)
        r = ft.dispatch_vehicle(
            "v1", 42.0, 30.0,
            priority="high",
        )
        assert r["dispatched"] is True
        assert r["priority"] == "high"
        assert ft.dispatch_count == 1

    def test_dispatch_unknown(self):
        ft = FleetTracker()
        r = ft.dispatch_vehicle(
            "no_v", 42.0, 30.0,
        )
        assert r["found"] is False


# ==================== GeolocationOrchestrator ====================


class TestTrackAndDetect:
    """track_and_detect testleri."""

    def test_basic_pipeline(self):
        go = GeolocationOrchestrator()
        r = go.track_and_detect(
            device_id="d1",
            lat=41.0,
            lon=29.0,
        )
        assert r["pipeline_complete"] is True
        assert r["tracked"] is True
        assert r["event"] == "none"

    def test_with_geofence(self):
        go = GeolocationOrchestrator()
        z = go.geofence.define_zone(
            name="Office",
            shape="circle",
            center_lat=41.0,
            center_lon=29.0,
            radius_m=5000.0,
        )
        r = go.track_and_detect(
            device_id="d1",
            lat=41.001,
            lon=29.001,
            zone_id=z["zone_id"],
            prev_lat=50.0,
            prev_lon=50.0,
        )
        assert r["event"] == "entry"
        assert go.pipeline_count == 1


class TestMultiAssetTrack:
    """multi_asset_track testleri."""

    def test_multi_asset(self):
        go = GeolocationOrchestrator()
        assets = [
            {"device_id": "d1", "lat": 41.0, "lon": 29.0},
            {"device_id": "d2", "lat": 42.0, "lon": 30.0},
        ]
        r = go.multi_asset_track(assets)
        assert r["tracked"] is True
        assert r["assets_tracked"] == 2
        assert go.asset_count == 2


class TestGetAnalytics:
    """get_analytics testleri."""

    def test_analytics(self):
        go = GeolocationOrchestrator()
        go.track_and_detect("d1", 41.0, 29.0)
        a = go.get_analytics()
        assert a["pipelines_run"] == 1
        assert a["location_updates"] >= 1
        assert a["history_records"] >= 1
        assert "zones_created" in a
        assert "vehicles_tracked" in a
