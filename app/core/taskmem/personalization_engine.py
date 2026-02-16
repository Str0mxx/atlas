"""ATLAS Kişiselleştirme Motoru modülü.

Kullanıcı modelleme, adaptif davranış,
tercih uygulama, bağlam adaptasyonu,
sürekli öğrenme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PersonalizationEngine:
    """Kişiselleştirme motoru.

    Kullanıcı profilini modeller ve kişiselleştirir.

    Attributes:
        _profile: Kullanıcı profili.
        _adaptations: Adaptasyon kayıtları.
    """

    def __init__(
        self,
        level: str = "moderate",
    ) -> None:
        """Motoru başlatır.

        Args:
            level: Kişiselleştirme seviyesi.
        """
        self._profile: dict[str, Any] = {
            "expertise": "intermediate",
            "communication_style": (
                "professional"
            ),
            "detail_preference": "medium",
            "proactivity": "moderate",
            "interests": [],
            "skills": [],
        }
        self._adaptations: list[
            dict[str, Any]
        ] = []
        self._learning_log: list[
            dict[str, Any]
        ] = []
        self._level = level
        self._counter = 0
        self._stats = {
            "adaptations_made": 0,
            "preferences_applied": 0,
            "learnings": 0,
        }

        logger.info(
            "PersonalizationEngine "
            "baslatildi",
        )

    def update_profile(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Profili günceller.

        Args:
            **kwargs: Profil alanları.

        Returns:
            Güncelleme bilgisi.
        """
        updated = []
        for key, value in kwargs.items():
            if key in self._profile:
                self._profile[key] = value
                updated.append(key)

        return {
            "updated_fields": updated,
            "count": len(updated),
            "updated": len(updated) > 0,
        }

    def get_profile(self) -> dict[str, Any]:
        """Profili getirir.

        Returns:
            Profil bilgisi.
        """
        return dict(self._profile)

    def adapt_response(
        self,
        content: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Yanıtı adapte eder.

        Args:
            content: İçerik.
            context: Bağlam.

        Returns:
            Adaptasyon bilgisi.
        """
        self._counter += 1
        aid = f"adp_{self._counter}"

        adapted = content
        adaptations = []

        # Detay seviyesi
        detail = self._profile.get(
            "detail_preference", "medium",
        )
        if detail == "brief":
            # Kısa tut
            lines = adapted.split("\n")
            if len(lines) > 5:
                adapted = "\n".join(
                    lines[:5],
                )
                adaptations.append(
                    "brevity",
                )
        elif detail == "detailed":
            adaptations.append(
                "keep_detailed",
            )

        # İletişim stili
        style = self._profile.get(
            "communication_style",
            "professional",
        )
        if style == "casual":
            adapted = adapted.replace(
                "Dear", "Hi",
            )
            adaptations.append(
                "casual_tone",
            )

        record = {
            "adaptation_id": aid,
            "context": context,
            "adaptations": adaptations,
            "timestamp": time.time(),
        }
        self._adaptations.append(record)
        self._stats[
            "adaptations_made"
        ] += 1

        return {
            "adaptation_id": aid,
            "original_length": len(content),
            "adapted_length": len(adapted),
            "adapted_content": adapted,
            "adaptations": adaptations,
            "adapted": True,
        }

    def apply_preferences(
        self,
        task_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Tercihleri uygular.

        Args:
            task_config: Görev ayarları.

        Returns:
            Uygulama bilgisi.
        """
        applied = dict(task_config)

        # Profil bazlı ayarlar
        if "detail_level" not in applied:
            applied["detail_level"] = (
                self._profile.get(
                    "detail_preference",
                    "medium",
                )
            )
        if "style" not in applied:
            applied["style"] = (
                self._profile.get(
                    "communication_style",
                    "professional",
                )
            )

        self._stats[
            "preferences_applied"
        ] += 1

        return {
            "config": applied,
            "personalized": True,
        }

    def adapt_to_context(
        self,
        context: str,
        urgency: str = "normal",
    ) -> dict[str, Any]:
        """Bağlama adapte olur.

        Args:
            context: Bağlam.
            urgency: Aciliyet.

        Returns:
            Adaptasyon bilgisi.
        """
        recommendations = {}

        if urgency == "high":
            recommendations["detail"] = (
                "brief"
            )
            recommendations["format"] = (
                "bullet_points"
            )
        elif urgency == "low":
            recommendations["detail"] = (
                self._profile.get(
                    "detail_preference",
                    "medium",
                )
            )
            recommendations["format"] = (
                "structured"
            )
        else:
            recommendations["detail"] = (
                "medium"
            )
            recommendations["format"] = (
                "standard"
            )

        # Proaktiflik seviyesi
        proactivity = self._profile.get(
            "proactivity", "moderate",
        )
        recommendations[
            "include_suggestions"
        ] = proactivity in (
            "moderate", "high",
        )

        return {
            "context": context,
            "urgency": urgency,
            "recommendations": (
                recommendations
            ),
            "adapted": True,
        }

    def learn(
        self,
        observation: str,
        category: str = "behavior",
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Gözlemden öğrenir.

        Args:
            observation: Gözlem.
            category: Kategori.
            confidence: Güven.

        Returns:
            Öğrenme bilgisi.
        """
        self._counter += 1
        lid = f"lrn_{self._counter}"

        entry = {
            "learning_id": lid,
            "observation": observation,
            "category": category,
            "confidence": confidence,
            "timestamp": time.time(),
        }
        self._learning_log.append(entry)
        self._stats["learnings"] += 1

        return {
            "learning_id": lid,
            "observation": observation,
            "category": category,
            "learned": True,
        }

    def get_learning_summary(
        self,
    ) -> dict[str, Any]:
        """Öğrenme özetini döndürür."""
        by_category: dict[str, int] = {}
        for entry in self._learning_log:
            cat = entry["category"]
            by_category[cat] = (
                by_category.get(cat, 0) + 1
            )

        return {
            "total_learnings": len(
                self._learning_log,
            ),
            "by_category": by_category,
            "adaptations_made": (
                self._stats[
                    "adaptations_made"
                ]
            ),
        }

    @property
    def adaptation_count(self) -> int:
        """Adaptasyon sayısı."""
        return self._stats[
            "adaptations_made"
        ]

    @property
    def learning_count(self) -> int:
        """Öğrenme sayısı."""
        return self._stats["learnings"]
