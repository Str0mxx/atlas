"""ATLAS Intelligent Web Navigator testleri.

BrowserAutomation, FormFiller, LoginManager,
PaginationHandler, CaptchaSolver, ScreenshotCapture,
StructuredDataExtractor, NavigationRecorder,
WebNavOrchestrator testleri.
"""

import pytest

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


# ── BrowserAutomation ──────────────────────


class TestBrowserAutomationInit:
    """BrowserAutomation başlatma testleri."""

    def test_default_init(self):
        ba = BrowserAutomation()
        assert ba._headless is True
        assert ba._timeout == 30
        assert ba.page_count == 0
        assert ba.navigated_count == 0

    def test_custom_init(self):
        ba = BrowserAutomation(
            headless=False, timeout=60,
        )
        assert ba._headless is False
        assert ba._timeout == 60

    def test_empty_history(self):
        ba = BrowserAutomation()
        assert ba.get_history() == []

    def test_interaction_count_zero(self):
        ba = BrowserAutomation()
        assert ba.interaction_count == 0


class TestBrowserAutomationNavigate:
    """BrowserAutomation gezinti testleri."""

    def test_navigate_basic(self):
        ba = BrowserAutomation()
        result = ba.navigate("https://example.com")
        assert result["page_id"] == "page_1"
        assert result["url"] == "https://example.com"
        assert result["status"] == "loaded"
        assert result["status_code"] == 200

    def test_navigate_increments_count(self):
        ba = BrowserAutomation()
        ba.navigate("https://a.com")
        ba.navigate("https://b.com")
        assert ba.navigated_count == 2
        assert ba.page_count == 2

    def test_navigate_unique_page_ids(self):
        ba = BrowserAutomation()
        r1 = ba.navigate("https://a.com")
        r2 = ba.navigate("https://b.com")
        assert r1["page_id"] != r2["page_id"]

    def test_navigate_records_history(self):
        ba = BrowserAutomation()
        ba.navigate("https://example.com")
        h = ba.get_history()
        assert len(h) == 1
        assert h[0]["action"] == "navigate"
        assert h[0]["url"] == "https://example.com"

    def test_navigate_load_time(self):
        ba = BrowserAutomation()
        r = ba.navigate("https://example.com")
        assert "load_time_ms" in r
        assert r["load_time_ms"] > 0


class TestBrowserAutomationInteract:
    """BrowserAutomation etkileşim testleri."""

    def test_click_success(self):
        ba = BrowserAutomation()
        nav = ba.navigate("https://example.com")
        result = ba.click(nav["page_id"], "#btn")
        assert result["clicked"] is True
        assert ba.interaction_count == 1

    def test_click_page_not_found(self):
        ba = BrowserAutomation()
        result = ba.click("invalid", "#btn")
        assert result["error"] == "page_not_found"

    def test_type_text_success(self):
        ba = BrowserAutomation()
        nav = ba.navigate("https://example.com")
        result = ba.type_text(
            nav["page_id"], "#input", "hello",
        )
        assert result["typed"] is True
        assert result["text_length"] == 5

    def test_type_text_page_not_found(self):
        ba = BrowserAutomation()
        result = ba.type_text(
            "invalid", "#input", "text",
        )
        assert result["error"] == "page_not_found"

    def test_execute_js_success(self):
        ba = BrowserAutomation()
        nav = ba.navigate("https://example.com")
        result = ba.execute_js(
            nav["page_id"], "return 1+1",
        )
        assert result["executed"] is True

    def test_execute_js_page_not_found(self):
        ba = BrowserAutomation()
        result = ba.execute_js(
            "invalid", "script",
        )
        assert result["error"] == "page_not_found"

    def test_screenshot_success(self):
        ba = BrowserAutomation()
        nav = ba.navigate("https://example.com")
        result = ba.screenshot(nav["page_id"])
        assert result["captured"] is True
        assert "screenshot_id" in result

    def test_screenshot_page_not_found(self):
        ba = BrowserAutomation()
        result = ba.screenshot("invalid")
        assert result["error"] == "page_not_found"


class TestBrowserAutomationPage:
    """BrowserAutomation sayfa yönetimi testleri."""

    def test_get_page_content(self):
        ba = BrowserAutomation()
        nav = ba.navigate("https://example.com")
        content = ba.get_page_content(
            nav["page_id"],
        )
        assert "html" in content
        assert "text" in content
        assert content["url"] == "https://example.com"

    def test_get_page_content_not_found(self):
        ba = BrowserAutomation()
        result = ba.get_page_content("invalid")
        assert result["error"] == "page_not_found"

    def test_close_page(self):
        ba = BrowserAutomation()
        nav = ba.navigate("https://example.com")
        assert ba.page_count == 1
        result = ba.close_page(nav["page_id"])
        assert result["closed"] is True
        assert ba.page_count == 0

    def test_close_page_not_found(self):
        ba = BrowserAutomation()
        result = ba.close_page("invalid")
        assert result["error"] == "page_not_found"

    def test_history_limit(self):
        ba = BrowserAutomation()
        for i in range(5):
            ba.navigate(f"https://site{i}.com")
        h = ba.get_history(limit=3)
        assert len(h) == 3


# ── FormFiller ──────────────────────────────


class TestFormFillerInit:
    """FormFiller başlatma testleri."""

    def test_default_init(self):
        ff = FormFiller()
        assert ff.form_count == 0
        assert ff.field_count == 0
        assert ff.upload_count == 0

    def test_field_mappings(self):
        ff = FormFiller()
        assert "name" in ff._field_mappings
        assert "email" in ff._field_mappings


class TestFormFillerDetect:
    """FormFiller alan tespiti testleri."""

    def test_detect_fields_basic(self):
        ff = FormFiller()
        result = ff.detect_fields(
            "<input name='email' type='email'>",
        )
        assert result["field_count"] >= 1
        assert "fields" in result

    def test_detect_fields_multiple(self):
        ff = FormFiller()
        html = (
            "<form>"
            "<input name='name'>"
            "<input name='email'>"
            "<input name='phone'>"
            "</form>"
        )
        result = ff.detect_fields(html)
        assert result["field_count"] >= 3

    def test_detect_fields_has_required(self):
        ff = FormFiller()
        result = ff.detect_fields(
            "<input name='name'>",
        )
        assert result["has_required"] is True

    def test_detect_fields_no_match(self):
        ff = FormFiller()
        result = ff.detect_fields(
            "<div>nothing here</div>",
        )
        assert result["field_count"] == 0


class TestFormFillerFill:
    """FormFiller doldurma testleri."""

    def test_fill_form_success(self):
        ff = FormFiller()
        fields = [
            {"name": "name", "type": "text", "required": True},
            {"name": "email", "type": "email", "required": True},
        ]
        data = {"name": "Test", "email": "a@b.com"}
        result = ff.fill_form(fields, data)
        assert result["success"] is True
        assert result["filled_count"] == 2
        assert ff.form_count == 1

    def test_fill_form_missing_required(self):
        ff = FormFiller()
        fields = [
            {"name": "name", "type": "text", "required": True},
        ]
        result = ff.fill_form(fields, {})
        assert result["success"] is False
        assert result["error_count"] == 1

    def test_fill_form_with_profile(self):
        ff = FormFiller()
        ff.create_profile(
            "default", {"name": "John"},
        )
        fields = [
            {"name": "name", "type": "text", "required": True},
        ]
        result = ff.fill_form(
            fields, {}, profile_id="prof_default",
        )
        assert result["success"] is True

    def test_fill_multistep(self):
        ff = FormFiller()
        steps = [
            {"fields": [
                {"name": "name", "type": "text", "required": False},
            ]},
            {"fields": [
                {"name": "email", "type": "email", "required": False},
            ]},
        ]
        data = {"name": "Test", "email": "a@b.com"}
        result = ff.fill_multistep(steps, data)
        assert result["steps_completed"] == 2
        assert result["all_success"] is True

    def test_fill_multistep_partial_fail(self):
        ff = FormFiller()
        steps = [
            {"fields": [
                {"name": "name", "type": "text", "required": True},
            ]},
        ]
        result = ff.fill_multistep(steps, {})
        assert result["all_success"] is False


class TestFormFillerMisc:
    """FormFiller yardımcı testleri."""

    def test_upload_file(self):
        ff = FormFiller()
        result = ff.upload_file(
            "#file", "/path/to/file.pdf",
        )
        assert result["uploaded"] is True
        assert ff.upload_count == 1

    def test_handle_validation(self):
        ff = FormFiller()
        errors = [
            {"name": "email", "error": "invalid"},
        ]
        result = ff.handle_validation(errors)
        assert result["handled_count"] == 1
        assert len(result["suggestions"]) == 1

    def test_create_profile(self):
        ff = FormFiller()
        result = ff.create_profile(
            "work", {"name": "Test"},
        )
        assert result["created"] is True
        assert result["profile_id"] == "prof_work"

    def test_get_fills(self):
        ff = FormFiller()
        fields = [
            {"name": "x", "type": "text", "required": False},
        ]
        ff.fill_form(fields, {"x": "v"})
        assert len(ff.get_fills()) == 1


# ── LoginManager ────────────────────────────


class TestLoginManagerInit:
    """LoginManager başlatma testleri."""

    def test_default_init(self):
        lm = LoginManager()
        assert lm.login_count == 0
        assert lm.active_session_count == 0
        assert lm.mfa_count == 0

    def test_no_active_sessions(self):
        lm = LoginManager()
        assert lm.get_active_sessions() == []


class TestLoginManagerCredentials:
    """LoginManager kimlik bilgisi testleri."""

    def test_store_credentials(self):
        lm = LoginManager()
        result = lm.store_credentials(
            "github", "user", "pass",
        )
        assert result["stored"] is True
        assert result["site"] == "github"
        assert result["has_mfa"] is False

    def test_store_with_mfa(self):
        lm = LoginManager()
        result = lm.store_credentials(
            "bank", "user", "pass", mfa_secret="secret",
        )
        assert result["has_mfa"] is True


class TestLoginManagerLogin:
    """LoginManager giriş testleri."""

    def test_login_success(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        result = lm.login("site", "https://site.com")
        assert result["logged_in"] is True
        assert "session_id" in result
        assert lm.login_count == 1

    def test_login_no_credentials(self):
        lm = LoginManager()
        result = lm.login("unknown")
        assert "error" in result

    def test_login_creates_session(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        result = lm.login("site")
        assert lm.active_session_count == 1
        sessions = lm.get_active_sessions()
        assert len(sessions) == 1

    def test_login_creates_cookies(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        result = lm.login("site")
        cookies = lm.get_cookies(result["session_id"])
        assert len(cookies) >= 1


class TestLoginManagerSession:
    """LoginManager oturum yönetimi testleri."""

    def test_handle_mfa(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        login = lm.login("site")
        result = lm.handle_mfa(
            login["session_id"], "123456",
        )
        assert result["mfa_verified"] is True
        assert lm.mfa_count == 1

    def test_handle_mfa_invalid_session(self):
        lm = LoginManager()
        result = lm.handle_mfa("invalid", "code")
        assert "error" in result

    def test_get_session(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        login = lm.login("site")
        session = lm.get_session(
            login["session_id"],
        )
        assert session["status"] == "active"

    def test_get_session_not_found(self):
        lm = LoginManager()
        result = lm.get_session("invalid")
        assert "error" in result

    def test_refresh_session(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        login = lm.login("site")
        result = lm.refresh_session(
            login["session_id"],
        )
        assert result["refreshed"] is True

    def test_refresh_session_not_found(self):
        lm = LoginManager()
        result = lm.refresh_session("invalid")
        assert "error" in result

    def test_logout(self):
        lm = LoginManager()
        lm.store_credentials("site", "u", "p")
        login = lm.login("site")
        result = lm.logout(login["session_id"])
        assert result["logged_out"] is True
        assert lm.active_session_count == 0

    def test_logout_not_found(self):
        lm = LoginManager()
        result = lm.logout("invalid")
        assert "error" in result


# ── PaginationHandler ───────────────────────


class TestPaginationHandlerInit:
    """PaginationHandler başlatma testleri."""

    def test_default_init(self):
        ph = PaginationHandler()
        assert ph.pagination_count == 0
        assert ph.pages_collected == 0
        assert ph.items_aggregated == 0

    def test_custom_max_pages(self):
        ph = PaginationHandler(max_pages=100)
        assert ph._max_pages == 100


class TestPaginationHandlerDetect:
    """PaginationHandler tespit testleri."""

    def test_detect_next_button(self):
        ph = PaginationHandler()
        result = ph.detect_pagination(
            "<a>Next Page</a>",
        )
        assert result["has_pagination"] is True
        assert result["type"] == "next_button"

    def test_detect_load_more(self):
        ph = PaginationHandler()
        result = ph.detect_pagination(
            "<button>Load More</button>",
        )
        assert result["type"] == "load_more"

    def test_detect_infinite_scroll(self):
        ph = PaginationHandler()
        result = ph.detect_pagination(
            "<div data-scroll='true'>scroll</div>",
        )
        assert result["type"] == "infinite_scroll"

    def test_detect_numbered(self):
        ph = PaginationHandler()
        result = ph.detect_pagination(
            "<a>page 1</a><a>page 2</a>",
        )
        assert result["type"] == "numbered"

    def test_detect_none(self):
        ph = PaginationHandler()
        result = ph.detect_pagination(
            "<div>simple content</div>",
        )
        assert result["has_pagination"] is False
        assert result["type"] == "none"


class TestPaginationHandlerHandle:
    """PaginationHandler işleme testleri."""

    def test_handle_pagination(self):
        ph = PaginationHandler()
        result = ph.handle_pagination(
            "https://example.com",
            pagination_type="next_button",
        )
        assert "pagination_id" in result
        assert result["pages_collected"] > 0
        assert ph.pagination_count == 1

    def test_handle_pagination_max_pages(self):
        ph = PaginationHandler()
        result = ph.handle_pagination(
            "https://example.com", max_pages=3,
        )
        assert result["pages_collected"] <= 3

    def test_handle_infinite_scroll(self):
        ph = PaginationHandler()
        result = ph.handle_infinite_scroll(
            "https://example.com", max_scrolls=3,
        )
        assert result["type"] == "infinite_scroll"
        assert result["items_loaded"] > 0

    def test_handle_load_more(self):
        ph = PaginationHandler()
        result = ph.handle_load_more(
            "https://example.com", max_clicks=3,
        )
        assert result["type"] == "load_more"
        assert result["completed"] is True

    def test_aggregate_data(self):
        ph = PaginationHandler()
        result = ph.handle_pagination(
            "https://example.com",
        )
        agg = ph.aggregate_data(
            result["pagination_id"],
            [{"item": "a"}, {"item": "b"}],
        )
        assert agg["new_items"] == 2
        assert agg["total_items"] == 2
        assert ph.items_aggregated == 2

    def test_get_aggregated(self):
        ph = PaginationHandler()
        result = ph.handle_pagination(
            "https://example.com",
        )
        ph.aggregate_data(
            result["pagination_id"],
            [{"x": 1}],
        )
        data = ph.get_aggregated(
            result["pagination_id"],
        )
        assert len(data) == 1

    def test_get_aggregated_empty(self):
        ph = PaginationHandler()
        data = ph.get_aggregated("nonexistent")
        assert data == []


# ── CaptchaSolver ───────────────────────────


class TestCaptchaSolverInit:
    """CaptchaSolver başlatma testleri."""

    def test_default_init(self):
        cs = CaptchaSolver()
        assert cs.detected_count == 0
        assert cs.solved_count == 0
        assert cs.escalation_count == 0

    def test_custom_max_attempts(self):
        cs = CaptchaSolver(max_attempts=5)
        assert cs._max_attempts == 5


class TestCaptchaSolverDetect:
    """CaptchaSolver tespit testleri."""

    def test_detect_recaptcha(self):
        cs = CaptchaSolver()
        result = cs.detect(
            "<div class='g-recaptcha'></div>",
        )
        assert result["has_captcha"] is True
        assert result["captcha_type"] == "recaptcha_v2"

    def test_detect_hcaptcha(self):
        cs = CaptchaSolver()
        result = cs.detect(
            "<div class='h-captcha hcaptcha'></div>",
        )
        assert result["has_captcha"] is True
        assert result["captcha_type"] == "hcaptcha"

    def test_detect_image_captcha(self):
        cs = CaptchaSolver()
        result = cs.detect(
            "<img src='captcha.png'>",
        )
        assert result["has_captcha"] is True
        assert result["captcha_type"] == "image"

    def test_detect_no_captcha(self):
        cs = CaptchaSolver()
        result = cs.detect(
            "<div>normal content</div>",
        )
        assert result["has_captcha"] is False
        assert result["captcha_type"] is None

    def test_detect_increments_stats(self):
        cs = CaptchaSolver()
        cs.detect("<div class='recaptcha'></div>")
        assert cs.detected_count == 1


class TestCaptchaSolverSolve:
    """CaptchaSolver çözme testleri."""

    def test_solve_success(self):
        cs = CaptchaSolver()
        result = cs.solve(
            "recaptcha_v2",
            page_url="https://example.com",
        )
        assert result["solved"] is True
        assert result["token"] is not None
        assert cs.solved_count == 1

    def test_solve_returns_id(self):
        cs = CaptchaSolver()
        result = cs.solve("image")
        assert result["solve_id"].startswith("cap_")

    def test_register_service(self):
        cs = CaptchaSolver()
        result = cs.register_service(
            "2captcha", api_key="key123",
            types=["recaptcha_v2", "image"],
        )
        assert result["registered"] is True

    def test_escalate_to_human(self):
        cs = CaptchaSolver()
        result = cs.escalate_to_human(
            "complex_captcha",
            reason="too_difficult",
        )
        assert result["escalated"] is True
        assert cs.escalation_count == 1

    def test_get_solves(self):
        cs = CaptchaSolver()
        cs.solve("image")
        solves = cs.get_solves()
        assert len(solves) == 1


# ── ScreenshotCapture ───────────────────────


class TestScreenshotCaptureInit:
    """ScreenshotCapture başlatma testleri."""

    def test_default_init(self):
        sc = ScreenshotCapture()
        assert sc.capture_count == 0
        assert sc.comparison_count == 0
        assert sc._default_width == 1920
        assert sc._default_height == 1080

    def test_custom_init(self):
        sc = ScreenshotCapture(
            default_width=1280,
            default_height=720,
        )
        assert sc._default_width == 1280
        assert sc._default_height == 720


class TestScreenshotCaptureCapture:
    """ScreenshotCapture yakalama testleri."""

    def test_capture_full_page(self):
        sc = ScreenshotCapture()
        result = sc.capture_full_page(
            "https://example.com",
        )
        assert result["type"] == "full_page"
        assert "screenshot_id" in result
        assert result["file_path"].endswith(".png")
        assert sc.capture_count == 1

    def test_capture_full_page_custom_width(self):
        sc = ScreenshotCapture()
        result = sc.capture_full_page(
            "https://example.com", width=1280,
        )
        assert result["width"] == 1280

    def test_capture_element(self):
        sc = ScreenshotCapture()
        result = sc.capture_element(
            "https://example.com", "#header",
        )
        assert result["type"] == "element"
        assert result["selector"] == "#header"

    def test_capture_viewport(self):
        sc = ScreenshotCapture()
        result = sc.capture_viewport(
            "https://example.com",
        )
        assert result["type"] == "viewport"
        assert result["width"] == 1920
        assert result["height"] == 1080

    def test_capture_viewport_custom(self):
        sc = ScreenshotCapture()
        result = sc.capture_viewport(
            "https://example.com",
            width=800, height=600,
        )
        assert result["width"] == 800
        assert result["height"] == 600

    def test_multiple_captures(self):
        sc = ScreenshotCapture()
        sc.capture_full_page("https://a.com")
        sc.capture_element("https://b.com", "#x")
        sc.capture_viewport("https://c.com")
        assert sc.capture_count == 3


class TestScreenshotCaptureAnnotate:
    """ScreenshotCapture açıklama testleri."""

    def test_annotate(self):
        sc = ScreenshotCapture()
        cap = sc.capture_full_page(
            "https://example.com",
        )
        result = sc.annotate(
            cap["screenshot_id"],
            [{"type": "arrow", "x": 100, "y": 200}],
        )
        assert result["annotations_added"] == 1
        assert result["total_annotations"] == 1

    def test_annotate_multiple(self):
        sc = ScreenshotCapture()
        cap = sc.capture_full_page(
            "https://example.com",
        )
        sc.annotate(
            cap["screenshot_id"],
            [{"type": "box"}],
        )
        result = sc.annotate(
            cap["screenshot_id"],
            [{"type": "text"}, {"type": "arrow"}],
        )
        assert result["total_annotations"] == 3


class TestScreenshotCaptureCompare:
    """ScreenshotCapture karşılaştırma testleri."""

    def test_compare_same_size(self):
        sc = ScreenshotCapture()
        c1 = sc.capture_viewport(
            "https://a.com",
        )
        c2 = sc.capture_viewport(
            "https://b.com",
        )
        result = sc.compare(
            c1["screenshot_id"],
            c2["screenshot_id"],
        )
        assert result["same_dimensions"] is True
        assert result["similarity_score"] == 0.95

    def test_compare_different_size(self):
        sc = ScreenshotCapture()
        c1 = sc.capture_full_page(
            "https://a.com",
        )
        c2 = sc.capture_element(
            "https://b.com", "#x",
        )
        result = sc.compare(
            c1["screenshot_id"],
            c2["screenshot_id"],
        )
        assert result["same_dimensions"] is False
        assert result["similarity_score"] == 0.5

    def test_compare_not_found(self):
        sc = ScreenshotCapture()
        result = sc.compare("x", "y")
        assert "error" in result

    def test_get_captures(self):
        sc = ScreenshotCapture()
        sc.capture_full_page("https://a.com")
        sc.capture_element("https://b.com", "#x")
        all_caps = sc.get_captures()
        assert len(all_caps) == 2

    def test_get_captures_filtered(self):
        sc = ScreenshotCapture()
        sc.capture_full_page("https://a.com")
        sc.capture_element("https://b.com", "#x")
        elements = sc.get_captures(
            capture_type="element",
        )
        assert len(elements) == 1


# ── StructuredDataExtractor ─────────────────


class TestStructuredDataExtractorInit:
    """StructuredDataExtractor başlatma testleri."""

    def test_default_init(self):
        sde = StructuredDataExtractor()
        assert sde.table_count == 0
        assert sde.list_count == 0
        assert sde.schema_count == 0
        assert sde.extraction_count == 0


class TestStructuredDataExtractorExtract:
    """StructuredDataExtractor çıkarma testleri."""

    def test_extract_table(self):
        sde = StructuredDataExtractor()
        result = sde.extract_table(
            "<table><tr><td>data</td></tr></table>",
        )
        assert result["type"] == "table"
        assert result["row_count"] > 0
        assert result["column_count"] > 0
        assert sde.table_count == 1

    def test_extract_table_custom_selector(self):
        sde = StructuredDataExtractor()
        result = sde.extract_table(
            "<html></html>",
            selector=".data-table",
        )
        assert result["selector"] == ".data-table"

    def test_extract_list(self):
        sde = StructuredDataExtractor()
        result = sde.extract_list(
            "<ul><li>item</li></ul>",
        )
        assert result["type"] == "list"
        assert result["item_count"] > 0
        assert sde.list_count == 1

    def test_extract_list_custom_selector(self):
        sde = StructuredDataExtractor()
        result = sde.extract_list(
            "<html></html>", selector="ol",
        )
        assert result["selector"] == "ol"

    def test_extraction_count(self):
        sde = StructuredDataExtractor()
        sde.extract_table("<table></table>")
        sde.extract_list("<ul></ul>")
        assert sde.extraction_count == 2


class TestStructuredDataExtractorSchema:
    """StructuredDataExtractor şema testleri."""

    def test_detect_json_ld(self):
        sde = StructuredDataExtractor()
        result = sde.detect_schema(
            '<script type="application/ld+json"></script>',
        )
        assert result["has_structured_data"] is True
        assert any(
            s["type"] == "json_ld"
            for s in result["schemas"]
        )

    def test_detect_microdata(self):
        sde = StructuredDataExtractor()
        result = sde.detect_schema(
            '<div itemscope itemtype="..."></div>',
        )
        assert result["has_structured_data"] is True
        assert any(
            s["type"] == "microdata"
            for s in result["schemas"]
        )

    def test_detect_open_graph(self):
        sde = StructuredDataExtractor()
        result = sde.detect_schema(
            '<meta property="og:title" content="Test">',
        )
        assert result["has_structured_data"] is True

    def test_detect_no_schema(self):
        sde = StructuredDataExtractor()
        result = sde.detect_schema(
            "<div>plain content</div>",
        )
        assert result["has_structured_data"] is False
        assert result["schemas_found"] == 0

    def test_parse_json_ld(self):
        sde = StructuredDataExtractor()
        result = sde.parse_json_ld(
            '{"@type": "Product", "name": "Test"}',
        )
        assert result["parsed"] is True
        assert result["type"] == "json_ld"


class TestStructuredDataExtractorNormalize:
    """StructuredDataExtractor normalleştirme testleri."""

    def test_normalize_data(self):
        sde = StructuredDataExtractor()
        data = [
            {"name": "  John  ", "age": "30"},
        ]
        result = sde.normalize_data(data)
        assert result["normalized_count"] == 1
        norm = result["normalized_data"][0]
        assert norm["name"] == "John"

    def test_normalize_with_schema(self):
        sde = StructuredDataExtractor()
        data = [{"fname": "Test"}]
        schema = {"fname": "first_name"}
        result = sde.normalize_data(data, schema)
        assert result["schema_applied"] is True
        norm = result["normalized_data"][0]
        assert "first_name" in norm

    def test_normalize_none_values(self):
        sde = StructuredDataExtractor()
        data = [{"x": None}]
        result = sde.normalize_data(data)
        assert result["normalized_data"][0]["x"] == ""

    def test_get_extractions(self):
        sde = StructuredDataExtractor()
        sde.extract_table("<table></table>")
        sde.extract_list("<ul></ul>")
        all_ext = sde.get_extractions()
        assert len(all_ext) == 2

    def test_get_extractions_filtered(self):
        sde = StructuredDataExtractor()
        sde.extract_table("<table></table>")
        sde.extract_list("<ul></ul>")
        tables = sde.get_extractions(
            extraction_type="table",
        )
        assert len(tables) == 1


# ── NavigationRecorder ──────────────────────


class TestNavigationRecorderInit:
    """NavigationRecorder başlatma testleri."""

    def test_default_init(self):
        nr = NavigationRecorder()
        assert nr.recording_count == 0
        assert nr.action_count == 0
        assert nr.replay_count == 0
        assert nr.error_count == 0


class TestNavigationRecorderRecording:
    """NavigationRecorder kayıt testleri."""

    def test_start_recording(self):
        nr = NavigationRecorder()
        result = nr.start_recording(
            name="test_recording",
        )
        assert result["started"] is True
        assert "recording_id" in result
        assert nr.recording_count == 1

    def test_start_recording_with_description(self):
        nr = NavigationRecorder()
        result = nr.start_recording(
            name="test",
            description="Test recording",
        )
        assert result["started"] is True

    def test_record_action(self):
        nr = NavigationRecorder()
        nr.start_recording(name="test")
        result = nr.record_action(
            "navigate",
            {"url": "https://example.com"},
        )
        assert result["recorded"] is True
        assert result["step"] == 1
        assert nr.action_count == 1

    def test_record_multiple_actions(self):
        nr = NavigationRecorder()
        nr.start_recording(name="test")
        nr.record_action("navigate", {"url": "a"})
        result = nr.record_action(
            "click", {"selector": "#btn"},
        )
        assert result["step"] == 2
        assert nr.action_count == 2

    def test_record_action_no_recording(self):
        nr = NavigationRecorder()
        result = nr.record_action(
            "navigate", {},
        )
        assert "error" in result

    def test_stop_recording(self):
        nr = NavigationRecorder()
        rec = nr.start_recording(name="test")
        nr.record_action("navigate", {"url": "a"})
        result = nr.stop_recording(
            rec["recording_id"],
        )
        assert result["stopped"] is True
        assert result["action_count"] == 1

    def test_stop_recording_not_found(self):
        nr = NavigationRecorder()
        result = nr.stop_recording("invalid")
        assert "error" in result

    def test_record_after_stop(self):
        nr = NavigationRecorder()
        rec = nr.start_recording(name="test")
        nr.stop_recording(rec["recording_id"])
        result = nr.record_action(
            "navigate", {},
            recording_id=rec["recording_id"],
        )
        assert "error" in result


class TestNavigationRecorderReplay:
    """NavigationRecorder tekrar oynatma testleri."""

    def test_replay(self):
        nr = NavigationRecorder()
        rec = nr.start_recording(name="test")
        nr.record_action("navigate", {"url": "a"})
        nr.record_action("click", {"selector": "#b"})
        nr.stop_recording(rec["recording_id"])
        result = nr.replay(rec["recording_id"])
        assert result["success"] is True
        assert result["steps_replayed"] == 2
        assert nr.replay_count == 1

    def test_replay_not_found(self):
        nr = NavigationRecorder()
        result = nr.replay("invalid")
        assert "error" in result

    def test_replay_empty_recording(self):
        nr = NavigationRecorder()
        rec = nr.start_recording(name="empty")
        nr.stop_recording(rec["recording_id"])
        result = nr.replay(rec["recording_id"])
        assert result["steps_replayed"] == 0


class TestNavigationRecorderMisc:
    """NavigationRecorder yardımcı testleri."""

    def test_log_error(self):
        nr = NavigationRecorder()
        result = nr.log_error(
            "page_timeout", step=3,
        )
        assert result["logged"] is True
        assert nr.error_count == 1

    def test_get_documentation(self):
        nr = NavigationRecorder()
        rec = nr.start_recording(name="doc_test")
        nr.record_action("navigate", {"url": "a"})
        nr.stop_recording(rec["recording_id"])
        doc = nr.get_documentation(
            rec["recording_id"],
        )
        assert doc["total_steps"] == 1
        assert len(doc["steps"]) == 1

    def test_get_documentation_not_found(self):
        nr = NavigationRecorder()
        result = nr.get_documentation("invalid")
        assert "error" in result

    def test_get_recordings(self):
        nr = NavigationRecorder()
        nr.start_recording(name="a")
        nr.start_recording(name="b")
        recordings = nr.get_recordings()
        assert len(recordings) == 2

    def test_get_recordings_filtered(self):
        nr = NavigationRecorder()
        rec = nr.start_recording(name="a")
        nr.stop_recording(rec["recording_id"])
        nr.start_recording(name="b")
        completed = nr.get_recordings(
            status="completed",
        )
        assert len(completed) == 1

    def test_get_audit_trail(self):
        nr = NavigationRecorder()
        nr.start_recording(name="test")
        trail = nr.get_audit_trail()
        assert len(trail) >= 1

    def test_get_error_log(self):
        nr = NavigationRecorder()
        nr.log_error("err1")
        nr.log_error("err2")
        errors = nr.get_error_log()
        assert len(errors) == 2


# ── WebNavOrchestrator ──────────────────────


class TestWebNavOrchestratorInit:
    """WebNavOrchestrator başlatma testleri."""

    def test_default_init(self):
        wno = WebNavOrchestrator()
        assert wno.navigation_count == 0
        assert wno.browser is not None
        assert wno.filler is not None
        assert wno.login is not None

    def test_custom_init(self):
        wno = WebNavOrchestrator(
            headless=False,
            timeout=60,
            screenshot_on_error=False,
        )
        assert wno.browser._headless is False
        assert wno.browser._timeout == 60
        assert wno._screenshot_on_error is False


class TestWebNavOrchestratorNavigate:
    """WebNavOrchestrator gezinti testleri."""

    def test_navigate_and_extract(self):
        wno = WebNavOrchestrator()
        result = wno.navigate_and_extract(
            "https://example.com",
        )
        assert result["success"] is True
        assert result["url"] == "https://example.com"
        assert "page_id" in result
        assert "table" in result["extractions"]
        assert wno.navigation_count == 1

    def test_navigate_and_extract_no_tables(self):
        wno = WebNavOrchestrator()
        result = wno.navigate_and_extract(
            "https://example.com",
            extract_tables=False,
        )
        assert "table" not in result["extractions"]

    def test_navigate_and_extract_with_lists(self):
        wno = WebNavOrchestrator()
        result = wno.navigate_and_extract(
            "https://example.com",
            extract_lists=True,
        )
        assert "list" in result["extractions"]

    def test_navigate_and_extract_screenshot(self):
        wno = WebNavOrchestrator()
        result = wno.navigate_and_extract(
            "https://example.com",
            take_screenshot=True,
        )
        assert result["screenshot"] is not None

    def test_navigate_and_extract_no_record(self):
        wno = WebNavOrchestrator()
        result = wno.navigate_and_extract(
            "https://example.com",
            record=False,
        )
        assert result["recording_id"] is None

    def test_navigate_and_extract_with_record(self):
        wno = WebNavOrchestrator()
        result = wno.navigate_and_extract(
            "https://example.com",
            record=True,
        )
        assert result["recording_id"] is not None


class TestWebNavOrchestratorLogin:
    """WebNavOrchestrator giriş testleri."""

    def test_login_and_navigate_success(self):
        wno = WebNavOrchestrator()
        wno.login.store_credentials(
            "site", "user", "pass",
        )
        result = wno.login_and_navigate(
            site="site",
            login_url="https://site.com/login",
            target_url="https://site.com/dashboard",
        )
        assert result["success"] is True
        assert "session_id" in result
        assert "page_id" in result

    def test_login_and_navigate_no_creds(self):
        wno = WebNavOrchestrator()
        result = wno.login_and_navigate(
            site="unknown",
            login_url="https://unknown.com/login",
            target_url="https://unknown.com/dashboard",
        )
        assert result["success"] is False
        assert "error" in result


class TestWebNavOrchestratorPagination:
    """WebNavOrchestrator sayfalama testleri."""

    def test_collect_paginated_data(self):
        wno = WebNavOrchestrator()
        result = wno.collect_paginated_data(
            "https://example.com/list",
        )
        assert result["success"] is True
        assert result["pages_collected"] > 0
        assert "pagination_id" in result

    def test_collect_paginated_max_pages(self):
        wno = WebNavOrchestrator()
        result = wno.collect_paginated_data(
            "https://example.com/list",
            max_pages=3,
        )
        assert result["pages_collected"] <= 3


class TestWebNavOrchestratorAnalytics:
    """WebNavOrchestrator analitik testleri."""

    def test_get_analytics(self):
        wno = WebNavOrchestrator()
        wno.navigate_and_extract(
            "https://example.com",
        )
        analytics = wno.get_analytics()
        assert analytics["navigations_completed"] >= 1
        assert "extractions_completed" in analytics
        assert "pages_navigated" in analytics
        assert "screenshots_taken" in analytics
        assert "recordings" in analytics

    def test_get_status(self):
        wno = WebNavOrchestrator()
        status = wno.get_status()
        assert "navigations_completed" in status
        assert "open_pages" in status
        assert "active_sessions" in status
        assert "extractions" in status

    def test_analytics_after_operations(self):
        wno = WebNavOrchestrator()
        wno.navigate_and_extract(
            "https://a.com",
        )
        wno.navigate_and_extract(
            "https://b.com",
            extract_lists=True,
        )
        analytics = wno.get_analytics()
        assert analytics["navigations_completed"] == 2
        assert analytics["extractions_completed"] >= 2


# ── Integration & __init__ ──────────────────


class TestWebNavImports:
    """Modül import testleri."""

    def test_import_all(self):
        from app.core.webnav import (
            BrowserAutomation,
            CaptchaSolver,
            FormFiller,
            LoginManager,
            NavigationRecorder,
            PaginationHandler,
            ScreenshotCapture,
            StructuredDataExtractor,
            WebNavOrchestrator,
        )
        assert BrowserAutomation is not None
        assert CaptchaSolver is not None
        assert FormFiller is not None
        assert LoginManager is not None
        assert NavigationRecorder is not None
        assert PaginationHandler is not None
        assert ScreenshotCapture is not None
        assert StructuredDataExtractor is not None
        assert WebNavOrchestrator is not None


class TestWebNavModels:
    """Model import testleri."""

    def test_import_enums(self):
        from app.models.webnav_models import (
            BrowserState,
            CaptchaType,
            ExtractionFormat,
            FormFieldType,
            NavigationAction,
            SessionStatus,
        )
        assert len(BrowserState) >= 1
        assert len(CaptchaType) >= 1
        assert len(ExtractionFormat) >= 1
        assert len(FormFieldType) >= 1
        assert len(NavigationAction) >= 1
        assert len(SessionStatus) >= 1

    def test_import_models(self):
        from app.models.webnav_models import (
            ExtractedData,
            NavigationRecord,
            ScreenshotRecord,
            WebNavSnapshot,
        )
        assert NavigationRecord is not None
        assert ExtractedData is not None
        assert ScreenshotRecord is not None
        assert WebNavSnapshot is not None

    def test_model_defaults(self):
        from app.models.webnav_models import (
            NavigationRecord,
        )
        record = NavigationRecord(
            url="https://example.com",
        )
        assert record.url == "https://example.com"
        assert record.record_id is not None


class TestWebNavConfig:
    """Config testleri."""

    def test_config_settings(self):
        from app.config import settings
        assert hasattr(settings, "webnav_enabled")
        assert hasattr(settings, "headless_mode")
        assert hasattr(settings, "page_timeout")
        assert hasattr(settings, "screenshot_on_error")
        assert hasattr(settings, "webnav_max_retries")

    def test_config_defaults(self):
        from app.config import settings
        assert settings.webnav_enabled is True
        assert settings.headless_mode is True
        assert settings.page_timeout == 30
        assert settings.screenshot_on_error is True
        assert settings.webnav_max_retries == 3
