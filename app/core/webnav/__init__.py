"""ATLAS Intelligent Web Navigator sistemi.

Tarayıcı otomasyonu, form doldurma,
giriş yönetimi, sayfalama, captcha çözme,
ekran görüntüsü, yapısal veri çıkarma,
gezinti kayıt, orkestrasyon.
"""

from app.core.webnav.browser_automation import (
    BrowserAutomation,
)
from app.core.webnav.captcha_solver import (
    CaptchaSolver,
)
from app.core.webnav.form_filler import (
    FormFiller,
)
from app.core.webnav.login_manager import (
    LoginManager,
)
from app.core.webnav.navigation_recorder import (
    NavigationRecorder,
)
from app.core.webnav.pagination_handler import (
    PaginationHandler,
)
from app.core.webnav.screenshot_capture import (
    ScreenshotCapture,
)
from app.core.webnav.structured_data_extractor import (
    StructuredDataExtractor,
)
from app.core.webnav.webnav_orchestrator import (
    WebNavOrchestrator,
)

__all__ = [
    "BrowserAutomation",
    "CaptchaSolver",
    "FormFiller",
    "LoginManager",
    "NavigationRecorder",
    "PaginationHandler",
    "ScreenshotCapture",
    "StructuredDataExtractor",
    "WebNavOrchestrator",
]
