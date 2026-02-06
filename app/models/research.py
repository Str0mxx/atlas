"""Arastirma agent'i veri modelleri.

Web aramasi sonuclari, scraping ciktilari, tedarikci puanlamalari
ve firma guvenilirlik bilgilerini modellar.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResearchType(str, Enum):
    """Arastirma tipi."""

    WEB_SEARCH = "web_search"
    SCRAPE = "scrape"
    SUPPLIER_RESEARCH = "supplier_research"
    COMPANY_CHECK = "company_check"


class ReliabilityLevel(str, Enum):
    """Firma guvenilirlik seviyesi."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResearchConfig(BaseModel):
    """Arastirma yapilandirmasi.

    Attributes:
        search_engine: Arama motoru (tavily/serp).
        max_results: Arama basina maksimum sonuc sayisi.
        scraping_timeout: Sayfa scraping zaman asimi (saniye).
        user_agent: HTTP istekleri icin User-Agent baslik degeri.
        supplier_criteria: Tedarikci puanlama kriterleri ve agirliklari.
    """

    search_engine: str = "tavily"
    max_results: int = 5
    scraping_timeout: int = 15
    user_agent: str = "ATLAS-Research-Agent/1.0"
    supplier_criteria: dict[str, float] = Field(
        default_factory=lambda: {
            "fiyat": 0.25,
            "kalite": 0.25,
            "teslimat": 0.20,
            "iletisim": 0.15,
            "referans": 0.15,
        },
    )


class WebSearchResult(BaseModel):
    """Web arama sonucu.

    Attributes:
        query: Arama sorgusu.
        url: Sonuc URL'i.
        title: Sayfa basligi.
        snippet: Kisa aciklama/ozet.
        source: Kaynak adi.
        relevance_score: Arama motorunun verdigi ilgililik puani.
    """

    query: str = ""
    url: str = ""
    title: str = ""
    snippet: str = ""
    source: str = ""
    relevance_score: float = 0.0


class ScrapedPage(BaseModel):
    """Scraping sonucu.

    Attributes:
        url: Sayfa URL'i.
        title: Sayfa basligi.
        content: Metin icerigi (HTML temizlenmis).
        meta_description: Meta description icerigi.
        status_code: HTTP durum kodu.
        success: Scraping basarili mi.
        word_count: Kelime sayisi.
        error: Hata mesaji (basarisizsa).
    """

    url: str = ""
    title: str = ""
    content: str = ""
    meta_description: str = ""
    status_code: int = 0
    success: bool = True
    word_count: int = 0
    error: str = ""


class SupplierScore(BaseModel):
    """Tedarikci puanlama sonucu.

    Attributes:
        name: Tedarikci adi.
        url: Tedarikci web sitesi.
        scores: Kriter bazli puanlar (0-10).
        overall_score: Agirlikli genel puan (0-10).
        reliability: Guvenilirlik seviyesi.
        pros: Guclu yanlar.
        cons: Zayif yanlar.
        notes: Ek notlar.
    """

    name: str = ""
    url: str = ""
    scores: dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0
    reliability: ReliabilityLevel = ReliabilityLevel.UNKNOWN
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class CompanyInfo(BaseModel):
    """Firma guvenilirlik bilgisi.

    Attributes:
        name: Firma adi.
        url: Firma web sitesi.
        domain_age_days: Domain yasi (gun).
        has_ssl: SSL sertifikasi var mi.
        has_contact_info: Iletisim bilgisi var mi.
        has_physical_address: Fiziksel adres var mi.
        social_media_count: Sosyal medya hesap sayisi.
        review_score: Ortalama musteri degerlendirme puani (0-5).
        review_count: Degerlendirme sayisi.
        reliability: Genel guvenilirlik seviyesi.
        red_flags: Dikkat edilmesi gereken noktalar.
        green_flags: Olumlu isretler.
    """

    name: str = ""
    url: str = ""
    domain_age_days: int = 0
    has_ssl: bool = False
    has_contact_info: bool = False
    has_physical_address: bool = False
    social_media_count: int = 0
    review_score: float = 0.0
    review_count: int = 0
    reliability: ReliabilityLevel = ReliabilityLevel.UNKNOWN
    red_flags: list[str] = Field(default_factory=list)
    green_flags: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """Arastirma genel sonucu.

    Attributes:
        research_type: Arastirma tipi.
        query: Ana arama sorgusu.
        search_results: Web arama sonuclari.
        scraped_pages: Scraping sonuclari.
        suppliers: Tedarikci puanlamalari.
        company_info: Firma bilgileri.
        summary: Arastirma ozeti.
    """

    research_type: ResearchType = ResearchType.WEB_SEARCH
    query: str = ""
    search_results: list[WebSearchResult] = Field(default_factory=list)
    scraped_pages: list[ScrapedPage] = Field(default_factory=list)
    suppliers: list[SupplierScore] = Field(default_factory=list)
    company_info: CompanyInfo | None = None
    summary: str = ""
