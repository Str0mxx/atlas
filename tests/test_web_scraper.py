"""WebScraper unit testleri.

Playwright ve httpx+BeautifulSoup ile web scraping
davranislari mock'larla test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.research import ScrapedPage
from app.tools.web_scraper import WebScraper


# === Init testleri ===


class TestWebScraperInit:
    """WebScraper baslatma testleri."""

    def test_default_config(self) -> None:
        """Varsayilan yapilandirma."""
        scraper = WebScraper()
        assert scraper.timeout == 30000
        assert scraper.user_agent == "ATLAS-WebScraper/1.0"
        assert scraper._playwright is None
        assert scraper._browser is None
        assert scraper._http_client is None

    def test_custom_config(self) -> None:
        """Ozel yapilandirma."""
        scraper = WebScraper(timeout=60000, user_agent="Custom/2.0")
        assert scraper.timeout == 60000
        assert scraper.user_agent == "Custom/2.0"


# === Context Manager testleri ===


class TestContextManager:
    """Async context manager testleri."""

    @pytest.mark.asyncio
    @patch("app.tools.web_scraper._PLAYWRIGHT_AVAILABLE", False)
    async def test_httpx_fallback(self) -> None:
        """Playwright yoksa httpx fallback."""
        scraper = WebScraper()
        scraper._use_playwright = False

        async with scraper:
            assert scraper._http_client is not None
            assert scraper._browser is None

        # Cikista temizlenir
        assert scraper._http_client is None

    @pytest.mark.asyncio
    async def test_playwright_failure_fallback(self) -> None:
        """Playwright baslatma hatasi httpx fallback."""
        scraper = WebScraper()
        scraper._use_playwright = True

        mock_pw = AsyncMock()
        mock_pw.start = AsyncMock(side_effect=Exception("Playwright error"))

        with patch("app.tools.web_scraper._PLAYWRIGHT_AVAILABLE", True), \
             patch("app.tools.web_scraper.async_playwright", return_value=mock_pw, create=True):
            async with scraper:
                assert scraper._use_playwright is False
                assert scraper._http_client is not None

    @pytest.mark.asyncio
    async def test_playwright_success(self) -> None:
        """Basarili Playwright baslatma."""
        scraper = WebScraper()
        scraper._use_playwright = True

        mock_browser = AsyncMock()
        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw = AsyncMock()
        mock_pw.start = AsyncMock(return_value=mock_pw_instance)

        with patch("app.tools.web_scraper._PLAYWRIGHT_AVAILABLE", True), \
             patch("app.tools.web_scraper.async_playwright", return_value=mock_pw, create=True):
            async with scraper:
                assert scraper._browser is mock_browser
                assert scraper._use_playwright is True

    @pytest.mark.asyncio
    @patch("app.tools.web_scraper._PLAYWRIGHT_AVAILABLE", False)
    async def test_aexit_cleanup(self) -> None:
        """Cikista tum kaynaklar temizlenir."""
        scraper = WebScraper()
        scraper._use_playwright = False

        async with scraper:
            assert scraper._http_client is not None

        assert scraper._http_client is None
        assert scraper._browser is None
        assert scraper._playwright is None


# === Scrape testleri ===


class TestScrape:
    """Scraping testleri."""

    @pytest.mark.asyncio
    async def test_scrape_routes_to_playwright(self) -> None:
        """Playwright aktifse Playwright kullanilir."""
        scraper = WebScraper()
        scraper._use_playwright = True
        scraper._browser = AsyncMock()

        mock_result = ScrapedPage(
            url="https://example.com",
            title="Example",
            content="Test content",
            success=True,
        )

        scraper._scrape_with_playwright = AsyncMock(return_value=mock_result)

        result = await scraper.scrape("https://example.com")

        scraper._scrape_with_playwright.assert_called_once_with("https://example.com")
        assert result.url == "https://example.com"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_scrape_routes_to_httpx(self) -> None:
        """Playwright deaktifse httpx kullanilir."""
        scraper = WebScraper()
        scraper._use_playwright = False

        mock_result = ScrapedPage(
            url="https://example.com",
            title="Example",
            content="Fallback content",
            success=True,
        )

        scraper._scrape_with_httpx = AsyncMock(return_value=mock_result)

        result = await scraper.scrape("https://example.com")

        scraper._scrape_with_httpx.assert_called_once_with("https://example.com")
        assert result.success is True


# === Playwright scraping testleri ===


class TestScrapeWithPlaywright:
    """Playwright ile scraping testleri."""

    @pytest.mark.asyncio
    async def test_playwright_scrape_success(self) -> None:
        """Basarili Playwright scraping."""
        scraper = WebScraper()
        scraper._use_playwright = True

        mock_response = MagicMock()
        mock_response.status = 200

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.evaluate = AsyncMock(
            side_effect=["Meta description", "Page content text"],
        )
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        scraper._browser = mock_browser

        result = await scraper._scrape_with_playwright("https://example.com")

        assert result.success is True
        assert result.url == "https://example.com"
        assert result.title == "Test Page"
        assert result.status_code == 200
        assert result.meta_description == "Meta description"
        assert result.content == "Page content text"
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_playwright_scrape_error(self) -> None:
        """Playwright scraping hatasi."""
        scraper = WebScraper()
        scraper._use_playwright = True

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        scraper._browser = mock_browser

        result = await scraper._scrape_with_playwright("https://bad-url.com")

        assert result.success is False
        assert "Navigation failed" in result.error
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_playwright_scrape_content_truncated(self) -> None:
        """5000 karakterden uzun icerik kesilir."""
        scraper = WebScraper()
        scraper._use_playwright = True

        long_content = "A" * 10000

        mock_response = MagicMock()
        mock_response.status = 200

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Long Page")
        mock_page.evaluate = AsyncMock(side_effect=["", long_content])
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        scraper._browser = mock_browser

        result = await scraper._scrape_with_playwright("https://example.com")

        assert len(result.content) == 5000


# === httpx scraping testleri ===


class TestScrapeWithHttpx:
    """httpx+BeautifulSoup ile scraping testleri."""

    @pytest.mark.asyncio
    async def test_httpx_scrape_success(self) -> None:
        """Basarili httpx scraping."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test meta desc">
        </head>
        <body>
            <p>Main content here</p>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        scraper = WebScraper()
        scraper._http_client = mock_client
        scraper._use_playwright = False

        result = await scraper._scrape_with_httpx("https://example.com")

        assert result.success is True
        assert result.url == "https://example.com"
        assert result.title == "Test Page"
        assert result.meta_description == "Test meta desc"
        assert "Main content" in result.content
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_httpx_scrape_strips_tags(self) -> None:
        """script, style, nav, footer, header etiketleri temizlenir."""
        html = """
        <html>
        <head><title>Strip Test</title></head>
        <body>
            <header>Header content</header>
            <nav>Nav content</nav>
            <script>var x = 1;</script>
            <style>body { color: red; }</style>
            <p>Visible content</p>
            <footer>Footer content</footer>
        </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        scraper = WebScraper()
        scraper._http_client = mock_client
        scraper._use_playwright = False

        result = await scraper._scrape_with_httpx("https://example.com")

        assert "Visible content" in result.content
        assert "var x = 1" not in result.content
        assert "Nav content" not in result.content

    @pytest.mark.asyncio
    async def test_httpx_scrape_http_error(self) -> None:
        """HTTP hatasi durumu."""
        mock_request = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        error = httpx.HTTPStatusError(
            "Not Found",
            request=mock_request,
            response=mock_resp,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=MagicMock(
            raise_for_status=MagicMock(side_effect=error),
            status_code=404,
        ))

        scraper = WebScraper()
        scraper._http_client = mock_client
        scraper._use_playwright = False

        result = await scraper._scrape_with_httpx("https://example.com/404")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_httpx_scrape_creates_client(self) -> None:
        """http_client None ise otomatik olusturulur."""
        html = "<html><head><title>Auto</title></head><body><p>Ok</p></body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch("app.tools.web_scraper.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_cls.return_value = mock_client

            scraper = WebScraper()
            scraper._http_client = None
            scraper._use_playwright = False

            result = await scraper._scrape_with_httpx("https://example.com")

            assert result.success is True
            mock_cls.assert_called_once()


# === Screenshot testleri ===


class TestScreenshot:
    """Ekran goruntusu testleri."""

    @pytest.mark.asyncio
    async def test_screenshot_success(self) -> None:
        """Basarili ekran goruntusu."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.screenshot = AsyncMock()
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        scraper = WebScraper()
        scraper._use_playwright = True
        scraper._browser = mock_browser

        result = await scraper.screenshot("https://example.com", "/tmp/test.png")

        assert result == "/tmp/test.png"
        mock_page.screenshot.assert_called_once_with(
            path="/tmp/test.png", full_page=True,
        )
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_screenshot_requires_playwright(self) -> None:
        """Playwright yoksa RuntimeError."""
        scraper = WebScraper()
        scraper._use_playwright = False
        scraper._browser = None

        with pytest.raises(RuntimeError, match="Playwright"):
            await scraper.screenshot("https://example.com", "/tmp/test.png")


# === Extract links testleri ===


class TestExtractLinks:
    """Link cikarma testleri."""

    @pytest.mark.asyncio
    async def test_extract_links_playwright(self) -> None:
        """Playwright ile link cikarma."""
        links = [
            {"href": "https://example.com/page1", "text": "Page 1"},
            {"href": "https://example.com/page2", "text": "Page 2"},
        ]

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=links)
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        scraper = WebScraper()
        scraper._use_playwright = True
        scraper._browser = mock_browser

        result = await scraper.extract_links("https://example.com")

        assert len(result) == 2
        assert result[0]["href"] == "https://example.com/page1"
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_links_httpx(self) -> None:
        """httpx ile link cikarma."""
        html = """
        <html><body>
            <a href="https://example.com/link1">Link 1</a>
            <a href="https://example.com/link2">Link 2</a>
            <a>No href</a>
        </body></html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        scraper = WebScraper()
        scraper._use_playwright = False
        scraper._browser = None
        scraper._http_client = mock_client

        result = await scraper.extract_links("https://example.com")

        assert len(result) == 2
        assert result[0]["href"] == "https://example.com/link1"
        assert result[0]["text"] == "Link 1"

    @pytest.mark.asyncio
    async def test_extract_links_playwright_error(self) -> None:
        """Playwright link cikarma hatasi bos liste doner."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Timeout"))
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        scraper = WebScraper()
        scraper._use_playwright = True
        scraper._browser = mock_browser

        result = await scraper.extract_links("https://example.com")

        assert result == []
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_links_httpx_error(self) -> None:
        """httpx link cikarma hatasi bos liste doner."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPError("Connection error"),
        )

        scraper = WebScraper()
        scraper._use_playwright = False
        scraper._http_client = mock_client

        result = await scraper.extract_links("https://bad-url.com")

        assert result == []


# === Execute JS testleri ===


class TestExecuteJs:
    """JavaScript calistirma testleri."""

    @pytest.mark.asyncio
    async def test_execute_js_success(self) -> None:
        """Basarili JS calistirma."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"key": "value"})
        mock_page.close = AsyncMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)

        scraper = WebScraper()
        scraper._use_playwright = True
        scraper._browser = mock_browser

        result = await scraper.execute_js(
            "https://example.com",
            "() => ({key: 'value'})",
        )

        assert result == {"key": "value"}
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_js_requires_playwright(self) -> None:
        """Playwright yoksa RuntimeError."""
        scraper = WebScraper()
        scraper._use_playwright = False
        scraper._browser = None

        with pytest.raises(RuntimeError, match="Playwright"):
            await scraper.execute_js("https://example.com", "() => 1")
