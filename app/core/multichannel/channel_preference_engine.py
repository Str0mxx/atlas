"""ATLAS Kanal Tercih Motoru modülü.

Tercih öğrenme, zaman bazlı yönlendirme,
içerik bazlı yönlendirme, aciliyet bazlı,
kullanıcı override.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ChannelPreferenceEngine:
    """Kanal tercih motoru.

    Kullanıcı kanal tercihlerini öğrenir.

    Attributes:
        _preferences: Tercih kayıtları.
        _usage_history: Kullanım geçmişi.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._preferences: dict[
            str, dict[str, Any]
        ] = {}
        self._usage_history: list[
            dict[str, Any]
        ] = []
        self._time_rules: list[
            dict[str, Any]
        ] = []
        self._content_rules: list[
            dict[str, Any]
        ] = []
        self._urgency_map: dict[str, str] = {
            "critical": "voice",
            "high": "telegram",
            "medium": "telegram",
            "low": "email",
            "routine": "email",
        }
        self._overrides: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "preferences_learned": 0,
            "recommendations": 0,
        }

        logger.info(
            "ChannelPreferenceEngine "
            "baslatildi",
        )

    def learn_preference(
        self,
        user_id: str,
        channel: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Tercih öğrenir.

        Args:
            user_id: Kullanıcı ID.
            channel: Kullanılan kanal.
            context: Kullanım bağlamı.

        Returns:
            Öğrenme bilgisi.
        """
        if user_id not in self._preferences:
            self._preferences[user_id] = {
                "channel_scores": {},
            }

        scores = self._preferences[user_id][
            "channel_scores"
        ]
        scores[channel] = scores.get(
            channel, 0,
        ) + 1

        self._usage_history.append({
            "user_id": user_id,
            "channel": channel,
            "context": context or {},
            "timestamp": time.time(),
        })
        self._stats["preferences_learned"] += 1

        return {
            "user_id": user_id,
            "channel": channel,
            "learned": True,
        }

    def recommend_channel(
        self,
        user_id: str,
        urgency: str = "medium",
        content_type: str = "text",
        hour: int | None = None,
    ) -> dict[str, Any]:
        """Kanal önerir.

        Args:
            user_id: Kullanıcı ID.
            urgency: Aciliyet.
            content_type: İçerik tipi.
            hour: Saat.

        Returns:
            Öneri bilgisi.
        """
        # Override kontrolü
        override = self._overrides.get(user_id)
        if override and override.get("active"):
            self._stats["recommendations"] += 1
            return {
                "user_id": user_id,
                "recommended": override[
                    "channel"
                ],
                "reason": "user_override",
            }

        # Zaman bazlı
        time_channel = self._check_time_rules(
            hour,
        )
        if time_channel:
            self._stats["recommendations"] += 1
            return {
                "user_id": user_id,
                "recommended": time_channel,
                "reason": "time_based",
            }

        # İçerik bazlı
        content_channel = (
            self._check_content_rules(
                content_type,
            )
        )
        if content_channel:
            self._stats["recommendations"] += 1
            return {
                "user_id": user_id,
                "recommended": content_channel,
                "reason": "content_based",
            }

        # Aciliyet bazlı
        urgency_channel = self._urgency_map.get(
            urgency, "telegram",
        )

        # Kullanıcı tercihi
        user_pref = self._get_top_preference(
            user_id,
        )
        if user_pref:
            # Düşük aciliyetlerde tercihe uy
            if urgency in ("low", "routine"):
                urgency_channel = user_pref

        self._stats["recommendations"] += 1

        return {
            "user_id": user_id,
            "recommended": urgency_channel,
            "reason": "urgency_and_preference",
        }

    def _get_top_preference(
        self,
        user_id: str,
    ) -> str | None:
        """En çok tercih edilen kanalı getirir."""
        prefs = self._preferences.get(user_id)
        if not prefs:
            return None

        scores = prefs.get("channel_scores", {})
        if not scores:
            return None

        return max(scores, key=scores.get)

    def add_time_rule(
        self,
        start_hour: int,
        end_hour: int,
        channel: str,
    ) -> dict[str, Any]:
        """Zaman kuralı ekler.

        Args:
            start_hour: Başlangıç saati.
            end_hour: Bitiş saati.
            channel: Kanal.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "start_hour": start_hour,
            "end_hour": end_hour,
            "channel": channel,
        }
        self._time_rules.append(rule)
        return {"rule_added": True, **rule}

    def _check_time_rules(
        self,
        hour: int | None,
    ) -> str | None:
        """Zaman kurallarını kontrol eder."""
        if hour is None:
            return None

        for rule in self._time_rules:
            start = rule["start_hour"]
            end = rule["end_hour"]
            if start <= end:
                if start <= hour < end:
                    return rule["channel"]
            else:
                if hour >= start or hour < end:
                    return rule["channel"]
        return None

    def add_content_rule(
        self,
        content_type: str,
        channel: str,
    ) -> dict[str, Any]:
        """İçerik kuralı ekler.

        Args:
            content_type: İçerik tipi.
            channel: Kanal.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "content_type": content_type,
            "channel": channel,
        }
        self._content_rules.append(rule)
        return {"rule_added": True, **rule}

    def _check_content_rules(
        self,
        content_type: str,
    ) -> str | None:
        """İçerik kurallarını kontrol eder."""
        for rule in self._content_rules:
            if (
                rule["content_type"]
                == content_type
            ):
                return rule["channel"]
        return None

    def set_urgency_channel(
        self,
        urgency: str,
        channel: str,
    ) -> dict[str, Any]:
        """Aciliyet-kanal eşlemesi ayarlar.

        Args:
            urgency: Aciliyet.
            channel: Kanal.

        Returns:
            Ayar bilgisi.
        """
        self._urgency_map[urgency] = channel
        return {
            "urgency": urgency,
            "channel": channel,
        }

    def set_override(
        self,
        user_id: str,
        channel: str,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Kullanıcı override ayarlar.

        Args:
            user_id: Kullanıcı ID.
            channel: Kanal.
            duration_minutes: Süre (dakika).

        Returns:
            Override bilgisi.
        """
        self._overrides[user_id] = {
            "channel": channel,
            "active": True,
            "expires_at": (
                time.time()
                + duration_minutes * 60
            ),
        }
        return {
            "user_id": user_id,
            "channel": channel,
            "override_set": True,
        }

    def clear_override(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Override temizler.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Temizleme bilgisi.
        """
        if user_id in self._overrides:
            self._overrides[user_id][
                "active"
            ] = False
        return {
            "user_id": user_id,
            "override_cleared": True,
        }

    def get_user_preferences(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Kullanıcı tercihlerini getirir.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Tercih bilgisi.
        """
        prefs = self._preferences.get(
            user_id, {},
        )
        return {
            "user_id": user_id,
            "preferences": prefs,
        }

    @property
    def preference_count(self) -> int:
        """Tercih sayısı."""
        return self._stats[
            "preferences_learned"
        ]

    @property
    def recommendation_count(self) -> int:
        """Öneri sayısı."""
        return self._stats["recommendations"]
