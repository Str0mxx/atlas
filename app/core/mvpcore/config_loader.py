"""
Yapilandirma yukleyici modulu.

Yapilandirma yukleme, ortam degiskenleri,
varsayilan degerler, dogrulama,
birlestirme stratejileri.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CoreConfigLoader:
    """Cekirdek yapilandirma yukleyici.

    Attributes:
        _configs: Yuklu yapilandirmalar.
        _defaults: Varsayilan degerler.
        _env_prefix: Ortam degiskeni oneki.
        _stats: Istatistikler.
    """

    MERGE_STRATEGIES: list[str] = [
        "override",
        "merge_deep",
        "merge_shallow",
        "keep_existing",
    ]

    def __init__(
        self,
        env_prefix: str = "ATLAS_",
        auto_load_env: bool = True,
    ) -> None:
        """Yukleyiciyi baslatir.

        Args:
            env_prefix: Ortam degiskeni oneki.
            auto_load_env: Otomatik env yukle.
        """
        self._env_prefix = env_prefix
        self._configs: dict[
            str, Any
        ] = {}
        self._defaults: dict[
            str, Any
        ] = {}
        self._sources: list[dict] = []
        self._validators: dict[
            str, list
        ] = {}
        self._stats: dict[str, int] = {
            "configs_loaded": 0,
            "env_vars_loaded": 0,
            "validations_passed": 0,
            "validations_failed": 0,
            "merges_performed": 0,
        }

        if auto_load_env:
            self._load_env_vars()

        logger.info(
            "CoreConfigLoader baslatildi"
        )

    @property
    def config_count(self) -> int:
        """Yapilandirma sayisi."""
        return len(self._configs)

    def set_default(
        self,
        key: str = "",
        value: Any = None,
    ) -> dict[str, Any]:
        """Varsayilan deger ayarlar.

        Args:
            key: Anahtar.
            value: Deger.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            self._defaults[key] = value
            # Mevcut yoksa varsayilani kullan
            if key not in self._configs:
                self._configs[key] = value

            return {
                "key": key,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def set_defaults(
        self,
        defaults: dict | None = None,
    ) -> dict[str, Any]:
        """Toplu varsayilan ayarlar.

        Args:
            defaults: Varsayilan sozlugu.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            defaults = defaults or {}
            count = 0
            for k, v in defaults.items():
                self.set_default(k, v)
                count += 1

            return {
                "count": count,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def get(
        self,
        key: str = "",
        default: Any = None,
    ) -> Any:
        """Yapilandirma degeri getirir.

        Args:
            key: Anahtar.
            default: Varsayilan deger.

        Returns:
            Yapilandirma degeri.
        """
        return self._configs.get(
            key,
            self._defaults.get(
                key, default
            ),
        )

    def set(
        self,
        key: str = "",
        value: Any = None,
        source: str = "manual",
    ) -> dict[str, Any]:
        """Yapilandirma degeri ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
            source: Kaynak.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            # Dogrulama
            valid = self._validate_key(
                key, value
            )
            if not valid["valid"]:
                self._stats[
                    "validations_failed"
                ] += 1
                return {
                    "set": False,
                    "error": valid.get(
                        "error"
                    ),
                }

            self._configs[key] = value
            self._stats[
                "configs_loaded"
            ] += 1
            self._stats[
                "validations_passed"
            ] += 1

            return {
                "key": key,
                "source": source,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def load_dict(
        self,
        data: dict | None = None,
        source: str = "dict",
        strategy: str = "override",
    ) -> dict[str, Any]:
        """Sozlukten yukler.

        Args:
            data: Yapilandirma sozlugu.
            source: Kaynak adi.
            strategy: Birlestirme stratejisi.

        Returns:
            Yukleme bilgisi.
        """
        try:
            data = data or {}
            loaded = 0

            if strategy == "override":
                for k, v in data.items():
                    self._configs[k] = v
                    loaded += 1
            elif strategy == "merge_deep":
                self._merge_deep(
                    self._configs, data
                )
                loaded = len(data)
            elif strategy == (
                "merge_shallow"
            ):
                for k, v in data.items():
                    if isinstance(
                        v, dict
                    ) and isinstance(
                        self._configs.get(
                            k
                        ),
                        dict,
                    ):
                        self._configs[
                            k
                        ].update(v)
                    else:
                        self._configs[
                            k
                        ] = v
                    loaded += 1
            elif strategy == (
                "keep_existing"
            ):
                for k, v in data.items():
                    if (
                        k
                        not in self._configs
                    ):
                        self._configs[
                            k
                        ] = v
                        loaded += 1

            sid = (
                f"src_{uuid4()!s:.8}"
            )
            self._sources.append({
                "source_id": sid,
                "source": source,
                "strategy": strategy,
                "keys_loaded": loaded,
                "loaded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })

            self._stats[
                "configs_loaded"
            ] += loaded
            self._stats[
                "merges_performed"
            ] += 1

            return {
                "source_id": sid,
                "loaded": loaded,
                "strategy": strategy,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _load_env_vars(self) -> None:
        """Ortam degiskenlerini yukler."""
        try:
            prefix = self._env_prefix
            for key, value in (
                os.environ.items()
            ):
                if key.startswith(prefix):
                    config_key = (
                        key[len(prefix):]
                        .lower()
                    )
                    # Tip donusumu
                    converted = (
                        self._convert_env(
                            value
                        )
                    )
                    self._configs[
                        config_key
                    ] = converted
                    self._stats[
                        "env_vars_loaded"
                    ] += 1
        except Exception as e:
            logger.error(
                f"Env yukleme hatasi: {e}"
            )

    def _convert_env(
        self, value: str
    ) -> Any:
        """Ortam degiskeni degerini donusturur."""
        if value.lower() in (
            "true",
            "yes",
            "1",
        ):
            return True
        if value.lower() in (
            "false",
            "no",
            "0",
        ):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _merge_deep(
        self,
        base: dict,
        override: dict,
    ) -> None:
        """Derin birlestirme yapar."""
        for key, value in (
            override.items()
        ):
            if (
                key in base
                and isinstance(
                    base[key], dict
                )
                and isinstance(
                    value, dict
                )
            ):
                self._merge_deep(
                    base[key], value
                )
            else:
                base[key] = value

    def add_validator(
        self,
        key: str = "",
        validator: Any = None,
    ) -> dict[str, Any]:
        """Dogrulayici ekler.

        Args:
            key: Anahtar.
            validator: Dogrulama fonksiyonu.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._validators.setdefault(
                key, []
            )
            if validator:
                self._validators[
                    key
                ].append(validator)
            return {
                "key": key,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def _validate_key(
        self, key: str, value: Any
    ) -> dict[str, Any]:
        """Tek anahtar dogrular."""
        validators = (
            self._validators.get(key, [])
        )
        for v in validators:
            try:
                if not v(value):
                    return {
                        "valid": False,
                        "error": (
                            f"{key} dogrulama "
                            "basarisiz"
                        ),
                    }
            except Exception as e:
                return {
                    "valid": False,
                    "error": str(e),
                }
        return {"valid": True}

    def validate_all(
        self,
    ) -> dict[str, Any]:
        """Tum yapilanlari dogrular.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            errors: list[str] = []
            for key in self._validators:
                if key in self._configs:
                    r = self._validate_key(
                        key,
                        self._configs[key],
                    )
                    if not r["valid"]:
                        errors.append(
                            r.get(
                                "error", key
                            )
                        )

            return {
                "valid": (
                    len(errors) == 0
                ),
                "errors": errors,
                "checked": len(
                    self._validators
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "valid": False,
                "error": str(e),
            }

    def export_config(
        self,
    ) -> dict[str, Any]:
        """Tum yapilandirmayi disari aktarir.

        Returns:
            Yapilandirma kopyasi.
        """
        try:
            return {
                "config": dict(
                    self._configs
                ),
                "defaults": dict(
                    self._defaults
                ),
                "sources": list(
                    self._sources
                ),
                "exported": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "exported": False,
                "error": str(e),
            }

    def reset(
        self,
    ) -> dict[str, Any]:
        """Varsayilanlara sifirlar.

        Returns:
            Sifirlama bilgisi.
        """
        try:
            self._configs = dict(
                self._defaults
            )
            return {
                "reset": True,
                "config_count": len(
                    self._configs
                ),
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reset": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "config_count": len(
                    self._configs
                ),
                "default_count": len(
                    self._defaults
                ),
                "sources": len(
                    self._sources
                ),
                "validators": len(
                    self._validators
                ),
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
