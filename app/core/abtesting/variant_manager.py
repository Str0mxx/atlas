"""ATLAS Varyant Yöneticisi modülü.

Varyant yapılandırma, özellik bayrakları,
yayılım yüzdesi, hedefleme kuralları,
karşılıklı dışlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VariantManager:
    """Varyant yöneticisi.

    Deney varyantlarını yönetir.

    Attributes:
        _variants: Varyant kayıtları.
        _flags: Özellik bayrakları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._variants: dict[
            str, dict[str, Any]
        ] = {}
        self._flags: dict[
            str, dict[str, Any]
        ] = {}
        self._rules: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._exclusions: list[
            tuple[str, str]
        ] = []
        self._counter = 0
        self._stats = {
            "variants_configured": 0,
            "flags_created": 0,
        }

        logger.info(
            "VariantManager baslatildi",
        )

    def configure_variant(
        self,
        experiment_id: str,
        variant_name: str,
        config: dict[str, Any]
        | None = None,
        traffic_pct: float = 50.0,
    ) -> dict[str, Any]:
        """Varyant yapılandırır.

        Args:
            experiment_id: Deney kimliği.
            variant_name: Varyant adı.
            config: Yapılandırma.
            traffic_pct: Trafik yüzdesi.

        Returns:
            Yapılandırma bilgisi.
        """
        config = config or {}
        self._counter += 1
        vid = f"var_{self._counter}"

        key = (
            f"{experiment_id}"
            f":{variant_name}"
        )
        self._variants[key] = {
            "variant_id": vid,
            "experiment_id": experiment_id,
            "name": variant_name,
            "config": config,
            "traffic_pct": traffic_pct,
            "active": True,
            "timestamp": time.time(),
        }

        self._stats[
            "variants_configured"
        ] += 1

        return {
            "variant_id": vid,
            "name": variant_name,
            "traffic_pct": traffic_pct,
            "configured": True,
        }

    def create_feature_flag(
        self,
        flag_name: str,
        default_value: bool = False,
        experiment_id: str = "",
    ) -> dict[str, Any]:
        """Özellik bayrağı oluşturur.

        Args:
            flag_name: Bayrak adı.
            default_value: Varsayılan değer.
            experiment_id: Deney kimliği.

        Returns:
            Oluşturma bilgisi.
        """
        self._flags[flag_name] = {
            "flag_name": flag_name,
            "default_value": default_value,
            "experiment_id": experiment_id,
            "enabled": default_value,
            "timestamp": time.time(),
        }

        self._stats[
            "flags_created"
        ] += 1

        return {
            "flag_name": flag_name,
            "default_value": default_value,
            "created": True,
        }

    def set_rollout_percentage(
        self,
        experiment_id: str,
        variant_name: str,
        percentage: float,
    ) -> dict[str, Any]:
        """Yayılım yüzdesi ayarlar.

        Args:
            experiment_id: Deney kimliği.
            variant_name: Varyant adı.
            percentage: Yüzde.

        Returns:
            Ayarlama bilgisi.
        """
        key = (
            f"{experiment_id}"
            f":{variant_name}"
        )
        variant = self._variants.get(key)
        if not variant:
            return {
                "experiment_id": experiment_id,
                "found": False,
            }

        variant[
            "traffic_pct"
        ] = percentage

        return {
            "experiment_id": experiment_id,
            "variant_name": variant_name,
            "percentage": percentage,
            "updated": True,
        }

    def add_targeting_rule(
        self,
        experiment_id: str,
        rule_type: str = "segment",
        condition: str = "",
        value: str = "",
    ) -> dict[str, Any]:
        """Hedefleme kuralı ekler.

        Args:
            experiment_id: Deney kimliği.
            rule_type: Kural tipi.
            condition: Koşul.
            value: Değer.

        Returns:
            Ekleme bilgisi.
        """
        rules = self._rules.get(
            experiment_id, [],
        )
        rules.append({
            "rule_type": rule_type,
            "condition": condition,
            "value": value,
            "timestamp": time.time(),
        })
        self._rules[
            experiment_id
        ] = rules

        return {
            "experiment_id": experiment_id,
            "rule_type": rule_type,
            "rule_count": len(rules),
            "added": True,
        }

    def set_mutual_exclusion(
        self,
        experiment_a: str,
        experiment_b: str,
    ) -> dict[str, Any]:
        """Karşılıklı dışlama ayarlar.

        Args:
            experiment_a: Deney A.
            experiment_b: Deney B.

        Returns:
            Ayarlama bilgisi.
        """
        pair = (experiment_a, experiment_b)
        if pair not in self._exclusions:
            self._exclusions.append(pair)

        return {
            "experiment_a": experiment_a,
            "experiment_b": experiment_b,
            "excluded": True,
        }

    def check_exclusion(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Dışlama kontrolü yapar.

        Args:
            experiment_id: Deney kimliği.

        Returns:
            Kontrol bilgisi.
        """
        excluded_with = []
        for a, b in self._exclusions:
            if a == experiment_id:
                excluded_with.append(b)
            elif b == experiment_id:
                excluded_with.append(a)

        return {
            "experiment_id": experiment_id,
            "excluded_with": excluded_with,
            "count": len(excluded_with),
            "checked": True,
        }

    @property
    def variant_count(self) -> int:
        """Varyant sayısı."""
        return self._stats[
            "variants_configured"
        ]

    @property
    def flag_count(self) -> int:
        """Bayrak sayısı."""
        return self._stats[
            "flags_created"
        ]
