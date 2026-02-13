"""ATLAS Geri Bildirim Yorumlayici modulu.

Hata aciklamasi, basari onaylamasi, ilerleme raporlama,
aciklama istekleri ve insan dostu yanitlar.
"""

import logging
from typing import Any

from app.models.nlp_engine import (
    FeedbackMessage,
    FeedbackType,
    VerbosityLevel,
)

logger = logging.getLogger(__name__)

# Hata mesaji sablonlari
_ERROR_TEMPLATES: dict[str, str] = {
    "not_found": "{entity} bulunamadi. Lutfen kontrol edin.",
    "permission": "{entity} icin yetkiniz bulunmuyor.",
    "timeout": "{entity} islemi zaman asimina ugradi. Tekrar deneyin.",
    "validation": "{entity} gecersiz. {detail}",
    "connection": "{entity} baglantisi kurulamadi.",
    "generic": "Bir hata olustu: {detail}",
}

# Basari mesaji sablonlari
_SUCCESS_TEMPLATES: dict[str, str] = {
    "created": "{entity} basariyla olusturuldu.",
    "updated": "{entity} basariyla guncellendi.",
    "deleted": "{entity} basariyla silindi.",
    "executed": "{entity} basariyla calistirildi.",
    "configured": "{entity} basariyla yapilandirildi.",
    "generic": "Islem basariyla tamamlandi.",
}


class FeedbackInterpreter:
    """Geri bildirim yorumlayici.

    Sistem olaylarini insan dostu mesajlara donusturur.
    Hata aciklamalari, basari onaylari, ilerleme raporlari
    ve aciklama istekleri olusturur.

    Attributes:
        _verbosity: Ayrinti seviyesi.
        _messages: Geri bildirim gecmisi.
    """

    def __init__(self, verbosity: VerbosityLevel = VerbosityLevel.NORMAL) -> None:
        """Geri bildirim yorumlayiciyi baslatir.

        Args:
            verbosity: Ayrinti seviyesi.
        """
        self._verbosity = verbosity
        self._messages: list[FeedbackMessage] = []

        logger.info("FeedbackInterpreter baslatildi (verbosity=%s)", verbosity.value)

    def explain_error(
        self,
        error_type: str,
        entity: str = "",
        detail: str = "",
        suggestions: list[str] | None = None,
    ) -> FeedbackMessage:
        """Hata aciklamasi olusturur.

        Args:
            error_type: Hata tipi (not_found, permission, timeout, vb).
            entity: Iliskili varlik.
            detail: Ek detay.
            suggestions: Oneriler.

        Returns:
            FeedbackMessage nesnesi.
        """
        template = _ERROR_TEMPLATES.get(error_type, _ERROR_TEMPLATES["generic"])
        content = template.format(entity=entity or "Hedef", detail=detail or "Bilinmeyen hata")

        technical = ""
        if self._verbosity in (VerbosityLevel.DETAILED, VerbosityLevel.DEBUG):
            technical = f"Hata tipi: {error_type}, Varlik: {entity}, Detay: {detail}"

        msg = FeedbackMessage(
            feedback_type=FeedbackType.ERROR_EXPLANATION,
            content=content,
            technical_detail=technical,
            suggestions=suggestions or [f"'{entity}' degerini kontrol edin" if entity else "Tekrar deneyin"],
            verbosity=self._verbosity,
        )
        self._messages.append(msg)
        logger.info("Hata aciklamasi: %s", content[:50])
        return msg

    def confirm_success(
        self,
        action: str = "generic",
        entity: str = "",
        detail: str = "",
    ) -> FeedbackMessage:
        """Basari onaylamasi olusturur.

        Args:
            action: Eylem tipi (created, updated, deleted, vb).
            entity: Iliskili varlik.
            detail: Ek detay.

        Returns:
            FeedbackMessage nesnesi.
        """
        template = _SUCCESS_TEMPLATES.get(action, _SUCCESS_TEMPLATES["generic"])
        content = template.format(entity=entity or "Islem")

        technical = ""
        if self._verbosity in (VerbosityLevel.DETAILED, VerbosityLevel.DEBUG):
            technical = f"Eylem: {action}, Varlik: {entity}, Detay: {detail}"

        msg = FeedbackMessage(
            feedback_type=FeedbackType.SUCCESS_CONFIRMATION,
            content=content,
            technical_detail=technical,
            verbosity=self._verbosity,
        )
        self._messages.append(msg)
        logger.info("Basari onaylamasi: %s", content[:50])
        return msg

    def report_progress(
        self,
        current_step: int,
        total_steps: int,
        description: str = "",
        details: dict[str, Any] | None = None,
    ) -> FeedbackMessage:
        """Ilerleme raporlar.

        Args:
            current_step: Mevcut adim.
            total_steps: Toplam adim sayisi.
            description: Adim aciklamasi.
            details: Ek detaylar.

        Returns:
            FeedbackMessage nesnesi.
        """
        pct = (current_step / total_steps * 100) if total_steps > 0 else 0
        content = f"Ilerleme: {current_step}/{total_steps} (%{pct:.0f})"
        if description:
            content += f" - {description}"

        technical = ""
        if self._verbosity in (VerbosityLevel.DETAILED, VerbosityLevel.DEBUG) and details:
            technical = str(details)

        msg = FeedbackMessage(
            feedback_type=FeedbackType.PROGRESS_REPORT,
            content=content,
            technical_detail=technical,
            verbosity=self._verbosity,
        )
        self._messages.append(msg)
        return msg

    def request_clarification(
        self,
        question: str,
        options: list[str] | None = None,
        context: str = "",
    ) -> FeedbackMessage:
        """Aciklama istegi olusturur.

        Args:
            question: Soru.
            options: Secenekler.
            context: Baglam bilgisi.

        Returns:
            FeedbackMessage nesnesi.
        """
        content = question
        if options:
            content += " Secenekler: " + ", ".join(options)

        technical = context if self._verbosity != VerbosityLevel.MINIMAL else ""

        msg = FeedbackMessage(
            feedback_type=FeedbackType.CLARIFICATION_REQUEST,
            content=content,
            technical_detail=technical,
            suggestions=options or [],
            verbosity=self._verbosity,
        )
        self._messages.append(msg)
        logger.info("Aciklama istegi: %s", question[:50])
        return msg

    def suggest(self, suggestion: str, reason: str = "") -> FeedbackMessage:
        """Oneri olusturur.

        Args:
            suggestion: Oneri metni.
            reason: Gerekce.

        Returns:
            FeedbackMessage nesnesi.
        """
        content = f"Oneri: {suggestion}"
        if reason and self._verbosity != VerbosityLevel.MINIMAL:
            content += f" (Sebep: {reason})"

        msg = FeedbackMessage(
            feedback_type=FeedbackType.SUGGESTION,
            content=content,
            suggestions=[suggestion],
            verbosity=self._verbosity,
        )
        self._messages.append(msg)
        return msg

    def set_verbosity(self, level: VerbosityLevel) -> None:
        """Ayrinti seviyesini degistirir.

        Args:
            level: Yeni ayrinti seviyesi.
        """
        self._verbosity = level
        logger.info("Ayrinti seviyesi degistirildi: %s", level.value)

    @property
    def verbosity(self) -> VerbosityLevel:
        """Ayrinti seviyesi."""
        return self._verbosity

    @property
    def message_count(self) -> int:
        """Toplam mesaj sayisi."""
        return len(self._messages)

    @property
    def messages(self) -> list[FeedbackMessage]:
        """Geri bildirim gecmisi."""
        return list(self._messages)
