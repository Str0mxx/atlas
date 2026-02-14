"""ATLAS Veri Donusturucu modulu.

Sema esleme, veri temizleme, tur
donusumu, gruplama ve zenginlestirme.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataTransformer:
    """Veri donusturucu.

    Verileri donusturur, temizler
    ve zenginlestirir.

    Attributes:
        _mappings: Sema eslemeleri.
        _transforms: Donusum gecmisi.
        _cleaners: Temizleme kurallari.
    """

    def __init__(self) -> None:
        """Veri donusturucuyu baslatir."""
        self._mappings: dict[
            str, dict[str, str]
        ] = {}
        self._transforms: list[dict[str, Any]] = []
        self._cleaners: dict[
            str, dict[str, Any]
        ] = {}
        self._enrichments: dict[
            str, dict[str, Any]
        ] = {}

        logger.info("DataTransformer baslatildi")

    def add_mapping(
        self,
        name: str,
        field_map: dict[str, str],
    ) -> dict[str, Any]:
        """Sema esleme ekler.

        Args:
            name: Esleme adi.
            field_map: Alan esleme (kaynak->hedef).

        Returns:
            Esleme bilgisi.
        """
        self._mappings[name] = field_map
        return {
            "name": name,
            "fields": len(field_map),
            "mapping": field_map,
        }

    def apply_mapping(
        self,
        data: list[dict[str, Any]],
        mapping_name: str,
    ) -> list[dict[str, Any]]:
        """Sema esleme uygular.

        Args:
            data: Veri.
            mapping_name: Esleme adi.

        Returns:
            Eslenmis veri.
        """
        mapping = self._mappings.get(mapping_name)
        if not mapping:
            return data

        result: list[dict[str, Any]] = []
        for row in data:
            new_row: dict[str, Any] = {}
            for src, dst in mapping.items():
                if src in row:
                    new_row[dst] = row[src]
            result.append(new_row)

        self._transforms.append({
            "type": "mapping",
            "name": mapping_name,
            "input_count": len(data),
            "output_count": len(result),
        })
        return result

    def clean(
        self,
        data: list[dict[str, Any]],
        rules: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Veri temizler.

        Args:
            data: Veri.
            rules: Temizleme kurallari.

        Returns:
            Temizlenmis veri.
        """
        rules = rules or {}
        result: list[dict[str, Any]] = []

        strip_whitespace = rules.get(
            "strip_whitespace", True,
        )
        remove_nulls = rules.get(
            "remove_nulls", False,
        )
        lowercase_keys = rules.get(
            "lowercase_keys", False,
        )

        for row in data:
            new_row: dict[str, Any] = {}
            for key, val in row.items():
                k = key.lower() if lowercase_keys else key
                if remove_nulls and val is None:
                    continue
                if (
                    strip_whitespace
                    and isinstance(val, str)
                ):
                    val = val.strip()
                new_row[k] = val
            result.append(new_row)

        self._transforms.append({
            "type": "clean",
            "input_count": len(data),
            "output_count": len(result),
            "rules": list(rules.keys()),
        })
        return result

    def convert_types(
        self,
        data: list[dict[str, Any]],
        type_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Tur donusumu uygular.

        Args:
            data: Veri.
            type_map: Alan->tur esleme.

        Returns:
            Donusturulmus veri.
        """
        converters = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
        }

        result: list[dict[str, Any]] = []
        for row in data:
            new_row = dict(row)
            for field, target_type in type_map.items():
                if field in new_row:
                    converter = converters.get(
                        target_type,
                    )
                    if converter:
                        try:
                            new_row[field] = converter(
                                new_row[field],
                            )
                        except (ValueError, TypeError):
                            pass
            result.append(new_row)

        self._transforms.append({
            "type": "convert_types",
            "input_count": len(data),
            "output_count": len(result),
        })
        return result

    def aggregate(
        self,
        data: list[dict[str, Any]],
        group_by: str,
        agg_field: str,
        agg_func: str = "sum",
    ) -> list[dict[str, Any]]:
        """Veri gruplar.

        Args:
            data: Veri.
            group_by: Gruplama alani.
            agg_field: Gruplama degeri.
            agg_func: Fonksiyon (sum, count, avg,
                min, max).

        Returns:
            Gruplanmis veri.
        """
        groups: dict[str, list[Any]] = {}
        for row in data:
            key = str(row.get(group_by, ""))
            if key not in groups:
                groups[key] = []
            val = row.get(agg_field, 0)
            if isinstance(val, (int, float)):
                groups[key].append(val)

        result: list[dict[str, Any]] = []
        for key, values in groups.items():
            agg_val: float = 0.0
            if values:
                if agg_func == "sum":
                    agg_val = sum(values)
                elif agg_func == "count":
                    agg_val = float(len(values))
                elif agg_func == "avg":
                    agg_val = sum(values) / len(values)
                elif agg_func == "min":
                    agg_val = float(min(values))
                elif agg_func == "max":
                    agg_val = float(max(values))

            result.append({
                group_by: key,
                f"{agg_func}_{agg_field}": agg_val,
            })

        self._transforms.append({
            "type": "aggregate",
            "group_by": group_by,
            "agg_func": agg_func,
            "input_count": len(data),
            "output_count": len(result),
        })
        return result

    def enrich(
        self,
        data: list[dict[str, Any]],
        enrichment_name: str,
    ) -> list[dict[str, Any]]:
        """Veri zenginlestirir.

        Args:
            data: Veri.
            enrichment_name: Zenginlestirme adi.

        Returns:
            Zenginlestirilmis veri.
        """
        enrichment = self._enrichments.get(
            enrichment_name,
        )
        if not enrichment:
            return data

        defaults = enrichment.get("defaults", {})
        result: list[dict[str, Any]] = []
        for row in data:
            new_row = dict(row)
            for key, val in defaults.items():
                if key not in new_row:
                    new_row[key] = val
            result.append(new_row)

        self._transforms.append({
            "type": "enrich",
            "name": enrichment_name,
            "input_count": len(data),
            "output_count": len(result),
        })
        return result

    def add_enrichment(
        self,
        name: str,
        defaults: dict[str, Any],
    ) -> dict[str, Any]:
        """Zenginlestirme kaydeder.

        Args:
            name: Zenginlestirme adi.
            defaults: Varsayilan degerler.

        Returns:
            Zenginlestirme bilgisi.
        """
        entry = {
            "name": name,
            "defaults": defaults,
        }
        self._enrichments[name] = entry
        return entry

    def add_cleaner(
        self,
        name: str,
        rules: dict[str, Any],
    ) -> dict[str, Any]:
        """Temizleme kurali ekler.

        Args:
            name: Kural adi.
            rules: Kurallar.

        Returns:
            Kural bilgisi.
        """
        self._cleaners[name] = {
            "name": name,
            "rules": rules,
        }
        return self._cleaners[name]

    @property
    def mapping_count(self) -> int:
        """Esleme sayisi."""
        return len(self._mappings)

    @property
    def transform_count(self) -> int:
        """Donusum sayisi."""
        return len(self._transforms)

    @property
    def enrichment_count(self) -> int:
        """Zenginlestirme sayisi."""
        return len(self._enrichments)
