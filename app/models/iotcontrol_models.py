"""ATLAS IoT & Device Controller modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DeviceStatus(str, Enum):
    """Cihaz durumu."""

    ONLINE = "online"
    OFFLINE = "offline"
    PAIRING = "pairing"
    ERROR = "error"


class ProtocolType(str, Enum):
    """Protokol tipi."""

    MQTT = "mqtt"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    WIFI = "wifi"
    BLE = "ble"


class CommandStatus(str, Enum):
    """Komut durumu."""

    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


class SensorType(str, Enum):
    """Sensör tipi."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    MOTION = "motion"
    LIGHT = "light"


class RuleTrigger(str, Enum):
    """Kural tetikleyici."""

    THRESHOLD = "threshold"
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"


class QoSLevel(str, Enum):
    """QoS seviyesi."""

    AT_MOST_ONCE = "0"
    AT_LEAST_ONCE = "1"
    EXACTLY_ONCE = "2"


class DeviceRecord(BaseModel):
    """Cihaz kaydı."""

    device_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    protocol: str = "wifi"
    status: str = "offline"
    ip_address: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SensorReading(BaseModel):
    """Sensör okuması."""

    reading_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    device_id: str = ""
    sensor_type: str = "temperature"
    value: float = 0.0
    unit: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class AutomationRule(BaseModel):
    """Otomasyon kuralı."""

    rule_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    trigger_type: str = "threshold"
    enabled: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class SceneRecord(BaseModel):
    """Sahne kaydı."""

    scene_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    name: str = ""
    device_count: int = 0
    active: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
