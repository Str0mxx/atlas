"""
Validation Engine modulu.

Sema dogrulama, tip kontrolu,
aralik dogrulama, bagimlilik kontrolu,
hata mesajlari.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Konfig dogrulama motoru.

    Attributes:
        _schema: Dogrulama semasi.
        _rules: Ozel dogrulama kurallari.
        _results: Son dogrulama sonuclari.
        _stats: Istatistikler.
    """

    # Desteklenen tipler
    SUPPORTED_TYPES: set[str] = {
        "str", "int", "float", "bool", "list", "dict",
    }

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._schema: dict[str, dict] = {}
        self._rules: list[dict] = []
        self._results: list[dict] = []
        self._stats: dict[str, int] = {
            "validations_run": 0,
            "validations_passed": 0,
            "validations_failed": 0,
            "schemas_registered": 0,
            "rules_registered": 0,
        }
        logger.info("ValidationEngine baslatildi")

    @property
    def schema_count(self) -> int:
        """Kayitli sema alani sayisi."""
        return len(self._schema)

    @property
    def rule_count(self) -> int:
        """Kayitli kural sayisi."""
        return len(self._rules)

    def register_schema(
        self,
        key: str = "",
        schema: dict | None = None,
    ) -> dict[str, Any]:
        """Konfig anahtari icin sema kaydeder.

        Args:
            key: Konfig anahtari.
            schema: Sema tanimi (type, required, min, max, allowed, default).

        Returns:
            Kayit bilgisi.

        Sema alanlari:
            type: str | Beklenen tip ('str', 'int', 'float', 'bool', 'list', 'dict').
            required: bool | Zorunlu mu (varsayilan: False).
            min: int|float | Minimum deger (sayilar icin).
            max: int|float | Maximum deger (sayilar icin).
            min_length: int | Minimum uzunluk (str/list icin).
            max_length: int | Maximum uzunluk (str/list icin).
            allowed: list | Izin verilen degerler.
            pattern: str | Regex kalıbi (str icin).
            default: Any | Varsayilan deger.
        """
        try:
            if not key:
                return {"registered": False, "error": "anahtar_gerekli"}

            if schema is None:
                schema = {}

            # Tip kontrolu
            if "type" in schema and schema["type"] not in self.SUPPORTED_TYPES:
                return {
                    "registered": False,
                    "error": f"desteklenmeyen_tip: {schema['type']}",
                }

            self._schema[key] = dict(schema)
            self._stats["schemas_registered"] += 1
            return {
                "registered": True,
                "key": key,
                "total_schemas": len(self._schema),
            }
        except Exception as e:
            logger.error("Sema kayit hatasi: %s", e)
            return {"registered": False, "error": str(e)}

    def register_rule(
        self,
        name: str = "",
        description: str = "",
        keys: list[str] | None = None,
        rule_type: str = "dependency",
    ) -> dict[str, Any]:
        """Ozel kural kaydeder.

        Args:
            name: Kural adi.
            description: Kural aciklamasi.
            keys: Ilgili anahtarlar.
            rule_type: Kural tipi (dependency, conflict, required_if).

        Returns:
            Kayit bilgisi.
        """
        try:
            if not name:
                return {"registered": False, "error": "kural_adi_gerekli"}

            rule = {
                "name": name,
                "description": description,
                "keys": keys or [],
                "type": rule_type,
            }
            self._rules.append(rule)
            self._stats["rules_registered"] += 1
            return {
                "registered": True,
                "name": name,
                "type": rule_type,
                "total_rules": len(self._rules),
            }
        except Exception as e:
            logger.error("Kural kayit hatasi: %s", e)
            return {"registered": False, "error": str(e)}

    def validate_value(
        self,
        key: str = "",
        value: Any = None,
    ) -> dict[str, Any]:
        """Tek bir degeri dogrular.

        Args:
            key: Konfig anahtari.
            value: Dogrulanacak deger.

        Returns:
            Dogrulama sonucu.
        """
        try:
            self._stats["validations_run"] += 1

            if not key:
                return {"valid": False, "error": "anahtar_gerekli"}

            schema = self._schema.get(key, {})
            errors = []

            # Tip kontrolu
            if "type" in schema:
                type_error = self._check_type(key, value, schema["type"])
                if type_error:
                    errors.append(type_error)

            # Aralik kontrolu
            if errors == [] and isinstance(value, (int, float)):
                range_errors = self._check_range(key, value, schema)
                errors.extend(range_errors)

            # Uzunluk kontrolu
            if errors == [] and isinstance(value, (str, list)):
                len_errors = self._check_length(key, value, schema)
                errors.extend(len_errors)

            # Izin verilen degerler
            if "allowed" in schema and value not in schema["allowed"]:
                errors.append({
                    "key": key,
                    "error": "gecersiz_deger",
                    "message": (
                        f"'{value}' izin verilen degerler disinda. "
                        f"Izin verilenler: {schema['allowed']}"
                    ),
                })

            valid = len(errors) == 0
            if valid:
                self._stats["validations_passed"] += 1
            else:
                self._stats["validations_failed"] += 1

            return {
                "valid": valid,
                "key": key,
                "value": value,
                "errors": errors,
                "error_count": len(errors),
            }
        except Exception as e:
            logger.error("Deger dogrulama hatasi: %s", e)
            self._stats["validations_failed"] += 1
            return {"valid": False, "error": str(e)}

    def validate_config(
        self,
        config: dict | None = None,
    ) -> dict[str, Any]:
        """Tum konfigurasyonu dogrular.

        Args:
            config: Dogrulanacak konfig.

        Returns:
            Dogrulama sonucu.
        """
        try:
            self._stats["validations_run"] += 1

            if config is None:
                return {"valid": False, "error": "konfig_gerekli"}

            all_errors = []

            # Her sema anahtarini kontrol et
            for key, schema in self._schema.items():
                # Zorunlu alan kontrolu
                if schema.get("required") and key not in config:
                    all_errors.append({
                        "key": key,
                        "error": "zorunlu_alan_eksik",
                        "message": f"'{key}' zorunlu ama eksik.",
                    })
                    continue

                if key in config:
                    result = self.validate_value(key, config[key])
                    all_errors.extend(result.get("errors", []))

            # Bagimlilik kurallarini kontrol et
            dep_errors = self._check_dependencies(config)
            all_errors.extend(dep_errors)

            valid = len(all_errors) == 0
            if valid:
                self._stats["validations_passed"] += 1
            else:
                self._stats["validations_failed"] += 1

            self._results = all_errors
            return {
                "valid": valid,
                "errors": all_errors,
                "error_count": len(all_errors),
                "checked_keys": len(config),
                "schema_keys": len(self._schema),
            }
        except Exception as e:
            logger.error("Konfig dogrulama hatasi: %s", e)
            self._stats["validations_failed"] += 1
            return {"valid": False, "error": str(e)}

    def check_type(
        self,
        key: str = "",
        value: Any = None,
        expected_type: str = "",
    ) -> dict[str, Any]:
        """Tip kontrolu yapar.

        Args:
            key: Konfig anahtari.
            value: Kontrol edilecek deger.
            expected_type: Beklenen tip adi.

        Returns:
            Kontrol sonucu.
        """
        try:
            if not expected_type:
                return {"valid": False, "error": "tip_gerekli"}

            if expected_type not in self.SUPPORTED_TYPES:
                return {
                    "valid": False,
                    "error": f"desteklenmeyen_tip: {expected_type}",
                }

            error = self._check_type(key, value, expected_type)
            valid = error is None
            return {
                "valid": valid,
                "key": key,
                "value": value,
                "expected_type": expected_type,
                "actual_type": type(value).__name__,
                "error": error.get("message") if error else None,
            }
        except Exception as e:
            logger.error("Tip kontrol hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def check_range(
        self,
        key: str = "",
        value: Any = None,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> dict[str, Any]:
        """Aralik kontrolu yapar.

        Args:
            key: Konfig anahtari.
            value: Kontrol edilecek deger.
            min_val: Minimum deger.
            max_val: Maximum deger.

        Returns:
            Kontrol sonucu.
        """
        try:
            if not isinstance(value, (int, float)):
                return {
                    "valid": False,
                    "error": "sayi_olmayan_deger",
                    "key": key,
                }

            errors = []
            if min_val is not None and value < min_val:
                errors.append({
                    "key": key,
                    "error": "minimum_altinda",
                    "message": f"'{key}' ({value}) < minimum ({min_val})",
                })
            if max_val is not None and value > max_val:
                errors.append({
                    "key": key,
                    "error": "maximum_ustunde",
                    "message": f"'{key}' ({value}) > maksimum ({max_val})",
                })

            return {
                "valid": len(errors) == 0,
                "key": key,
                "value": value,
                "min": min_val,
                "max": max_val,
                "errors": errors,
            }
        except Exception as e:
            logger.error("Aralik kontrol hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def check_dependency(
        self,
        config: dict | None = None,
        if_key: str = "",
        if_value: Any = None,
        then_key: str = "",
    ) -> dict[str, Any]:
        """Bagimlilik kontrolu yapar.

        'if_key == if_value ise then_key zorunludur' kuralini kontrol eder.

        Args:
            config: Konfig.
            if_key: Kosul anahtari.
            if_value: Kosul degeri.
            then_key: Zorunlu anahtar.

        Returns:
            Kontrol sonucu.
        """
        try:
            if config is None:
                return {"valid": False, "error": "konfig_gerekli"}

            if not if_key or not then_key:
                return {"valid": False, "error": "anahtarlar_gerekli"}

            # Kosul saglanmiyor mu, kontrol gerekmez
            if config.get(if_key) != if_value:
                return {
                    "valid": True,
                    "condition_met": False,
                    "if_key": if_key,
                    "then_key": then_key,
                }

            # Kosul saglaniyorsa then_key zorunlu
            if then_key not in config or config[then_key] is None:
                return {
                    "valid": False,
                    "condition_met": True,
                    "if_key": if_key,
                    "then_key": then_key,
                    "message": (
                        f"'{if_key}' = '{if_value}' ise "
                        f"'{then_key}' zorunludur."
                    ),
                }

            return {
                "valid": True,
                "condition_met": True,
                "if_key": if_key,
                "then_key": then_key,
            }
        except Exception as e:
            logger.error("Bagimlilik kontrol hatasi: %s", e)
            return {"valid": False, "error": str(e)}

    def get_error_messages(
        self,
        errors: list[dict] | None = None,
        lang: str = "tr",
    ) -> dict[str, Any]:
        """Hata listesinden okunabilir mesajlar uretir.

        Args:
            errors: Hata listesi.
            lang: Dil kodu ('tr' veya 'en').

        Returns:
            Mesaj listesi.
        """
        try:
            if errors is None:
                errors = self._results

            messages = []
            for err in errors:
                msg = err.get("message") or err.get("error", "bilinmeyen_hata")
                if lang == "en":
                    msg = self._translate_error(msg)
                messages.append({
                    "key": err.get("key", ""),
                    "message": msg,
                    "severity": err.get("severity", "error"),
                })

            return {
                "retrieved": True,
                "messages": messages,
                "count": len(messages),
                "lang": lang,
            }
        except Exception as e:
            logger.error("Hata mesaji hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    def get_summary(self) -> dict[str, Any]:
        """Ozet bilgi dondurur.

        Returns:
            Ozet.
        """
        try:
            return {
                "retrieved": True,
                "schema_count": self.schema_count,
                "rule_count": self.rule_count,
                "last_error_count": len(self._results),
                "stats": dict(self._stats),
            }
        except Exception as e:
            logger.error("Ozet hatasi: %s", e)
            return {"retrieved": False, "error": str(e)}

    # ── Ozel yardimci metodlar ────────────────────────────────────────────────

    _TYPE_MAP: dict[str, type] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
    }

    def _check_type(
        self, key: str, value: Any, expected: str
    ) -> dict | None:
        """Tip uyumsuzlugunu dondurur, uyumluysa None."""
        python_type = self._TYPE_MAP.get(expected)
        if python_type is None:
            return None

        # bool int'in alt sinifidir; bool kontrolu once yapilmali
        if expected == "int" and isinstance(value, bool):
            return {
                "key": key,
                "error": "yanlis_tip",
                "message": (
                    f"'{key}' int bekleniyor ama bool alindi."
                ),
            }

        if not isinstance(value, python_type):
            return {
                "key": key,
                "error": "yanlis_tip",
                "message": (
                    f"'{key}' {expected} bekleniyor, "
                    f"{type(value).__name__} alindi."
                ),
            }
        return None

    def _check_range(
        self, key: str, value: float, schema: dict
    ) -> list[dict]:
        """Aralik hatalarini dondurur."""
        errors = []
        if "min" in schema and value < schema["min"]:
            errors.append({
                "key": key,
                "error": "minimum_altinda",
                "message": (
                    f"'{key}' ({value}) minimum degerin "
                    f"({schema['min']}) altinda."
                ),
            })
        if "max" in schema and value > schema["max"]:
            errors.append({
                "key": key,
                "error": "maximum_ustunde",
                "message": (
                    f"'{key}' ({value}) maksimum degerin "
                    f"({schema['max']}) ustunde."
                ),
            })
        return errors

    def _check_length(
        self, key: str, value: str | list, schema: dict
    ) -> list[dict]:
        """Uzunluk hatalarini dondurur."""
        errors = []
        length = len(value)
        if "min_length" in schema and length < schema["min_length"]:
            errors.append({
                "key": key,
                "error": "cok_kisa",
                "message": (
                    f"'{key}' uzunlugu ({length}) minimum "
                    f"uzunluktan ({schema['min_length']}) kisa."
                ),
            })
        if "max_length" in schema and length > schema["max_length"]:
            errors.append({
                "key": key,
                "error": "cok_uzun",
                "message": (
                    f"'{key}' uzunlugu ({length}) maksimum "
                    f"uzunluktan ({schema['max_length']}) uzun."
                ),
            })
        return errors

    def _check_dependencies(self, config: dict) -> list[dict]:
        """Kural bagimliliklerini kontrol eder."""
        errors = []
        for rule in self._rules:
            if rule.get("type") != "dependency":
                continue
            keys = rule.get("keys", [])
            if len(keys) < 2:
                continue
            # Ilk anahtar diger anahtarlara bagimli
            primary = keys[0]
            if config.get(primary):
                for dep_key in keys[1:]:
                    if dep_key not in config or not config[dep_key]:
                        errors.append({
                            "key": dep_key,
                            "error": "bagimlilik_hatasi",
                            "message": (
                                f"'{primary}' aktif oldugunda "
                                f"'{dep_key}' gereklidir."
                            ),
                            "rule": rule.get("name", ""),
                        })
        return errors

    def _translate_error(self, msg: str) -> str:
        """Turkce hata mesajlarini Ingilizce'ye cevirir (basit esleme)."""
        translations = {
            "zorunlu_alan_eksik": "required field missing",
            "yanlis_tip": "wrong type",
            "minimum_altinda": "below minimum",
            "maximum_ustunde": "above maximum",
            "cok_kisa": "too short",
            "cok_uzun": "too long",
            "gecersiz_deger": "invalid value",
            "bagimlilik_hatasi": "dependency error",
        }
        for tr_key, en_val in translations.items():
            msg = msg.replace(tr_key, en_val)
        return msg
