"""
Unified Dashboard & Control Panel modelleri.

Gösterge paneli, widget, veri akışı,
görünüm, dışa aktarma modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class WidgetType(str, Enum):
    """Widget türleri."""

    chart = "chart"
    table = "table"
    metric = "metric"
    gauge = "gauge"
    timeline = "timeline"
    map_widget = "map_widget"


class DashboardTheme(str, Enum):
    """Gösterge paneli temaları."""

    light = "light"
    dark = "dark"
    system = "system"
    custom = "custom"
    high_contrast = "high_contrast"


class ExportFormat(str, Enum):
    """Dışa aktarma formatları."""

    pdf = "pdf"
    png = "png"
    csv = "csv"
    json = "json"
    excel = "excel"
    html = "html"


class StreamStatus(str, Enum):
    """Akış durumları."""

    connected = "connected"
    disconnected = "disconnected"
    reconnecting = "reconnecting"
    paused = "paused"
    error = "error"


class LayoutMode(str, Enum):
    """Düzen modları."""

    grid = "grid"
    freeform = "freeform"
    stacked = "stacked"
    responsive = "responsive"
    compact = "compact"


class PlatformType(str, Enum):
    """Platform türleri."""

    web = "web"
    mobile = "mobile"
    telegram = "telegram"
    desktop = "desktop"
    tablet = "tablet"
    api = "api"


class DashboardRecord(BaseModel):
    """Gösterge paneli kaydı."""

    dashboard_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    theme: str = "dark"
    layout: str = "grid"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class WidgetRecord(BaseModel):
    """Widget kaydı."""

    widget_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    widget_type: str = "metric"
    dashboard_id: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ViewRecord(BaseModel):
    """Görünüm kaydı."""

    view_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    name: str = ""
    filters: list = Field(default_factory=list)
    columns: list = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


class ExportRecord(BaseModel):
    """Dışa aktarma kaydı."""

    export_id: str = Field(
        default_factory=lambda: str(uuid4())[:8]
    )
    format: str = "pdf"
    dashboard_id: str = ""
    status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )
