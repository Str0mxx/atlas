"""Arastirma agent modulu.

Web aramasi, sayfa scraping, tedarikci arastirma/puanlama
ve firma guvenilirlik kontrolu yeteneklerine sahip agent.

Sonuclari analiz ederek risk/aciliyet siniflandirmasi yapar
ve karar matrisine entegre eder.
"""

import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.agents.base_agent import BaseAgent, TaskResult
from app.config import settings
from app.core.decision_matrix import (
    DECISION_RULES,
    ActionType,
    RiskLevel,
    UrgencyLevel,
)
from app.models.research import (
    CompanyInfo,
    ReliabilityLevel,
    ResearchConfig,
    ResearchResult,
    ResearchType,
    ScrapedPage,
    SupplierScore,
    WebSearchResult,
)

logger = logging.getLogger("atlas.agent.research")


class ResearchAgent(BaseAgent):
    """Arastirma agent'i.

    Web aramasi, scraping, tedarikci puanlama ve firma guvenilirlik
    kontrolu yaparak sonuclari karar matrisine entegre eder.

    Attributes:
        config: Arastirma yapilandirmasi.
        http_client: Paylasimli httpx async istemcisi.
    """

    def __init__(
        self,
        config: ResearchConfig | None = None,
    ) -> None:
        """ResearchAgent'i baslatir.

        Args:
            config: Arastirma yapilandirmasi.
                Bos ise varsayilan degerler kullanilir.
        """
        super().__init__(name="research")
        self.config = config or ResearchConfig()
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Paylasimli HTTP istemcisini dondurur (lazy init).

        Returns:
            httpx.AsyncClient ornegi.
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.config.scraping_timeout,
                headers={"User-Agent": self.config.user_agent},
                follow_redirects=True,
            )
        return self._http_client

    async def close(self) -> None:
        """HTTP istemcisini kapatir."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def execute(self, task: dict[str, Any]) -> TaskResult:
        """Arastirma gorevini calistirir.

        Args:
            task: Gorev detaylari. Beklenen anahtarlar:
                - research_type: Arastirma tipi (web_search/scrape/supplier_research/company_check).
                - query: Arama sorgusu.
                - urls: Scraping icin URL listesi.
                - suppliers: Tedarikci listesi (dict listesi: name, url).
                - company_url: Firma kontrolu icin URL.
                - config: Ozel yapilandirma (dict).

        Returns:
            Arastirma sonuclarini iceren TaskResult.
        """
        if task.get("config"):
            self.config = ResearchConfig(**task["config"])

        research_type_str = task.get("research_type", "web_search")
        try:
            research_type = ResearchType(research_type_str)
        except ValueError:
            return TaskResult(
                success=False,
                message=f"Gecersiz arastirma tipi: {research_type_str}",
                errors=[f"Gecerli tipler: {[t.value for t in ResearchType]}"],
            )

        query = task.get("query", "")
        result = ResearchResult(research_type=research_type, query=query)
        errors: list[str] = []

        try:
            if research_type == ResearchType.WEB_SEARCH:
                if not query:
                    return TaskResult(
                        success=False,
                        message="Arama sorgusu belirtilmedi.",
                        errors=["'query' alani gerekli."],
                    )
                result.search_results = await self._web_search(query)

            elif research_type == ResearchType.SCRAPE:
                urls = task.get("urls", [])
                if not urls:
                    return TaskResult(
                        success=False,
                        message="Scraping icin URL belirtilmedi.",
                        errors=["'urls' alani gerekli."],
                    )
                for url in urls:
                    page = await self._scrape_page(url)
                    result.scraped_pages.append(page)
                    if not page.success:
                        errors.append(f"{url}: {page.error}")

            elif research_type == ResearchType.SUPPLIER_RESEARCH:
                suppliers_data = task.get("suppliers", [])
                if not suppliers_data and not query:
                    return TaskResult(
                        success=False,
                        message="Tedarikci listesi veya arama sorgusu belirtilmedi.",
                        errors=["'suppliers' veya 'query' alani gerekli."],
                    )
                # Sorgu varsa once web araması yap
                if query:
                    result.search_results = await self._web_search(query)
                # Tedarikci puanlama
                for supplier_data in suppliers_data:
                    name = supplier_data.get("name", "")
                    url = supplier_data.get("url", "")
                    supplier_score = await self._research_supplier(name, url)
                    result.suppliers.append(supplier_score)

            elif research_type == ResearchType.COMPANY_CHECK:
                company_url = task.get("company_url", "")
                if not company_url:
                    return TaskResult(
                        success=False,
                        message="Firma URL'i belirtilmedi.",
                        errors=["'company_url' alani gerekli."],
                    )
                result.company_info = await self._check_company(company_url)

        except Exception as exc:
            self.logger.error("Arastirma hatasi: %s", exc)
            errors.append(str(exc))
        finally:
            await self.close()

        # Analiz et
        analysis = await self.analyze({"research_result": result.model_dump()})
        result.summary = analysis.get("summary", "")

        task_result = TaskResult(
            success=len(errors) == 0,
            data={
                "research_result": result.model_dump(),
                "analysis": analysis,
            },
            message=analysis.get("summary", "Arastirma tamamlandi."),
            errors=errors,
        )

        report_text = await self.report(task_result)
        self.logger.info("Arastirma Raporu:\n%s", report_text)

        return task_result

    async def analyze(self, data: dict[str, Any]) -> dict[str, Any]:
        """Arastirma sonuclarini analiz eder ve risk/aciliyet belirler.

        Args:
            data: {"research_result": ResearchResult dict}.

        Returns:
            Analiz sonuclari: risk, urgency, action, summary, details.
        """
        result_dict = data.get("research_result", {})
        result = ResearchResult(**result_dict) if isinstance(result_dict, dict) else result_dict

        details: list[dict[str, Any]] = []
        risk = RiskLevel.LOW
        urgency = UrgencyLevel.LOW

        # Arama sonucu analizi
        if result.search_results:
            details.append({
                "type": "web_search",
                "count": len(result.search_results),
                "top_results": [
                    {"title": r.title, "url": r.url}
                    for r in result.search_results[:3]
                ],
            })

        # Scraping analizi
        if result.scraped_pages:
            failed = [p for p in result.scraped_pages if not p.success]
            details.append({
                "type": "scraping",
                "total": len(result.scraped_pages),
                "successful": len(result.scraped_pages) - len(failed),
                "failed": len(failed),
            })
            if len(failed) > len(result.scraped_pages) / 2:
                risk = RiskLevel.MEDIUM
                urgency = UrgencyLevel.LOW

        # Tedarikci analizi
        if result.suppliers:
            low_score = [s for s in result.suppliers if s.overall_score < 4.0]
            unreliable = [s for s in result.suppliers if s.reliability == ReliabilityLevel.LOW]

            details.append({
                "type": "supplier_research",
                "total": len(result.suppliers),
                "low_score_count": len(low_score),
                "unreliable_count": len(unreliable),
                "best": max(result.suppliers, key=lambda s: s.overall_score).name
                if result.suppliers else "",
            })

            if unreliable:
                risk = self._escalate_risk(risk, RiskLevel.MEDIUM)
                urgency = self._escalate_urgency(urgency, UrgencyLevel.MEDIUM)
            if len(low_score) == len(result.suppliers):
                risk = self._escalate_risk(risk, RiskLevel.HIGH)
                urgency = self._escalate_urgency(urgency, UrgencyLevel.MEDIUM)

        # Firma guvenilirlik analizi
        if result.company_info:
            info = result.company_info
            details.append({
                "type": "company_check",
                "name": info.name,
                "reliability": info.reliability.value,
                "red_flags": info.red_flags,
                "green_flags": info.green_flags,
            })

            if info.reliability == ReliabilityLevel.LOW:
                risk = self._escalate_risk(risk, RiskLevel.HIGH)
                urgency = self._escalate_urgency(urgency, UrgencyLevel.HIGH)
            elif info.reliability == ReliabilityLevel.MEDIUM:
                risk = self._escalate_risk(risk, RiskLevel.MEDIUM)
                urgency = self._escalate_urgency(urgency, UrgencyLevel.MEDIUM)

        action = self._determine_action(risk, urgency)
        summary = self._build_analysis_summary(result, details)

        return {
            "risk": risk.value,
            "urgency": urgency.value,
            "action": action.value,
            "summary": summary,
            "details": details,
        }

    async def report(self, result: TaskResult) -> str:
        """Arastirma sonucunu formatli rapor metnine donusturur.

        Args:
            result: Raporlanacak gorev sonucu.

        Returns:
            Formatlanmis rapor metni.
        """
        analysis = result.data.get("analysis", {})
        research = result.data.get("research_result", {})
        details = analysis.get("details", [])

        lines = [
            "=== ARASTIRMA RAPORU ===",
            f"Tip: {research.get('research_type', '-')}",
            f"Sorgu: {research.get('query', '-')}",
            f"Risk: {analysis.get('risk', '-')} | Aciliyet: {analysis.get('urgency', '-')}",
            f"Aksiyon: {analysis.get('action', '-')}",
            "",
            analysis.get("summary", ""),
            "",
        ]

        for detail in details:
            dtype = detail.get("type", "?")

            if dtype == "web_search":
                lines.append(f"--- Web Arama ({detail.get('count', 0)} sonuc) ---")
                for r in detail.get("top_results", []):
                    lines.append(f"  - {r.get('title', '?')}")
                    lines.append(f"    {r.get('url', '?')}")

            elif dtype == "scraping":
                lines.append(
                    f"--- Scraping ({detail.get('successful', 0)}/{detail.get('total', 0)} basarili) ---"
                )

            elif dtype == "supplier_research":
                lines.append(f"--- Tedarikci Arastirmasi ({detail.get('total', 0)} firma) ---")
                best = detail.get("best", "")
                if best:
                    lines.append(f"  En iyi: {best}")
                low = detail.get("low_score_count", 0)
                if low:
                    lines.append(f"  Dusuk puanli: {low}")

            elif dtype == "company_check":
                lines.append(f"--- Firma Kontrolu: {detail.get('name', '?')} ---")
                lines.append(f"  Guvenilirlik: {detail.get('reliability', '?')}")
                for flag in detail.get("red_flags", []):
                    lines.append(f"  [!] {flag}")
                for flag in detail.get("green_flags", []):
                    lines.append(f"  [+] {flag}")

            lines.append("")

        if result.errors:
            lines.append("HATALAR:")
            for err in result.errors:
                lines.append(f"  ! {err}")

        return "\n".join(lines)

    # === Web Arama ===

    async def _web_search(self, query: str) -> list[WebSearchResult]:
        """Web araması yapar (Tavily API).

        Args:
            query: Arama sorgusu.

        Returns:
            Arama sonuclari listesi.
        """
        api_key = settings.tavily_api_key.get_secret_value()
        if not api_key:
            self.logger.warning("Tavily API key tanimlanmamis, bos sonuc donuyor")
            return []

        client = await self._get_http_client()
        try:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": self.config.max_results,
                    "include_answer": False,
                },
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            self.logger.error("Tavily API hatasi: %s", exc)
            return []

        results: list[WebSearchResult] = []
        for item in data.get("results", []):
            results.append(
                WebSearchResult(
                    query=query,
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("content", "")[:500],
                    source=urlparse(item.get("url", "")).netloc,
                    relevance_score=item.get("score", 0.0),
                )
            )

        self.logger.info("Web arama tamamlandi: '%s' -> %d sonuc", query, len(results))
        return results

    # === Web Scraping ===

    async def _scrape_page(self, url: str) -> ScrapedPage:
        """Bir web sayfasini scrape eder.

        Args:
            url: Hedef URL.

        Returns:
            ScrapedPage sonucu.
        """
        client = await self._get_http_client()
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            self.logger.error("Scraping hatasi [%s]: %s", url, exc)
            return ScrapedPage(
                url=url,
                success=False,
                status_code=getattr(getattr(exc, "response", None), "status_code", 0),
                error=str(exc),
            )

        soup = BeautifulSoup(response.text, "html.parser")

        # Script ve style etiketlerini kaldir
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # Metin icerigi cikar
        text = soup.get_text(separator="\n", strip=True)
        # Coklu bos satirlari tek satira indir
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Icerigi sinirla (ilk 5000 karakter)
        content = text[:5000]

        page = ScrapedPage(
            url=url,
            title=title,
            content=content,
            meta_description=meta_desc,
            status_code=response.status_code,
            success=True,
            word_count=len(content.split()),
        )

        self.logger.info("Sayfa scrape edildi: %s (%d kelime)", url, page.word_count)
        return page

    # === Tedarikci Arastirma ===

    async def _research_supplier(self, name: str, url: str) -> SupplierScore:
        """Bir tedarikciyi arastirir ve puanlar.

        Tedarikci web sitesini scrape eder, icerigi analiz eder
        ve kriter bazli puanlama yapar.

        Args:
            name: Tedarikci adi.
            url: Tedarikci web sitesi URL'i.

        Returns:
            Tedarikci puan karti.
        """
        supplier = SupplierScore(name=name, url=url)

        # Siteyi scrape et
        page = await self._scrape_page(url) if url else ScrapedPage(success=False, error="URL yok")

        if not page.success:
            supplier.notes.append(f"Site erisilemedi: {page.error}")
            supplier.reliability = ReliabilityLevel.LOW
            supplier.cons.append("Web sitesi erisilemez")
            return supplier

        content_lower = page.content.lower()

        # Kriter bazli puanlama (icerge analizi ile)
        scores: dict[str, float] = {}

        # Fiyat: Fiyat bilgisi/listesi var mi?
        price_keywords = ["fiyat", "price", "ucret", "teklif", "quote", "maliyet"]
        scores["fiyat"] = 7.0 if any(k in content_lower for k in price_keywords) else 4.0

        # Kalite: Kalite belgeleri, sertifika var mi?
        quality_keywords = [
            "iso", "sertifika", "kalite", "quality", "ce", "gmp",
            "haccp", "certificate", "garanti", "warranty",
        ]
        quality_hits = sum(1 for k in quality_keywords if k in content_lower)
        scores["kalite"] = min(10.0, 4.0 + quality_hits * 1.5)

        # Teslimat: Teslimat/kargo bilgisi var mi?
        delivery_keywords = ["teslimat", "kargo", "shipping", "delivery", "sevkiyat", "lojistik"]
        scores["teslimat"] = 7.0 if any(k in content_lower for k in delivery_keywords) else 4.0

        # Iletisim: Iletisim bilgileri var mi?
        contact_score = 4.0
        if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", page.content):
            contact_score += 2.0
            supplier.pros.append("E-posta adresi mevcut")
        if re.search(r"\+?\d[\d\s\-()]{8,}", page.content):
            contact_score += 2.0
            supplier.pros.append("Telefon numarasi mevcut")
        if any(k in content_lower for k in ["adres", "address", "konum", "location"]):
            contact_score += 2.0
            supplier.pros.append("Fiziksel adres mevcut")
        scores["iletisim"] = min(10.0, contact_score)

        # Referans: Referanslar, musteriler var mi?
        ref_keywords = [
            "referans", "musteri", "customer", "client",
            "partner", "portfolio", "basari", "proje",
        ]
        ref_hits = sum(1 for k in ref_keywords if k in content_lower)
        scores["referans"] = min(10.0, 3.0 + ref_hits * 2.0)

        supplier.scores = scores

        # Agirlikli genel puan hesapla
        criteria = self.config.supplier_criteria
        total_weight = sum(criteria.get(k, 0) for k in scores)
        if total_weight > 0:
            weighted_sum = sum(
                scores[k] * criteria.get(k, 0) for k in scores if k in criteria
            )
            supplier.overall_score = round(weighted_sum / total_weight, 1)

        # Guvenilirlik belirle
        if supplier.overall_score >= 7.0:
            supplier.reliability = ReliabilityLevel.HIGH
        elif supplier.overall_score >= 5.0:
            supplier.reliability = ReliabilityLevel.MEDIUM
        else:
            supplier.reliability = ReliabilityLevel.LOW

        # Guclu/zayif yanlar
        for criterion, score in scores.items():
            if score >= 7.0:
                supplier.pros.append(f"{criterion}: iyi ({score:.1f}/10)")
            elif score < 5.0:
                supplier.cons.append(f"{criterion}: zayif ({score:.1f}/10)")

        self.logger.info(
            "Tedarikci puanlandi: %s -> %.1f/10 (%s)",
            name, supplier.overall_score, supplier.reliability.value,
        )
        return supplier

    # === Firma Guvenilirlik Kontrolu ===

    async def _check_company(self, url: str) -> CompanyInfo:
        """Bir firmanin guvenilirligini kontrol eder.

        Web sitesini scrape ederek iletisim bilgileri, SSL,
        sosyal medya varligi gibi sinyalleri degerlendirir.

        Args:
            url: Firma web sitesi URL'i.

        Returns:
            Firma guvenilirlik bilgisi.
        """
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        info = CompanyInfo(name=domain, url=url)

        # SSL kontrolu
        info.has_ssl = url.startswith("https://")
        if info.has_ssl:
            info.green_flags.append("SSL sertifikasi mevcut")
        else:
            info.red_flags.append("SSL sertifikasi yok")

        # Siteyi fetch et (raw HTML + parsed content)
        client = await self._get_http_client()
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            info.red_flags.append(f"Web sitesi erisilemez: {exc}")
            info.reliability = ReliabilityLevel.LOW
            return info

        raw_html = response.text
        raw_html_lower = raw_html.lower()
        soup = BeautifulSoup(raw_html, "html.parser")

        # Script/style temizle ve metin cikar
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        content = soup.get_text(separator="\n", strip=True)
        content_lower = content.lower()
        word_count = len(content.split())

        # Iletisim bilgisi kontrolu
        if re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", content):
            info.has_contact_info = True
            info.green_flags.append("E-posta adresi mevcut")

        if re.search(r"\+?\d[\d\s\-()]{8,}", content):
            info.has_contact_info = True
            info.green_flags.append("Telefon numarasi mevcut")

        # Fiziksel adres kontrolu
        address_keywords = [
            "adres", "address", "merkez", "ofis", "office",
            "konum", "location", "sokak", "cadde", "mahalle",
        ]
        if any(k in content_lower for k in address_keywords):
            info.has_physical_address = True
            info.green_flags.append("Fiziksel adres bilgisi mevcut")
        else:
            info.red_flags.append("Fiziksel adres bulunamadi")

        # Sosyal medya varligi (raw HTML'de ara - href'ler dahil)
        social_patterns = [
            r"facebook\.com", r"instagram\.com", r"twitter\.com",
            r"linkedin\.com", r"youtube\.com", r"x\.com",
        ]
        for pattern in social_patterns:
            if re.search(pattern, raw_html_lower):
                info.social_media_count += 1

        if info.social_media_count >= 3:
            info.green_flags.append(f"{info.social_media_count} sosyal medya hesabi")
        elif info.social_media_count == 0:
            info.red_flags.append("Sosyal medya hesabi bulunamadi")

        # Sayfa icerigi yeterliligi
        if word_count < 50:
            info.red_flags.append("Cok az icerik (bos site sinyali)")
        elif word_count > 500:
            info.green_flags.append("Zengin icerik")

        # Guvenilirlik hesapla
        info.reliability = self._calculate_reliability(info)

        self.logger.info(
            "Firma kontrolu: %s -> %s (red=%d, green=%d)",
            domain, info.reliability.value,
            len(info.red_flags), len(info.green_flags),
        )
        return info

    # === Yardimci metodlar ===

    @staticmethod
    def _calculate_reliability(info: CompanyInfo) -> ReliabilityLevel:
        """Firma bilgilerinden guvenilirlik seviyesi hesaplar.

        Args:
            info: Firma bilgileri.

        Returns:
            Guvenilirlik seviyesi.
        """
        score = 0

        if info.has_ssl:
            score += 2
        if info.has_contact_info:
            score += 2
        if info.has_physical_address:
            score += 2
        if info.social_media_count >= 2:
            score += 2
        elif info.social_media_count >= 1:
            score += 1

        # Red flag'ler puan dusurur
        score -= len(info.red_flags)

        if score >= 5:
            return ReliabilityLevel.HIGH
        if score >= 2:
            return ReliabilityLevel.MEDIUM
        return ReliabilityLevel.LOW

    @staticmethod
    def _escalate_risk(current: RiskLevel, new: RiskLevel) -> RiskLevel:
        """Risk seviyesini yukseltir (asla dusurulmez).

        Args:
            current: Mevcut risk seviyesi.
            new: Yeni risk seviyesi.

        Returns:
            En yuksek risk seviyesi.
        """
        order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}
        return new if order[new] > order[current] else current

    @staticmethod
    def _escalate_urgency(current: UrgencyLevel, new: UrgencyLevel) -> UrgencyLevel:
        """Aciliyet seviyesini yukseltir (asla dusurulmez).

        Args:
            current: Mevcut aciliyet seviyesi.
            new: Yeni aciliyet seviyesi.

        Returns:
            En yuksek aciliyet seviyesi.
        """
        order = {UrgencyLevel.LOW: 0, UrgencyLevel.MEDIUM: 1, UrgencyLevel.HIGH: 2}
        return new if order[new] > order[current] else current

    @staticmethod
    def _determine_action(risk: RiskLevel, urgency: UrgencyLevel) -> ActionType:
        """Risk ve aciliyetten aksiyon tipini belirler.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.

        Returns:
            Uygun aksiyon tipi.
        """
        action, _ = DECISION_RULES.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )
        return action

    def _build_analysis_summary(
        self, result: ResearchResult, details: list[dict[str, Any]]
    ) -> str:
        """Analiz icin ozet metin olusturur.

        Args:
            result: Arastirma sonucu.
            details: Analiz detaylari.

        Returns:
            Ozet metni.
        """
        parts: list[str] = []

        if result.search_results:
            parts.append(f"{len(result.search_results)} web arama sonucu bulundu")

        if result.scraped_pages:
            ok = sum(1 for p in result.scraped_pages if p.success)
            parts.append(f"{ok}/{len(result.scraped_pages)} sayfa basariyla scrape edildi")

        if result.suppliers:
            best = max(result.suppliers, key=lambda s: s.overall_score)
            parts.append(
                f"{len(result.suppliers)} tedarikci incelendi, "
                f"en iyi: {best.name} ({best.overall_score:.1f}/10)"
            )

        if result.company_info:
            info = result.company_info
            parts.append(
                f"Firma kontrolu: {info.name} -> {info.reliability.value}"
            )

        return ". ".join(parts) + "." if parts else "Arastirma tamamlandi."
