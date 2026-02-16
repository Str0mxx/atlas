"""ATLAS Tercih Takipçisi modülü.

Format tercihleri, detay seviyesi,
çıktı stili, zamanlama tercihleri,
kanal tercihleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TaskPreferenceTracker:
    """Tercih takipçisi.

    Kullanıcı tercihlerini takip eder ve öğrenir.

    Attributes:
        _preferences: Tercih kayıtları.
        _history: Tercih geçmişi.
    """

    DEFAULT_PREFERENCES = {
        "format": "markdown",
        "detail_level": "medium",
        "output_style": "structured",
        "language": "tr",
        "channel": "telegram",
        "timing": "immediate",
    }

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._preferences: dict[
            str, Any
        ] = dict(self.DEFAULT_PREFERENCES)
        self._history: list[
            dict[str, Any]
        ] = []
        self._category_prefs: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "preferences_set": 0,
            "preferences_applied": 0,
            "overrides": 0,
        }

        logger.info(
            "TaskPreferenceTracker "
            "baslatildi",
        )

    def set_preference(
        self,
        key: str,
        value: Any,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Tercih ayarlar.

        Args:
            key: Anahtar.
            value: Değer.
            category: Kategori.

        Returns:
            Ayar bilgisi.
        """
        old_value = None
        if category:
            if category not in (
                self._category_prefs
            ):
                self._category_prefs[
                    category
                ] = {}
            old_value = (
                self._category_prefs[
                    category
                ].get(key)
            )
            self._category_prefs[
                category
            ][key] = value
        else:
            old_value = self._preferences.get(
                key,
            )
            self._preferences[key] = value

        self._history.append({
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "category": category,
            "timestamp": time.time(),
        })
        self._stats["preferences_set"] += 1

        return {
            "key": key,
            "value": value,
            "category": category,
            "old_value": old_value,
            "set": True,
        }

    def get_preference(
        self,
        key: str,
        category: str | None = None,
    ) -> Any:
        """Tercihi getirir.

        Args:
            key: Anahtar.
            category: Kategori.

        Returns:
            Tercih değeri.
        """
        if category:
            cat_prefs = (
                self._category_prefs.get(
                    category, {},
                )
            )
            if key in cat_prefs:
                return cat_prefs[key]
        return self._preferences.get(key)

    def get_all_preferences(
        self,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Tüm tercihleri getirir.

        Args:
            category: Kategori.

        Returns:
            Tercih sözlüğü.
        """
        if category:
            base = dict(self._preferences)
            overrides = (
                self._category_prefs.get(
                    category, {},
                )
            )
            base.update(overrides)
            return base
        return dict(self._preferences)

    def apply_preferences(
        self,
        task_type: str,
    ) -> dict[str, Any]:
        """Tercihleri uygular.

        Args:
            task_type: Görev tipi.

        Returns:
            Uygulanan tercihler.
        """
        prefs = self.get_all_preferences(
            category=task_type,
        )
        self._stats[
            "preferences_applied"
        ] += 1

        return {
            "task_type": task_type,
            "preferences": prefs,
            "applied": True,
        }

    def learn_from_usage(
        self,
        key: str,
        value: Any,
        category: str = "",
    ) -> dict[str, Any]:
        """Kullanımdan öğrenir.

        Args:
            key: Anahtar.
            value: Gözlemlenen değer.
            category: Kategori.

        Returns:
            Öğrenme bilgisi.
        """
        # Mevcut değerle karşılaştır
        current = self.get_preference(
            key, category or None,
        )

        if current != value:
            self._stats["overrides"] += 1

        return {
            "key": key,
            "observed": value,
            "current": current,
            "differs": current != value,
            "learned": True,
        }

    def get_history(
        self,
        key: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Tercih geçmişini getirir.

        Args:
            key: Anahtar filtresi.
            limit: Maks kayıt.

        Returns:
            Geçmiş listesi.
        """
        results = self._history
        if key:
            results = [
                h for h in results
                if h["key"] == key
            ]
        return list(results[-limit:])

    @property
    def preference_count(self) -> int:
        """Tercih sayısı."""
        return len(self._preferences)

    @property
    def category_count(self) -> int:
        """Kategori sayısı."""
        return len(self._category_prefs)
