"""ATLAS Veri Dogrulayici modulu.

Sema dogrulama, veri kalitesi,
null islemleri, aralik dogrulama
ve benzersizlik kontrolleri.
"""

import logging
from typing import Any

from app.models.pipeline import ValidationLevel

logger = logging.getLogger(__name__)


class DataValidator:
    """Veri dogrulayici.

    Verileri dogrular ve kalite
    kontrolu yapar.

    Attributes:
        _schemas: Sema tanimlari.
        _rules: Dogrulama kurallari.
        _results: Dogrulama sonuclari.
    """

    def __init__(
        self,
        level: ValidationLevel = ValidationLevel.MODERATE,
    ) -> None:
        """Veri dogrulayiciyi baslatir.

        Args:
            level: Dogrulama seviyesi.
        """
        self._schemas: dict[
            str, dict[str, Any]
        ] = {}
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._results: list[dict[str, Any]] = []
        self._level = level

        logger.info("DataValidator baslatildi")

    def add_schema(
        self,
        name: str,
        fields: dict[str, str],
        required: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sema ekler.

        Args:
            name: Sema adi.
            fields: Alan tanimlari (ad->tur).
            required: Zorunlu alanlar.

        Returns:
            Sema bilgisi.
        """
        schema = {
            "name": name,
            "fields": fields,
            "required": required or [],
        }
        self._schemas[name] = schema
        return schema

    def validate_schema(
        self,
        data: list[dict[str, Any]],
        schema_name: str,
    ) -> dict[str, Any]:
        """Sema dogrulama yapar.

        Args:
            data: Veri.
            schema_name: Sema adi.

        Returns:
            Dogrulama sonucu.
        """
        schema = self._schemas.get(schema_name)
        if not schema:
            return {
                "valid": False,
                "errors": ["schema_not_found"],
            }

        errors: list[str] = []
        required = schema["required"]
        fields = schema["fields"]

        for i, row in enumerate(data):
            for req in required:
                if req not in row:
                    errors.append(
                        f"row[{i}]: missing '{req}'",
                    )
            for field, expected_type in fields.items():
                if field in row:
                    val = row[field]
                    if not self._check_type(
                        val, expected_type,
                    ):
                        errors.append(
                            f"row[{i}]: '{field}' "
                            f"type mismatch",
                        )

        result = {
            "valid": len(errors) == 0,
            "schema": schema_name,
            "checked": len(data),
            "errors": errors,
        }
        self._results.append(result)
        return result

    def check_nulls(
        self,
        data: list[dict[str, Any]],
        fields: list[str],
    ) -> dict[str, Any]:
        """Null kontrol eder.

        Args:
            data: Veri.
            fields: Kontrol edilecek alanlar.

        Returns:
            Kontrol sonucu.
        """
        nulls: dict[str, int] = {f: 0 for f in fields}

        for row in data:
            for field in fields:
                if row.get(field) is None:
                    nulls[field] += 1

        total_nulls = sum(nulls.values())
        result = {
            "valid": total_nulls == 0,
            "null_counts": nulls,
            "total_nulls": total_nulls,
            "checked": len(data),
        }
        self._results.append(result)
        return result

    def check_range(
        self,
        data: list[dict[str, Any]],
        field: str,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> dict[str, Any]:
        """Aralik kontrol eder.

        Args:
            data: Veri.
            field: Alan.
            min_val: Minimum.
            max_val: Maksimum.

        Returns:
            Kontrol sonucu.
        """
        violations: list[dict[str, Any]] = []

        for i, row in enumerate(data):
            val = row.get(field)
            if val is None:
                continue
            if not isinstance(val, (int, float)):
                continue
            if min_val is not None and val < min_val:
                violations.append({
                    "row": i,
                    "value": val,
                    "reason": f"below_min({min_val})",
                })
            if max_val is not None and val > max_val:
                violations.append({
                    "row": i,
                    "value": val,
                    "reason": f"above_max({max_val})",
                })

        result = {
            "valid": len(violations) == 0,
            "field": field,
            "violations": violations,
            "checked": len(data),
        }
        self._results.append(result)
        return result

    def check_uniqueness(
        self,
        data: list[dict[str, Any]],
        field: str,
    ) -> dict[str, Any]:
        """Benzersizlik kontrol eder.

        Args:
            data: Veri.
            field: Alan.

        Returns:
            Kontrol sonucu.
        """
        seen: dict[Any, int] = {}
        duplicates: list[dict[str, Any]] = []

        for i, row in enumerate(data):
            val = row.get(field)
            if val is None:
                continue
            if val in seen:
                duplicates.append({
                    "row": i,
                    "value": val,
                    "first_seen": seen[val],
                })
            else:
                seen[val] = i

        result = {
            "valid": len(duplicates) == 0,
            "field": field,
            "duplicates": duplicates,
            "unique_count": len(seen),
            "checked": len(data),
        }
        self._results.append(result)
        return result

    def check_quality(
        self,
        data: list[dict[str, Any]],
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Genel kalite kontrolu.

        Args:
            data: Veri.
            fields: Kontrol edilecek alanlar.

        Returns:
            Kalite raporu.
        """
        if not data:
            return {
                "total_rows": 0,
                "completeness": 0.0,
                "score": 0.0,
            }

        check_fields = fields or list(
            data[0].keys(),
        )
        total_cells = len(data) * len(check_fields)
        filled = 0

        for row in data:
            for field in check_fields:
                val = row.get(field)
                if val is not None and val != "":
                    filled += 1

        completeness = round(
            filled / max(1, total_cells), 3,
        )

        result = {
            "total_rows": len(data),
            "total_fields": len(check_fields),
            "completeness": completeness,
            "score": completeness,
        }
        self._results.append(result)
        return result

    def add_rule(
        self,
        name: str,
        field: str,
        rule_type: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dogrulama kurali ekler.

        Args:
            name: Kural adi.
            field: Alan.
            rule_type: Kural turu.
            params: Parametreler.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "field": field,
            "type": rule_type,
            "params": params or {},
        }
        self._rules[name] = rule
        return rule

    def _check_type(
        self,
        value: Any,
        expected: str,
    ) -> bool:
        """Tur kontrol eder.

        Args:
            value: Deger.
            expected: Beklenen tur.

        Returns:
            Uygun ise True.
        """
        type_map = {
            "str": str,
            "int": int,
            "float": (int, float),
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        expected_type = type_map.get(expected)
        if not expected_type:
            return True
        return isinstance(value, expected_type)

    @property
    def schema_count(self) -> int:
        """Sema sayisi."""
        return len(self._schemas)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)

    @property
    def level(self) -> ValidationLevel:
        """Dogrulama seviyesi."""
        return self._level
