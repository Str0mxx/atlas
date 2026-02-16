"""
Smart Speaker Response Formatter - Akıllı hoparlör yanıt formatlama modülü.

Bu modül SSML üretimi, card/audio/visual yanıt oluşturma ve platform
adaptasyonu sağlar.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SmartSpeakerResponseFormatter:
    """Akıllı hoparlör yanıt formatlama sınıfı."""

    def __init__(self) -> None:
        """SmartSpeakerResponseFormatter başlatıcı."""
        self._responses: list[dict] = []
        self._stats = {"responses_formatted": 0, "ssml_generated": 0}
        logger.info("SmartSpeakerResponseFormatter başlatıldı")

    @property
    def response_count(self) -> int:
        """Formatlanan yanıt sayısını döndürür."""
        return self._stats["responses_formatted"]

    @property
    def ssml_count(self) -> int:
        """Üretilen SSML sayısını döndürür."""
        return self._stats["ssml_generated"]

    def generate_ssml(
        self,
        text: str,
        rate: str = "medium",
        pitch: str = "medium",
        voice: str = ""
    ) -> dict[str, Any]:
        """
        SSML (Speech Synthesis Markup Language) üretir.

        Args:
            text: Konuşulacak metin
            rate: Konuşma hızı
            pitch: Ses perdesi
            voice: Ses profili

        Returns:
            Üretilen SSML
        """
        ssml = (
            f'<speak><prosody rate="{rate}" pitch="{pitch}">'
            f'{text}</prosody></speak>'
        )

        if voice:
            ssml = (
                f'<speak><voice name="{voice}">'
                f'<prosody rate="{rate}" pitch="{pitch}">'
                f'{text}</prosody></voice></speak>'
            )

        self._stats["ssml_generated"] += 1

        logger.debug(
            f"SSML üretildi (rate: {rate}, pitch: {pitch}, "
            f"voice: {voice or 'default'})"
        )

        return {
            "ssml": ssml,
            "rate": rate,
            "pitch": pitch,
            "generated": True
        }

    def build_card(
        self,
        title: str,
        content: str,
        image_url: str = ""
    ) -> dict[str, Any]:
        """
        Görsel kart oluşturur.

        Args:
            title: Kart başlığı
            content: Kart içeriği
            image_url: Kart görseli URL'i

        Returns:
            Oluşturulan kart
        """
        card = {
            "title": title,
            "content": content,
            "image_url": image_url
        }

        has_image = bool(image_url)

        logger.debug(
            f"Kart oluşturuldu: {title} (görsel: {has_image})"
        )

        return {
            "card": card,
            "has_image": has_image,
            "built": True
        }

    def build_audio_response(
        self,
        audio_url: str,
        fallback_text: str = ""
    ) -> dict[str, Any]:
        """
        Ses yanıtı oluşturur.

        Args:
            audio_url: Ses dosyası URL'i
            fallback_text: Yedek metin

        Returns:
            Oluşturulan ses yanıtı
        """
        if not fallback_text:
            fallback_text = "Audio playing"

        logger.debug(f"Ses yanıtı oluşturuldu: {audio_url}")

        return {
            "audio_url": audio_url,
            "fallback_text": fallback_text,
            "type": "audio",
            "built": True
        }

    def build_visual_response(
        self,
        title: str,
        body: str = "",
        image_url: str = "",
        buttons: Optional[list] = None
    ) -> dict[str, Any]:
        """
        Görsel yanıt oluşturur.

        Args:
            title: Başlık
            body: İçerik metni
            image_url: Görsel URL'i
            buttons: Buton listesi

        Returns:
            Oluşturulan görsel yanıt
        """
        if buttons is None:
            buttons = []

        logger.debug(
            f"Görsel yanıt oluşturuldu: {title} "
            f"({len(buttons)} buton)"
        )

        return {
            "title": title,
            "body": body,
            "image_url": image_url,
            "buttons": buttons,
            "button_count": len(buttons),
            "type": "visual",
            "built": True
        }

    def adapt_platform(
        self,
        response: dict,
        platform: str = "alexa"
    ) -> dict[str, Any]:
        """
        Yanıtı platforma göre adapte eder.

        Args:
            response: Ham yanıt
            platform: Hedef platform (alexa, google, siri)

        Returns:
            Adapte edilmiş yanıt
        """
        adapted = {}

        if platform == "alexa":
            adapted = {
                "outputSpeech": response.get("speech", ""),
                "card": response.get("card")
            }
        elif platform == "google":
            adapted = {
                "fulfillmentText": response.get("text", ""),
                "payload": response
            }
        elif platform == "siri":
            adapted = {
                "spoken": response.get("spoken_text", ""),
                "display": response.get("display_text", "")
            }
        else:
            adapted = response

        self._stats["responses_formatted"] += 1

        logger.debug(f"Yanıt {platform} için adapte edildi")

        return {
            "platform": platform,
            "adapted_response": adapted,
            "adapted": True
        }
