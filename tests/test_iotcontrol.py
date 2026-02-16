"""ATLAS IoT & Device Controller testleri."""

import pytest

from app.core.iotcontrol.device_discovery import (
    DeviceDiscovery,
)
from app.core.iotcontrol.mqtt_bridge import (
    MQTTBridge,
)
from app.core.iotcontrol.device_commander import (
    DeviceCommander,
)
from app.core.iotcontrol.sensor_data_collector import (
    SensorDataCollector,
)
from app.core.iotcontrol.automation_rule_engine import (
    AutomationRuleEngine,
)
from app.core.iotcontrol.device_health_monitor import (
    DeviceHealthMonitor,
)
from app.core.iotcontrol.scene_manager import (
    SceneManager,
)
from app.core.iotcontrol.protocol_adapter import (
    ProtocolAdapter,
)
from app.core.iotcontrol.iotcontrol_orchestrator import (
    IoTControlOrchestrator,
)
from app.models.iotcontrol_models import (
    DeviceStatus,
    ProtocolType,
    CommandStatus,
    SensorType,
    RuleTrigger,
    QoSLevel,
    DeviceRecord,
    SensorReading,
    AutomationRule,
    SceneRecord,
)


# --- DeviceDiscovery ---

class TestScanNetwork:
    def test_basic(self):
        dd = DeviceDiscovery()
        r = dd.scan_network()
        assert r["scanned"]
        assert r["devices_found"] > 0

    def test_count(self):
        dd = DeviceDiscovery()
        dd.scan_network()
        assert dd.scan_count == 1


class TestDetectProtocol:
    def test_mqtt(self):
        dd = DeviceDiscovery()
        r = dd.detect_protocol(
            "192.168.1.10",
            open_ports=[1883, 80],
        )
        assert r["detected"]
        assert "mqtt" in r["protocols"]

    def test_unknown(self):
        dd = DeviceDiscovery()
        r = dd.detect_protocol(
            "192.168.1.10",
            open_ports=[9999],
        )
        assert r["primary"] == "unknown"


class TestIdentifyDevice:
    def test_basic(self):
        dd = DeviceDiscovery()
        r = dd.identify_device(
            "192.168.1.10",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        assert r["identified"]
        assert r["manufacturer"] == (
            "SmartHome Inc"
        )

    def test_unknown_mfr(self):
        dd = DeviceDiscovery()
        r = dd.identify_device(
            "192.168.1.10",
            mac_address="XX:YY:ZZ:00:00:00",
        )
        assert r["manufacturer"] == "unknown"


class TestAutoRegister:
    def test_basic(self):
        dd = DeviceDiscovery()
        r = dd.auto_register(
            "dev_1", "192.168.1.10",
            name="Lamp",
        )
        assert r["registered"]
        assert r["name"] == "Lamp"

    def test_default_name(self):
        dd = DeviceDiscovery()
        r = dd.auto_register(
            "dev_1", "192.168.1.10",
        )
        assert "dev_1" in r["name"]


class TestMapCapabilities:
    def test_basic(self):
        dd = DeviceDiscovery()
        r = dd.map_capabilities(
            "dev_1",
            capabilities=[
                "on_off", "dimming",
            ],
        )
        assert r["mapped"]
        assert r["count"] == 2


# --- MQTTBridge ---

class TestMQTTConnect:
    def test_basic(self):
        mb = MQTTBridge()
        r = mb.connect("broker.local")
        assert r["connected"]
        assert mb.is_connected


class TestManageTopic:
    def test_create(self):
        mb = MQTTBridge()
        r = mb.manage_topic(
            "home/lights", "create",
        )
        assert r["managed"]

    def test_delete(self):
        mb = MQTTBridge()
        mb.manage_topic(
            "home/lights", "create",
        )
        r = mb.manage_topic(
            "home/lights", "delete",
        )
        assert r["managed"]


class TestMQTTPublish:
    def test_basic(self):
        mb = MQTTBridge()
        r = mb.publish(
            "home/lights",
            payload='{"on": true}',
            qos=1,
        )
        assert r["published"]
        assert mb.published_count == 1


class TestMQTTSubscribe:
    def test_basic(self):
        mb = MQTTBridge()
        r = mb.subscribe(
            "home/lights", qos=1,
        )
        assert r["subscribed"]


class TestSetQoS:
    def test_basic(self):
        mb = MQTTBridge()
        mb.subscribe("home/lights")
        r = mb.set_qos("home/lights", 2)
        assert r["set"]
        assert r["qos"] == 2

    def test_clamp(self):
        mb = MQTTBridge()
        r = mb.set_qos("topic", 5)
        assert r["qos"] == 2


# --- DeviceCommander ---

class TestSendCommand:
    def test_basic(self):
        dc = DeviceCommander()
        r = dc.send_command(
            "dev_1", "turn_on",
        )
        assert r["sent"]
        assert r["status"] == "sent"


class TestManageState:
    def test_basic(self):
        dc = DeviceCommander()
        r = dc.manage_state(
            "dev_1",
            state={"power": "on"},
        )
        assert r["managed"]
        assert r["state"]["power"] == "on"


class TestBatchCommand:
    def test_basic(self):
        dc = DeviceCommander()
        r = dc.batch_command(
            device_ids=["d1", "d2", "d3"],
            command="turn_off",
        )
        assert r["batch_sent"]
        assert r["sent_count"] == 3


class TestHandleResponse:
    def test_success(self):
        dc = DeviceCommander()
        dc.send_command("d1", "on")
        r = dc.handle_response(
            "cmd_1", success=True,
        )
        assert r["handled"]

    def test_failure(self):
        dc = DeviceCommander()
        dc.send_command("d1", "on")
        r = dc.handle_response(
            "cmd_1", success=False,
        )
        assert r["handled"]
        assert dc.failed_count == 1

    def test_not_found(self):
        dc = DeviceCommander()
        r = dc.handle_response("x")
        assert not r["found"]


class TestRetryCommand:
    def test_basic(self):
        dc = DeviceCommander()
        dc.send_command("d1", "on")
        r = dc.retry_command("cmd_1")
        assert r["retried"]

    def test_not_found(self):
        dc = DeviceCommander()
        r = dc.retry_command("x")
        assert not r["found"]


# --- SensorDataCollector ---

class TestCollectData:
    def test_basic(self):
        sc = SensorDataCollector()
        r = sc.collect_data(
            "d1", "temperature",
            value=22.5, unit="C",
        )
        assert r["collected"]
        assert r["value"] == 22.5


class TestProcessStream:
    def test_basic(self):
        sc = SensorDataCollector()
        for v in [20, 21, 22, 23]:
            sc.collect_data(
                "d1", "temperature",
                value=v,
            )
        r = sc.process_stream(
            "d1", "temperature",
        )
        assert r["processed"]
        assert r["data_points"] == 4

    def test_empty(self):
        sc = SensorDataCollector()
        r = sc.process_stream(
            "d1", "temperature",
        )
        assert r["data_points"] == 0


class TestSensorAggregate:
    def test_basic(self):
        sc = SensorDataCollector()
        sc.collect_data(
            "d1", "temperature", value=20,
        )
        sc.collect_data(
            "d1", "temperature", value=30,
        )
        r = sc.aggregate(
            "d1", "temperature",
        )
        assert r["aggregated"]
        assert r["min"] == 20
        assert r["max"] == 30
        assert r["avg"] == 25.0


class TestSensorAnomaly:
    def test_anomaly(self):
        sc = SensorDataCollector()
        for v in [20, 21, 20, 21, 20]:
            sc.collect_data(
                "d1", "temperature",
                value=v,
            )
        r = sc.detect_anomaly(
            "d1", "temperature", value=50,
        )
        assert r["detected"]
        assert r["is_anomaly"]

    def test_normal(self):
        sc = SensorDataCollector()
        for v in [20, 21, 20, 21]:
            sc.collect_data(
                "d1", "temperature",
                value=v,
            )
        r = sc.detect_anomaly(
            "d1", "temperature", value=20.5,
        )
        assert not r["is_anomaly"]

    def test_insufficient(self):
        sc = SensorDataCollector()
        sc.collect_data(
            "d1", "temperature", value=20,
        )
        r = sc.detect_anomaly(
            "d1", "temperature", value=50,
        )
        assert not r["is_anomaly"]


class TestStoreData:
    def test_basic(self):
        sc = SensorDataCollector()
        sc.collect_data(
            "d1", "temperature", value=22,
        )
        r = sc.store_data(
            "d1", "temperature",
        )
        assert r["stored"]
        assert r["records_stored"] == 1


# --- AutomationRuleEngine ---

class TestDefineRule:
    def test_basic(self):
        re = AutomationRuleEngine()
        r = re.define_rule(
            "temp_alert",
            trigger_type="threshold",
            condition={
                "operator": "gt",
                "threshold": 30,
            },
            action={
                "type": "send_alert",
            },
        )
        assert r["defined"]
        assert re.rule_count == 1


class TestCheckTrigger:
    def test_triggered(self):
        re = AutomationRuleEngine()
        re.define_rule(
            "temp_alert",
            condition={
                "operator": "gt",
                "threshold": 30,
            },
        )
        r = re.check_trigger(
            "rule_1", current_value=35,
        )
        assert r["checked"]
        assert r["triggered"]

    def test_not_triggered(self):
        re = AutomationRuleEngine()
        re.define_rule(
            "temp_alert",
            condition={
                "operator": "gt",
                "threshold": 30,
            },
        )
        r = re.check_trigger(
            "rule_1", current_value=25,
        )
        assert not r["triggered"]

    def test_not_found(self):
        re = AutomationRuleEngine()
        r = re.check_trigger("x")
        assert not r["found"]


class TestExecuteAction:
    def test_basic(self):
        re = AutomationRuleEngine()
        re.define_rule(
            "test",
            action={"type": "alert"},
        )
        r = re.execute_action("rule_1")
        assert r["executed"]

    def test_not_found(self):
        re = AutomationRuleEngine()
        r = re.execute_action("x")
        assert not r["found"]


class TestScheduleRule:
    def test_cron(self):
        re = AutomationRuleEngine()
        re.define_rule("test")
        r = re.schedule_rule(
            "rule_1", cron="0 * * * *",
        )
        assert r["scheduled"]

    def test_not_found(self):
        re = AutomationRuleEngine()
        r = re.schedule_rule("x")
        assert not r["found"]


class TestChainRules:
    def test_basic(self):
        re = AutomationRuleEngine()
        re.define_rule("r1")
        re.define_rule("r2")
        r = re.chain_rules(
            ["rule_1", "rule_2"],
        )
        assert r["chained"]
        assert r["length"] == 2


# --- DeviceHealthMonitor ---

class TestCheckDeviceHealth:
    def test_healthy(self):
        hm = DeviceHealthMonitor()
        r = hm.check_health(
            "d1", cpu_pct=50,
            memory_pct=60,
        )
        assert r["checked"]
        assert r["status"] == "healthy"

    def test_degraded(self):
        hm = DeviceHealthMonitor()
        r = hm.check_health(
            "d1", cpu_pct=95,
        )
        assert r["status"] == "degraded"
        assert "high_cpu" in r["issues"]


class TestMonitorBattery:
    def test_ok(self):
        hm = DeviceHealthMonitor()
        r = hm.monitor_battery(
            "d1", battery_pct=80,
        )
        assert r["monitored"]
        assert not r["low_battery"]

    def test_critical(self):
        hm = DeviceHealthMonitor()
        r = hm.monitor_battery(
            "d1", battery_pct=3,
        )
        assert r["critical"]
        assert hm.alert_count == 1


class TestCheckConnectivity:
    def test_good(self):
        hm = DeviceHealthMonitor()
        r = hm.check_connectivity(
            "d1", latency_ms=50,
        )
        assert r["checked"]
        assert r["connectivity"] == "good"

    def test_disconnected(self):
        hm = DeviceHealthMonitor()
        r = hm.check_connectivity(
            "d1", packet_loss_pct=60,
        )
        assert r["connectivity"] == (
            "disconnected"
        )


class TestUpdateFirmware:
    def test_needs_update(self):
        hm = DeviceHealthMonitor()
        r = hm.update_firmware(
            "d1",
            current_version="1.0",
            target_version="2.0",
        )
        assert r["needs_update"]

    def test_up_to_date(self):
        hm = DeviceHealthMonitor()
        r = hm.update_firmware(
            "d1",
            current_version="2.0",
            target_version="2.0",
        )
        assert not r["needs_update"]


class TestGenerateDeviceAlert:
    def test_basic(self):
        hm = DeviceHealthMonitor()
        r = hm.generate_alert(
            "d1", "warning", "High temp",
        )
        assert r["generated"]


# --- SceneManager ---

class TestCreateScene:
    def test_basic(self):
        sm = SceneManager()
        r = sm.create_scene(
            "Movie Night",
            devices=[
                {
                    "device_id": "d1",
                    "command": "dim",
                },
            ],
        )
        assert r["created"]
        assert r["device_count"] == 1


class TestControlDevices:
    def test_basic(self):
        sm = SceneManager()
        sm.create_scene(
            "Test",
            devices=[
                {"device_id": "d1"},
            ],
        )
        r = sm.control_devices("scene_1")
        assert r["controlled"]

    def test_not_found(self):
        sm = SceneManager()
        r = sm.control_devices("x")
        assert not r["found"]


class TestManagePreset:
    def test_save(self):
        sm = SceneManager()
        r = sm.manage_preset(
            "evening", scene_id="s1",
        )
        assert r["managed"]


class TestActivateScene:
    def test_basic(self):
        sm = SceneManager()
        sm.create_scene("Test")
        r = sm.activate_scene("scene_1")
        assert r["activated"]

    def test_not_found(self):
        sm = SceneManager()
        r = sm.activate_scene("x")
        assert not r["found"]


class TestScheduleScene:
    def test_basic(self):
        sm = SceneManager()
        sm.create_scene("Test")
        r = sm.schedule_scene(
            "scene_1",
            time_of_day="18:00",
        )
        assert r["scheduled"]

    def test_not_found(self):
        sm = SceneManager()
        r = sm.schedule_scene("x")
        assert not r["found"]


# --- ProtocolAdapter ---

class TestZigbeeCommand:
    def test_basic(self):
        pa = ProtocolAdapter()
        r = pa.zigbee_command(
            "d1", command="on",
            cluster="on_off",
        )
        assert r["sent"]
        assert r["protocol"] == "zigbee"


class TestZwaveCommand:
    def test_basic(self):
        pa = ProtocolAdapter()
        r = pa.zwave_command(
            "d1",
            command_class="switch_binary",
        )
        assert r["sent"]
        assert r["protocol"] == "zwave"


class TestWifiCommand:
    def test_basic(self):
        pa = ProtocolAdapter()
        r = pa.wifi_command(
            "d1", endpoint="/api/on",
        )
        assert r["sent"]
        assert r["protocol"] == "wifi"


class TestBleCommand:
    def test_basic(self):
        pa = ProtocolAdapter()
        r = pa.ble_command(
            "d1",
            service_uuid="1234",
        )
        assert r["sent"]
        assert r["protocol"] == "ble"


class TestTranslateProtocol:
    def test_basic(self):
        pa = ProtocolAdapter()
        r = pa.translate_protocol(
            "zigbee", "mqtt",
            command="on",
        )
        assert r["translated"]
        assert pa.translation_count == 1

    def test_unsupported(self):
        pa = ProtocolAdapter()
        r = pa.translate_protocol(
            "unknown_proto", "mqtt",
        )
        assert not r["translated"]


# --- IoTControlOrchestrator ---

class TestManageDevice:
    def test_basic(self):
        oc = IoTControlOrchestrator()
        r = oc.manage_device(
            "192.168.1.10",
            name="Lamp",
        )
        assert r["pipeline_complete"]
        assert r["registered"]
        assert r["connected"]

    def test_default(self):
        oc = IoTControlOrchestrator()
        r = oc.manage_device(
            "192.168.1.20",
        )
        assert r["pipeline_complete"]


class TestSmartControl:
    def test_basic(self):
        oc = IoTControlOrchestrator()
        r = oc.smart_control(
            "d1", command="turn_on",
        )
        assert r["sent"]
        assert r["published"]


class TestIoTAnalytics:
    def test_basic(self):
        oc = IoTControlOrchestrator()
        oc.manage_device("192.168.1.10")
        r = oc.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["devices_managed"] == 1


# --- Models ---

class TestIoTModels:
    def test_device_status(self):
        assert (
            DeviceStatus.ONLINE == "online"
        )
        assert (
            DeviceStatus.OFFLINE == "offline"
        )

    def test_protocol_type(self):
        assert (
            ProtocolType.MQTT == "mqtt"
        )
        assert (
            ProtocolType.ZIGBEE == "zigbee"
        )

    def test_command_status(self):
        assert (
            CommandStatus.PENDING
            == "pending"
        )
        assert (
            CommandStatus.ACKNOWLEDGED
            == "acknowledged"
        )

    def test_sensor_type(self):
        assert (
            SensorType.TEMPERATURE
            == "temperature"
        )
        assert (
            SensorType.MOTION == "motion"
        )

    def test_rule_trigger(self):
        assert (
            RuleTrigger.THRESHOLD
            == "threshold"
        )
        assert (
            RuleTrigger.SCHEDULE
            == "schedule"
        )

    def test_qos_level(self):
        assert QoSLevel.AT_MOST_ONCE == "0"
        assert QoSLevel.EXACTLY_ONCE == "2"

    def test_device_record(self):
        r = DeviceRecord(
            name="Lamp",
            protocol="wifi",
        )
        assert r.name == "Lamp"
        assert r.device_id

    def test_sensor_reading(self):
        r = SensorReading(
            device_id="d1",
            value=22.5,
        )
        assert r.value == 22.5
        assert r.reading_id

    def test_automation_rule(self):
        r = AutomationRule(
            name="temp_alert",
        )
        assert r.name == "temp_alert"
        assert r.rule_id

    def test_scene_record(self):
        r = SceneRecord(
            name="Movie",
            device_count=3,
        )
        assert r.device_count == 3
        assert r.scene_id
