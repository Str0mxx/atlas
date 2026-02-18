"""
Model Seçici modulu.

Model listeleme, yetenek gosterimi,
maliyet karsilastirma, öneri, secim.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WizardModelSelector:
    """Sihirbaz model secici.

    Attributes:
        _models: Model katalogu.
        _selected: Secilen model.
        _stats: Istatistikler.
    """

    # Varsayilan model katalogu
    DEFAULT_MODELS: list[dict] = [
        {
            "model_id": "claude-opus-4-6",
            "name": "Claude Opus 4.6",
            "provider": "anthropic",
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "context_window": 200000,
            "capabilities": [
                "reasoning",
                "coding",
                "analysis",
                "vision",
            ],
            "recommended_for": ["complex", "research", "production"],
        },
        {
            "model_id": "claude-sonnet-4-6",
            "name": "Claude Sonnet 4.6",
            "provider": "anthropic",
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "context_window": 200000,
            "capabilities": [
                "reasoning",
                "coding",
                "analysis",
                "vision",
            ],
            "recommended_for": ["general", "balanced", "development"],
        },
        {
            "model_id": "claude-haiku-4-5-20251001",
            "name": "Claude Haiku 4.5",
            "provider": "anthropic",
            "cost_per_1k_input": 0.0008,
            "cost_per_1k_output": 0.004,
            "context_window": 200000,
            "capabilities": ["fast_response", "simple_tasks"],
            "recommended_for": ["simple", "high_volume", "low_cost"],
        },
        {
            "model_id": "gpt-4o",
            "name": "GPT-4o",
            "provider": "openai",
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
            "context_window": 128000,
            "capabilities": [
                "reasoning",
                "coding",
                "vision",
            ],
            "recommended_for": ["general", "vision"],
        },
        {
            "model_id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "provider": "google",
            "cost_per_1k_input": 0.00125,
            "cost_per_1k_output": 0.005,
            "context_window": 1000000,
            "capabilities": [
                "long_context",
                "multimodal",
            ],
            "recommended_for": ["long_context", "multimodal"],
        },
    ]

    def __init__(self) -> None:
        """Seciciyi baslatir."""
        self._models: dict[str, dict] = {
            m["model_id"]: m for m in self.DEFAULT_MODELS
        }
        self._selected: str | None = None
        self._stats: dict[str, int] = {
            "listings": 0,
            "comparisons": 0,
            "recommendations": 0,
            "selections": 0,
        }
        logger.info("WizardModelSelector baslatildi")

    @property
    def model_count(self) -> int:
        """Model sayisi."""
        return len(self._models)

    def list_models(
        self,
        provider: str | None = None,
    ) -> list[dict]:
        """Modelleri listeler.

        Args:
            provider: Saglayici filtresi.

        Returns:
            Model listesi.
        """
        self._stats["listings"] += 1
        models = list(self._models.values())
        if provider:
            models = [
                m for m in models if m.get("provider") == provider
            ]
        return models

    def get_capabilities(
        self, model_id: str = ""
    ) -> dict[str, Any]:
        """Model yeteneklerini getirir.

        Args:
            model_id: Model kimlik.

        Returns:
            Yetenek bilgisi.
        """
        try:
            model = self._models.get(model_id)
            if not model:
                return {"found": False, "error": "model_bulunamadi"}
            return {
                "found": True,
                "model_id": model_id,
                "name": model["name"],
                "capabilities": model.get("capabilities", []),
                "context_window": model.get("context_window", 0),
            }
        except Exception as e:
            logger.error("Yetenek getirme hatasi: %s", e)
            return {"found": False, "error": str(e)}

    def compare_costs(
        self, model_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Model maliyetlerini karsilastirir.

        Args:
            model_ids: Karsilastirilacak model IDler.

        Returns:
            Karsilastirma sonucu.
        """
        try:
            self._stats["comparisons"] += 1
            ids = model_ids or list(self._models.keys())
            comparison = []

            for mid in ids:
                model = self._models.get(mid)
                if model:
                    comparison.append({
                        "model_id": mid,
                        "name": model.get("name", ""),
                        "cost_per_1k_input": model.get(
                            "cost_per_1k_input", 0
                        ),
                        "cost_per_1k_output": model.get(
                            "cost_per_1k_output", 0
                        ),
                        "total_cost_1k": (
                            model.get("cost_per_1k_input", 0)
                            + model.get("cost_per_1k_output", 0)
                        ),
                    })

            # Maliyete gore sirala
            comparison.sort(key=lambda x: x["total_cost_1k"])

            return {
                "compared": True,
                "models": comparison,
                "cheapest": comparison[0]["model_id"] if comparison else None,
                "count": len(comparison),
            }
        except Exception as e:
            logger.error("Maliyet karsilastirma hatasi: %s", e)
            return {"compared": False, "error": str(e)}

    def get_recommendation(
        self, use_case: str = "general"
    ) -> dict[str, Any]:
        """Kullanim durumuna gore öneri verir.

        Args:
            use_case: Kullanim durumu.

        Returns:
            Öneri bilgisi.
        """
        try:
            self._stats["recommendations"] += 1

            # Use-case eslesme
            use_case_map = {
                "complex": "claude-opus-4-6",
                "research": "claude-opus-4-6",
                "production": "claude-opus-4-6",
                "general": "claude-sonnet-4-6",
                "balanced": "claude-sonnet-4-6",
                "development": "claude-sonnet-4-6",
                "simple": "claude-haiku-4-5-20251001",
                "high_volume": "claude-haiku-4-5-20251001",
                "low_cost": "claude-haiku-4-5-20251001",
                "long_context": "gemini-1.5-pro",
                "vision": "gpt-4o",
            }

            recommended_id = use_case_map.get(
                use_case, "claude-sonnet-4-6"
            )
            model = self._models.get(recommended_id, {})

            reasons = {
                "complex": "En güçlü muhakeme",
                "general": "Maliyet-performans dengesi",
                "simple": "En hızlı ve ucuz",
                "long_context": "1M token bağlam",
                "vision": "Görüntü analizi",
            }
            reason = reasons.get(use_case, "Genel kullanim icin uygun")

            return {
                "recommended": recommended_id,
                "name": model.get("name", ""),
                "reason": reason,
                "use_case": use_case,
            }
        except Exception as e:
            logger.error("Öneri hatasi: %s", e)
            return {"recommended": "", "error": str(e)}

    def select_model(
        self, model_id: str = ""
    ) -> dict[str, Any]:
        """Model secer.

        Args:
            model_id: Secilecek model.

        Returns:
            Secim bilgisi.
        """
        try:
            if model_id not in self._models:
                return {
                    "selected": False,
                    "error": "model_bulunamadi",
                    "model_id": model_id,
                }
            self._selected = model_id
            self._stats["selections"] += 1
            model = self._models[model_id]
            return {
                "selected": True,
                "model_id": model_id,
                "name": model.get("name", ""),
                "provider": model.get("provider", ""),
            }
        except Exception as e:
            logger.error("Model secim hatasi: %s", e)
            return {"selected": False, "error": str(e)}

    def get_selected(self) -> dict[str, Any]:
        """Secili modeli dondurur.

        Returns:
            Secili model bilgisi.
        """
        if not self._selected:
            return {"found": False, "model_id": None}
        model = self._models.get(self._selected, {})
        return {
            "found": True,
            "model_id": self._selected,
            "name": model.get("name", ""),
        }

    def add_model(
        self, model_info: dict | None = None
    ) -> dict[str, Any]:
        """Ozel model ekler.

        Args:
            model_info: Model bilgisi.

        Returns:
            Ekleme bilgisi.
        """
        try:
            if not model_info:
                return {"added": False, "error": "model_bilgisi_gerekli"}
            mid = model_info.get("model_id", "")
            if not mid:
                return {"added": False, "error": "model_id_gerekli"}
            self._models[mid] = model_info
            return {"added": True, "model_id": mid}
        except Exception as e:
            logger.error("Model ekleme hatasi: %s", e)
            return {"added": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            providers = list(
                {m.get("provider", "") for m in self._models.values()}
            )
            return {
                "retrieved": True,
                "model_count": len(self._models),
                "providers": providers,
                "selected": self._selected,
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}
