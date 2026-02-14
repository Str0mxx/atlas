"""Multi-Language & Localization veri modelleri."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class LanguageCode(str, Enum):
    """Dil kodu."""

    TR = "tr"
    EN = "en"
    DE = "de"
    FR = "fr"
    ES = "es"
    AR = "ar"
    ZH = "zh"
    JA = "ja"
    RU = "ru"


class ScriptType(str, Enum):
    """Yazi sistemi."""

    LATIN = "latin"
    CYRILLIC = "cyrillic"
    ARABIC = "arabic"
    CJK = "cjk"
    DEVANAGARI = "devanagari"


class TextDirection(str, Enum):
    """Metin yonu."""

    LTR = "ltr"
    RTL = "rtl"


class FormalityLevel(str, Enum):
    """Resmiyet seviyesi."""

    INFORMAL = "informal"
    NEUTRAL = "neutral"
    FORMAL = "formal"
    VERY_FORMAL = "very_formal"


class QualityLevel(str, Enum):
    """Kalite seviyesi."""

    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class PluralForm(str, Enum):
    """Cogul formu."""

    ZERO = "zero"
    ONE = "one"
    TWO = "two"
    FEW = "few"
    MANY = "many"
    OTHER = "other"


class DetectionResult(BaseModel):
    """Dil tespit sonucu."""

    result_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    text: str = ""
    detected_language: LanguageCode = LanguageCode.EN
    confidence: float = 0.0
    script: ScriptType = ScriptType.LATIN
    alternatives: list[dict[str, Any]] = Field(
        default_factory=list,
    )


class TranslationRecord(BaseModel):
    """Ceviri kaydi."""

    translation_id: str = Field(
        default_factory=lambda: str(uuid4())[:8],
    )
    source_lang: LanguageCode = LanguageCode.EN
    target_lang: LanguageCode = LanguageCode.TR
    source_text: str = ""
    translated_text: str = ""
    quality_score: float = 0.0
    domain: str = "general"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class MessageEntry(BaseModel):
    """Mesaj girisi."""

    key: str = ""
    translations: dict[str, str] = Field(
        default_factory=dict,
    )
    context: str = ""
    plurals: dict[str, str] = Field(
        default_factory=dict,
    )


class LocalizationSnapshot(BaseModel):
    """Yerellestirme goruntusu."""

    supported_languages: int = 0
    total_messages: int = 0
    translation_coverage: float = 0.0
    quality_score: float = 0.0
    glossary_terms: int = 0
    pending_reviews: int = 0
    detected_languages: int = 0
    cache_hit_rate: float = 0.0
