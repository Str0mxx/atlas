"""
Wake Word Handler - Uyandırma kelimesi tespit ve yönetim modülü.

Bu modül wake word kayıt, tespit, aktivasyon yönlendirme ve gizlilik
yönetimi sağlar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WakeWordHandler:
    """Uyandırma kelimesi tespit ve yönetim sınıfı."""

    def __init__(self) -> None:
        """WakeWordHandler başlatıcı."""
        self._wake_words: dict[str, dict] = {}
        self._activations: list[dict] = []
        self._privacy: dict[str, dict] = {}
        self._stats = {"activations_handled": 0, "words_registered": 0}

        # Default wake word
        self.register_wake_word("atlas", "en", 0.7)

        logger.info("WakeWordHandler başlatıldı")

    @property
    def activation_count(self) -> int:
        """İşlenen aktivasyon sayısını döndürür."""
        return self._stats["activations_handled"]

    @property
    def word_count(self) -> int:
        """Kayıtlı wake word sayısını döndürür."""
        return self._stats["words_registered"]

    def register_wake_word(
        self,
        word: str,
        language: str = "en",
        sensitivity: float = 0.7
    ) -> dict[str, Any]:
        """
        Yeni bir wake word kaydeder.

        Args:
            word: Uyandırma kelimesi
            language: Dil kodu
            sensitivity: Hassasiyet eşiği (0.0-1.0)

        Returns:
            Wake word kayıt sonucu
        """
        self._wake_words[word] = {
            "language": language,
            "sensitivity": sensitivity,
            "registered_at": time.time()
        }

        self._stats["words_registered"] += 1

        logger.info(
            f"Wake word kaydedildi: {word} ({language}, "
            f"sensitivity: {sensitivity})"
        )

        return {
            "word": word,
            "language": language,
            "sensitivity": sensitivity,
            "registered": True
        }

    def handle_detection(
        self,
        word: str,
        device_id: str = "",
        confidence: float = 0.0
    ) -> dict[str, Any]:
        """
        Wake word tespitini işler.

        Args:
            word: Tespit edilen kelime
            device_id: Cihaz kimliği
            confidence: Tespit güven skoru

        Returns:
            Tespit işleme sonucu
        """
        if word not in self._wake_words:
            logger.warning(f"Kayıtsız wake word: {word}")
            return {
                "word": word,
                "device_id": device_id,
                "confidence": confidence,
                "activated": False,
                "handled": True
            }

        word_config = self._wake_words[word]
        sensitivity = word_config["sensitivity"]
        activated = confidence >= sensitivity

        if activated:
            activation_entry = {
                "word": word,
                "device_id": device_id,
                "confidence": confidence,
                "timestamp": time.time()
            }
            self._activations.append(activation_entry)
            self._stats["activations_handled"] += 1

            logger.info(
                f"Wake word aktivasyonu: {word} (cihaz: {device_id}, "
                f"güven: {confidence:.2f})"
            )
        else:
            logger.debug(
                f"Wake word eşik altı: {word} (güven: {confidence:.2f} < "
                f"eşik: {sensitivity})"
            )

        return {
            "word": word,
            "device_id": device_id,
            "confidence": confidence,
            "activated": activated,
            "handled": True
        }

    def route_activation(
        self,
        device_id: str,
        command_text: str = ""
    ) -> dict[str, Any]:
        """
        Aktivasyonu uygun bileşene yönlendirir.

        Args:
            device_id: Cihaz kimliği
            command_text: Komut metni

        Returns:
            Yönlendirme sonucu
        """
        logger.debug(
            f"Aktivasyon yönlendiriliyor: {device_id} -> voice_parser"
        )

        return {
            "device_id": device_id,
            "command_text": command_text,
            "routed_to": "voice_parser",
            "routed": True
        }

    def set_privacy(
        self,
        device_id: str,
        always_listen: bool = False,
        store_audio: bool = False,
        retention_hours: int = 0
    ) -> dict[str, Any]:
        """
        Gizlilik ayarlarını yapılandırır.

        Args:
            device_id: Cihaz kimliği
            always_listen: Sürekli dinleme
            store_audio: Ses kayıt
            retention_hours: Saklama süresi (saat)

        Returns:
            Gizlilik ayarlama sonucu
        """
        self._privacy[device_id] = {
            "always_listen": always_listen,
            "store_audio": store_audio,
            "retention_hours": retention_hours,
            "updated_at": time.time()
        }

        logger.info(
            f"Gizlilik ayarları güncellendi: {device_id} "
            f"(listen: {always_listen}, store: {store_audio})"
        )

        return {
            "device_id": device_id,
            "always_listen": always_listen,
            "store_audio": store_audio,
            "privacy_set": True
        }

    def train_model(
        self,
        word: str,
        samples_count: int = 10
    ) -> dict[str, Any]:
        """
        Wake word modelini eğitir.

        Args:
            word: Eğitilecek kelime
            samples_count: Örnek sayısı

        Returns:
            Eğitim sonucu
        """
        # Basit simülasyon: 10+ örnek ile %92 doğruluk
        accuracy = 0.92 if samples_count >= 10 else 0.7

        logger.info(
            f"Model eğitildi: {word} ({samples_count} örnek, "
            f"doğruluk: {accuracy:.2f})"
        )

        return {
            "word": word,
            "samples_count": samples_count,
            "accuracy": accuracy,
            "trained": True
        }
