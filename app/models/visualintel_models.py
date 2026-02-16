"""ATLAS Camera & Visual Intelligence modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ImageFormat(str, Enum):
    """Görüntü formatı."""

    JPEG = "jpeg"
    PNG = "png"
    BMP = "bmp"
    TIFF = "tiff"
    WEBP = "webp"


class DetectionType(str, Enum):
    """Tespit tipi."""

    OBJECT = "object"
    FACE = "face"
    TEXT = "text"
    ANOMALY = "anomaly"
    MOTION = "motion"


class SceneCategory(str, Enum):
    """Sahne kategorisi."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    INDUSTRIAL = "industrial"
    OFFICE = "office"
    RETAIL = "retail"


class StreamStatus(str, Enum):
    """Akış durumu."""

    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class AnomalySeverity(str, Enum):
    """Anomali ciddiyet seviyesi."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OCRLanguage(str, Enum):
    """OCR dil desteği."""

    TURKISH = "tr"
    ENGLISH = "en"
    GERMAN = "de"
    FRENCH = "fr"
    ARABIC = "ar"


class ImageRecord(BaseModel):
    """Görüntü kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    source: str = ""
    width: int = 0
    height: int = 0
    format: str = "jpeg"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class DetectionRecord(BaseModel):
    """Tespit kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    detection_type: str = "object"
    label: str = ""
    confidence: float = 0.0
    bounding_box: dict[str, float] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class StreamRecord(BaseModel):
    """Akış kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    stream_url: str = ""
    status: str = "active"
    fps: int = 30
    resolution: str = "1080p"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class VisualSearchRecord(BaseModel):
    """Görsel arama kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )[:8],
    )
    query_image: str = ""
    results_count: int = 0
    best_score: float = 0.0
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
