"""
Talk Mode Manager - Konusma modu yonetimi.

Arka plan dinleme, araya girme (barge-in), uyandirma kelimesi,
ses yonergesi ipuclari ve token tasarrufu modu ozelliklerini yonetir.
"""

import hashlib
import logging
import time
from typing import Optional

from app.models.voicesys_models import TalkModeConfig

logger = logging.getLogger(__name__)


class TalkModeManager:
    """
    Konusma modu yoneticisi.

    Sesli arama sirasinda arka plan dinleme, araya girme,
    uyandirma kelimesi ve token tasarrufu ozelliklerini kontrol eder.

    Attributes:
        _config: Aktif konusma modu yapilandirmasi
    """

    def __init__(self) -> None:
        """TalkModeManager baslatici."""
        self._config: TalkModeConfig = TalkModeConfig()
        self._history: list[dict] = []
        logger.info("TalkModeManager baslatildi")

    def _record_history(self, action: str, details: Optional[dict] = None) -> None:
        """Gecmis kaydina olay ekler."""
        entry = {"action": action, "timestamp": time.time(), "details": details or {}}
        self._history.append(entry)

    def get_history(self) -> list[dict]:
        """Tum gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Konusma modu istatistiklerini dondurur."""
        return {
            "enabled": self._config.enabled,
            "background_listening": self._config.background_listening,
            "barge_in_enabled": self._config.barge_in_enabled,
            "token_saving_mode": self._config.token_saving_mode,
            "wake_word": self._config.wake_word,
            "history_count": len(self._history),
        }

    def enable(self, config: Optional[TalkModeConfig] = None) -> TalkModeConfig:
        """
        Konusma modunu etkinlestirir.

        Args:
            config: Ozel yapilandirma (None ise varsayilan kullanilir)

        Returns:
            Aktif yapilandirma
        """
        if config is not None:
            self._config = config
        self._config.enabled = True
        self._record_history("enable", {"config": self._config.model_dump()})
        logger.info("Konusma modu etkinlestirildi")
        return self._config

    def disable(self) -> None:
        """Konusma modunu devre disi birakir."""
        self._config.enabled = False
        self._record_history("disable")
        logger.info("Konusma modu devre disi birakildi")

    def is_active(self) -> bool:
        """Konusma modunun aktif olup olmadigini kontrol eder."""
        return self._config.enabled

    def get_config(self) -> TalkModeConfig:
        """Aktif yapilandirmayi dondurur."""
        return self._config

    def toggle_background_listening(self) -> bool:
        """Arka plan dinlemeyi acar/kapatir."""
        self._config.background_listening = not self._config.background_listening
        self._record_history("toggle_background_listening", {"enabled": self._config.background_listening})
        return self._config.background_listening

    def toggle_voice_directives(self) -> bool:
        """Ses yonergesi ipuclarini acar/kapatir."""
        self._config.voice_directive_hints = not self._config.voice_directive_hints
        self._record_history("toggle_voice_directives", {"enabled": self._config.voice_directive_hints})
        return self._config.voice_directive_hints

    def set_barge_in(self, enabled: bool = True, speaker_disable: bool = False, receiver_disable: bool = False) -> None:
        """
        Araya girme (barge-in) ayarlarini yapilandirir.

        Args:
            enabled: Araya girme etkin mi
            speaker_disable: Konusmaci tarafini devre disi birak
            receiver_disable: Alici tarafini devre disi birak
        """
        self._config.barge_in_enabled = enabled
        self._config.barge_in_speaker_disable = speaker_disable
        self._config.barge_in_receiver_disable = receiver_disable
        self._record_history("set_barge_in", {"enabled": enabled, "speaker_disable": speaker_disable, "receiver_disable": receiver_disable})

    def enable_token_saving(self) -> None:
        """Token tasarrufu modunu etkinlestirir."""
        self._config.token_saving_mode = True
        self._record_history("enable_token_saving")
        logger.info("Token tasarrufu modu etkinlestirildi")

    def set_wake_word(self, word: str) -> None:
        """
        Uyandirma kelimesini ayarlar.

        Args:
            word: Uyandirma kelimesi
        """
        self._config.wake_word = word
        self._record_history("set_wake_word", {"word": word})
        logger.info("Uyandirma kelimesi ayarlandi: %s", word)

    def process_audio_input(self, audio_data: bytes) -> Optional[str]:
        """
        Gelen ses verisini isler.

        Args:
            audio_data: Ham ses verisi

        Returns:
            Islenmis metin veya None (sessize alinmissa)
        """
        if not self._config.enabled:
            return None
        if not audio_data:
            return None
        # Stub: gercek uygulamada STT entegrasyonu yapilir
        audio_hash = hashlib.md5(audio_data).hexdigest()[:8]
        self._record_history("process_audio_input", {"audio_hash": audio_hash, "size": len(audio_data)})
        return f"[audio:{audio_hash}]"
