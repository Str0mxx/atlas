"""ATLAS Intelligent Web Navigator modelleri.

Tarayıcı otomasyonu, form doldurma,
giriş yönetimi, sayfalama, captcha,
ekran görüntüsü, veri çıkarma, kayıt.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class BrowserState(str, Enum):
    """Tarayıcı durumu."""

    idle = "idle"
    navigating = "navigating"
    interacting = "interacting"
    extracting = "extracting"
    waiting = "waiting"
    error = "error"


class FormFieldType(str, Enum):
    """Form alan tipi."""

    text = "text"
    password = "password"
    email = "email"
    select = "select"
    checkbox = "checkbox"
    file = "file"


class CaptchaType(str, Enum):
    """Captcha tipi."""

    recaptcha_v2 = "recaptcha_v2"
    recaptcha_v3 = "recaptcha_v3"
    hcaptcha = "hcaptcha"
    image = "image"
    text = "text"
    invisible = "invisible"


class NavigationAction(str, Enum):
    """Gezinti aksiyonu."""

    click = "click"
    type_text = "type_text"
    scroll = "scroll"
    navigate = "navigate"
    screenshot = "screenshot"
    wait = "wait"


class ExtractionFormat(str, Enum):
    """Çıkarma formatı."""

    table = "table"
    list_items = "list_items"
    json_ld = "json_ld"
    microdata = "microdata"
    raw_text = "raw_text"
    structured = "structured"


class SessionStatus(str, Enum):
    """Oturum durumu."""

    active = "active"
    expired = "expired"
    refreshing = "refreshing"
    logged_out = "logged_out"
    mfa_required = "mfa_required"
    blocked = "blocked"


class NavigationRecord(BaseModel):
    """Gezinti kaydı."""

    record_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    url: str = ""
    action: NavigationAction = (
        NavigationAction.navigate
    )
    status: BrowserState = BrowserState.idle
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ExtractedData(BaseModel):
    """Çıkarılan veri."""

    data_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_url: str = ""
    format: ExtractionFormat = (
        ExtractionFormat.raw_text
    )
    row_count: int = 0
    content: dict[str, Any] = Field(
        default_factory=dict,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class ScreenshotRecord(BaseModel):
    """Ekran görüntüsü kaydı."""

    screenshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    url: str = ""
    capture_type: str = "full_page"
    width: int = 1920
    height: int = 1080
    file_path: str = ""
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )


class WebNavSnapshot(BaseModel):
    """Web gezgini sistem anlık görüntüsü."""

    snapshot_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    active_sessions: int = 0
    pages_navigated: int = 0
    forms_filled: int = 0
    data_extracted: int = 0
    screenshots_taken: int = 0
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )
