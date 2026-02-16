"""ATLAS Location & Geofence Intelligence modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class GeofenceShape(str, Enum):
    """Geofence şekil tipi."""

    CIRCLE = "circle"
    POLYGON = "polygon"
    RECTANGLE = "rectangle"


class TrackingStatus(str, Enum):
    """Takip durumu."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    LOST_SIGNAL = "lost_signal"


class AlertType(str, Enum):
    """Uyarı tipi."""

    ENTRY = "entry"
    EXIT = "exit"
    DWELL = "dwell"
    SPEEDING = "speeding"
    PROXIMITY = "proximity"


class VehicleStatus(str, Enum):
    """Araç durumu."""

    MOVING = "moving"
    IDLE = "idle"
    PARKED = "parked"
    MAINTENANCE = "maintenance"


class RouteStrategy(str, Enum):
    """Rota stratejisi."""

    FASTEST = "fastest"
    SHORTEST = "shortest"
    ECONOMICAL = "economical"
    BALANCED = "balanced"


class PrecisionLevel(str, Enum):
    """Konum hassasiyet seviyesi."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GeofenceRecord(BaseModel):
    """Geofence kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    zone_name: str = ""
    shape: str = "circle"
    center_lat: float = 0.0
    center_lon: float = 0.0
    radius_m: float = 100.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class LocationRecord(BaseModel):
    """Konum kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    device_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    accuracy_m: float = 0.0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class FleetRecord(BaseModel):
    """Filo kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    vehicle_id: str = ""
    driver_id: str = ""
    status: str = "idle"
    last_lat: float = 0.0
    last_lon: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RouteRecord(BaseModel):
    """Rota kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    origin_lat: float = 0.0
    origin_lon: float = 0.0
    dest_lat: float = 0.0
    dest_lon: float = 0.0
    strategy: str = "fastest"
    total_distance_km: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
