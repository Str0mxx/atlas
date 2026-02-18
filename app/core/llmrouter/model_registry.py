"""
Model kayit defteri modulu.

Model kayit, saglayici yonetimi,
yetenek haritalama, fiyat bilgisi,
durum takibi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Model kayit defteri.

    Attributes:
        _models: Model kayitlari.
        _providers: Saglayici kayitlari.
        _stats: Istatistikler.
    """

    CAPABILITIES: list[str] = [
        "text_generation",
        "code_generation",
        "reasoning",
        "summarization",
        "translation",
        "classification",
        "embedding",
        "vision",
        "function_calling",
        "structured_output",
    ]

    def __init__(self) -> None:
        """Kayit defterini baslatir."""
        self._models: dict[
            str, dict
        ] = {}
        self._providers: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "models_registered": 0,
            "providers_registered": 0,
            "lookups_performed": 0,
        }
        logger.info(
            "ModelRegistry baslatildi"
        )

    @property
    def model_count(self) -> int:
        """Model sayisi."""
        return len(self._models)

    def register_provider(
        self,
        name: str = "",
        api_type: str = "rest",
        base_url: str = "",
        auth_type: str = "api_key",
        rate_limit: int = 60,
        description: str = "",
    ) -> dict[str, Any]:
        """Saglayici kaydeder.

        Args:
            name: Saglayici adi.
            api_type: API tipi.
            base_url: Temel URL.
            auth_type: Kimlik tipi.
            rate_limit: Hiz limiti.
            description: Aciklama.

        Returns:
            Saglayici bilgisi.
        """
        try:
            self._providers[name] = {
                "name": name,
                "api_type": api_type,
                "base_url": base_url,
                "auth_type": auth_type,
                "rate_limit": rate_limit,
                "description": description,
                "status": "active",
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "providers_registered"
            ] += 1

            return {
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def register_model(
        self,
        model_id: str = "",
        provider: str = "",
        name: str = "",
        capabilities: (
            list[str] | None
        ) = None,
        max_tokens: int = 4096,
        input_cost_per_1k: float = 0.0,
        output_cost_per_1k: float = 0.0,
        context_window: int = 4096,
        description: str = "",
    ) -> dict[str, Any]:
        """Model kaydeder.

        Args:
            model_id: Model ID.
            provider: Saglayici.
            name: Model adi.
            capabilities: Yetenekler.
            max_tokens: Maks token.
            input_cost_per_1k: Girdi maliyet.
            output_cost_per_1k: Cikti maliyet.
            context_window: Baglam penceresi.
            description: Aciklama.

        Returns:
            Model bilgisi.
        """
        try:
            caps = capabilities or []
            for c in caps:
                if c not in self.CAPABILITIES:
                    return {
                        "registered": False,
                        "error": (
                            f"Gecersiz "
                            f"yetenek: {c}"
                        ),
                    }

            self._models[model_id] = {
                "model_id": model_id,
                "provider": provider,
                "name": name,
                "capabilities": caps,
                "max_tokens": max_tokens,
                "input_cost_per_1k": (
                    input_cost_per_1k
                ),
                "output_cost_per_1k": (
                    output_cost_per_1k
                ),
                "context_window": (
                    context_window
                ),
                "description": description,
                "status": "active",
                "usage_count": 0,
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "models_registered"
            ] += 1

            return {
                "model_id": model_id,
                "provider": provider,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def get_model(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Model getirir.

        Args:
            model_id: Model ID.

        Returns:
            Model bilgisi.
        """
        try:
            m = self._models.get(model_id)
            if not m:
                return {
                    "retrieved": False,
                    "error": (
                        "Model bulunamadi"
                    ),
                }

            self._stats[
                "lookups_performed"
            ] += 1
            return {
                **m,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def find_by_capability(
        self,
        capability: str = "",
        provider: str = "",
    ) -> dict[str, Any]:
        """Yetenege gore model bulur.

        Args:
            capability: Yetenek.
            provider: Saglayici filtresi.

        Returns:
            Model listesi.
        """
        try:
            results = []
            for m in self._models.values():
                if m["status"] != "active":
                    continue
                if (
                    capability
                    and capability
                    not in m["capabilities"]
                ):
                    continue
                if (
                    provider
                    and m["provider"]
                    != provider
                ):
                    continue
                results.append(m)

            self._stats[
                "lookups_performed"
            ] += 1

            return {
                "models": results,
                "count": len(results),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def update_status(
        self,
        model_id: str = "",
        status: str = "active",
    ) -> dict[str, Any]:
        """Model durumunu gunceller.

        Args:
            model_id: Model ID.
            status: Yeni durum.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            m = self._models.get(model_id)
            if not m:
                return {
                    "updated": False,
                    "error": (
                        "Model bulunamadi"
                    ),
                }

            valid = [
                "active",
                "inactive",
                "deprecated",
                "maintenance",
            ]
            if status not in valid:
                return {
                    "updated": False,
                    "error": (
                        f"Gecersiz: {status}"
                    ),
                }

            m["status"] = status
            return {
                "model_id": model_id,
                "status": status,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def increment_usage(
        self,
        model_id: str = "",
    ) -> None:
        """Kullanim sayacini arttirir."""
        m = self._models.get(model_id)
        if m:
            m["usage_count"] += 1

    def get_pricing(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Fiyat bilgisi getirir.

        Args:
            model_id: Model ID.

        Returns:
            Fiyat bilgisi.
        """
        try:
            m = self._models.get(model_id)
            if not m:
                return {
                    "retrieved": False,
                    "error": (
                        "Model bulunamadi"
                    ),
                }

            return {
                "model_id": model_id,
                "input_cost_per_1k": (
                    m["input_cost_per_1k"]
                ),
                "output_cost_per_1k": (
                    m["output_cost_per_1k"]
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def list_providers(
        self,
    ) -> dict[str, Any]:
        """Saglayicilari listeler."""
        try:
            return {
                "providers": list(
                    self._providers.values()
                ),
                "count": len(
                    self._providers
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_provider: dict[
                str, int
            ] = {}
            for m in self._models.values():
                p = m["provider"]
                by_provider[p] = (
                    by_provider.get(p, 0) + 1
                )

            return {
                "total_models": len(
                    self._models
                ),
                "total_providers": len(
                    self._providers
                ),
                "active_models": sum(
                    1
                    for m in (
                        self._models.values()
                    )
                    if m["status"] == "active"
                ),
                "by_provider": by_provider,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
