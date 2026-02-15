"""ATLAS Konuşmadan Metne modülü.

Gerçek zamanlı transkripsiyon, çoklu dil,
gürültü filtreleme, konuşmacı ayrımı,
güven puanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SpeechToText:
    """Konuşmadan metne dönüştürücü.

    Ses verilerini metne çevirir.

    Attributes:
        _transcriptions: Transkripsiyon kayıtları.
        _languages: Desteklenen diller.
    """

    def __init__(
        self,
        default_language: str = "en",
        noise_filter: bool = True,
    ) -> None:
        """STT'yi başlatır.

        Args:
            default_language: Varsayılan dil.
            noise_filter: Gürültü filtresi.
        """
        self._transcriptions: list[
            dict[str, Any]
        ] = []
        self._languages: dict[
            str, dict[str, Any]
        ] = {
            "en": {"name": "English", "enabled": True},
            "tr": {"name": "Turkish", "enabled": True},
            "de": {"name": "German", "enabled": True},
            "fr": {"name": "French", "enabled": True},
            "ar": {"name": "Arabic", "enabled": True},
        }
        self._default_language = default_language
        self._noise_filter = noise_filter
        self._counter = 0
        self._stats = {
            "transcriptions": 0,
            "total_duration": 0.0,
            "avg_confidence": 0.0,
        }

        logger.info("SpeechToText baslatildi")

    def transcribe(
        self,
        audio_data: str,
        language: str | None = None,
        call_id: str | None = None,
        speaker_id: str | None = None,
    ) -> dict[str, Any]:
        """Ses verisini metne çevirir.

        Args:
            audio_data: Ses verisi (simüle).
            language: Dil kodu.
            call_id: İlişkili arama ID.
            speaker_id: Konuşmacı ID.

        Returns:
            Transkripsiyon bilgisi.
        """
        self._counter += 1
        tid = f"tr_{self._counter}"
        lang = language or self._default_language

        # Simüle transkripsiyon
        text = audio_data
        confidence = 0.85
        if self._noise_filter:
            confidence += 0.05

        # Dil kontrolü
        if lang not in self._languages:
            return {
                "error": "unsupported_language",
                "language": lang,
            }

        transcription = {
            "transcription_id": tid,
            "call_id": call_id,
            "text": text,
            "language": lang,
            "confidence": round(confidence, 3),
            "speaker_id": speaker_id,
            "duration_seconds": len(
                audio_data,
            ) * 0.1,
            "noise_filtered": self._noise_filter,
            "timestamp": time.time(),
        }
        self._transcriptions.append(
            transcription,
        )
        self._update_stats(transcription)

        return transcription

    def transcribe_realtime(
        self,
        audio_chunks: list[str],
        language: str | None = None,
        call_id: str | None = None,
    ) -> dict[str, Any]:
        """Gerçek zamanlı transkripsiyon yapar.

        Args:
            audio_chunks: Ses parçaları.
            language: Dil kodu.
            call_id: Arama ID.

        Returns:
            Transkripsiyon sonucu.
        """
        results = []
        for chunk in audio_chunks:
            result = self.transcribe(
                chunk, language, call_id,
            )
            results.append(result)

        full_text = " ".join(
            r["text"] for r in results
            if "text" in r
        )
        avg_conf = (
            sum(
                r.get("confidence", 0)
                for r in results
            )
            / max(len(results), 1)
        )

        return {
            "call_id": call_id,
            "full_text": full_text,
            "chunks": len(results),
            "average_confidence": round(
                avg_conf, 3,
            ),
        }

    def diarize(
        self,
        transcription_id: str,
        speakers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Konuşmacı ayrımı yapar.

        Args:
            transcription_id: Transkripsiyon ID.
            speakers: Bilinen konuşmacılar.

        Returns:
            Ayrım bilgisi.
        """
        trans = self._find_transcription(
            transcription_id,
        )
        if not trans:
            return {
                "error": "transcription_not_found",
            }

        speaker_list = speakers or [
            "speaker_1", "speaker_2",
        ]
        # Simüle konuşmacı atama
        segments = []
        words = trans["text"].split()
        for i, word in enumerate(words):
            speaker = speaker_list[
                i % len(speaker_list)
            ]
            segments.append({
                "word": word,
                "speaker": speaker,
                "confidence": 0.8,
            })

        trans["diarization"] = {
            "speakers": speaker_list,
            "segments": segments,
        }

        return {
            "transcription_id": transcription_id,
            "speakers_detected": len(
                speaker_list,
            ),
            "segments": len(segments),
        }

    def filter_noise(
        self,
        audio_data: str,
        aggressiveness: int = 2,
    ) -> dict[str, Any]:
        """Gürültü filtreler.

        Args:
            audio_data: Ses verisi.
            aggressiveness: Agresiflik (1-3).

        Returns:
            Filtreleme bilgisi.
        """
        aggressiveness = max(
            1, min(3, aggressiveness),
        )
        noise_reduction = aggressiveness * 0.15

        return {
            "filtered": True,
            "aggressiveness": aggressiveness,
            "noise_reduction": round(
                noise_reduction, 2,
            ),
            "data_length": len(audio_data),
        }

    def get_confidence_score(
        self,
        transcription_id: str,
    ) -> dict[str, Any]:
        """Güven puanı getirir.

        Args:
            transcription_id: Transkripsiyon ID.

        Returns:
            Güven bilgisi.
        """
        trans = self._find_transcription(
            transcription_id,
        )
        if not trans:
            return {
                "error": "transcription_not_found",
            }

        conf = trans.get("confidence", 0)
        quality = "high"
        if conf < 0.6:
            quality = "low"
        elif conf < 0.8:
            quality = "medium"

        return {
            "transcription_id": transcription_id,
            "confidence": conf,
            "quality": quality,
        }

    def add_language(
        self,
        code: str,
        name: str,
    ) -> dict[str, Any]:
        """Dil ekler.

        Args:
            code: Dil kodu.
            name: Dil adı.

        Returns:
            Ekleme bilgisi.
        """
        self._languages[code] = {
            "name": name,
            "enabled": True,
        }
        return {
            "language": code,
            "added": True,
        }

    def _find_transcription(
        self,
        transcription_id: str,
    ) -> dict[str, Any] | None:
        """Transkripsiyon bulur."""
        for t in self._transcriptions:
            if (
                t["transcription_id"]
                == transcription_id
            ):
                return t
        return None

    def _update_stats(
        self,
        trans: dict[str, Any],
    ) -> None:
        """İstatistikleri günceller."""
        self._stats["transcriptions"] += 1
        self._stats["total_duration"] += trans.get(
            "duration_seconds", 0,
        )
        n = self._stats["transcriptions"]
        old_avg = self._stats["avg_confidence"]
        new_conf = trans.get("confidence", 0)
        self._stats["avg_confidence"] = round(
            old_avg + (new_conf - old_avg) / n, 3,
        )

    def get_transcriptions(
        self,
        call_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Transkripsiyonları getirir.

        Args:
            call_id: Arama filtresi.
            limit: Maks kayıt.

        Returns:
            Transkripsiyon listesi.
        """
        results = self._transcriptions
        if call_id:
            results = [
                t for t in results
                if t.get("call_id") == call_id
            ]
        return list(results[-limit:])

    @property
    def transcription_count(self) -> int:
        """Transkripsiyon sayısı."""
        return self._stats["transcriptions"]

    @property
    def language_count(self) -> int:
        """Dil sayısı."""
        return len(self._languages)
