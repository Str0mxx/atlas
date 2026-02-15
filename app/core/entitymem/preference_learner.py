"""ATLAS Varlık Tercih Öğrenici modulu.

Tercih öğrenme, iletişim stili,
zamanlama tercihleri, ilgi alanları, davranış kalıpları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EntityPreferenceLearner:
    """Varlık tercih öğrenici.

    Varlıkların tercihlerini öğrenir.

    Attributes:
        _preferences: Tercih verileri.
        _behaviors: Davranış kayıtları.
    """

    def __init__(self) -> None:
        """Öğreniciyi başlatır."""
        self._preferences: dict[
            str, dict[str, Any]
        ] = {}
        self._behaviors: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "preferences_learned": 0,
            "behaviors_recorded": 0,
        }

        logger.info(
            "EntityPreferenceLearner "
            "baslatildi",
        )

    def learn_preference(
        self,
        entity_id: str,
        category: str,
        key: str,
        value: Any,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Tercih öğrenir.

        Args:
            entity_id: Varlık ID.
            category: Kategori.
            key: Tercih anahtarı.
            value: Tercih değeri.
            confidence: Güven puanı.

        Returns:
            Öğrenme bilgisi.
        """
        if entity_id not in self._preferences:
            self._preferences[entity_id] = {}

        prefs = self._preferences[entity_id]
        if category not in prefs:
            prefs[category] = {}

        prefs[category][key] = {
            "value": value,
            "confidence": max(
                0.0, min(1.0, confidence),
            ),
            "observations": 1,
            "learned_at": time.time(),
        }

        self._stats["preferences_learned"] += 1

        return {
            "entity_id": entity_id,
            "category": category,
            "key": key,
            "learned": True,
            "confidence": confidence,
        }

    def reinforce_preference(
        self,
        entity_id: str,
        category: str,
        key: str,
    ) -> dict[str, Any]:
        """Tercihi pekiştirir.

        Args:
            entity_id: Varlık ID.
            category: Kategori.
            key: Tercih anahtarı.

        Returns:
            Pekiştirme bilgisi.
        """
        prefs = self._preferences.get(
            entity_id, {},
        )
        cat = prefs.get(category, {})
        pref = cat.get(key)

        if not pref:
            return {
                "error": "preference_not_found",
            }

        pref["observations"] += 1
        # Güven artır (azalan getiri)
        old_conf = pref["confidence"]
        boost = 0.1 / max(
            pref["observations"], 1,
        )
        pref["confidence"] = min(
            1.0, old_conf + boost,
        )

        return {
            "entity_id": entity_id,
            "category": category,
            "key": key,
            "observations": pref["observations"],
            "confidence": round(
                pref["confidence"], 3,
            ),
            "reinforced": True,
        }

    def get_communication_style(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """İletişim stilini getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Stil bilgisi.
        """
        prefs = self._preferences.get(
            entity_id, {},
        )
        comm = prefs.get("communication", {})

        return {
            "entity_id": entity_id,
            "formality": comm.get(
                "formality", {},
            ).get("value", "neutral"),
            "preferred_channel": comm.get(
                "channel", {},
            ).get("value", "any"),
            "response_length": comm.get(
                "length", {},
            ).get("value", "medium"),
            "language": comm.get(
                "language", {},
            ).get("value", "tr"),
        }

    def get_timing_preferences(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Zamanlama tercihlerini getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Zamanlama bilgisi.
        """
        prefs = self._preferences.get(
            entity_id, {},
        )
        timing = prefs.get("timing", {})

        return {
            "entity_id": entity_id,
            "preferred_hours": timing.get(
                "hours", {},
            ).get("value", "business"),
            "preferred_days": timing.get(
                "days", {},
            ).get("value", "weekdays"),
            "timezone": timing.get(
                "timezone", {},
            ).get("value", "UTC+3"),
            "response_speed": timing.get(
                "speed", {},
            ).get("value", "normal"),
        }

    def get_topic_interests(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """İlgi alanlarını getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            İlgi bilgisi.
        """
        prefs = self._preferences.get(
            entity_id, {},
        )
        topics = prefs.get("topics", {})

        interests = []
        for key, data in topics.items():
            interests.append({
                "topic": key,
                "interest_level": data.get(
                    "value", "medium",
                ),
                "confidence": data.get(
                    "confidence", 0.5,
                ),
            })

        interests.sort(
            key=lambda x: x["confidence"],
            reverse=True,
        )

        return {
            "entity_id": entity_id,
            "interests": interests,
            "interest_count": len(interests),
        }

    def record_behavior(
        self,
        entity_id: str,
        behavior_type: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Davranış kaydeder.

        Args:
            entity_id: Varlık ID.
            behavior_type: Davranış tipi.
            details: Detaylar.

        Returns:
            Kayıt bilgisi.
        """
        if entity_id not in self._behaviors:
            self._behaviors[entity_id] = []

        record = {
            "behavior_type": behavior_type,
            "details": details or {},
            "timestamp": time.time(),
        }
        self._behaviors[entity_id].append(
            record,
        )
        self._stats["behaviors_recorded"] += 1

        return {
            "entity_id": entity_id,
            "behavior_type": behavior_type,
            "recorded": True,
        }

    def get_behavior_patterns(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Davranış kalıplarını getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Kalıp bilgisi.
        """
        behaviors = self._behaviors.get(
            entity_id, [],
        )
        if not behaviors:
            return {
                "entity_id": entity_id,
                "patterns": [],
                "behavior_count": 0,
            }

        # Tip frekansı
        freq: dict[str, int] = {}
        for b in behaviors:
            t = b["behavior_type"]
            freq[t] = freq.get(t, 0) + 1

        patterns = [
            {
                "behavior_type": t,
                "frequency": c,
                "is_habitual": c >= 3,
            }
            for t, c in sorted(
                freq.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]

        return {
            "entity_id": entity_id,
            "patterns": patterns,
            "behavior_count": len(behaviors),
        }

    def get_all_preferences(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Tüm tercihleri getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Tercih bilgisi.
        """
        prefs = self._preferences.get(
            entity_id, {},
        )
        return {
            "entity_id": entity_id,
            "categories": list(prefs.keys()),
            "preferences": {
                cat: {
                    k: v.get("value")
                    for k, v in items.items()
                }
                for cat, items in prefs.items()
            },
        }

    @property
    def preference_count(self) -> int:
        """Tercih sayısı."""
        return self._stats[
            "preferences_learned"
        ]

    @property
    def behavior_count(self) -> int:
        """Davranış sayısı."""
        return self._stats[
            "behaviors_recorded"
        ]
