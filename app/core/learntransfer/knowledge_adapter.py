"""ATLAS Bilgi Adaptoru modulu.

Baglam adaptasyonu, alan cevirisi,
olcek ayarlama, parametre ayar, kisit esleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class KnowledgeAdapter:
    """Bilgi adaptoru.

    Bilgiyi hedef sisteme uyarlar.

    Attributes:
        _adaptations: Adaptasyon kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Bilgi adaptorunu baslatir."""
        self._adaptations: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "adapted": 0,
        }

        logger.info(
            "KnowledgeAdapter baslatildi",
        )

    def adapt_knowledge(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
        method: str = "direct",
    ) -> dict[str, Any]:
        """Bilgiyi adapte eder.

        Args:
            knowledge: Kaynak bilgi.
            target_context: Hedef baglam.
            method: Adaptasyon yontemi.

        Returns:
            Adapte edilmis bilgi.
        """
        self._counter += 1
        adapt_id = f"adapt_{self._counter}"

        kid = knowledge.get(
            "knowledge_id", "",
        )

        if method == "direct":
            adapted = self._direct_adapt(
                knowledge, target_context,
            )
        elif method == "scaled":
            adapted = self._scale_adapt(
                knowledge, target_context,
            )
        elif method == "translated":
            adapted = self._translate_adapt(
                knowledge, target_context,
            )
        elif method == "constrained":
            adapted = self._constrain_adapt(
                knowledge, target_context,
            )
        else:
            adapted = self._direct_adapt(
                knowledge, target_context,
            )

        result = {
            "adaptation_id": adapt_id,
            "knowledge_id": kid,
            "method": method,
            "adapted_content": adapted,
            "target_context": target_context,
            "confidence": self._calc_confidence(
                knowledge, target_context,
                method,
            ),
            "adapted_at": time.time(),
        }

        self._adaptations[adapt_id] = result
        self._stats["adapted"] += 1

        return {
            "adaptation_id": adapt_id,
            "knowledge_id": kid,
            "method": method,
            "confidence": result[
                "confidence"
            ],
            "adapted": True,
        }

    def _direct_adapt(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Dogrudan adaptasyon.

        Args:
            knowledge: Kaynak bilgi.
            target_context: Hedef baglam.

        Returns:
            Adapte edilmis icerik.
        """
        content = dict(
            knowledge.get("content", {}),
        )
        content["adapted_for"] = (
            target_context.get("system_id", "")
        )
        content["adaptation_method"] = "direct"
        return content

    def _scale_adapt(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Olcek adaptasyonu.

        Args:
            knowledge: Kaynak bilgi.
            target_context: Hedef baglam.

        Returns:
            Adapte edilmis icerik.
        """
        content = dict(
            knowledge.get("content", {}),
        )
        source_scale = knowledge.get(
            "scale", 1.0,
        )
        target_scale = target_context.get(
            "scale", 1.0,
        )

        scale_factor = (
            target_scale / max(source_scale, 0.01)
        )

        content["scale_factor"] = round(
            scale_factor, 3,
        )
        content["adapted_for"] = (
            target_context.get("system_id", "")
        )
        content["adaptation_method"] = "scaled"

        # Sayisal parametreleri olcekle
        for key, val in list(content.items()):
            if isinstance(val, (int, float)):
                if key not in (
                    "scale_factor",
                    "confidence",
                ):
                    content[key] = round(
                        val * scale_factor, 3,
                    )

        return content

    def _translate_adapt(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Alan cevirisi adaptasyonu.

        Args:
            knowledge: Kaynak bilgi.
            target_context: Hedef baglam.

        Returns:
            Adapte edilmis icerik.
        """
        content = dict(
            knowledge.get("content", {}),
        )
        mapping = target_context.get(
            "term_mapping", {},
        )

        # Terimleri cevir
        translated = {}
        for key, val in content.items():
            new_key = mapping.get(key, key)
            translated[new_key] = val

        translated["adapted_for"] = (
            target_context.get("system_id", "")
        )
        translated["adaptation_method"] = (
            "translated"
        )
        return translated

    def _constrain_adapt(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Kisitli adaptasyon.

        Args:
            knowledge: Kaynak bilgi.
            target_context: Hedef baglam.

        Returns:
            Adapte edilmis icerik.
        """
        content = dict(
            knowledge.get("content", {}),
        )
        constraints = target_context.get(
            "constraints", {},
        )

        # Kisitlari uygula
        for key, limit in constraints.items():
            if key in content:
                val = content[key]
                if isinstance(val, (int, float)):
                    if isinstance(limit, dict):
                        min_v = limit.get(
                            "min", val,
                        )
                        max_v = limit.get(
                            "max", val,
                        )
                        content[key] = max(
                            min_v,
                            min(val, max_v),
                        )

        content["adapted_for"] = (
            target_context.get("system_id", "")
        )
        content["adaptation_method"] = (
            "constrained"
        )
        return content

    def _calc_confidence(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
        method: str,
    ) -> float:
        """Adaptasyon guveni hesaplar.

        Args:
            knowledge: Kaynak bilgi.
            target_context: Hedef baglam.
            method: Adaptasyon yontemi.

        Returns:
            Guven skoru (0-1).
        """
        base = knowledge.get(
            "confidence", 0.5,
        )

        # Yontem etkisi
        method_factor = {
            "direct": 0.9,
            "scaled": 0.8,
            "translated": 0.7,
            "constrained": 0.75,
        }
        factor = method_factor.get(
            method, 0.7,
        )

        return round(base * factor, 3)

    def get_adaptation(
        self,
        adaptation_id: str,
    ) -> dict[str, Any]:
        """Adaptasyon getirir.

        Args:
            adaptation_id: Adaptasyon ID.

        Returns:
            Adaptasyon bilgisi.
        """
        a = self._adaptations.get(
            adaptation_id,
        )
        if not a:
            return {
                "error": (
                    "adaptation_not_found"
                ),
            }
        return dict(a)

    @property
    def adaptation_count(self) -> int:
        """Adaptasyon sayisi."""
        return self._stats["adapted"]
