"""ATLAS Metin Yazıcı modülü.

Reklam metni, başlık, açıklama,
CTA, varyasyon üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CopyWriter:
    """Metin yazıcı.

    Pazarlama metinleri üretir.

    Attributes:
        _copies: Metin kayıtları.
        _templates: Şablon kayıtları.
    """

    def __init__(self) -> None:
        """Yazıcıyı başlatır."""
        self._copies: dict[
            str, dict[str, Any]
        ] = {}
        self._templates: dict[
            str, list[str]
        ] = {
            "ad_copy": [
                "{product} - {benefit}. "
                "{cta}",
                "Discover {product}. "
                "{benefit} today!",
            ],
            "headline": [
                "{benefit} with {product}",
                "{product}: {benefit}",
            ],
            "cta": [
                "Shop Now",
                "Learn More",
                "Get Started",
                "Try Free",
                "Buy Now",
            ],
        }
        self._counter = 0
        self._stats = {
            "copies_written": 0,
            "headlines_created": 0,
            "ctas_generated": 0,
            "variations_made": 0,
        }

        logger.info(
            "CopyWriter baslatildi",
        )

    def write_ad_copy(
        self,
        product: str,
        benefit: str = "",
        tone: str = "professional",
        max_length: int = 0,
    ) -> dict[str, Any]:
        """Reklam metni yazar.

        Args:
            product: Ürün.
            benefit: Fayda.
            tone: Ton.
            max_length: Maks uzunluk.

        Returns:
            Metin bilgisi.
        """
        self._counter += 1
        cid = f"copy_{self._counter}"

        text = (
            f"{product} - {benefit}. "
            f"Get yours today!"
            if benefit
            else f"Discover {product}. "
            f"The best choice for you!"
        )

        if max_length and len(text) > max_length:
            text = text[:max_length - 3] + "..."

        copy = {
            "copy_id": cid,
            "type": "ad_copy",
            "product": product,
            "text": text,
            "tone": tone,
            "char_count": len(text),
            "timestamp": time.time(),
        }
        self._copies[cid] = copy
        self._stats["copies_written"] += 1

        return {
            "copy_id": cid,
            "text": text,
            "char_count": len(text),
            "tone": tone,
            "created": True,
        }

    def create_headline(
        self,
        product: str,
        benefit: str = "",
        style: str = "direct",
        max_length: int = 60,
    ) -> dict[str, Any]:
        """Başlık oluşturur.

        Args:
            product: Ürün.
            benefit: Fayda.
            style: Stil.
            max_length: Maks uzunluk.

        Returns:
            Başlık bilgisi.
        """
        if style == "question":
            headline = (
                f"Looking for {benefit}? "
                f"Try {product}"
                if benefit
                else f"Need {product}?"
            )
        elif style == "how_to":
            headline = (
                f"How {product} delivers "
                f"{benefit}"
                if benefit
                else f"How to use {product}"
            )
        else:
            headline = (
                f"{product}: {benefit}"
                if benefit
                else product
            )

        if len(headline) > max_length:
            headline = (
                headline[:max_length - 3] + "..."
            )

        self._stats[
            "headlines_created"
        ] += 1

        return {
            "headline": headline,
            "style": style,
            "char_count": len(headline),
            "within_limit": (
                len(headline) <= max_length
            ),
        }

    def write_description(
        self,
        product: str,
        features: list[str]
        | None = None,
        max_length: int = 200,
    ) -> dict[str, Any]:
        """Açıklama yazar.

        Args:
            product: Ürün.
            features: Özellikler.
            max_length: Maks uzunluk.

        Returns:
            Açıklama bilgisi.
        """
        features = features or []

        if features:
            feat_text = ", ".join(
                features[:3],
            )
            desc = (
                f"{product} offers "
                f"{feat_text}."
            )
        else:
            desc = (
                f"{product} - your premium "
                f"solution."
            )

        if len(desc) > max_length:
            desc = desc[:max_length - 3] + "..."

        self._stats["copies_written"] += 1

        return {
            "description": desc,
            "char_count": len(desc),
            "features_used": len(
                features[:3],
            ),
            "within_limit": (
                len(desc) <= max_length
            ),
        }

    def generate_cta(
        self,
        action: str = "buy",
        urgency: bool = False,
    ) -> dict[str, Any]:
        """CTA üretir.

        Args:
            action: Aksiyon.
            urgency: Aciliyet.

        Returns:
            CTA bilgisi.
        """
        cta_map = {
            "buy": "Buy Now",
            "learn": "Learn More",
            "start": "Get Started",
            "try": "Try Free",
            "sign_up": "Sign Up",
            "contact": "Contact Us",
            "download": "Download Now",
        }

        cta = cta_map.get(
            action, "Learn More",
        )

        if urgency:
            cta = f"{cta} - Limited Time!"

        self._stats[
            "ctas_generated"
        ] += 1

        return {
            "cta": cta,
            "action": action,
            "urgency": urgency,
            "char_count": len(cta),
        }

    def create_variations(
        self,
        original: str,
        count: int = 3,
        variation_type: str = "rephrase",
    ) -> dict[str, Any]:
        """Varyasyon oluşturur.

        Args:
            original: Orijinal metin.
            count: Adet.
            variation_type: Varyasyon tipi.

        Returns:
            Varyasyon bilgisi.
        """
        variations = []
        words = original.split()

        for i in range(min(count, 5)):
            if variation_type == "shorten":
                cut = max(
                    len(words) - i - 1, 1,
                )
                var = " ".join(words[:cut])
            elif variation_type == "extend":
                var = (
                    f"{original} "
                    f"(version {i + 1})"
                )
            else:
                if i == 0:
                    var = original.upper()
                elif i == 1:
                    var = original.title()
                else:
                    var = (
                        f"{original} "
                        f"[v{i + 1}]"
                    )
            variations.append(var)

        self._stats[
            "variations_made"
        ] += len(variations)

        return {
            "original": original,
            "variations": variations,
            "count": len(variations),
            "type": variation_type,
        }

    def get_copy(
        self,
        copy_id: str,
    ) -> dict[str, Any] | None:
        """Metin döndürür."""
        return self._copies.get(copy_id)

    @property
    def copy_count(self) -> int:
        """Metin sayısı."""
        return self._stats[
            "copies_written"
        ]

    @property
    def headline_count(self) -> int:
        """Başlık sayısı."""
        return self._stats[
            "headlines_created"
        ]
