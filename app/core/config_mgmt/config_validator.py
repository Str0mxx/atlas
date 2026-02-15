"""ATLAS Konfigurasyon Dogrulayici modulu.

Sema dogrulama, tip kontrolu,
aralik dogrulama, bagimlilk
dogrulama ve ozel kurallar.
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Konfigurasyon dogrulayici.

    Konfigurasyon degerlerini dogrular.

    Attributes:
        _schemas: Sema tanimlari.
        _rules: Ozel kurallar.
    """

    def __init__(self) -> None:
        """Konfigurasyon dogrulayiciyi baslatir."""
        self._schemas: dict[
            str, dict[str, Any]
        ] = {}
        self._rules: dict[
            str, Callable[..., bool]
        ] = {}
        self._results: list[
            dict[str, Any]
        ] = []

        logger.info(
            "ConfigValidator baslatildi",
        )

    def define_schema(
        self,
        name: str,
        fields: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Sema tanimlar.

        Args:
            name: Sema adi.
            fields: Alan tanimlari.

        Returns:
            Tanim bilgisi.
        """
        self._schemas[name] = {
            "name": name,
            "fields": fields,
        }
        return {"name": name, "fields": len(fields)}

    def validate(
        self,
        data: dict[str, Any],
        schema_name: str,
    ) -> dict[str, Any]:
        """Dogrular.

        Args:
            data: Dogrulanacak veri.
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

        errors = []
        fields = schema["fields"]

        for field_name, field_def in fields.items():
            value = data.get(field_name)

            # Zorunlu alan kontrolu
            if field_def.get("required", False):
                if value is None:
                    errors.append(
                        f"{field_name}: required",
                    )
                    continue

            if value is None:
                continue

            # Tip kontrolu
            expected_type = field_def.get("type")
            if expected_type:
                if not self._check_type(
                    value, expected_type,
                ):
                    errors.append(
                        f"{field_name}: expected "
                        f"{expected_type}",
                    )
                    continue

            # Aralik kontrolu
            min_val = field_def.get("min")
            max_val = field_def.get("max")
            if min_val is not None and value < min_val:
                errors.append(
                    f"{field_name}: min {min_val}",
                )
            if max_val is not None and value > max_val:
                errors.append(
                    f"{field_name}: max {max_val}",
                )

            # Enum kontrolu
            allowed = field_def.get("enum")
            if allowed and value not in allowed:
                errors.append(
                    f"{field_name}: not in "
                    f"{allowed}",
                )

        # Ozel kurallar
        for rule_name, rule_fn in self._rules.items():
            try:
                if not rule_fn(data):
                    errors.append(
                        f"rule:{rule_name}",
                    )
            except Exception as e:
                errors.append(
                    f"rule:{rule_name}: {e}",
                )

        result = {
            "schema": schema_name,
            "valid": len(errors) == 0,
            "errors": errors,
            "fields_checked": len(fields),
        }
        self._results.append(result)
        return result

    def validate_type(
        self,
        value: Any,
        expected: str,
    ) -> bool:
        """Tip dogrular.

        Args:
            value: Deger.
            expected: Beklenen tip.

        Returns:
            Gecerli mi.
        """
        return self._check_type(value, expected)

    def _check_type(
        self,
        value: Any,
        expected: str,
    ) -> bool:
        """Tip kontrol eder.

        Args:
            value: Deger.
            expected: Beklenen tip.

        Returns:
            Uygun mu.
        """
        type_map = {
            "str": str,
            "string": str,
            "int": int,
            "integer": int,
            "float": float,
            "number": (int, float),
            "bool": bool,
            "boolean": bool,
            "list": list,
            "array": list,
            "dict": dict,
            "object": dict,
        }
        expected_type = type_map.get(
            expected.lower(),
        )
        if expected_type is None:
            return True
        return isinstance(value, expected_type)

    def validate_dependencies(
        self,
        data: dict[str, Any],
        dependencies: dict[str, list[str]],
    ) -> dict[str, Any]:
        """Bagimliliklari dogrular.

        Args:
            data: Konfigurasyon.
            dependencies: Bagimlilik haritasi.

        Returns:
            Dogrulama sonucu.
        """
        errors = []
        for key, deps in dependencies.items():
            if key in data:
                for dep in deps:
                    if dep not in data:
                        errors.append(
                            f"{key} requires {dep}",
                        )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def add_rule(
        self,
        name: str,
        rule: Callable[..., bool],
    ) -> None:
        """Ozel kural ekler.

        Args:
            name: Kural adi.
            rule: Kural fonksiyonu.
        """
        self._rules[name] = rule

    def remove_rule(
        self,
        name: str,
    ) -> bool:
        """Kural kaldirir.

        Args:
            name: Kural adi.

        Returns:
            Basarili mi.
        """
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    @property
    def schema_count(self) -> int:
        """Sema sayisi."""
        return len(self._schemas)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def validation_count(self) -> int:
        """Dogrulama sayisi."""
        return len(self._results)
