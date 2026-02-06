"""E-posta iletisim agent'i veri modelleri.

Profesyonel e-posta yazma, Gmail API ile gonderme/okuma,
cevap analizi, takip hatirlatma ve sablon yonetimi
sonuclarini modellar.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class EmailTaskType(str, Enum):
    """E-posta gorev tipleri."""

    COMPOSE = "compose"
    SEND = "send"
    READ_INBOX = "read_inbox"
    BULK_SEND = "bulk_send"
    ANALYZE_RESPONSES = "analyze_responses"
    FOLLOW_UP_CHECK = "follow_up_check"


class EmailLanguage(str, Enum):
    """Desteklenen e-posta dilleri."""

    TURKISH = "turkish"
    ENGLISH = "english"
    ARABIC = "arabic"


class EmailTone(str, Enum):
    """E-posta tonu."""

    FORMAL = "formal"
    SEMI_FORMAL = "semi_formal"
    FRIENDLY = "friendly"
    URGENT = "urgent"


class ResponseSentiment(str, Enum):
    """Cevap duygu analizi sonucu."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    NEEDS_ACTION = "needs_action"
    OUT_OF_OFFICE = "out_of_office"


class FollowUpStatus(str, Enum):
    """Takip durumu."""

    PENDING = "pending"
    RESPONDED = "responded"
    FOLLOW_UP_SENT = "follow_up_sent"
    NO_RESPONSE = "no_response"
    EXPIRED = "expired"


class CommunicationConfig(BaseModel):
    """E-posta iletisim yapilandirmasi.

    Attributes:
        model: Kullanilacak Anthropic modeli.
        max_tokens: LLM yanit uzunlugu limiti.
        default_language: Varsayilan e-posta dili.
        default_tone: Varsayilan e-posta tonu.
        follow_up_days: Cevap bekleme suresi (gun).
        max_follow_ups: Maksimum hatirlatma sayisi.
        max_bulk_batch_size: Toplu gonderim batch buyuklugu.
        max_inbox_results: Okunacak maksimum e-posta sayisi.
        sender_name: Gonderici adi.
        sender_email: Gonderici e-posta adresi.
    """

    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    default_language: EmailLanguage = EmailLanguage.TURKISH
    default_tone: EmailTone = EmailTone.FORMAL
    follow_up_days: int = 3
    max_follow_ups: int = 2
    max_bulk_batch_size: int = 50
    max_inbox_results: int = 20
    sender_name: str = ""
    sender_email: str = ""


class EmailRecipient(BaseModel):
    """E-posta alicisi.

    Attributes:
        email: Alici e-posta adresi.
        name: Alici adi.
        variables: Sablon degisken degerleri (kisisellistirme).
    """

    email: str
    name: str = ""
    variables: dict[str, str] = Field(default_factory=dict)


class EmailMessage(BaseModel):
    """Olusturulan veya gonderilen e-posta.

    Attributes:
        message_id: Gmail API mesaj ID (gonderildikten sonra).
        thread_id: Gmail API thread ID.
        to: Alici e-posta adresi.
        to_name: Alici adi.
        subject: E-posta konusu.
        body_html: HTML icerik.
        body_text: Duz metin icerik.
        language: E-posta dili.
        tone: E-posta tonu.
        sent_at: Gonderim zamani.
        is_sent: Gonderildi mi.
    """

    message_id: str = ""
    thread_id: str = ""
    to: str = ""
    to_name: str = ""
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    language: EmailLanguage = EmailLanguage.TURKISH
    tone: EmailTone = EmailTone.FORMAL
    sent_at: datetime | None = None
    is_sent: bool = False


class EmailTemplate(BaseModel):
    """E-posta sablonu.

    Attributes:
        name: Sablon adi (benzersiz anahtar).
        subject: Konu sablonu (degisken iceren).
        body: Govde sablonu (degisken iceren).
        language: Sablon dili.
        tone: Sablon tonu.
        variables: Beklenen degisken adlari.
        description: Sablonun aciklamasi.
    """

    name: str
    subject: str
    body: str
    language: EmailLanguage = EmailLanguage.TURKISH
    tone: EmailTone = EmailTone.FORMAL
    variables: list[str] = Field(default_factory=list)
    description: str = ""


class InboxMessage(BaseModel):
    """Gelen kutusu mesaji.

    Attributes:
        message_id: Gmail API mesaj ID.
        thread_id: Gmail API thread ID.
        from_email: Gonderici e-posta.
        from_name: Gonderici adi.
        subject: Konu.
        snippet: Kisa on izleme.
        body_text: Duz metin icerik.
        received_at: Alinma zamani.
        is_read: Okundu mu.
        labels: Gmail etiketleri.
    """

    message_id: str = ""
    thread_id: str = ""
    from_email: str = ""
    from_name: str = ""
    subject: str = ""
    snippet: str = ""
    body_text: str = ""
    received_at: datetime | None = None
    is_read: bool = False
    labels: list[str] = Field(default_factory=list)


class ResponseAnalysis(BaseModel):
    """E-posta cevap analizi.

    Attributes:
        message_id: Analiz edilen mesaj ID.
        original_message_id: Orijinal gonderilen mesaj ID.
        from_email: Gonderici e-posta.
        sentiment: Duygu analizi sonucu.
        summary: LLM tarafindan uretilen ozet.
        action_required: Aksiyon gerekiyor mu.
        suggested_response: Onerilen cevap metni.
    """

    message_id: str = ""
    original_message_id: str = ""
    from_email: str = ""
    sentiment: ResponseSentiment = ResponseSentiment.NEUTRAL
    summary: str = ""
    action_required: bool = False
    suggested_response: str = ""


class FollowUpEntry(BaseModel):
    """Takip kaydi.

    Attributes:
        original_message_id: Orijinal gonderilen mesaj ID.
        thread_id: Gmail thread ID.
        to_email: Alici e-posta.
        to_name: Alici adi.
        subject: Konu.
        sent_at: Orijinal gonderim zamani.
        follow_up_count: Gonderilen hatirlatma sayisi.
        status: Takip durumu.
        last_follow_up_at: Son hatirlatma zamani.
        response_received_at: Cevap alinma zamani.
    """

    original_message_id: str = ""
    thread_id: str = ""
    to_email: str = ""
    to_name: str = ""
    subject: str = ""
    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    follow_up_count: int = 0
    status: FollowUpStatus = FollowUpStatus.PENDING
    last_follow_up_at: datetime | None = None
    response_received_at: datetime | None = None


class BulkSendResult(BaseModel):
    """Toplu gonderim sonucu.

    Attributes:
        total: Toplam alici sayisi.
        sent: Basariyla gonderilen sayisi.
        failed: Basarisiz sayisi.
        failed_recipients: Basarisiz alicilar ve hatalari.
    """

    total: int = 0
    sent: int = 0
    failed: int = 0
    failed_recipients: list[dict[str, str]] = Field(default_factory=list)


class CommunicationAnalysisResult(BaseModel):
    """E-posta iletisim analiz genel sonucu.

    Attributes:
        task_type: Yapilan gorev tipi.
        composed_emails: Olusturulan e-postalar.
        sent_emails: Gonderilen e-postalar.
        inbox_messages: Okunan gelen kutusu mesajlari.
        response_analyses: Cevap analizleri.
        follow_ups: Takip kayitlari.
        bulk_result: Toplu gonderim sonucu.
        templates_used: Kullanilan sablonlar.
        summary: Analiz ozeti.
    """

    task_type: EmailTaskType = EmailTaskType.COMPOSE
    composed_emails: list[EmailMessage] = Field(default_factory=list)
    sent_emails: list[EmailMessage] = Field(default_factory=list)
    inbox_messages: list[InboxMessage] = Field(default_factory=list)
    response_analyses: list[ResponseAnalysis] = Field(default_factory=list)
    follow_ups: list[FollowUpEntry] = Field(default_factory=list)
    bulk_result: BulkSendResult | None = None
    templates_used: list[str] = Field(default_factory=list)
    summary: str = ""
