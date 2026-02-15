"""ATLAS Metinden Konuşmaya modülü.

Doğal ses sentezi, çoklu ses, duygu kontrolü,
hız ayarı, SSML desteği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Metinden konuşmaya dönüştürücü.

    Metni sese dönüştürür.

    Attributes:
        _syntheses: Sentez kayıtları.
        _voices: Mevcut sesler.
    """

    def __init__(
        self,
        default_voice: str = "atlas_default",
        default_speed: float = 1.0,
    ) -> None:
        """TTS'yi başlatır.

        Args:
            default_voice: Varsayılan ses.
            default_speed: Varsayılan hız.
        """
        self._syntheses: list[
            dict[str, Any]
        ] = []
        self._voices: dict[
            str, dict[str, Any]
        ] = {
            "atlas_default": {
                "gender": "neutral",
                "language": "en",
                "style": "professional",
            },
            "atlas_warm": {
                "gender": "female",
                "language": "en",
                "style": "warm",
            },
            "atlas_formal": {
                "gender": "male",
                "language": "en",
                "style": "formal",
            },
        }
        self._default_voice = default_voice
        self._default_speed = default_speed
        self._counter = 0
        self._stats = {
            "syntheses": 0,
            "total_chars": 0,
        }

        logger.info("TextToSpeech baslatildi")

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
        emotion: str = "neutral",
        language: str = "en",
    ) -> dict[str, Any]:
        """Metni sese dönüştürür.

        Args:
            text: Metin.
            voice: Ses adı.
            speed: Hız çarpanı.
            emotion: Duygu.
            language: Dil.

        Returns:
            Sentez bilgisi.
        """
        self._counter += 1
        sid = f"tts_{self._counter}"
        used_voice = voice or self._default_voice
        used_speed = speed or self._default_speed
        used_speed = max(0.5, min(2.0, used_speed))

        # Simüle süre
        duration = len(text) * 0.05 / used_speed

        synthesis = {
            "synthesis_id": sid,
            "text": text,
            "voice": used_voice,
            "speed": used_speed,
            "emotion": emotion,
            "language": language,
            "duration_seconds": round(
                duration, 2,
            ),
            "audio_format": "wav",
            "timestamp": time.time(),
        }
        self._syntheses.append(synthesis)
        self._stats["syntheses"] += 1
        self._stats["total_chars"] += len(text)

        return synthesis

    def synthesize_ssml(
        self,
        ssml: str,
        voice: str | None = None,
    ) -> dict[str, Any]:
        """SSML ile sentez yapar.

        Args:
            ssml: SSML metni.
            voice: Ses adı.

        Returns:
            Sentez bilgisi.
        """
        # SSML tag'lerini çıkar
        import re

        plain_text = re.sub(
            r"<[^>]+>", "", ssml,
        )

        result = self.synthesize(
            plain_text,
            voice=voice,
        )
        result["ssml"] = True
        result["original_ssml"] = ssml

        return result

    def set_emotion(
        self,
        synthesis_id: str,
        emotion: str,
        intensity: float = 0.5,
    ) -> dict[str, Any]:
        """Duygu ayarlar.

        Args:
            synthesis_id: Sentez ID.
            emotion: Duygu (happy, sad, angry, calm, excited).
            intensity: Yoğunluk (0-1).

        Returns:
            Ayar bilgisi.
        """
        synth = self._find_synthesis(
            synthesis_id,
        )
        if not synth:
            return {"error": "synthesis_not_found"}

        intensity = max(0.0, min(1.0, intensity))
        synth["emotion"] = emotion
        synth["emotion_intensity"] = intensity

        return {
            "synthesis_id": synthesis_id,
            "emotion": emotion,
            "intensity": intensity,
        }

    def adjust_speed(
        self,
        synthesis_id: str,
        speed: float,
    ) -> dict[str, Any]:
        """Hız ayarlar.

        Args:
            synthesis_id: Sentez ID.
            speed: Hız çarpanı (0.5-2.0).

        Returns:
            Ayar bilgisi.
        """
        synth = self._find_synthesis(
            synthesis_id,
        )
        if not synth:
            return {"error": "synthesis_not_found"}

        speed = max(0.5, min(2.0, speed))
        synth["speed"] = speed

        return {
            "synthesis_id": synthesis_id,
            "speed": speed,
        }

    def add_voice(
        self,
        name: str,
        gender: str = "neutral",
        language: str = "en",
        style: str = "default",
    ) -> dict[str, Any]:
        """Ses ekler.

        Args:
            name: Ses adı.
            gender: Cinsiyet.
            language: Dil.
            style: Stil.

        Returns:
            Ekleme bilgisi.
        """
        self._voices[name] = {
            "gender": gender,
            "language": language,
            "style": style,
        }
        return {
            "voice": name,
            "added": True,
        }

    def list_voices(
        self,
        language: str | None = None,
    ) -> list[dict[str, Any]]:
        """Sesleri listeler.

        Args:
            language: Dil filtresi.

        Returns:
            Ses listesi.
        """
        results = []
        for name, info in self._voices.items():
            if language and info.get(
                "language",
            ) != language:
                continue
            results.append({
                "name": name,
                **info,
            })
        return results

    def _find_synthesis(
        self,
        synthesis_id: str,
    ) -> dict[str, Any] | None:
        """Sentez bulur."""
        for s in self._syntheses:
            if s["synthesis_id"] == synthesis_id:
                return s
        return None

    def get_syntheses(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Sentezleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Sentez listesi.
        """
        return list(self._syntheses[-limit:])

    @property
    def synthesis_count(self) -> int:
        """Sentez sayısı."""
        return self._stats["syntheses"]

    @property
    def voice_count(self) -> int:
        """Ses sayısı."""
        return len(self._voices)
