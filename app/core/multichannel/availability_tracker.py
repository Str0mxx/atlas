"""ATLAS Müsaitlik Takipçisi modülü.

Kullanıcı varlığı, kanal durumu,
yanıt süresi takibi, tercih edilen kanallar,
müsaitlik kalıpları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AvailabilityTracker:
    """Müsaitlik takipçisi.

    Kullanıcı ve kanal müsaitliğini takip eder.

    Attributes:
        _presences: Kullanıcı varlık durumları.
        _channel_status: Kanal durumları.
        _response_times: Yanıt süreleri.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._presences: dict[
            str, dict[str, Any]
        ] = {}
        self._channel_status: dict[
            str, dict[str, Any]
        ] = {}
        self._response_times: list[
            dict[str, Any]
        ] = []
        self._preferred_channels: dict[
            str, list[str]
        ] = {}
        self._patterns: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "presence_updates": 0,
            "response_times_recorded": 0,
        }

        logger.info(
            "AvailabilityTracker baslatildi",
        )

    def set_presence(
        self,
        user_id: str,
        status: str = "online",
        channel: str | None = None,
    ) -> dict[str, Any]:
        """Varlık durumu ayarlar.

        Args:
            user_id: Kullanıcı ID.
            status: Durum.
            channel: Kanal.

        Returns:
            Ayar bilgisi.
        """
        self._presences[user_id] = {
            "status": status,
            "channel": channel,
            "updated_at": time.time(),
        }
        self._stats["presence_updates"] += 1

        # Kalıp kaydet
        if user_id not in self._patterns:
            self._patterns[user_id] = []
        self._patterns[user_id].append({
            "status": status,
            "channel": channel,
            "hour": int(time.time() / 3600) % 24,
            "timestamp": time.time(),
        })

        return {
            "user_id": user_id,
            "status": status,
            "channel": channel,
        }

    def get_presence(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Varlık durumu getirir.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Varlık bilgisi.
        """
        presence = self._presences.get(user_id)
        if not presence:
            return {
                "user_id": user_id,
                "status": "unknown",
            }
        return {
            "user_id": user_id,
            **presence,
        }

    def set_channel_status(
        self,
        channel: str,
        online: bool = True,
        latency_ms: float = 0.0,
    ) -> dict[str, Any]:
        """Kanal durumu ayarlar.

        Args:
            channel: Kanal.
            online: Çevrimiçi mi.
            latency_ms: Gecikme (ms).

        Returns:
            Ayar bilgisi.
        """
        self._channel_status[channel] = {
            "online": online,
            "latency_ms": latency_ms,
            "updated_at": time.time(),
        }
        return {
            "channel": channel,
            "online": online,
            "latency_ms": latency_ms,
        }

    def get_channel_status(
        self,
        channel: str,
    ) -> dict[str, Any]:
        """Kanal durumu getirir.

        Args:
            channel: Kanal.

        Returns:
            Durum bilgisi.
        """
        status = self._channel_status.get(
            channel,
        )
        if not status:
            return {
                "channel": channel,
                "online": False,
            }
        return {"channel": channel, **status}

    def record_response_time(
        self,
        user_id: str,
        channel: str,
        response_ms: float,
    ) -> dict[str, Any]:
        """Yanıt süresi kaydeder.

        Args:
            user_id: Kullanıcı ID.
            channel: Kanal.
            response_ms: Yanıt süresi (ms).

        Returns:
            Kayıt bilgisi.
        """
        record = {
            "user_id": user_id,
            "channel": channel,
            "response_ms": response_ms,
            "timestamp": time.time(),
        }
        self._response_times.append(record)
        self._stats[
            "response_times_recorded"
        ] += 1

        return record

    def get_avg_response_time(
        self,
        user_id: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """Ortalama yanıt süresini getirir.

        Args:
            user_id: Kullanıcı filtresi.
            channel: Kanal filtresi.

        Returns:
            Ortalama bilgisi.
        """
        filtered = self._response_times
        if user_id:
            filtered = [
                r for r in filtered
                if r["user_id"] == user_id
            ]
        if channel:
            filtered = [
                r for r in filtered
                if r["channel"] == channel
            ]

        if not filtered:
            return {"avg_response_ms": 0.0, "count": 0}

        avg = sum(
            r["response_ms"] for r in filtered
        ) / len(filtered)

        return {
            "avg_response_ms": round(avg, 2),
            "count": len(filtered),
        }

    def set_preferred_channels(
        self,
        user_id: str,
        channels: list[str],
    ) -> dict[str, Any]:
        """Tercih edilen kanalları ayarlar.

        Args:
            user_id: Kullanıcı ID.
            channels: Kanal listesi.

        Returns:
            Ayar bilgisi.
        """
        self._preferred_channels[user_id] = (
            channels
        )
        return {
            "user_id": user_id,
            "preferred_channels": channels,
        }

    def get_preferred_channel(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Tercih edilen kanalı getirir.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Tercih bilgisi.
        """
        prefs = self._preferred_channels.get(
            user_id, [],
        )
        best = prefs[0] if prefs else "telegram"
        return {
            "user_id": user_id,
            "preferred": best,
            "all_preferences": prefs,
        }

    def analyze_patterns(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Müsaitlik kalıplarını analiz eder.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Kalıp bilgisi.
        """
        patterns = self._patterns.get(
            user_id, [],
        )
        if not patterns:
            return {
                "user_id": user_id,
                "patterns": [],
            }

        hour_counts: dict[int, int] = {}
        channel_counts: dict[str, int] = {}

        for p in patterns:
            if p["status"] == "online":
                h = p.get("hour", 0)
                hour_counts[h] = (
                    hour_counts.get(h, 0) + 1
                )
            ch = p.get("channel")
            if ch:
                channel_counts[ch] = (
                    channel_counts.get(ch, 0) + 1
                )

        peak_hours = sorted(
            hour_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        return {
            "user_id": user_id,
            "peak_hours": [
                h for h, _ in peak_hours
            ],
            "channel_usage": channel_counts,
            "total_records": len(patterns),
        }

    @property
    def tracked_user_count(self) -> int:
        """Takip edilen kullanıcı sayısı."""
        return len(self._presences)

    @property
    def online_user_count(self) -> int:
        """Çevrimiçi kullanıcı sayısı."""
        return sum(
            1 for p in self._presences.values()
            if p["status"] == "online"
        )
