"""ATLAS Kaynak Tanimlayici modulu.

Kaynak tipleri, ozellik tanimlari,
bagimliliklar, ciktilar ve kosullar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResourceDefiner:
    """Kaynak tanimlayici.

    IaC kaynaklarini tanimlar.

    Attributes:
        _resources: Tanimli kaynaklar.
        _outputs: Cikti tanimlari.
    """

    def __init__(self) -> None:
        """Tanimlayiciyi baslatir."""
        self._resources: dict[
            str, dict[str, Any]
        ] = {}
        self._outputs: dict[
            str, dict[str, Any]
        ] = {}
        self._conditions: dict[
            str, dict[str, Any]
        ] = {}
        self._variables: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "ResourceDefiner baslatildi",
        )

    def define(
        self,
        resource_type: str,
        name: str,
        properties: dict[str, Any]
            | None = None,
        depends_on: list[str] | None = None,
        condition: str | None = None,
        provider: str = "default",
    ) -> dict[str, Any]:
        """Kaynak tanimlar.

        Args:
            resource_type: Kaynak tipi.
            name: Kaynak adi.
            properties: Ozellikler.
            depends_on: Bagimliliklar.
            condition: Kosul adi.
            provider: Saglayici.

        Returns:
            Tanim bilgisi.
        """
        key = f"{resource_type}.{name}"
        self._resources[key] = {
            "type": resource_type,
            "name": name,
            "properties": properties or {},
            "depends_on": depends_on or [],
            "condition": condition,
            "provider": provider,
            "defined_at": time.time(),
        }

        return {
            "key": key,
            "type": resource_type,
            "name": name,
        }

    def get(
        self,
        resource_type: str,
        name: str,
    ) -> dict[str, Any] | None:
        """Kaynak tanimini getirir.

        Args:
            resource_type: Kaynak tipi.
            name: Kaynak adi.

        Returns:
            Tanim bilgisi veya None.
        """
        key = f"{resource_type}.{name}"
        return self._resources.get(key)

    def remove(
        self,
        resource_type: str,
        name: str,
    ) -> bool:
        """Kaynak tanimini kaldirir.

        Args:
            resource_type: Kaynak tipi.
            name: Kaynak adi.

        Returns:
            Basarili mi.
        """
        key = f"{resource_type}.{name}"
        if key in self._resources:
            del self._resources[key]
            return True
        return False

    def set_property(
        self,
        resource_type: str,
        name: str,
        prop_name: str,
        prop_value: Any,
    ) -> bool:
        """Kaynak ozelligini ayarlar.

        Args:
            resource_type: Kaynak tipi.
            name: Kaynak adi.
            prop_name: Ozellik adi.
            prop_value: Ozellik degeri.

        Returns:
            Basarili mi.
        """
        key = f"{resource_type}.{name}"
        res = self._resources.get(key)
        if not res:
            return False

        res["properties"][prop_name] = prop_value
        return True

    def add_dependency(
        self,
        resource_type: str,
        name: str,
        depends_on: str,
    ) -> bool:
        """Bagimlilik ekler.

        Args:
            resource_type: Kaynak tipi.
            name: Kaynak adi.
            depends_on: Bagimlilik.

        Returns:
            Basarili mi.
        """
        key = f"{resource_type}.{name}"
        res = self._resources.get(key)
        if not res:
            return False

        if depends_on not in res["depends_on"]:
            res["depends_on"].append(depends_on)
        return True

    def get_dependencies(
        self,
        resource_type: str,
        name: str,
    ) -> list[str]:
        """Bagimliliklari getirir.

        Args:
            resource_type: Kaynak tipi.
            name: Kaynak adi.

        Returns:
            Bagimlilik listesi.
        """
        key = f"{resource_type}.{name}"
        res = self._resources.get(key)
        if not res:
            return []
        return list(res["depends_on"])

    def define_output(
        self,
        name: str,
        value: Any,
        description: str = "",
    ) -> dict[str, Any]:
        """Cikti tanimlar.

        Args:
            name: Cikti adi.
            value: Deger.
            description: Aciklama.

        Returns:
            Cikti bilgisi.
        """
        self._outputs[name] = {
            "value": value,
            "description": description,
        }
        return {"name": name}

    def get_output(
        self,
        name: str,
    ) -> Any | None:
        """Cikti degerini getirir.

        Args:
            name: Cikti adi.

        Returns:
            Deger veya None.
        """
        out = self._outputs.get(name)
        return out["value"] if out else None

    def define_condition(
        self,
        name: str,
        expression: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Kosul tanimlar.

        Args:
            name: Kosul adi.
            expression: Ifade.
            description: Aciklama.

        Returns:
            Kosul bilgisi.
        """
        self._conditions[name] = {
            "expression": expression,
            "description": description,
        }
        return {"name": name}

    def evaluate_condition(
        self,
        name: str,
        context: dict[str, Any]
            | None = None,
    ) -> bool:
        """Kosulu degerlendirir.

        Args:
            name: Kosul adi.
            context: Baglam.

        Returns:
            Sonuc.
        """
        cond = self._conditions.get(name)
        if not cond:
            return True

        expr = cond["expression"]
        ctx = context or {}

        # Basit degerlendirme
        if expr in ctx:
            return bool(ctx[expr])
        if expr == "true":
            return True
        if expr == "false":
            return False
        return True

    def define_variable(
        self,
        name: str,
        var_type: str = "string",
        default: Any = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Degisken tanimlar.

        Args:
            name: Degisken adi.
            var_type: Tip.
            default: Varsayilan.
            description: Aciklama.

        Returns:
            Degisken bilgisi.
        """
        self._variables[name] = {
            "type": var_type,
            "default": default,
            "description": description,
        }
        return {"name": name, "type": var_type}

    def get_variable(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Degisken bilgisini getirir.

        Args:
            name: Degisken adi.

        Returns:
            Degisken bilgisi veya None.
        """
        return self._variables.get(name)

    def list_resources(
        self,
        resource_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Kaynaklari listeler.

        Args:
            resource_type: Tip filtresi.

        Returns:
            Kaynak listesi.
        """
        resources = list(
            self._resources.values(),
        )
        if resource_type:
            resources = [
                r for r in resources
                if r["type"] == resource_type
            ]
        return resources

    def get_dependency_order(
        self,
    ) -> list[str]:
        """Bagimlilik sirasini getirir.

        Returns:
            Sirali kaynak anahtarlari.
        """
        visited: set[str] = set()
        order: list[str] = []

        def visit(key: str) -> None:
            if key in visited:
                return
            visited.add(key)
            res = self._resources.get(key)
            if res:
                for dep in res["depends_on"]:
                    visit(dep)
            order.append(key)

        for key in self._resources:
            visit(key)

        return order

    @property
    def resource_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._resources)

    @property
    def output_count(self) -> int:
        """Cikti sayisi."""
        return len(self._outputs)

    @property
    def condition_count(self) -> int:
        """Kosul sayisi."""
        return len(self._conditions)

    @property
    def variable_count(self) -> int:
        """Degisken sayisi."""
        return len(self._variables)
