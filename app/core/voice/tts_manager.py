"""
TTS Manager - Metin-konusma sentezleme yonetimi.

Birden fazla TTS saglayiciyi destekler (ElevenLabs, Edge TTS, Google TTS).
Onbellek, guvenli gecici dosya olusturma ve saglayici saglik kontrolu saglar.
"""

import hashlib
import logging
import os
import secrets
import time
import uuid
from typing import Optional

from app.models.voicesys_models import TTSProvider, TTSRequest, TTSResult

logger = logging.getLogger(__name__)


class TTSManager:
    """
    Metin-konusma sentezleme yoneticisi.

    Attributes:
        default_provider: Varsayilan TTS saglayici
        cache_dir: Onbellek dizini
    """

    def __init__(self, default_provider: TTSProvider = TTSProvider.ELEVENLABS, cache_dir: str = "workspace/voice/cache", temp_dir: str = "workspace/voice/temp", secure_temp: bool = True, owner_only: bool = True) -> None:
        """TTSManager baslatici."""
        self.default_provider = default_provider
        self.cache_dir = cache_dir
        self.temp_dir = temp_dir
        self.secure_temp = secure_temp
        self.owner_only = owner_only
        self._cache: dict[str, TTSResult] = {}
        self._history: list[dict] = []
        self._provider_status: dict[str, dict] = {}

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina olay ekler."""
        entry = {"action": action, "timestamp": time.time(), "details": details or {}}
        self._history.append(entry)

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """TTS istatistiklerini dondurur."""
        return {"default_provider": self.default_provider.value, "cache_size": len(self._cache), "history_count": len(self._history)}

    def synthesize(self, text: str, provider: Optional[TTSProvider] = None, voice_id: str = "default") -> TTSResult:
        """Metni konusmaya sentezler."""
        prov = provider or self.default_provider
        cache_key = self._make_cache_key(text, prov, voice_id)
        cached = self.get_cached(cache_key)
        if cached is not None:
            self._record_history("synthesize_cached", {"cache_key": cache_key})
            return cached
        errors: list[str] = []
        result = TTSResult(request_id=str(uuid.uuid4()), provider=prov)
        try:
            if prov == TTSProvider.ELEVENLABS:
                result = self._synthesize_elevenlabs(text, voice_id)
            elif prov == TTSProvider.EDGE_TTS:
                result = self._synthesize_edge_tts(text)
            elif prov == TTSProvider.GOOGLE_TTS:
                result = self._synthesize_google(text)
            else:
                result.error = f"Bilinmeyen saglayici: {prov}"
                errors.append(result.error)
        except Exception as e:
            err_msg = f"{prov.value} hatasi: {str(e)}"
            errors.append(err_msg)
            result.error = self._surface_all_errors(errors)
        if not result.error:
            self._cache[cache_key] = result
        self._record_history("synthesize", {"provider": prov.value, "text_len": len(text), "error": result.error})
        return result

    def pre_cache_greeting(self, text: str) -> TTSResult:
        """Karsilama sesini onceden onbellege alir."""
        self._record_history("pre_cache_greeting", {"text": text})
        return self.synthesize(text)

    def get_cached(self, cache_key: str) -> Optional[TTSResult]:
        """Onbellekten sonuc dondurur."""
        result = self._cache.get(cache_key)
        if result is not None:
            cached_copy = result.model_copy()
            cached_copy.cached = True
            return cached_copy
        return None

    def clear_cache(self) -> int:
        """TTS onbellegini temizler."""
        count = len(self._cache)
        self._cache.clear()
        self._record_history("clear_cache", {"cleared": count})
        return count

    def list_voices(self, provider: Optional[TTSProvider] = None) -> list[dict]:
        """Mevcut sesleri listeler."""
        prov = provider or self.default_provider
        voices = [{"id": "default", "name": "Varsayilan", "language": "tr", "provider": prov.value}, {"id": "voice_1", "name": "Ses 1", "language": "tr", "provider": prov.value}]
        self._record_history("list_voices", {"provider": prov.value})
        return voices

    def set_default_provider(self, provider: TTSProvider) -> None:
        """Varsayilan TTS saglayiciyi ayarlar."""
        self.default_provider = provider
        self._record_history("set_default_provider", {"provider": provider.value})

    def get_provider_status(self) -> dict:
        """Saglayici saglik durumlarini dondurur."""
        status = {}
        for prov in TTSProvider:
            status[prov.value] = self._provider_status.get(prov.value, {"status": "unknown", "last_check": 0})
        return status

    def _synthesize_elevenlabs(self, text: str, voice_id: str = "default") -> TTSResult:
        """ElevenLabs TTS sentezleme (stub)."""
        audio_path = self._create_secure_temp_file(".mp3")
        return TTSResult(request_id=str(uuid.uuid4()), provider=TTSProvider.ELEVENLABS, audio_path=audio_path, duration=len(text) * 0.06, size_bytes=len(text) * 100)

    def _synthesize_edge_tts(self, text: str) -> TTSResult:
        """Edge TTS sentezleme (stub)."""
        audio_path = self._create_secure_temp_file(".mp3")
        return TTSResult(request_id=str(uuid.uuid4()), provider=TTSProvider.EDGE_TTS, audio_path=audio_path, duration=len(text) * 0.07, size_bytes=len(text) * 80)

    def _synthesize_google(self, text: str) -> TTSResult:
        """Google TTS sentezleme (stub)."""
        audio_path = self._create_secure_temp_file(".mp3")
        return TTSResult(request_id=str(uuid.uuid4()), provider=TTSProvider.GOOGLE_TTS, audio_path=audio_path, duration=len(text) * 0.065, size_bytes=len(text) * 90)

    def _create_secure_temp_file(self, suffix: str = ".tmp") -> str:
        """Kriptografik rastgele isimli guvenli gecici dosya olusturur."""
        random_name = secrets.token_hex(16) + suffix
        file_path = os.path.join(self.temp_dir, random_name)
        self._record_history("create_secure_temp_file", {"path": file_path})
        return file_path

    def _surface_all_errors(self, errors: list[str]) -> str:
        """Tum saglayici hatalarini birlestirerek dondurur."""
        if not errors:
            return ""
        return " | ".join(errors)

    def _make_cache_key(self, text: str, provider: TTSProvider, voice_id: str) -> str:
        """Onbellek anahtari olusturur."""
        raw = f"{provider.value}:{voice_id}:{text}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
