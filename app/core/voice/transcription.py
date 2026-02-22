"""
Transcription Manager - Ses-metin donusum yonetimi.

Whisper entegrasyonu, kaynak-farkindalikli parmak izi tekillestirme
ve medya yer tutucusu degistirme islemlerini yonetir.
"""

import hashlib
import logging
import time
import uuid
from typing import Optional

from app.models.voicesys_models import TranscriptionResult

logger = logging.getLogger(__name__)


class TranscriptionManager:
    """
    Ses-metin donusum yoneticisi.

    Whisper entegrasyonu, kaynak-farkindalikli parmak izi tekillestirme
    ve medya yer tutucusu degistirme islemlerini yonetir.

    Attributes:
        whisper_model: Whisper model adi
    """

    def __init__(self, whisper_model: str = "base") -> None:
        """TranscriptionManager baslatici."""
        self.whisper_model = whisper_model
        self._transcriptions: dict[str, TranscriptionResult] = {}
        self._history: list[dict] = []
        logger.info("TranscriptionManager baslatildi, model=%s", whisper_model)

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina olay ekler."""
        entry = {"action": action, "timestamp": time.time(), "details": details or {}}
        self._history.append(entry)

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Transkripsiyon istatistiklerini dondurur."""
        total = len(self._transcriptions)
        dupes = sum(1 for t in self._transcriptions.values() if t.is_duplicate)
        return {"total_transcriptions": total, "duplicate_count": dupes, "whisper_model": self.whisper_model, "history_count": len(self._history)}

    def transcribe(self, audio_path: str, language: str = "tr") -> TranscriptionResult:
        """
        Ses dosyasini metne donusturur.

        Args:
            audio_path: Ses dosyasi yolu
            language: Hedef dil kodu

        Returns:
            TranscriptionResult sonucu
        """
        transcription_id = str(uuid.uuid4())
        text = self._whisper_transcribe(audio_path, language)
        fingerprint = self._compute_fingerprint(text, "whisper")
        result = TranscriptionResult(
            transcription_id=transcription_id,
            text=text,
            language=language,
            confidence=0.85,
            timestamp=time.time(),
            source="whisper",
            fingerprint=fingerprint,
        )
        self._transcriptions[transcription_id] = result
        self._record_history("transcribe", {"transcription_id": transcription_id, "audio_path": audio_path, "language": language})
        return result

    def transcribe_voice_note(self, audio_data: bytes, fallback: str = "") -> TranscriptionResult:
        """
        DM sesli notunu metne donusturur.

        Args:
            audio_data: Ham ses verisi
            fallback: Basarisiz olursa varsayilan metin

        Returns:
            TranscriptionResult sonucu
        """
        transcription_id = str(uuid.uuid4())
        if not audio_data:
            result = TranscriptionResult(transcription_id=transcription_id, text=fallback, confidence=0.0, timestamp=time.time(), source="fallback")
            self._transcriptions[transcription_id] = result
            self._record_history("transcribe_voice_note_fallback", {"transcription_id": transcription_id})
            return result
        audio_hash = hashlib.md5(audio_data).hexdigest()[:8]
        text = f"[ses notu: {audio_hash}]"
        fingerprint = self._compute_fingerprint(text, "voice_note")
        result = TranscriptionResult(
            transcription_id=transcription_id,
            text=text,
            language="tr",
            confidence=0.75,
            timestamp=time.time(),
            source="voice_note",
            fingerprint=fingerprint,
        )
        self._transcriptions[transcription_id] = result
        self._record_history("transcribe_voice_note", {"transcription_id": transcription_id, "audio_hash": audio_hash})
        return result

    def dedupe_transcript(self, result: TranscriptionResult, existing: list[TranscriptionResult]) -> bool:
        """
        Kaynak-farkindalikli parmak izi tekillestirme yapar.

        Args:
            result: Kontrol edilecek transkripsiyon
            existing: Mevcut transkripsiyon listesi

        Returns:
            Tekrar ise True
        """
        for ex in existing:
            if ex.fingerprint == result.fingerprint and ex.source == result.source:
                result.is_duplicate = True
                self._record_history("dedupe_transcript", {"duplicate_of": ex.transcription_id, "transcription_id": result.transcription_id})
                return True
        return False

    def replace_media_placeholder(self, text: str, transcript: str) -> str:
        """
        Medya yer tutucusunu transkript ile degistirir.

        Args:
            text: Orijinal metin (<media:audio> yer tutucusu iceren)
            transcript: Degistirilecek transkript

        Returns:
            Guncellenmis metin
        """
        placeholder = "<media:audio>"
        if placeholder in text:
            result = text.replace(placeholder, transcript)
            self._record_history("replace_media_placeholder", {"original_len": len(text), "result_len": len(result)})
            return result
        return text

    def get_transcription(self, transcription_id: str) -> Optional[TranscriptionResult]:
        """Transkripsiyon sonucunu dondurur."""
        return self._transcriptions.get(transcription_id)

    def list_transcriptions(self, call_id: str = "") -> list[TranscriptionResult]:
        """Belirli bir aramaya ait transkripsiyon listesi."""
        if not call_id:
            return list(self._transcriptions.values())
        return [t for t in self._transcriptions.values() if t.call_id == call_id]

    def _compute_fingerprint(self, text: str, source: str) -> str:
        """Kaynak-farkindalikli parmak izi hesaplar."""
        normalized = text.strip().lower()
        raw = f"{source}:{normalized}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _whisper_transcribe(self, audio_path: str, language: str) -> str:
        """Whisper ile transkripsiyon (stub)."""
        return f"[transkripsiyon: {audio_path}]"
