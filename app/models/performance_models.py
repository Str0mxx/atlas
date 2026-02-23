"""Performance & Quality veri modelleri.

Baglam sikistirma, akim iyilestirme,
hata siniflandirma ve sayfa bilgisi modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class TruncationInfo(BaseModel):
    """Kesme bilgisi.

    Baglam penceresi kesme isleminin
    sonuclarini tutar.

    Attributes:
        total_chars: Toplam karakter sayisi.
        cap: Karakter limiti.
        truncated: Kesildi mi.
        truncated_count: Kesilen mesaj sayisi.
        kept_count: Tutulan mesaj sayisi.
        truncation_ratio: Kesme orani.
    """

    total_chars: int = 0
    cap: int = 150_000
    truncated: bool = False
    truncated_count: int = 0
    kept_count: int = 0
    truncation_ratio: float = 0.0


class StreamLane(str, Enum):
    """Akim seridi.

    Farkli icerik tiplerini ayirmak
    icin kullanilir.
    """

    REASONING = "reasoning"
    ANSWER = "answer"
    TOOL_CALL = "tool_call"


class StreamChunk(BaseModel):
    """Akim parcasi.

    Tek bir akim parcasinin bilgilerini tutar.

    Attributes:
        content: Parca icerigi.
        lane: Akim seridi.
        thread_id: Is parcacigi kimlik.
        chunk_index: Parca indeksi.
        is_final: Son parca mi.
    """

    content: str = ""
    lane: StreamLane = StreamLane.ANSWER
    thread_id: str = ""
    chunk_index: int = 0
    is_final: bool = False


class CompactionResult(BaseModel):
    """Sikistirma sonucu.

    Arac sonucu sikistirma isleminin
    sonuclarini tutar.

    Attributes:
        original_size: Orijinal boyut.
        compacted_size: Sikistirilmis boyut.
        ratio: Sikistirma orani.
        items_removed: Kaldirilan oge sayisi.
        items_kept: Tutulan oge sayisi.
        strategy: Kullanilan strateji.
    """

    original_size: int = 0
    compacted_size: int = 0
    ratio: float = 0.0
    items_removed: int = 0
    items_kept: int = 0
    strategy: str = ""


class ErrorClassification(str, Enum):
    """Hata siniflandirmasi.

    Hata tiplerini kategorize eder.
    """

    BILLING = "billing"
    TIMEOUT = "timeout"
    CONTEXT_OVERFLOW = "context_overflow"
    PROVIDER = "provider"
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class EnhancedError(BaseModel):
    """Gelistirilmis hata modeli.

    Hata bilgilerini zenginlestirilmis
    formatta tutar.

    Attributes:
        original_error: Orijinal hata mesaji.
        classification: Hata sinifi.
        model: Aktif model adi.
        provider: Saglayici adi.
        retryable: Yeniden denenebilir mi.
        retry_count: Yeniden deneme sayisi.
        max_retries: Maksimum yeniden deneme.
        deferred: Ertelenmis mi.
    """

    original_error: str = ""
    classification: ErrorClassification = (
        ErrorClassification.TRANSIENT
    )
    model: str = ""
    provider: str = ""
    retryable: bool = True
    retry_count: int = 0
    max_retries: int = 3
    deferred: bool = False


class PageInfo(BaseModel):
    """Sayfa bilgisi.

    Otomatik sayfalama isleminin
    sayfa bilgilerini tutar.

    Attributes:
        page_number: Sayfa numarasi.
        total_pages: Toplam sayfa sayisi.
        content_length: Icerik uzunlugu.
        budget_used: Kullanilan butce.
        budget_remaining: Kalan butce.
    """

    page_number: int = 0
    total_pages: int = 0
    content_length: int = 0
    budget_used: int = 0
    budget_remaining: int = 0
