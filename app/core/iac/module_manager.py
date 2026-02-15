"""ATLAS IaC Modul Yoneticisi modulu.

Tekrar kullanilabilir moduller,
modul kayit defteri, surumleme,
bagimliliklar ve dokumantasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ModuleManager:
    """IaC modul yoneticisi.

    Tekrar kullanilabilir modulleri yonetir.

    Attributes:
        _modules: Kayitli moduller.
        _instances: Modul ornekleri.
    """

    def __init__(self) -> None:
        """Yoneticiyi baslatir."""
        self._modules: dict[
            str, dict[str, Any]
        ] = {}
        self._instances: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "registered": 0,
            "instantiated": 0,
        }

        logger.info(
            "ModuleManager baslatildi",
        )

    def register(
        self,
        name: str,
        version: str = "1.0.0",
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        resources: dict[str, Any]
            | None = None,
        description: str = "",
        author: str = "",
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Modul kaydeder.

        Args:
            name: Modul adi.
            version: Surum.
            inputs: Giris parametreleri.
            outputs: Cikis parametreleri.
            resources: Kaynak tanimlari.
            description: Aciklama.
            author: Yazar.
            dependencies: Bagimliliklar.

        Returns:
            Kayit bilgisi.
        """
        key = f"{name}@{version}"
        self._modules[key] = {
            "name": name,
            "version": version,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "resources": resources or {},
            "description": description,
            "author": author,
            "dependencies": dependencies or [],
            "registered_at": time.time(),
        }

        self._stats["registered"] += 1

        return {
            "name": name,
            "version": version,
            "key": key,
        }

    def get(
        self,
        name: str,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        """Modul bilgisini getirir.

        Args:
            name: Modul adi.
            version: Surum (None ise son).

        Returns:
            Modul bilgisi veya None.
        """
        if version:
            key = f"{name}@{version}"
            return self._modules.get(key)

        # Son surumu bul
        latest = None
        for key, mod in self._modules.items():
            if mod["name"] == name:
                if (
                    latest is None
                    or mod["version"]
                    > latest["version"]
                ):
                    latest = mod
        return latest

    def unregister(
        self,
        name: str,
        version: str,
    ) -> bool:
        """Modul kaydini siler.

        Args:
            name: Modul adi.
            version: Surum.

        Returns:
            Basarili mi.
        """
        key = f"{name}@{version}"
        if key in self._modules:
            del self._modules[key]
            return True
        return False

    def instantiate(
        self,
        instance_id: str,
        module_name: str,
        module_version: str = "1.0.0",
        input_values: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Modul ornegi olusturur.

        Args:
            instance_id: Ornek ID.
            module_name: Modul adi.
            module_version: Modul surumu.
            input_values: Giris degerleri.

        Returns:
            Ornek bilgisi.
        """
        key = f"{module_name}@{module_version}"
        mod = self._modules.get(key)
        if not mod:
            return {"error": "module_not_found"}

        # Giris dogrulamasi
        resolved: dict[str, Any] = {}
        for inp_name, inp_def in mod[
            "inputs"
        ].items():
            if input_values and (
                inp_name in input_values
            ):
                resolved[inp_name] = (
                    input_values[inp_name]
                )
            elif "default" in inp_def:
                resolved[inp_name] = (
                    inp_def["default"]
                )
            else:
                resolved[inp_name] = None

        self._instances[instance_id] = {
            "module_key": key,
            "module_name": module_name,
            "module_version": module_version,
            "inputs": resolved,
            "outputs": dict(mod["outputs"]),
            "created_at": time.time(),
        }

        self._stats["instantiated"] += 1

        return {
            "instance_id": instance_id,
            "module": module_name,
            "version": module_version,
        }

    def get_instance(
        self,
        instance_id: str,
    ) -> dict[str, Any] | None:
        """Modul ornegini getirir.

        Args:
            instance_id: Ornek ID.

        Returns:
            Ornek bilgisi veya None.
        """
        return self._instances.get(
            instance_id,
        )

    def remove_instance(
        self,
        instance_id: str,
    ) -> bool:
        """Modul ornegini kaldirir.

        Args:
            instance_id: Ornek ID.

        Returns:
            Basarili mi.
        """
        if instance_id in self._instances:
            del self._instances[instance_id]
            return True
        return False

    def list_modules(
        self,
        name_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Modulleri listeler.

        Args:
            name_filter: Isim filtresi.

        Returns:
            Modul listesi.
        """
        modules = list(
            self._modules.values(),
        )
        if name_filter:
            modules = [
                m for m in modules
                if name_filter in m["name"]
            ]
        return modules

    def list_versions(
        self,
        name: str,
    ) -> list[str]:
        """Modul surumlerini listeler.

        Args:
            name: Modul adi.

        Returns:
            Surum listesi.
        """
        versions = []
        for mod in self._modules.values():
            if mod["name"] == name:
                versions.append(mod["version"])
        return sorted(versions)

    def get_dependencies(
        self,
        name: str,
        version: str,
    ) -> list[str]:
        """Modul bagimliklarini getirir.

        Args:
            name: Modul adi.
            version: Surum.

        Returns:
            Bagimlilik listesi.
        """
        key = f"{name}@{version}"
        mod = self._modules.get(key)
        if not mod:
            return []
        return list(mod["dependencies"])

    def validate_inputs(
        self,
        name: str,
        version: str,
        input_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Giris degerlerini dogrular.

        Args:
            name: Modul adi.
            version: Surum.
            input_values: Giris degerleri.

        Returns:
            Dogrulama sonucu.
        """
        key = f"{name}@{version}"
        mod = self._modules.get(key)
        if not mod:
            return {"valid": False, "error": "not_found"}

        missing: list[str] = []
        for inp_name, inp_def in mod[
            "inputs"
        ].items():
            if inp_name not in input_values:
                if "default" not in inp_def:
                    missing.append(inp_name)

        return {
            "valid": len(missing) == 0,
            "missing": missing,
        }

    @property
    def module_count(self) -> int:
        """Modul sayisi."""
        return len(self._modules)

    @property
    def instance_count(self) -> int:
        """Ornek sayisi."""
        return len(self._instances)

    @property
    def registered_count(self) -> int:
        """Kaydedilen toplam."""
        return self._stats["registered"]

    @property
    def instantiated_count(self) -> int:
        """Orneklenen toplam."""
        return self._stats["instantiated"]
