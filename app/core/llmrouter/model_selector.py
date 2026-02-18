"""
Model secici modulu.

En iyi model secimi, maliyet-performans
dengesi, yetenek esleme, kisit
yonetimi, tercih ogrenme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ModelSelector:
    """Model secici.

    Attributes:
        _selections: Secim kayitlari.
        _preferences: Tercihler.
        _constraints: Kisitlar.
        _stats: Istatistikler.
    """

    STRATEGIES: list[str] = [
        "best_quality",
        "lowest_cost",
        "balanced",
        "fastest",
        "capability_match",
    ]

    def __init__(self) -> None:
        """Seciciyi baslatir."""
        self._selections: list[dict] = []
        self._preferences: dict[
            str, dict
        ] = {}
        self._constraints: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "selections_made": 0,
            "cost_selections": 0,
            "quality_selections": 0,
            "fallback_selections": 0,
        }
        logger.info(
            "ModelSelector baslatildi"
        )

    @property
    def selection_count(self) -> int:
        """Secim sayisi."""
        return len(self._selections)

    def select_model(
        self,
        available_models: (
            list[dict] | None
        ) = None,
        required_capabilities: (
            list[str] | None
        ) = None,
        strategy: str = "balanced",
        max_cost_per_1k: float = 0.0,
        max_latency_ms: int = 0,
        min_context: int = 0,
        task_domain: str = "",
        complexity_score: float = 0.5,
    ) -> dict[str, Any]:
        """En iyi modeli secer.

        Args:
            available_models: Modeller.
            required_capabilities: Gerekler.
            strategy: Strateji.
            max_cost_per_1k: Maks maliyet.
            max_latency_ms: Maks gecikme.
            min_context: Min baglam.
            task_domain: Gorev alani.
            complexity_score: Karmasiklik.

        Returns:
            Secim bilgisi.
        """
        try:
            if strategy not in (
                self.STRATEGIES
            ):
                return {
                    "selected": False,
                    "error": (
                        f"Gecersiz: "
                        f"{strategy}"
                    ),
                }

            models = available_models or []
            if not models:
                return {
                    "selected": False,
                    "error": (
                        "Model listesi bos"
                    ),
                }

            req_caps = (
                required_capabilities or []
            )

            # Filtrele
            candidates = (
                self._filter_models(
                    models,
                    req_caps,
                    max_cost_per_1k,
                    min_context,
                )
            )

            if not candidates:
                self._stats[
                    "fallback_selections"
                ] += 1
                # Fallback: ilk model
                candidates = models[:1]

            # Puanla ve sirala
            scored = self._score_models(
                candidates,
                strategy,
                complexity_score,
            )

            best = scored[0]
            sid = f"sl_{uuid4()!s:.8}"

            record = {
                "selection_id": sid,
                "model_id": best[
                    "model_id"
                ],
                "strategy": strategy,
                "score": best["_score"],
                "complexity": (
                    complexity_score
                ),
                "candidates": len(scored),
                "selected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._selections.append(record)
            self._stats[
                "selections_made"
            ] += 1

            if strategy == "lowest_cost":
                self._stats[
                    "cost_selections"
                ] += 1
            elif strategy == "best_quality":
                self._stats[
                    "quality_selections"
                ] += 1

            return {
                "selection_id": sid,
                "model_id": best[
                    "model_id"
                ],
                "provider": best.get(
                    "provider", ""
                ),
                "score": best["_score"],
                "candidates": len(scored),
                "selected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "selected": False,
                "error": str(e),
            }

    def _filter_models(
        self,
        models: list[dict],
        req_caps: list[str],
        max_cost: float,
        min_context: int,
    ) -> list[dict]:
        """Modelleri filtreler."""
        result = []
        for m in models:
            if m.get("status") not in (
                "active",
                None,
            ):
                continue

            # Yetenek kontrolu
            caps = set(
                m.get("capabilities", [])
            )
            if req_caps and not set(
                req_caps
            ).issubset(caps):
                continue

            # Maliyet kontrolu
            if max_cost > 0:
                cost = m.get(
                    "input_cost_per_1k", 0
                )
                if cost > max_cost:
                    continue

            # Baglam kontrolu
            if min_context > 0:
                ctx = m.get(
                    "context_window", 0
                )
                if ctx < min_context:
                    continue

            result.append(m)

        return result

    def _score_models(
        self,
        models: list[dict],
        strategy: str,
        complexity: float,
    ) -> list[dict]:
        """Modelleri puanlar."""
        for m in models:
            score = 0.0

            ctx = m.get(
                "context_window", 4096
            )
            in_cost = m.get(
                "input_cost_per_1k", 0.01
            )
            cap_count = len(
                m.get("capabilities", [])
            )

            if strategy == "best_quality":
                score = (
                    min(ctx / 200000, 1.0)
                    * 0.5
                    + min(cap_count / 10, 1.0)
                    * 0.5
                )
            elif strategy == "lowest_cost":
                score = max(
                    0,
                    1.0
                    - min(in_cost / 0.1, 1.0),
                )
            elif strategy == "balanced":
                quality = (
                    min(ctx / 200000, 1.0)
                    * 0.3
                    + min(cap_count / 10, 1.0)
                    * 0.3
                )
                cost_s = max(
                    0,
                    1.0
                    - min(
                        in_cost / 0.1, 1.0
                    ),
                )
                score = (
                    quality * 0.6
                    + cost_s * 0.4
                )
            elif strategy == "fastest":
                # Kucuk model = hizli
                score = max(
                    0,
                    1.0
                    - min(
                        ctx / 200000, 1.0
                    ),
                )
            elif strategy == (
                "capability_match"
            ):
                score = min(
                    cap_count / 10, 1.0
                )

            m["_score"] = round(score, 4)

        models.sort(
            key=lambda x: x["_score"],
            reverse=True,
        )
        return models

    def set_preference(
        self,
        domain: str = "",
        preferred_model: str = "",
        preferred_provider: str = "",
        strategy: str = "balanced",
    ) -> dict[str, Any]:
        """Tercih ayarlar.

        Args:
            domain: Alan.
            preferred_model: Tercih model.
            preferred_provider: Saglayici.
            strategy: Strateji.

        Returns:
            Tercih bilgisi.
        """
        try:
            self._preferences[domain] = {
                "domain": domain,
                "preferred_model": (
                    preferred_model
                ),
                "preferred_provider": (
                    preferred_provider
                ),
                "strategy": strategy,
                "set_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            return {
                "domain": domain,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def add_constraint(
        self,
        name: str = "",
        constraint_type: str = "",
        value: Any = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Kisit ekler.

        Args:
            name: Kisit adi.
            constraint_type: Tip.
            value: Deger.
            description: Aciklama.

        Returns:
            Kisit bilgisi.
        """
        try:
            self._constraints[name] = {
                "name": name,
                "constraint_type": (
                    constraint_type
                ),
                "value": value,
                "description": description,
            }
            return {
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            by_strategy: dict[
                str, int
            ] = {}
            for s in self._selections:
                st = s["strategy"]
                by_strategy[st] = (
                    by_strategy.get(st, 0)
                    + 1
                )

            return {
                "total_selections": len(
                    self._selections
                ),
                "total_preferences": len(
                    self._preferences
                ),
                "total_constraints": len(
                    self._constraints
                ),
                "by_strategy": by_strategy,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
