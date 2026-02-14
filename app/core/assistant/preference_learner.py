"""ATLAS Tercih Ogrenici modulu.

Etkilesimlerden ogrenme, stil tercihleri,
iletisim tercihleri, arac tercihleri
ve zaman tercihleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import PreferenceType, UserPreference

logger = logging.getLogger(__name__)


class PreferenceLearner:
    """Tercih ogrenici.

    Kullanici etkilesimlerinden tercihler
    ogrenip deneyimi kisisellestirir.

    Attributes:
        _preferences: Ogrenilen tercihler.
        _interactions: Etkilesim gecmisi.
        _observation_buffer: Gozlem tamponu.
        _confidence_threshold: Guven esigi.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
    ) -> None:
        """Tercih ogrenicisini baslatir.

        Args:
            confidence_threshold: Guven esigi.
        """
        self._preferences: dict[str, UserPreference] = {}
        self._interactions: list[dict[str, Any]] = []
        self._observation_buffer: list[dict[str, Any]] = []
        self._confidence_threshold = max(0.0, min(1.0, confidence_threshold))

        logger.info(
            "PreferenceLearner baslatildi (threshold=%.2f)",
            self._confidence_threshold,
        )

    def observe_interaction(
        self,
        interaction_type: str,
        data: dict[str, Any],
    ) -> None:
        """Etkilesimi gozlemler.

        Args:
            interaction_type: Etkilesim turu.
            data: Etkilesim verisi.
        """
        observation = {
            "type": interaction_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._interactions.append(observation)
        self._observation_buffer.append(observation)

    def learn_from_feedback(
        self,
        preference_key: str,
        preference_type: PreferenceType,
        value: Any,
        is_positive: bool = True,
    ) -> UserPreference:
        """Geri bildirimden ogrenilir.

        Args:
            preference_key: Tercih anahtari.
            preference_type: Tercih turu.
            value: Deger.
            is_positive: Pozitif geri bildirim mi.

        Returns:
            UserPreference nesnesi.
        """
        existing = self._preferences.get(preference_key)

        if existing:
            # Mevcut tercihi guncelle
            existing.learned_from += 1
            if is_positive:
                existing.confidence = min(
                    1.0,
                    existing.confidence + 0.1,
                )
                existing.value = value
            else:
                existing.confidence = max(
                    0.0,
                    existing.confidence - 0.15,
                )
            return existing

        # Yeni tercih
        pref = UserPreference(
            preference_type=preference_type,
            key=preference_key,
            value=value,
            confidence=0.5 if is_positive else 0.2,
            learned_from=1,
        )
        self._preferences[preference_key] = pref

        logger.info(
            "Tercih oğrenildi: %s = %s (tip=%s)",
            preference_key, value, preference_type.value,
        )
        return pref

    def learn_style_preference(
        self,
        style_key: str,
        style_value: str,
    ) -> UserPreference:
        """Stil tercihi ogrenilir.

        Args:
            style_key: Stil anahtari.
            style_value: Stil degeri.

        Returns:
            UserPreference nesnesi.
        """
        return self.learn_from_feedback(
            f"style_{style_key}",
            PreferenceType.STYLE,
            style_value,
        )

    def learn_communication_preference(
        self,
        comm_key: str,
        comm_value: Any,
    ) -> UserPreference:
        """Iletisim tercihi ogrenilir.

        Args:
            comm_key: Iletisim anahtari.
            comm_value: Iletisim degeri.

        Returns:
            UserPreference nesnesi.
        """
        return self.learn_from_feedback(
            f"comm_{comm_key}",
            PreferenceType.COMMUNICATION,
            comm_value,
        )

    def learn_tool_preference(
        self,
        tool_name: str,
        is_preferred: bool = True,
    ) -> UserPreference:
        """Arac tercihi ogrenilir.

        Args:
            tool_name: Arac adi.
            is_preferred: Tercih ediliyor mu.

        Returns:
            UserPreference nesnesi.
        """
        return self.learn_from_feedback(
            f"tool_{tool_name}",
            PreferenceType.TOOL,
            tool_name,
            is_positive=is_preferred,
        )

    def learn_time_preference(
        self,
        time_key: str,
        time_value: Any,
    ) -> UserPreference:
        """Zaman tercihi ogrenilir.

        Args:
            time_key: Zaman anahtari.
            time_value: Zaman degeri.

        Returns:
            UserPreference nesnesi.
        """
        return self.learn_from_feedback(
            f"time_{time_key}",
            PreferenceType.TIME,
            time_value,
        )

    def get_preference(
        self,
        key: str,
    ) -> UserPreference | None:
        """Tercihi getirir.

        Args:
            key: Tercih anahtari.

        Returns:
            UserPreference veya None.
        """
        return self._preferences.get(key)

    def get_preferences_by_type(
        self,
        preference_type: PreferenceType,
    ) -> list[UserPreference]:
        """Ture gore tercihleri getirir.

        Args:
            preference_type: Tercih turu.

        Returns:
            Tercih listesi.
        """
        return [
            p for p in self._preferences.values()
            if p.preference_type == preference_type
        ]

    def get_confident_preferences(self) -> list[UserPreference]:
        """Guvenilir tercihleri getirir.

        Returns:
            Guven esigi uzerindeki tercihler.
        """
        return [
            p for p in self._preferences.values()
            if p.confidence >= self._confidence_threshold
        ]

    def get_preference_summary(self) -> dict[str, Any]:
        """Tercih ozetini getirir.

        Returns:
            Ozet sozlugu.
        """
        by_type: dict[str, int] = {}
        for p in self._preferences.values():
            t = p.preference_type.value
            by_type[t] = by_type.get(t, 0) + 1

        confident = self.get_confident_preferences()
        avg_confidence = 0.0
        if self._preferences:
            avg_confidence = sum(
                p.confidence for p in self._preferences.values()
            ) / len(self._preferences)

        return {
            "total": len(self._preferences),
            "by_type": by_type,
            "confident_count": len(confident),
            "avg_confidence": round(avg_confidence, 3),
            "interactions_observed": len(self._interactions),
        }

    def apply_preferences(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Tercihleri baglama uygular.

        Args:
            context: Mevcut baglam.

        Returns:
            Zenginlestirilmis baglam.
        """
        enriched = dict(context)
        enriched["preferences"] = {}

        for key, pref in self._preferences.items():
            if pref.confidence >= self._confidence_threshold:
                enriched["preferences"][key] = {
                    "value": pref.value,
                    "confidence": pref.confidence,
                    "type": pref.preference_type.value,
                }

        return enriched

    def decay_preferences(
        self,
        decay_rate: float = 0.05,
    ) -> int:
        """Tercihleri zamanla zayiflatir.

        Args:
            decay_rate: Zayiflama orani.

        Returns:
            Zayiflanan tercih sayisi.
        """
        decayed_count = 0
        to_remove: list[str] = []

        for key, pref in self._preferences.items():
            pref.confidence = max(0.0, pref.confidence - decay_rate)
            decayed_count += 1
            if pref.confidence <= 0.05:
                to_remove.append(key)

        for key in to_remove:
            del self._preferences[key]

        return decayed_count

    def reset_preference(self, key: str) -> bool:
        """Tercihi sifirlar.

        Args:
            key: Tercih anahtari.

        Returns:
            Basarili ise True.
        """
        if key in self._preferences:
            del self._preferences[key]
            return True
        return False

    @property
    def preference_count(self) -> int:
        """Tercih sayisi."""
        return len(self._preferences)

    @property
    def interaction_count(self) -> int:
        """Etkilesim sayisi."""
        return len(self._interactions)

    @property
    def confident_count(self) -> int:
        """Guvenilir tercih sayisi."""
        return len(self.get_confident_preferences())
