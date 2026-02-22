"""Device Nodes sistem modelleri."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Cihaz dugum tipleri."""
    CAMERA = "camera"
    SCREEN = "screen"
    LOCATION = "location"
    NOTIFICATION = "notification"
    SYSTEM = "system"
    SENSOR = "sensor"


class NodeStatus(str, Enum):
    """Dugum baglanti durumlari."""
    ONLINE = "online"
    OFFLINE = "offline"
    PAIRING = "pairing"
    ERROR = "error"
    SLEEPING = "sleeping"


class DeviceNode(BaseModel):
    """Kayitli bir cihaz dugumu."""
    node_id: str = ""
    name: str = ""
    node_type: NodeType = NodeType.SYSTEM
    status: NodeStatus = NodeStatus.OFFLINE
    paired_at: float = 0.0
    last_heartbeat: float = 0.0
    ip_address: str = ""
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    is_paired: bool = False


class CameraCapture(BaseModel):
    """Kamera yakalama sonucu."""
    capture_id: str = ""
    node_id: str = ""
    capture_type: str = "snap"
    filepath: str = ""
    width: int = 0
    height: int = 0
    duration: float = 0.0
    timestamp: float = 0.0
    format: str = "jpg"
    size_bytes: int = 0


class ScreenCapture(BaseModel):
    """Ekran yakalama sonucu."""
    capture_id: str = ""
    node_id: str = ""
    capture_type: str = "screenshot"
    filepath: str = ""
    width: int = 0
    height: int = 0
    duration: float = 0.0
    timestamp: float = 0.0
    format: str = "png"


class LocationData(BaseModel):
    """Konum verisi."""
    node_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    accuracy: float = 0.0
    timestamp: float = 0.0
    source: str = "gps"
    address: str = ""


class NodeNotification(BaseModel):
    """Cihaz bildirimi."""
    notification_id: str = ""
    node_id: str = ""
    title: str = ""
    body: str = ""
    priority: str = "normal"
    sent_at: float = 0.0
    delivered: bool = False


class NodeHealthCheck(BaseModel):
    """Dugum saglik kontrolu sonucu."""
    node_id: str = ""
    status: NodeStatus = NodeStatus.OFFLINE
    latency_ms: float = 0.0
    last_check: float = 0.0
    consecutive_failures: int = 0
    auto_reconnect: bool = True


class NodesConfig(BaseModel):
    """Nodes sistemi genel yapilandirmasi."""
    heartbeat_interval: int = 30
    max_nodes: int = 50
    auto_reconnect: bool = True
    reconnect_max_retries: int = 5
    capture_dir: str = "workspace/captures"
    max_capture_size: int = 52428800
    location_cache_ttl: int = 60
