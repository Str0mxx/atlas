"""ATLAS Trafik Bölücü modülü.

Rastgele atama, tutarlı hash,
katmanlı örnekleme, tutma grupları,
yeniden dengeleme.
"""

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TrafficSplitter:
    """Trafik bölücü.

    Deneylerde trafik dağılımını yönetir.

    Attributes:
        _assignments: Atama kayıtları.
        _holdout: Tutma grubu.
    """

    def __init__(self) -> None:
        """Bölücüyü başlatır."""
        self._assignments: dict[
            str, dict[str, str]
        ] = {}
        self._holdout: set[str] = set()
        self._strata: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "assignments_made": 0,
            "rebalances": 0,
        }

        logger.info(
            "TrafficSplitter baslatildi",
        )

    def assign_random(
        self,
        user_id: str,
        experiment_id: str,
        variants: list[str]
        | None = None,
        weights: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Rastgele atar.

        Args:
            user_id: Kullanıcı kimliği.
            experiment_id: Deney kimliği.
            variants: Varyantlar.
            weights: Ağırlıklar.

        Returns:
            Atama bilgisi.
        """
        variants = variants or [
            "control", "treatment",
        ]
        weights = weights or [
            1.0 / len(variants)
        ] * len(variants)

        if user_id in self._holdout:
            return {
                "user_id": user_id,
                "variant": "holdout",
                "holdout": True,
                "assigned": True,
            }

        seed = f"{user_id}:{experiment_id}"
        h = int(
            hashlib.md5(
                seed.encode(),
            ).hexdigest()[:8],
            16,
        )
        bucket = (
            h % 1000
        ) / 1000.0

        cumulative = 0.0
        chosen = variants[-1]
        for v, w in zip(
            variants, weights,
        ):
            cumulative += w
            if bucket < cumulative:
                chosen = v
                break

        if experiment_id not in (
            self._assignments
        ):
            self._assignments[
                experiment_id
            ] = {}
        self._assignments[
            experiment_id
        ][user_id] = chosen

        self._stats[
            "assignments_made"
        ] += 1

        return {
            "user_id": user_id,
            "experiment_id": experiment_id,
            "variant": chosen,
            "holdout": False,
            "assigned": True,
        }

    def assign_consistent(
        self,
        user_id: str,
        experiment_id: str,
        variants: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Tutarlı hash ile atar.

        Args:
            user_id: Kullanıcı kimliği.
            experiment_id: Deney kimliği.
            variants: Varyantlar.

        Returns:
            Atama bilgisi.
        """
        variants = variants or [
            "control", "treatment",
        ]

        existing = self._assignments.get(
            experiment_id, {},
        ).get(user_id)
        if existing:
            return {
                "user_id": user_id,
                "variant": existing,
                "cached": True,
                "assigned": True,
            }

        return self.assign_random(
            user_id, experiment_id,
            variants,
        )

    def stratified_sample(
        self,
        users: list[dict[str, Any]],
        experiment_id: str,
        stratum_key: str = "segment",
        variants: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Katmanlı örnekleme yapar.

        Args:
            users: Kullanıcı listesi.
            experiment_id: Deney kimliği.
            stratum_key: Katman anahtarı.
            variants: Varyantlar.

        Returns:
            Örnekleme bilgisi.
        """
        variants = variants or [
            "control", "treatment",
        ]

        strata: dict[
            str, list[dict[str, Any]]
        ] = {}
        for u in users:
            s = u.get(stratum_key, "other")
            if s not in strata:
                strata[s] = []
            strata[s].append(u)

        assignments = []
        for stratum, members in (
            strata.items()
        ):
            for i, user in enumerate(
                members,
            ):
                uid = user.get(
                    "user_id",
                    f"u_{i}",
                )
                vidx = i % len(variants)
                assignments.append({
                    "user_id": uid,
                    "stratum": stratum,
                    "variant": (
                        variants[vidx]
                    ),
                })

        return {
            "experiment_id": experiment_id,
            "strata_count": len(strata),
            "total_assigned": len(
                assignments,
            ),
            "assignments": assignments,
            "sampled": True,
        }

    def create_holdout(
        self,
        user_ids: list[str],
        holdout_pct: float = 5.0,
    ) -> dict[str, Any]:
        """Tutma grubu oluşturur.

        Args:
            user_ids: Kullanıcı kimlikleri.
            holdout_pct: Tutma yüzdesi.

        Returns:
            Oluşturma bilgisi.
        """
        count = max(
            int(
                len(user_ids)
                * holdout_pct
                / 100,
            ),
            1,
        )

        sorted_ids = sorted(
            user_ids,
            key=lambda u: hashlib.md5(
                u.encode(),
            ).hexdigest(),
        )
        holdout = sorted_ids[:count]

        for uid in holdout:
            self._holdout.add(uid)

        return {
            "holdout_size": len(holdout),
            "holdout_pct": holdout_pct,
            "total_users": len(user_ids),
            "created": True,
        }

    def rebalance(
        self,
        experiment_id: str,
        new_weights: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Yeniden dengeler.

        Args:
            experiment_id: Deney kimliği.
            new_weights: Yeni ağırlıklar.

        Returns:
            Dengeleme bilgisi.
        """
        new_weights = new_weights or {}

        current = self._assignments.get(
            experiment_id, {},
        )
        total = len(current)

        self._stats["rebalances"] += 1

        return {
            "experiment_id": experiment_id,
            "current_users": total,
            "new_weights": new_weights,
            "rebalanced": True,
        }

    @property
    def assignment_count(self) -> int:
        """Atama sayısı."""
        return self._stats[
            "assignments_made"
        ]

    @property
    def holdout_size(self) -> int:
        """Tutma grubu boyutu."""
        return len(self._holdout)
