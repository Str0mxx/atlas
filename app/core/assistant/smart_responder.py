"""ATLAS Akilli Yanitlayici modulu.

Baglama duyarli yanitlar, ton adaptasyonu,
detay seviyesi ayarlama, format optimizasyonu
ve coklu-modal yanit uretimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import (
    ChannelType,
    ResponseFormat,
    SmartResponse,
)

logger = logging.getLogger(__name__)


class SmartResponder:
    """Akilli yanitlayici.

    Baglama ve kullanici tercihlerine gore
    optimize edilmis yanitlar uretir.

    Attributes:
        _responses: Yanit gecmisi.
        _tone_rules: Ton kurallari.
        _format_rules: Format kurallari.
        _templates: Yanit sablonlari.
        _default_tone: Varsayilan ton.
        _default_detail: Varsayilan detay seviyesi.
    """

    def __init__(
        self,
        default_tone: str = "professional",
        default_detail: float = 0.5,
    ) -> None:
        """Akilli yanitlayiciyi baslatir.

        Args:
            default_tone: Varsayilan ton.
            default_detail: Varsayilan detay seviyesi.
        """
        self._responses: list[SmartResponse] = []
        self._tone_rules: dict[str, str] = {
            "error": "empathetic",
            "success": "enthusiastic",
            "question": "helpful",
            "urgent": "direct",
            "casual": "friendly",
        }
        self._format_rules: dict[str, ResponseFormat] = {
            "list_request": ResponseFormat.LIST,
            "summary_request": ResponseFormat.SUMMARY,
            "detail_request": ResponseFormat.DETAILED,
            "comparison": ResponseFormat.TABLE,
        }
        self._templates: dict[str, str] = {}
        self._default_tone = default_tone
        self._default_detail = max(0.0, min(1.0, default_detail))

        logger.info(
            "SmartResponder baslatildi (tone=%s, detail=%.1f)",
            default_tone, self._default_detail,
        )

    def generate_response(
        self,
        content: str,
        context: dict[str, Any] | None = None,
        channel: ChannelType = ChannelType.TELEGRAM,
    ) -> SmartResponse:
        """Baglama duyarli yanit uretir.

        Args:
            content: Yanit icerigi.
            context: Baglam bilgisi.
            channel: Hedef kanal.

        Returns:
            SmartResponse nesnesi.
        """
        ctx = context or {}

        # Ton belirle
        tone = self._determine_tone(ctx)

        # Format belirle
        fmt = self._determine_format(content, ctx)

        # Detay seviyesi
        detail = self._determine_detail(ctx)

        # Icerigi formata uyarla
        formatted = self._format_content(content, fmt, channel)

        response = SmartResponse(
            content=formatted,
            format=fmt,
            tone=tone,
            detail_level=detail,
            channel=channel,
        )
        self._responses.append(response)

        logger.info(
            "Yanit uretildi: format=%s, tone=%s, channel=%s",
            fmt.value, tone, channel.value,
        )
        return response

    def adapt_tone(
        self,
        content: str,
        target_tone: str,
    ) -> str:
        """Ton adapte eder.

        Args:
            content: Orijinal icerik.
            target_tone: Hedef ton.

        Returns:
            Adapte edilmis icerik.
        """
        if target_tone == "formal":
            return content.replace("!", ".").replace("hey", "merhaba")
        if target_tone == "friendly":
            if not content.endswith(("!", "?")):
                content = content.rstrip(".") + "!"
            return content
        if target_tone == "direct":
            sentences = content.split(". ")
            if len(sentences) > 2:
                return ". ".join(sentences[:2]) + "."
            return content
        return content

    def adjust_detail(
        self,
        content: str,
        level: float,
    ) -> str:
        """Detay seviyesi ayarlar.

        Args:
            content: Orijinal icerik.
            level: Detay seviyesi (0-1).

        Returns:
            Ayarlanmis icerik.
        """
        level = max(0.0, min(1.0, level))
        sentences = [s.strip() for s in content.split(".") if s.strip()]

        if not sentences:
            return content

        if level < 0.3:
            # Az detay - ilk cumle
            return sentences[0] + "."
        if level < 0.7:
            # Orta detay - ilk yari
            mid = max(1, len(sentences) // 2)
            return ". ".join(sentences[:mid]) + "."

        # Tam detay
        return content

    def optimize_format(
        self,
        content: str,
        target_format: ResponseFormat,
    ) -> str:
        """Format optimize eder.

        Args:
            content: Orijinal icerik.
            target_format: Hedef format.

        Returns:
            Formatlanmis icerik.
        """
        if target_format == ResponseFormat.LIST:
            lines = [
                s.strip() for s in content.split(".")
                if s.strip()
            ]
            return "\n".join(f"- {line}" for line in lines)

        if target_format == ResponseFormat.SUMMARY:
            sentences = [
                s.strip() for s in content.split(".")
                if s.strip()
            ]
            if len(sentences) > 1:
                return sentences[0] + "."
            return content

        if target_format == ResponseFormat.TABLE:
            return f"| Bilgi |\n|-------|\n| {content} |"

        return content

    def add_tone_rule(self, context_key: str, tone: str) -> None:
        """Ton kurali ekler.

        Args:
            context_key: Baglam anahtari.
            tone: Ton.
        """
        self._tone_rules[context_key] = tone

    def add_format_rule(
        self,
        context_key: str,
        fmt: ResponseFormat,
    ) -> None:
        """Format kurali ekler.

        Args:
            context_key: Baglam anahtari.
            fmt: Format.
        """
        self._format_rules[context_key] = fmt

    def add_template(self, name: str, template: str) -> None:
        """Sablon ekler.

        Args:
            name: Sablon adi.
            template: Sablon icerigi.
        """
        self._templates[name] = template

    def render_template(
        self,
        name: str,
        variables: dict[str, Any],
    ) -> str | None:
        """Sablonu render eder.

        Args:
            name: Sablon adi.
            variables: Degiskenler.

        Returns:
            Render edilmis metin veya None.
        """
        template = self._templates.get(name)
        if not template:
            return None

        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def format_for_channel(
        self,
        content: str,
        channel: ChannelType,
    ) -> str:
        """Kanala gore formatlar.

        Args:
            content: Icerik.
            channel: Kanal.

        Returns:
            Formatlanmis icerik.
        """
        if channel == ChannelType.TELEGRAM:
            # Telegram markdown
            return content

        if channel == ChannelType.EMAIL:
            # E-posta - resmi baslik/bitis
            return f"Merhaba,\n\n{content}\n\nSaygilarimla,\nATLAS"

        if channel == ChannelType.VOICE:
            # Ses - kisa ve net
            sentences = content.split(". ")
            return ". ".join(sentences[:3])

        return content

    def _determine_tone(self, context: dict[str, Any]) -> str:
        """Baglama gore ton belirler.

        Args:
            context: Baglam.

        Returns:
            Ton adi.
        """
        for key, tone in self._tone_rules.items():
            if context.get(key):
                return tone

        return context.get("tone", self._default_tone)

    def _determine_format(
        self,
        content: str,
        context: dict[str, Any],
    ) -> ResponseFormat:
        """Baglama gore format belirler.

        Args:
            content: Icerik.
            context: Baglam.

        Returns:
            ResponseFormat.
        """
        for key, fmt in self._format_rules.items():
            if context.get(key):
                return fmt

        explicit = context.get("format")
        if explicit:
            try:
                return ResponseFormat(explicit)
            except ValueError:
                pass

        return ResponseFormat.TEXT

    def _determine_detail(self, context: dict[str, Any]) -> float:
        """Baglama gore detay seviyesi belirler.

        Args:
            context: Baglam.

        Returns:
            Detay seviyesi (0-1).
        """
        explicit = context.get("detail_level")
        if isinstance(explicit, (int, float)):
            return max(0.0, min(1.0, float(explicit)))
        return self._default_detail

    def _format_content(
        self,
        content: str,
        fmt: ResponseFormat,
        channel: ChannelType,
    ) -> str:
        """Icerigi format ve kanala uyarlar.

        Args:
            content: Ham icerik.
            fmt: Format.
            channel: Kanal.

        Returns:
            Formatlanmis icerik.
        """
        formatted = self.optimize_format(content, fmt)
        return self.format_for_channel(formatted, channel)

    @property
    def response_count(self) -> int:
        """Yanit sayisi."""
        return len(self._responses)

    @property
    def template_count(self) -> int:
        """Sablon sayisi."""
        return len(self._templates)

    @property
    def tone_rule_count(self) -> int:
        """Ton kurali sayisi."""
        return len(self._tone_rules)
