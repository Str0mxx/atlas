"""ATLAS Platform Adaptörü modülü.

Format adaptasyonu, uzunluk optimizasyonu,
özellik kullanımı, en iyi uygulamalar,
önizleme üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PlatformAdapter:
    """Platform adaptörü.

    İçerikleri platformlara uyarlar.

    Attributes:
        _specs: Platform spesifikasyonları.
    """

    def __init__(self) -> None:
        """Adaptörü başlatır."""
        self._specs: dict[
            str, dict[str, Any]
        ] = {
            "google_ads": {
                "headline_max": 30,
                "description_max": 90,
                "cta_required": True,
            },
            "facebook": {
                "headline_max": 40,
                "description_max": 125,
                "image_required": True,
            },
            "instagram": {
                "caption_max": 2200,
                "hashtag_max": 30,
                "image_required": True,
            },
            "twitter": {
                "text_max": 280,
                "hashtag_max": 5,
            },
            "linkedin": {
                "headline_max": 70,
                "text_max": 3000,
            },
            "tiktok": {
                "caption_max": 150,
                "hashtag_max": 5,
            },
        }
        self._stats = {
            "adaptations_done": 0,
            "previews_generated": 0,
        }

        logger.info(
            "PlatformAdapter baslatildi",
        )

    def adapt_format(
        self,
        text: str,
        platform: str,
        content_type: str = "ad_copy",
    ) -> dict[str, Any]:
        """Format adapte eder.

        Args:
            text: Metin.
            platform: Platform.
            content_type: İçerik tipi.

        Returns:
            Adaptasyon bilgisi.
        """
        spec = self._specs.get(
            platform, {},
        )

        max_len = spec.get(
            "description_max",
            spec.get(
                "text_max",
                spec.get(
                    "caption_max", 500,
                ),
            ),
        )

        adapted = text
        truncated = False
        if len(text) > max_len:
            adapted = (
                text[:max_len - 3] + "..."
            )
            truncated = True

        self._stats[
            "adaptations_done"
        ] += 1

        return {
            "platform": platform,
            "original_length": len(text),
            "adapted_length": len(adapted),
            "adapted": adapted,
            "truncated": truncated,
            "max_allowed": max_len,
            "within_limit": (
                len(adapted) <= max_len
            ),
        }

    def optimize_length(
        self,
        text: str,
        platform: str,
    ) -> dict[str, Any]:
        """Uzunluk optimize eder.

        Args:
            text: Metin.
            platform: Platform.

        Returns:
            Optimizasyon bilgisi.
        """
        spec = self._specs.get(
            platform, {},
        )
        max_len = spec.get(
            "text_max",
            spec.get(
                "description_max",
                spec.get(
                    "caption_max", 500,
                ),
            ),
        )

        current = len(text)
        suggestions = []

        if current > max_len:
            excess = current - max_len
            suggestions.append(
                f"Remove {excess} characters",
            )
            suggestions.append(
                "Shorten sentences",
            )
        elif current < max_len * 0.5:
            suggestions.append(
                "Content is too short",
            )
            suggestions.append(
                "Add more detail",
            )

        ratio = round(
            current / max(max_len, 1) * 100,
            1,
        )

        return {
            "platform": platform,
            "current_length": current,
            "max_length": max_len,
            "usage_pct": ratio,
            "optimal": (
                50 <= ratio <= 100
            ),
            "suggestions": suggestions,
        }

    def get_features(
        self,
        platform: str,
    ) -> dict[str, Any]:
        """Platform özelliklerini döndürür.

        Args:
            platform: Platform.

        Returns:
            Özellik bilgisi.
        """
        spec = self._specs.get(
            platform, {},
        )

        features = []
        if spec.get("cta_required"):
            features.append(
                "CTA button available",
            )
        if spec.get("image_required"):
            features.append(
                "Image/visual required",
            )
        if spec.get("hashtag_max"):
            features.append(
                f"Up to {spec['hashtag_max']} "
                f"hashtags",
            )

        return {
            "platform": platform,
            "spec": spec,
            "features": features,
            "feature_count": len(features),
            "supported": bool(spec),
        }

    def get_best_practices(
        self,
        platform: str,
    ) -> dict[str, Any]:
        """En iyi uygulamaları döndürür.

        Args:
            platform: Platform.

        Returns:
            Uygulama bilgisi.
        """
        practices = {
            "google_ads": [
                "Include keywords in headline",
                "Add clear CTA",
                "Use all character limits",
                "Test multiple variations",
            ],
            "facebook": [
                "Use eye-catching image",
                "Keep text concise",
                "Include social proof",
                "Target specific audience",
            ],
            "instagram": [
                "Use high-quality visuals",
                "Include relevant hashtags",
                "Write engaging caption",
                "Use stories and reels",
            ],
            "twitter": [
                "Keep it brief",
                "Use trending hashtags",
                "Include media",
                "Engage with replies",
            ],
            "linkedin": [
                "Professional tone",
                "Share industry insights",
                "Include data/stats",
                "Tag relevant people",
            ],
            "tiktok": [
                "Hook in first 3 seconds",
                "Use trending sounds",
                "Keep captions short",
                "Use popular hashtags",
            ],
        }

        tips = practices.get(
            platform, [
                "Follow platform guidelines",
                "Test and iterate",
                "Monitor performance",
            ],
        )

        return {
            "platform": platform,
            "practices": tips,
            "count": len(tips),
        }

    def generate_preview(
        self,
        text: str,
        platform: str,
        headline: str = "",
    ) -> dict[str, Any]:
        """Önizleme üretir.

        Args:
            text: Metin.
            platform: Platform.
            headline: Başlık.

        Returns:
            Önizleme bilgisi.
        """
        adapted = self.adapt_format(
            text, platform,
        )

        spec = self._specs.get(
            platform, {},
        )
        hl_max = spec.get(
            "headline_max", 60,
        )
        preview_headline = (
            headline[:hl_max]
            if headline else ""
        )

        self._stats[
            "previews_generated"
        ] += 1

        return {
            "platform": platform,
            "headline": preview_headline,
            "body": adapted["adapted"],
            "within_limits": (
                adapted["within_limit"]
            ),
            "preview_generated": True,
        }

    def get_supported_platforms(
        self,
    ) -> list[str]:
        """Desteklenen platformlar."""
        return list(self._specs.keys())

    @property
    def adaptation_count(self) -> int:
        """Adaptasyon sayısı."""
        return self._stats[
            "adaptations_done"
        ]

    @property
    def preview_count(self) -> int:
        """Önizleme sayısı."""
        return self._stats[
            "previews_generated"
        ]
