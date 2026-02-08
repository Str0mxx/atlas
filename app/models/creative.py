"""Yaratici agent veri modelleri.

Urun fikri, icerik uretimi, reklam metni, marka ismi
ve ambalaj tasarimi onerilerini modellar.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CreativeType(str, Enum):
    """Yaratici icerik tipi."""

    PRODUCT_IDEA = "product_idea"
    CONTENT = "content"
    AD_COPY = "ad_copy"
    BRAND_NAME = "brand_name"
    PACKAGING = "packaging"


class CreativeConfig(BaseModel):
    """Yaratici agent yapilandirmasi.

    Attributes:
        model: Kullanilacak LLM modeli.
        max_tokens: Maks yanit token sayisi.
        creativity_level: Yaraticilik seviyesi (temperature, 0.0-1.0).
        language: Yanit dili.
        brand_voice: Marka ses tonu aciklamasi.
    """

    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    creativity_level: float = Field(default=0.8, ge=0.0, le=1.0)
    language: str = "tr"
    brand_voice: str = "profesyonel, samimi, guven veren"


class ProductIdea(BaseModel):
    """Urun fikri onerisi.

    Attributes:
        name: Urun adi.
        description: Urun aciklamasi.
        target_audience: Hedef kitle.
        unique_value: Benzersiz deger onerisi.
        estimated_cost: Tahmini uretim maliyeti.
        market_potential: Pazar potansiyeli degerlendirmesi.
    """

    name: str = ""
    description: str = ""
    target_audience: str = ""
    unique_value: str = ""
    estimated_cost: str = ""
    market_potential: str = ""


class ContentPiece(BaseModel):
    """Icerik parcasi.

    Attributes:
        title: Baslik.
        body: Icerik metni.
        content_type: Icerik turu (blog/social/email/video_script).
        target_platform: Hedef platform.
        hashtags: Hashtag listesi.
        cta: Call to action (harekete gecirici mesaj).
    """

    title: str = ""
    body: str = ""
    content_type: str = "social"
    target_platform: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""


class AdCopy(BaseModel):
    """Reklam metni.

    Attributes:
        headline: Ana baslik.
        description: Aciklama metni.
        cta: Call to action.
        target_audience: Hedef kitle.
        platform: Reklam platformu.
        variations: Alternatif varyasyonlar.
    """

    headline: str = ""
    description: str = ""
    cta: str = ""
    target_audience: str = ""
    platform: str = ""
    variations: list[dict[str, str]] = Field(default_factory=list)


class BrandSuggestion(BaseModel):
    """Marka isim onerisi.

    Attributes:
        name: Marka adi.
        tagline: Slogan.
        reasoning: Isim secim gerekceleri.
        domain_suggestions: Domain onerileri.
    """

    name: str = ""
    tagline: str = ""
    reasoning: str = ""
    domain_suggestions: list[str] = Field(default_factory=list)


class PackagingIdea(BaseModel):
    """Ambalaj tasarimi onerisi.

    Attributes:
        concept: Tasarim konsepti.
        materials: Malzeme onerileri.
        colors: Renk paleti.
        style: Tasarim stili.
        sustainability: Surdurulebilirlik notu.
    """

    concept: str = ""
    materials: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    style: str = ""
    sustainability: str = ""


class CreativeResult(BaseModel):
    """Yaratici cikti sonucu.

    Attributes:
        creative_type: Icerik turu.
        items: Uretilen icerik ogelerinin listesi.
        summary: Genel ozet.
        recommendations: Ek oneriler.
    """

    creative_type: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
