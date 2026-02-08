"""ATLAS web scraping arac modulu.

Playwright tabanli gelismis web scraping:
- JavaScript render destegi
- Ekran goruntusu alma
- Link cikarma
- Ozel JS calistirma

Playwright kullanilamazsa httpx+BeautifulSoup'a duser.
"""

import logging
import re
from types import TracebackType
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.models.research import ScrapedPage

logger = logging.getLogger("atlas.tools.web_scraper")

# Playwright opsiyonel import
_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright

    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.info("Playwright kurulu degil, httpx+BeautifulSoup kullanilacak")


class WebScraper:
    """Playwright tabanli async web scraper.

    Async context manager olarak kullanilir:
        async with WebScraper() as scraper:
            page = await scraper.scrape("https://example.com")

    Playwright kullanilamazsa httpx+BeautifulSoup ile
    statik scraping yapar.

    Attributes:
        timeout: Sayfa yukleme zaman asimi (milisaniye).
        user_agent: HTTP istekleri icin User-Agent.
    """

    def __init__(
        self,
        timeout: int = 30000,
        user_agent: str = "ATLAS-WebScraper/1.0",
    ) -> None:
        """WebScraper'i yapilandirir.

        Args:
            timeout: Sayfa yukleme zaman asimi (milisaniye).
            user_agent: HTTP istekleri icin User-Agent.
        """
        self.timeout = timeout
        self.user_agent = user_agent
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._http_client: httpx.AsyncClient | None = None
        self._use_playwright = _PLAYWRIGHT_AVAILABLE

    async def __aenter__(self) -> "WebScraper":
        """Context manager giris — tarayiciyi baslatir.

        Returns:
            Yapilandirilmis WebScraper.
        """
        if self._use_playwright:
            try:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                )
                logger.info("Playwright tarayici baslatildi")
            except Exception as exc:
                logger.warning(
                    "Playwright baslatilamadi, fallback kullanilacak: %s", exc,
                )
                self._use_playwright = False

        if not self._use_playwright:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout / 1000,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )
            logger.info("httpx fallback istemcisi baslatildi")

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager cikis — kaynaklari temizler."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("WebScraper kaynaklari temizlendi")

    async def scrape(self, url: str) -> ScrapedPage:
        """Web sayfasini scrape eder.

        Playwright aktifse JavaScript render edilerek scrape edilir.
        Degilse httpx+BeautifulSoup ile statik scraping yapilir.

        Args:
            url: Hedef sayfa URL'i.

        Returns:
            ScrapedPage sonucu.
        """
        if self._use_playwright and self._browser is not None:
            return await self._scrape_with_playwright(url)
        return await self._scrape_with_httpx(url)

    async def screenshot(self, url: str, path: str) -> str:
        """Sayfa ekran goruntusu alir.

        Args:
            url: Hedef sayfa URL'i.
            path: Kaydedilecek dosya yolu (.png).

        Returns:
            Kaydedilen dosya yolu.

        Raises:
            RuntimeError: Playwright kullanilamazsa.
        """
        if not self._use_playwright or self._browser is None:
            raise RuntimeError("Screenshot icin Playwright gerekli")

        page = await self._browser.new_page(user_agent=self.user_agent)
        try:
            await page.goto(url, timeout=self.timeout, wait_until="networkidle")
            await page.screenshot(path=path, full_page=True)
            logger.info("Screenshot alindi: %s -> %s", url, path)
            return path
        finally:
            await page.close()

    async def extract_links(self, url: str) -> list[dict[str, str]]:
        """Sayfadaki tum linkleri cikarir.

        Args:
            url: Hedef sayfa URL'i.

        Returns:
            Link bilgileri listesi [{"href": "...", "text": "..."}].
        """
        if self._use_playwright and self._browser is not None:
            return await self._extract_links_playwright(url)
        return await self._extract_links_httpx(url)

    async def execute_js(self, url: str, script: str) -> Any:
        """Sayfada ozel JavaScript kodu calistirir.

        Args:
            url: Hedef sayfa URL'i.
            script: Calistirilacak JavaScript kodu.

        Returns:
            JavaScript calistirma sonucu.

        Raises:
            RuntimeError: Playwright kullanilamazsa.
        """
        if not self._use_playwright or self._browser is None:
            raise RuntimeError("JavaScript calistirmak icin Playwright gerekli")

        page = await self._browser.new_page(user_agent=self.user_agent)
        try:
            await page.goto(url, timeout=self.timeout, wait_until="networkidle")
            result = await page.evaluate(script)
            logger.info("JS calistirildi: %s", url)
            return result
        finally:
            await page.close()

    # === Dahili metodlar ===

    async def _scrape_with_playwright(self, url: str) -> ScrapedPage:
        """Playwright ile JS render'li scraping.

        Args:
            url: Hedef sayfa URL'i.

        Returns:
            ScrapedPage sonucu.
        """
        page = None
        try:
            page = await self._browser.new_page(user_agent=self.user_agent)
            response = await page.goto(
                url, timeout=self.timeout, wait_until="networkidle",
            )

            status_code = response.status if response else 0
            title = await page.title()

            # Meta description
            meta_desc = await page.evaluate(
                "() => {"
                "  const m = document.querySelector('meta[name=\"description\"]');"
                "  return m ? m.content : '';"
                "}"
            )

            # Icerik cikar (script/style temizlenmis metin)
            content = await page.evaluate(
                "() => {"
                "  ['script','style','nav','footer','header'].forEach(tag => {"
                "    document.querySelectorAll(tag).forEach(el => el.remove());"
                "  });"
                "  return document.body ? document.body.innerText : '';"
                "}"
            )

            # Coklu bos satirlari temizle ve sinirla
            content = re.sub(r"\n{3,}", "\n\n", content or "")
            content = content[:5000]

            logger.info(
                "Playwright scrape tamamlandi: %s (%d kelime)",
                url, len(content.split()),
            )

            return ScrapedPage(
                url=url,
                title=title or "",
                content=content,
                meta_description=meta_desc or "",
                status_code=status_code,
                success=True,
                word_count=len(content.split()),
            )
        except Exception as exc:
            logger.error("Playwright scraping hatasi [%s]: %s", url, exc)
            return ScrapedPage(url=url, success=False, error=str(exc))
        finally:
            if page is not None:
                await page.close()

    async def _scrape_with_httpx(self, url: str) -> ScrapedPage:
        """httpx+BeautifulSoup ile statik scraping (fallback).

        Args:
            url: Hedef sayfa URL'i.

        Returns:
            ScrapedPage sonucu.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout / 1000,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )

        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("httpx scraping hatasi [%s]: %s", url, exc)
            return ScrapedPage(
                url=url,
                success=False,
                status_code=getattr(
                    getattr(exc, "response", None), "status_code", 0,
                ),
                error=str(exc),
            )

        soup = BeautifulSoup(response.text, "html.parser")

        # Script ve style etiketlerini kaldir
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_tag.get("content", "") if meta_tag else ""

        # Metin icerigi cikar
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        content = text[:5000]

        logger.info(
            "httpx scrape tamamlandi: %s (%d kelime)",
            url, len(content.split()),
        )

        return ScrapedPage(
            url=url,
            title=title,
            content=content,
            meta_description=meta_desc,
            status_code=response.status_code,
            success=True,
            word_count=len(content.split()),
        )

    async def _extract_links_playwright(self, url: str) -> list[dict[str, str]]:
        """Playwright ile link cikarma.

        Args:
            url: Hedef sayfa URL'i.

        Returns:
            Link bilgileri listesi.
        """
        page = await self._browser.new_page(user_agent=self.user_agent)
        try:
            await page.goto(url, timeout=self.timeout, wait_until="networkidle")
            links = await page.evaluate(
                "() => Array.from(document.querySelectorAll('a[href]')).map("
                "a => ({href: a.href, text: a.innerText.trim().substring(0, 200)}))"
            )
            return links or []
        except Exception as exc:
            logger.error("Link cikarma hatasi [%s]: %s", url, exc)
            return []
        finally:
            await page.close()

    async def _extract_links_httpx(self, url: str) -> list[dict[str, str]]:
        """httpx+BeautifulSoup ile link cikarma.

        Args:
            url: Hedef sayfa URL'i.

        Returns:
            Link bilgileri listesi.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout / 1000,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
            )

        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Link cikarma hatasi [%s]: %s", url, exc)
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        links: list[dict[str, str]] = []

        for a_tag in soup.find_all("a", href=True):
            links.append({
                "href": a_tag["href"],
                "text": a_tag.get_text(strip=True)[:200],
            })

        return links
