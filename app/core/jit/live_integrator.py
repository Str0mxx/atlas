"""ATLAS Canli Entegrasyon modulu.

Hot-load yeni kod, MasterAgent kaydi, yonlendirme
guncelleme, restart gerektirmez ve hata durumunda rollback.
"""

import logging
import time
from typing import Any

from app.models.jit import CapabilityStatus, GeneratedCode

logger = logging.getLogger(__name__)


class LiveIntegrator:
    """Canli entegrasyon sistemi.

    Yeni uretilen kodu canli sisteme entegre eder,
    hata durumunda geri alir.

    Attributes:
        _loaded: Yuklenen moduller.
        _routing: Yonlendirme tablosu.
        _rollback_stack: Geri alma yigini.
        _master_registry: MasterAgent kayitlari.
    """

    def __init__(self) -> None:
        """Canli entegrasyon sistemini baslatir."""
        self._loaded: dict[str, dict[str, Any]] = {}
        self._routing: dict[str, str] = {}
        self._rollback_stack: list[dict[str, Any]] = []
        self._master_registry: dict[str, dict[str, Any]] = {}

        logger.info("LiveIntegrator baslatildi")

    def hot_load(self, code: GeneratedCode) -> bool:
        """Kodu canli olarak yukler.

        Args:
            code: Yuklenecek kod.

        Returns:
            Basarili mi.
        """
        module_name = code.module_name

        # Geri alma bilgisi kaydet
        if module_name in self._loaded:
            self._rollback_stack.append({
                "action": "update",
                "module": module_name,
                "previous": self._loaded[module_name].copy(),
                "timestamp": time.time(),
            })
        else:
            self._rollback_stack.append({
                "action": "add",
                "module": module_name,
                "timestamp": time.time(),
            })

        self._loaded[module_name] = {
            "code_type": code.code_type,
            "line_count": code.line_count,
            "dependencies": code.dependencies,
            "status": CapabilityStatus.ACTIVE.value,
            "loaded_at": time.time(),
        }

        logger.info("Modul yuklendi: %s (%s)", module_name, code.code_type)
        return True

    def register_with_master(self, capability_name: str, handler_info: dict[str, Any]) -> bool:
        """MasterAgent'a kaydeder.

        Args:
            capability_name: Yetenek adi.
            handler_info: Handler bilgisi.

        Returns:
            Basarili mi.
        """
        self._master_registry[capability_name] = {
            **handler_info,
            "registered_at": time.time(),
            "active": True,
        }
        logger.info("MasterAgent'a kaydedildi: %s", capability_name)
        return True

    def update_routing(self, capability_name: str, route: str) -> bool:
        """Yonlendirme tablosunu gunceller.

        Args:
            capability_name: Yetenek adi.
            route: Yonlendirme hedefi.

        Returns:
            Basarili mi.
        """
        old_route = self._routing.get(capability_name)
        if old_route:
            self._rollback_stack.append({
                "action": "route_update",
                "capability": capability_name,
                "previous_route": old_route,
                "timestamp": time.time(),
            })

        self._routing[capability_name] = route
        logger.info("Yonlendirme guncellendi: %s -> %s", capability_name, route)
        return True

    def rollback(self, steps: int = 1) -> int:
        """Son islemleri geri alir.

        Args:
            steps: Geri alinacak adim sayisi.

        Returns:
            Geri alinan adim sayisi.
        """
        rolled_back = 0

        for _ in range(steps):
            if not self._rollback_stack:
                break

            entry = self._rollback_stack.pop()
            action = entry["action"]

            if action == "add":
                # Eklenen modulu kaldir
                module = entry["module"]
                self._loaded.pop(module, None)
                rolled_back += 1

            elif action == "update":
                # Onceki versiyona dondur
                module = entry["module"]
                self._loaded[module] = entry["previous"]
                rolled_back += 1

            elif action == "route_update":
                # Onceki yonlendirmeye dondur
                cap = entry["capability"]
                self._routing[cap] = entry["previous_route"]
                rolled_back += 1

            logger.info("Geri alma: %s", action)

        logger.info("Toplam %d adim geri alindi", rolled_back)
        return rolled_back

    def rollback_capability(self, capability_name: str) -> bool:
        """Belirli bir yetenegi geri alir.

        Args:
            capability_name: Yetenek adi.

        Returns:
            Basarili mi.
        """
        removed = False

        # Yuklenen modulleri temizle
        modules_to_remove = [
            name for name in self._loaded
            if capability_name in name
        ]
        for module in modules_to_remove:
            del self._loaded[module]
            removed = True

        # Yonlendirmeyi kaldir
        if capability_name in self._routing:
            del self._routing[capability_name]
            removed = True

        # Master kayitni kaldir
        if capability_name in self._master_registry:
            self._master_registry[capability_name]["active"] = False
            removed = True

        if removed:
            logger.info("Yetenek geri alindi: %s", capability_name)

        return removed

    def get_status(self, module_name: str) -> dict[str, Any]:
        """Modul durumunu getirir.

        Args:
            module_name: Modul adi.

        Returns:
            Durum bilgisi.
        """
        if module_name in self._loaded:
            return self._loaded[module_name]
        return {"status": "not_loaded"}

    def is_loaded(self, module_name: str) -> bool:
        """Modulun yuklu olup olmadigini kontrol eder."""
        return module_name in self._loaded

    @property
    def loaded_count(self) -> int:
        """Yuklu modul sayisi."""
        return len(self._loaded)

    @property
    def routing_table(self) -> dict[str, str]:
        """Yonlendirme tablosu."""
        return dict(self._routing)

    @property
    def rollback_depth(self) -> int:
        """Geri alma yigin derinligi."""
        return len(self._rollback_stack)

    @property
    def registered_capabilities(self) -> list[str]:
        """Kayitli yetenek listesi."""
        return [name for name, info in self._master_registry.items() if info.get("active", False)]
