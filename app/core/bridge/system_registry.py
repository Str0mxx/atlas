"""ATLAS Sistem Kaydi modulu.

Tum 38 sistemin kaydi, yetenek haritalama,
bagimlilik grafi, saglik durumu ve versiyon takibi.
"""

import logging
from typing import Any

from app.models.bridge import SystemInfo, SystemState

logger = logging.getLogger(__name__)


class SystemRegistry:
    """Sistem kaydi.

    Tum alt sistemleri kaydeder, yeteneklerini haritalar,
    bagimlilik grafini yonetir.

    Attributes:
        _systems: Kayitli sistemler.
        _capability_index: Yetenek -> sistem eslesmesi.
    """

    def __init__(self) -> None:
        """Sistem kaydini baslatir."""
        self._systems: dict[str, SystemInfo] = {}
        self._capability_index: dict[str, list[str]] = {}

        logger.info("SystemRegistry baslatildi")

    def register(
        self,
        system_id: str,
        name: str,
        capabilities: list[str] | None = None,
        dependencies: list[str] | None = None,
        version: str = "1.0.0",
    ) -> SystemInfo:
        """Sistem kaydeder.

        Args:
            system_id: Sistem ID.
            name: Sistem adi.
            capabilities: Yetenekler.
            dependencies: Bagimliliklar.
            version: Versiyon.

        Returns:
            SystemInfo nesnesi.
        """
        info = SystemInfo(
            system_id=system_id,
            name=name,
            capabilities=capabilities or [],
            dependencies=dependencies or [],
            version=version,
        )
        self._systems[system_id] = info

        # Yetenek indeksini guncelle
        for cap in info.capabilities:
            self._capability_index.setdefault(cap, []).append(system_id)

        logger.info("Sistem kaydedildi: %s (%s)", name, system_id)
        return info

    def unregister(self, system_id: str) -> bool:
        """Sistem kaydini siler.

        Args:
            system_id: Sistem ID.

        Returns:
            Basarili ise True.
        """
        info = self._systems.pop(system_id, None)
        if not info:
            return False

        # Yetenek indeksinden cikar
        for cap in info.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap] = [
                    s for s in self._capability_index[cap]
                    if s != system_id
                ]

        return True

    def activate(self, system_id: str) -> bool:
        """Sistemi aktiflestirir.

        Args:
            system_id: Sistem ID.

        Returns:
            Basarili ise True.
        """
        info = self._systems.get(system_id)
        if not info:
            return False

        info.state = SystemState.ACTIVE
        return True

    def set_state(
        self,
        system_id: str,
        state: SystemState,
    ) -> bool:
        """Sistem durumunu degistirir.

        Args:
            system_id: Sistem ID.
            state: Yeni durum.

        Returns:
            Basarili ise True.
        """
        info = self._systems.get(system_id)
        if not info:
            return False

        info.state = state
        return True

    def get(self, system_id: str) -> SystemInfo | None:
        """Sistemi getirir.

        Args:
            system_id: Sistem ID.

        Returns:
            SystemInfo veya None.
        """
        return self._systems.get(system_id)

    def find_by_capability(self, capability: str) -> list[str]:
        """Yetenege gore sistem bulur.

        Args:
            capability: Yetenek.

        Returns:
            Sistem ID listesi.
        """
        return list(self._capability_index.get(capability, []))

    def get_dependencies(self, system_id: str) -> list[str]:
        """Bagimliliklari getirir.

        Args:
            system_id: Sistem ID.

        Returns:
            Bagimlilik listesi.
        """
        info = self._systems.get(system_id)
        return list(info.dependencies) if info else []

    def get_dependents(self, system_id: str) -> list[str]:
        """Bu sisteme bagli sistemleri getirir.

        Args:
            system_id: Sistem ID.

        Returns:
            Bagimli sistem listesi.
        """
        return [
            sid for sid, info in self._systems.items()
            if system_id in info.dependencies
        ]

    def get_dependency_graph(self) -> dict[str, list[str]]:
        """Bagimlilik grafini getirir.

        Returns:
            Sistem -> bagimlilik listesi.
        """
        return {
            sid: list(info.dependencies)
            for sid, info in self._systems.items()
        }

    def check_dependencies_met(self, system_id: str) -> bool:
        """Bagimliliklarin karsilandigini kontrol eder.

        Args:
            system_id: Sistem ID.

        Returns:
            Tum bagimliliklar aktif ise True.
        """
        info = self._systems.get(system_id)
        if not info:
            return False

        for dep in info.dependencies:
            dep_info = self._systems.get(dep)
            if not dep_info or dep_info.state != SystemState.ACTIVE:
                return False

        return True

    def get_active_systems(self) -> list[str]:
        """Aktif sistemleri getirir.

        Returns:
            Sistem ID listesi.
        """
        return [
            sid for sid, info in self._systems.items()
            if info.state == SystemState.ACTIVE
        ]

    def get_all_capabilities(self) -> dict[str, list[str]]:
        """Tum yetenek haritasini getirir.

        Returns:
            Yetenek -> sistem listesi.
        """
        return {k: list(v) for k, v in self._capability_index.items()}

    def update_version(
        self,
        system_id: str,
        version: str,
    ) -> bool:
        """Versiyon gunceller.

        Args:
            system_id: Sistem ID.
            version: Yeni versiyon.

        Returns:
            Basarili ise True.
        """
        info = self._systems.get(system_id)
        if not info:
            return False

        info.version = version
        return True

    @property
    def total_systems(self) -> int:
        """Toplam sistem sayisi."""
        return len(self._systems)

    @property
    def active_count(self) -> int:
        """Aktif sistem sayisi."""
        return sum(
            1 for info in self._systems.values()
            if info.state == SystemState.ACTIVE
        )

    @property
    def total_capabilities(self) -> int:
        """Toplam yetenek sayisi."""
        return len(self._capability_index)
