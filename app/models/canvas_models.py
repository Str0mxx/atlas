"""Live Canvas & A2UI Engine modelleri.

Gercek zamanli canvas render, A2UI bilesen sistemi,
WebSocket iletisimi ve oturum yonetimi icin veri modelleri.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    """A2UI bilesen turleri."""
    COLUMN = "column"
    ROW = "row"
    TEXT = "text"
    BUTTON = "button"
    INPUT = "input"
    IMAGE = "image"
    CARD = "card"
    CONTAINER = "container"


class CanvasCommand(str, Enum):
    """Canvas komut turleri."""
    SURFACE_UPDATE = "surfaceUpdate"
    BEGIN_RENDERING = "beginRendering"
    RESET = "reset"
    EVAL = "eval"
    SNAPSHOT = "snapshot"


class A2UIComponent(BaseModel):
    """A2UI bilesen modeli.

    Attributes:
        type: Bilesen turu
        id: Benzersiz bilesen kimligi
        props: Bilesen ozellikleri
        children: Alt bilesenler
        text: Metin icerigi
    """
    type: ComponentType = ComponentType.TEXT
    id: str = ""
    props: dict[str, Any] = Field(default_factory=dict)
    children: list["A2UIComponent"] = Field(default_factory=list)
    text: str = ""


class CanvasSession(BaseModel):
    """Canvas oturum modeli."""
    session_id: str = ""
    created_at: float = 0.0
    last_activity: float = 0.0
    root_dir: str = ""
    components: list[A2UIComponent] = Field(default_factory=list)
    is_active: bool = True


class CanvasPushRequest(BaseModel):
    """Canvas push istek modeli."""
    session_id: str = ""
    command: CanvasCommand = CanvasCommand.SURFACE_UPDATE
    html: str = ""
    js_code: str = ""
    components: list[A2UIComponent] = Field(default_factory=list)


class CanvasSnapshot(BaseModel):
    """Canvas ekran goruntusu modeli."""
    session_id: str = ""
    snapshot_id: str = ""
    filepath: str = ""
    width: int = 1920
    height: int = 1080
    timestamp: float = 0.0
    format: str = "png"


class WebSocketClient(BaseModel):
    """WebSocket istemci modeli."""
    client_id: str = ""
    session_id: str = ""
    connected_at: float = 0.0
    is_alive: bool = True
    capabilities: list[str] = Field(default_factory=list)


class CanvasConfig(BaseModel):
    """Canvas yapilandirma modeli."""
    port: int = 18793
    host: str = "0.0.0.0"
    max_sessions: int = 100
    session_timeout: int = 3600
    snapshot_dir: str = "workspace/canvas/snapshots"
    enable_js_eval: bool = False
    max_component_depth: int = 10
