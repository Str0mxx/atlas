"""ATLAS Konfigurasyon Yukleyici modulu.

Dosya yukleme (YAML, JSON, TOML),
ortam degiskenleri, uzak konfigler,
birlestirme stratejileri ve dogrulama.
"""

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Konfigurasyon yukleyici.

    Cesitli kaynaklardan konfigurasyon yukler.

    Attributes:
        _sources: Kaynak tanimlari.
        _loaded: Yuklenen konfigler.
    """

    def __init__(self) -> None:
        """Konfigurasyon yukleyiciyi baslatir."""
        self._sources: list[
            dict[str, Any]
        ] = []
        self._loaded: dict[
            str, dict[str, Any]
        ] = {}
        self._env_prefix: str = ""

        logger.info("ConfigLoader baslatildi")

    def load_json(
        self,
        content: str,
        source_name: str = "json",
    ) -> dict[str, Any]:
        """JSON yukler.

        Args:
            content: JSON icerigi.
            source_name: Kaynak adi.

        Returns:
            Yuklenen konfigurasyon.
        """
        try:
            data = json.loads(content)
            self._loaded[source_name] = data
            self._sources.append({
                "name": source_name,
                "format": "json",
                "loaded_at": time.time(),
            })
            return data
        except json.JSONDecodeError as e:
            return {"error": str(e)}

    def load_yaml(
        self,
        content: str,
        source_name: str = "yaml",
    ) -> dict[str, Any]:
        """YAML yukler (basit parser).

        Args:
            content: YAML icerigi.
            source_name: Kaynak adi.

        Returns:
            Yuklenen konfigurasyon.
        """
        data: dict[str, Any] = {}
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if val.isdigit():
                    data[key] = int(val)
                elif val.lower() in (
                    "true", "false",
                ):
                    data[key] = val.lower() == "true"
                else:
                    data[key] = val

        self._loaded[source_name] = data
        self._sources.append({
            "name": source_name,
            "format": "yaml",
            "loaded_at": time.time(),
        })
        return data

    def load_env(
        self,
        env_vars: dict[str, str],
        prefix: str = "",
    ) -> dict[str, Any]:
        """Ortam degiskenlerinden yukler.

        Args:
            env_vars: Ortam degiskenleri.
            prefix: Onek filtresi.

        Returns:
            Yuklenen konfigurasyon.
        """
        self._env_prefix = prefix
        data: dict[str, Any] = {}

        for key, value in env_vars.items():
            if prefix and not key.startswith(
                prefix,
            ):
                continue
            clean_key = key
            if prefix:
                clean_key = key[len(prefix):]
                if clean_key.startswith("_"):
                    clean_key = clean_key[1:]
            clean_key = clean_key.lower()
            data[clean_key] = value

        self._loaded["env"] = data
        self._sources.append({
            "name": "env",
            "format": "env",
            "prefix": prefix,
            "loaded_at": time.time(),
        })
        return data

    def load_dict(
        self,
        data: dict[str, Any],
        source_name: str = "dict",
    ) -> dict[str, Any]:
        """Sozlukten yukler.

        Args:
            data: Konfigurasyon sozlugu.
            source_name: Kaynak adi.

        Returns:
            Yuklenen konfigurasyon.
        """
        self._loaded[source_name] = dict(data)
        self._sources.append({
            "name": source_name,
            "format": "dict",
            "loaded_at": time.time(),
        })
        return data

    def merge(
        self,
        strategy: str = "override",
    ) -> dict[str, Any]:
        """Kaynaklari birlestirir.

        Args:
            strategy: Birlestirme stratejisi.

        Returns:
            Birlesmis konfigurasyon.
        """
        if not self._loaded:
            return {}

        sources = list(self._loaded.values())
        if strategy == "override":
            result: dict[str, Any] = {}
            for src in sources:
                result.update(src)
            return result
        elif strategy == "first_wins":
            result = {}
            for src in sources:
                for k, v in src.items():
                    if k not in result:
                        result[k] = v
            return result
        elif strategy == "deep_merge":
            result = {}
            for src in sources:
                self._deep_merge(result, src)
            return result
        else:
            return sources[-1] if sources else {}

    def _deep_merge(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> None:
        """Derin birlestirme.

        Args:
            base: Temel sozluk.
            override: Uzerine yazilacak.
        """
        for key, value in override.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(
                    base[key], value,
                )
            else:
                base[key] = value

    def get_source(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Kaynak konfigurasyon getirir.

        Args:
            name: Kaynak adi.

        Returns:
            Konfigurasyon veya None.
        """
        return self._loaded.get(name)

    def clear(self) -> int:
        """Yuklenen konfigurlari temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._loaded)
        self._loaded.clear()
        self._sources.clear()
        return count

    @property
    def source_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._sources)

    @property
    def loaded_count(self) -> int:
        """Yuklenen konfigurasyon sayisi."""
        return len(self._loaded)
