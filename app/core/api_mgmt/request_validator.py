"""ATLAS Istek Dogrulayici modulu.

Sema dogrulama, parametre dogrulama,
baslik dogrulama, govde dogrulama
ve ozel dogrulayicilar.
"""

import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RequestValidator:
    """Istek dogrulayici.

    Gelen istekleri dogrular
    ve hatalari raporlar.

    Attributes:
        _schemas: Sema tanimlari.
        _validators: Ozel dogrulayicilar.
    """

    def __init__(self) -> None:
        """Istek dogrulayiciyi baslatir."""
        self._schemas: dict[
            str, dict[str, Any]
        ] = {}
        self._validators: dict[
            str, Callable[[Any], bool]
        ] = {}
        self._header_rules: dict[
            str, list[str]
        ] = {}
        self._validations = 0
        self._failures = 0

        logger.info(
            "RequestValidator baslatildi",
        )

    def register_schema(
        self,
        endpoint: str,
        schema: dict[str, Any],
    ) -> None:
        """Sema kaydeder.

        Args:
            endpoint: Endpoint yolu.
            schema: Sema tanimi.
        """
        self._schemas[endpoint] = schema

    def validate_schema(
        self,
        endpoint: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Sema dogrular.

        Args:
            endpoint: Endpoint yolu.
            data: Veri.

        Returns:
            Dogrulama sonucu.
        """
        self._validations += 1
        schema = self._schemas.get(endpoint)

        if not schema:
            return {
                "valid": True,
                "message": "no_schema",
            }

        errors: list[str] = []

        # Zorunlu alan kontrolu
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(
                    f"missing_field:{field}",
                )

        # Tip kontrolu
        types = schema.get("types", {})
        for field, expected_type in types.items():
            if field in data:
                if expected_type == "string":
                    if not isinstance(
                        data[field], str,
                    ):
                        errors.append(
                            f"type_error:{field}",
                        )
                elif expected_type == "int":
                    if not isinstance(
                        data[field], int,
                    ):
                        errors.append(
                            f"type_error:{field}",
                        )
                elif expected_type == "float":
                    if not isinstance(
                        data[field], (int, float),
                    ):
                        errors.append(
                            f"type_error:{field}",
                        )

        if errors:
            self._failures += 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def validate_params(
        self,
        params: dict[str, Any],
        rules: dict[str, Any],
    ) -> dict[str, Any]:
        """Parametre dogrular.

        Args:
            params: Parametreler.
            rules: Kurallar.

        Returns:
            Dogrulama sonucu.
        """
        self._validations += 1
        errors: list[str] = []

        for name, rule in rules.items():
            if rule.get("required") and name not in params:
                errors.append(
                    f"missing_param:{name}",
                )
                continue

            if name in params:
                val = params[name]
                # Min-max kontrolu
                if "min" in rule:
                    try:
                        if float(val) < rule["min"]:
                            errors.append(
                                f"below_min:{name}",
                            )
                    except (ValueError, TypeError):
                        pass
                if "max" in rule:
                    try:
                        if float(val) > rule["max"]:
                            errors.append(
                                f"above_max:{name}",
                            )
                    except (ValueError, TypeError):
                        pass
                # Pattern kontrolu
                if "pattern" in rule:
                    if not re.match(
                        rule["pattern"],
                        str(val),
                    ):
                        errors.append(
                            f"pattern_mismatch:{name}",
                        )

        if errors:
            self._failures += 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def validate_headers(
        self,
        headers: dict[str, str],
        endpoint: str = "",
    ) -> dict[str, Any]:
        """Baslik dogrular.

        Args:
            headers: Basliklar.
            endpoint: Endpoint yolu.

        Returns:
            Dogrulama sonucu.
        """
        self._validations += 1
        errors: list[str] = []

        required_headers = self._header_rules.get(
            endpoint, [],
        )
        for header in required_headers:
            if header.lower() not in {
                h.lower() for h in headers
            }:
                errors.append(
                    f"missing_header:{header}",
                )

        if errors:
            self._failures += 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def set_required_headers(
        self,
        endpoint: str,
        headers: list[str],
    ) -> None:
        """Zorunlu basliklari ayarlar.

        Args:
            endpoint: Endpoint yolu.
            headers: Baslik listesi.
        """
        self._header_rules[endpoint] = headers

    def validate_body(
        self,
        body: Any,
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        """Govde dogrular.

        Args:
            body: Istek govdesi.
            content_type: Icerik tipi.

        Returns:
            Dogrulama sonucu.
        """
        self._validations += 1
        errors: list[str] = []

        if content_type == "application/json":
            if not isinstance(
                body, (dict, list),
            ):
                errors.append("invalid_json_body")
        elif body is None:
            errors.append("empty_body")

        if errors:
            self._failures += 1

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "content_type": content_type,
        }

    def register_validator(
        self,
        name: str,
        validator: Callable[[Any], bool],
    ) -> None:
        """Ozel dogrulayici kaydeder.

        Args:
            name: Dogrulayici adi.
            validator: Dogrulama fonksiyonu.
        """
        self._validators[name] = validator

    def run_custom(
        self,
        name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Ozel dogrulayici calistirir.

        Args:
            name: Dogrulayici adi.
            value: Deger.

        Returns:
            Dogrulama sonucu.
        """
        self._validations += 1
        fn = self._validators.get(name)
        if not fn:
            return {
                "valid": False,
                "error": "validator_not_found",
            }

        try:
            result = fn(value)
            if not result:
                self._failures += 1
            return {"valid": result}
        except Exception as e:
            self._failures += 1
            return {
                "valid": False,
                "error": str(e),
            }

    @property
    def schema_count(self) -> int:
        """Sema sayisi."""
        return len(self._schemas)

    @property
    def validator_count(self) -> int:
        """Dogrulayici sayisi."""
        return len(self._validators)

    @property
    def validation_count(self) -> int:
        """Dogrulama sayisi."""
        return self._validations

    @property
    def failure_count(self) -> int:
        """Basarisiz dogrulama sayisi."""
        return self._failures
