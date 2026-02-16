"""ATLAS Senaryo Oluşturucu.

Senaryo oluşturma, değişken tanımlama,
varsayım ayarlama, dallanma yolları, şablon.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ScenarioBuilder:
    """Senaryo oluşturucu.

    Senaryolar tasarlar, değişkenler tanımlar,
    varsayımlar belirler ve dallanma yolları oluşturur.

    Attributes:
        _scenarios: Senaryo kayıtları.
        _templates: Şablon kütüphanesi.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._scenarios: dict[
            str, dict
        ] = {}
        self._templates: dict[
            str, dict
        ] = {
            "market_entry": {
                "variables": [
                    "market_size",
                    "competition",
                    "investment",
                ],
                "assumptions": [
                    "stable_economy",
                    "regulatory_approval",
                ],
            },
            "product_launch": {
                "variables": [
                    "demand",
                    "pricing",
                    "marketing_budget",
                ],
                "assumptions": [
                    "on_time_delivery",
                    "quality_standards",
                ],
            },
            "expansion": {
                "variables": [
                    "new_markets",
                    "hiring",
                    "capex",
                ],
                "assumptions": [
                    "funding_available",
                    "talent_pool",
                ],
            },
        }
        self._stats = {
            "scenarios_created": 0,
            "variables_defined": 0,
        }
        logger.info(
            "ScenarioBuilder baslatildi",
        )

    @property
    def scenario_count(self) -> int:
        """Senaryo sayısı."""
        return self._stats[
            "scenarios_created"
        ]

    @property
    def variable_count(self) -> int:
        """Değişken sayısı."""
        return self._stats[
            "variables_defined"
        ]

    def create_scenario(
        self,
        name: str,
        scenario_type: str = "realistic",
        description: str = "",
    ) -> dict[str, Any]:
        """Senaryo oluşturur.

        Args:
            name: Senaryo adı.
            scenario_type: Senaryo tipi.
            description: Açıklama.

        Returns:
            Senaryo bilgisi.
        """
        sid = f"sc_{str(uuid4())[:8]}"
        self._scenarios[sid] = {
            "name": name,
            "type": scenario_type,
            "description": description,
            "variables": {},
            "assumptions": [],
            "branches": [],
        }
        self._stats[
            "scenarios_created"
        ] += 1

        return {
            "scenario_id": sid,
            "name": name,
            "type": scenario_type,
            "created": True,
        }

    def define_variable(
        self,
        scenario_id: str,
        var_name: str,
        base_value: float = 0.0,
        min_value: float = 0.0,
        max_value: float = 100.0,
    ) -> dict[str, Any]:
        """Değişken tanımlar.

        Args:
            scenario_id: Senaryo kimliği.
            var_name: Değişken adı.
            base_value: Temel değer.
            min_value: Minimum değer.
            max_value: Maksimum değer.

        Returns:
            Değişken bilgisi.
        """
        if scenario_id in self._scenarios:
            self._scenarios[scenario_id][
                "variables"
            ][var_name] = {
                "base": base_value,
                "min": min_value,
                "max": max_value,
            }

        self._stats[
            "variables_defined"
        ] += 1

        return {
            "scenario_id": scenario_id,
            "variable": var_name,
            "base_value": base_value,
            "range": [min_value, max_value],
            "defined": True,
        }

    def set_assumption(
        self,
        scenario_id: str,
        assumption: str,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Varsayım ayarlar.

        Args:
            scenario_id: Senaryo kimliği.
            assumption: Varsayım açıklaması.
            confidence: Güven seviyesi (0-1).

        Returns:
            Varsayım bilgisi.
        """
        if scenario_id in self._scenarios:
            self._scenarios[scenario_id][
                "assumptions"
            ].append(
                {
                    "text": assumption,
                    "confidence": confidence,
                },
            )

        return {
            "scenario_id": scenario_id,
            "assumption": assumption,
            "confidence": confidence,
            "set": True,
        }

    def create_branch(
        self,
        scenario_id: str,
        branch_name: str,
        probability: float = 0.5,
        description: str = "",
    ) -> dict[str, Any]:
        """Dallanma yolu oluşturur.

        Args:
            scenario_id: Senaryo kimliği.
            branch_name: Dal adı.
            probability: Olasılık.
            description: Açıklama.

        Returns:
            Dallanma bilgisi.
        """
        bid = f"br_{str(uuid4())[:6]}"

        if scenario_id in self._scenarios:
            self._scenarios[scenario_id][
                "branches"
            ].append(
                {
                    "branch_id": bid,
                    "name": branch_name,
                    "probability": probability,
                },
            )

        return {
            "branch_id": bid,
            "scenario_id": scenario_id,
            "branch_name": branch_name,
            "probability": probability,
            "created": True,
        }

    def get_template(
        self,
        template_name: str,
    ) -> dict[str, Any]:
        """Şablon getirir.

        Args:
            template_name: Şablon adı.

        Returns:
            Şablon bilgisi.
        """
        tmpl = self._templates.get(
            template_name,
        )

        if tmpl is None:
            return {
                "template_name": template_name,
                "found": False,
                "available": list(
                    self._templates.keys(),
                ),
            }

        return {
            "template_name": template_name,
            "variables": tmpl["variables"],
            "assumptions": tmpl[
                "assumptions"
            ],
            "found": True,
        }
