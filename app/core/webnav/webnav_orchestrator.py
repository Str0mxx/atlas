"""ATLAS Web Gezgini Orkestratörü modülü.

Tam web gezinti pipeline'ı,
Navigate → Interact → Extract → Record,
çoklu site yönetimi, analitik.
"""

import logging
from typing import Any

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

logger = logging.getLogger(__name__)


class WebNavOrchestrator:
    """Web gezgini orkestratörü.

    Tüm web gezinti bileşenlerini koordine eder.

    Attributes:
        browser: Tarayıcı otomasyonu.
        filler: Form doldurucusu.
        login: Giriş yöneticisi.
        pagination: Sayfalama işleyicisi.
        captcha: Captcha çözücü.
        screenshot: Ekran görüntüsü.
        extractor: Veri çıkarıcı.
        recorder: Gezinti kaydedici.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        screenshot_on_error: bool = True,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            headless: Headless mod.
            timeout: Zaman aşımı.
            screenshot_on_error: Hatada SS al.
        """
        self.browser = BrowserAutomation(
            headless=headless,
            timeout=timeout,
        )
        self.filler = FormFiller()
        self.login = LoginManager()
        self.pagination = PaginationHandler()
        self.captcha = CaptchaSolver()
        self.screenshot = ScreenshotCapture()
        self.extractor = (
            StructuredDataExtractor()
        )
        self.recorder = NavigationRecorder()

        self._screenshot_on_error = (
            screenshot_on_error
        )
        self._stats = {
            "navigations_completed": 0,
            "extractions_completed": 0,
            "errors": 0,
        }

        logger.info(
            "WebNavOrchestrator baslatildi",
        )

    def navigate_and_extract(
        self,
        url: str,
        extract_tables: bool = True,
        extract_lists: bool = False,
        take_screenshot: bool = False,
        record: bool = True,
    ) -> dict[str, Any]:
        """Gezinti ve çıkarma pipeline'ı.

        Args:
            url: Hedef URL.
            extract_tables: Tablo çıkar.
            extract_lists: Liste çıkar.
            take_screenshot: SS al.
            record: Kayıt yap.

        Returns:
            Pipeline sonucu.
        """
        # Kayıt başlat
        recording_id = None
        if record:
            rec = self.recorder.start_recording(
                name=f"nav_{url[:30]}",
            )
            recording_id = rec["recording_id"]

        # 1) Navigate
        nav = self.browser.navigate(url)
        page_id = nav["page_id"]

        if record and recording_id:
            self.recorder.record_action(
                "navigate",
                {"url": url, "page_id": page_id},
            )

        # 2) Get content
        content = self.browser.get_page_content(
            page_id,
        )
        html = content.get("html", "")

        # 3) Captcha check
        captcha_check = self.captcha.detect(html)
        if captcha_check["has_captcha"]:
            self.captcha.solve(
                captcha_check["captcha_type"],
                page_url=url,
            )

        # 4) Extract
        extractions = {}
        if extract_tables:
            table = self.extractor.extract_table(
                html,
            )
            extractions["table"] = table
            self._stats[
                "extractions_completed"
            ] += 1

        if extract_lists:
            lst = self.extractor.extract_list(
                html,
            )
            extractions["list"] = lst
            self._stats[
                "extractions_completed"
            ] += 1

        # 5) Screenshot
        screenshot_data = None
        if take_screenshot:
            screenshot_data = (
                self.screenshot.capture_full_page(
                    url,
                )
            )

        # Stop recording
        if record and recording_id:
            self.recorder.stop_recording(
                recording_id,
            )

        self._stats[
            "navigations_completed"
        ] += 1

        return {
            "success": True,
            "url": url,
            "page_id": page_id,
            "extractions": extractions,
            "screenshot": screenshot_data,
            "recording_id": recording_id,
            "captcha_detected": (
                captcha_check["has_captcha"]
            ),
        }

    def login_and_navigate(
        self,
        site: str,
        login_url: str,
        target_url: str,
    ) -> dict[str, Any]:
        """Giriş yapıp gezinir.

        Args:
            site: Site adı.
            login_url: Giriş URL.
            target_url: Hedef URL.

        Returns:
            Gezinti bilgisi.
        """
        # Login
        login_result = self.login.login(
            site=site, url=login_url,
        )

        if login_result.get("error"):
            return {
                "success": False,
                "error": login_result["error"],
            }

        # Navigate to target
        nav = self.browser.navigate(target_url)

        self._stats[
            "navigations_completed"
        ] += 1

        return {
            "success": True,
            "session_id": login_result[
                "session_id"
            ],
            "page_id": nav["page_id"],
            "url": target_url,
        }

    def collect_paginated_data(
        self,
        url: str,
        max_pages: int = 10,
    ) -> dict[str, Any]:
        """Sayfalı veri toplar.

        Args:
            url: Başlangıç URL.
            max_pages: Maks sayfa.

        Returns:
            Toplama bilgisi.
        """
        # Navigate
        nav = self.browser.navigate(url)
        content = self.browser.get_page_content(
            nav["page_id"],
        )
        html = content.get("html", "")

        # Pagination detect
        pag_info = (
            self.pagination.detect_pagination(
                html,
            )
        )

        # Handle pagination
        pag_result = (
            self.pagination.handle_pagination(
                url=url,
                pagination_type=pag_info[
                    "type"
                ],
                max_pages=max_pages,
            )
        )

        self._stats[
            "navigations_completed"
        ] += 1

        return {
            "success": True,
            "url": url,
            "pagination_type": pag_info["type"],
            "pages_collected": pag_result[
                "pages_collected"
            ],
            "pagination_id": pag_result[
                "pagination_id"
            ],
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "navigations_completed": (
                self._stats[
                    "navigations_completed"
                ]
            ),
            "extractions_completed": (
                self._stats[
                    "extractions_completed"
                ]
            ),
            "errors": self._stats["errors"],
            "pages_navigated": (
                self.browser.navigated_count
            ),
            "forms_filled": (
                self.filler.form_count
            ),
            "logins": (
                self.login.login_count
            ),
            "captchas_solved": (
                self.captcha.solved_count
            ),
            "screenshots_taken": (
                self.screenshot.capture_count
            ),
            "tables_extracted": (
                self.extractor.table_count
            ),
            "recordings": (
                self.recorder.recording_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "navigations_completed": (
                self._stats[
                    "navigations_completed"
                ]
            ),
            "open_pages": (
                self.browser.page_count
            ),
            "active_sessions": (
                self.login.active_session_count
            ),
            "extractions": (
                self._stats[
                    "extractions_completed"
                ]
            ),
        }

    @property
    def navigation_count(self) -> int:
        """Gezinti sayısı."""
        return self._stats[
            "navigations_completed"
        ]
