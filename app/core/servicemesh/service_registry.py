"""ATLAS Mesh Servis Kayit Defteri modulu.

Servis kaydi, ornek takibi,
metadata yonetimi, TTL isleme
ve kayit silme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MeshServiceRegistry:
    """Mesh servis kayit defteri.

    Servisleri ve ornekleri kaydeder.

    Attributes:
        _services: Servis tanimlari.
        _instances: Ornek tanimlari.
    """

    def __init__(self) -> None:
        """Kayit defterini baslatir."""
        self._services: dict[
            str, dict[str, Any]
        ] = {}
        self._instances: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._metadata: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "MeshServiceRegistry baslatildi",
        )

    def register(
        self,
        name: str,
        host: str,
        port: int,
        version: str = "1.0.0",
        metadata: dict[str, Any] | None = None,
        ttl: int = 0,
    ) -> dict[str, Any]:
        """Servis kaydeder.

        Args:
            name: Servis adi.
            host: Host adresi.
            port: Port numarasi.
            version: Surum.
            metadata: Metadata.
            ttl: Yasam suresi (sn, 0=sinirsiz).

        Returns:
            Kayit bilgisi.
        """
        if name not in self._services:
            self._services[name] = {
                "name": name,
                "version": version,
                "status": "active",
                "created_at": time.time(),
            }
            self._instances[name] = []

        instance_id = f"{host}:{port}"
        instance = {
            "instance_id": instance_id,
            "host": host,
            "port": port,
            "version": version,
            "status": "active",
            "ttl": ttl,
            "registered_at": time.time(),
            "last_heartbeat": time.time(),
            "metadata": metadata or {},
        }

        # Varsa guncelle
        existing = [
            i for i in self._instances[name]
            if i["instance_id"] == instance_id
        ]
        if existing:
            idx = self._instances[name].index(
                existing[0],
            )
            self._instances[name][idx] = instance
        else:
            self._instances[name].append(instance)

        if metadata:
            self._metadata[instance_id] = metadata

        return {
            "name": name,
            "instance_id": instance_id,
            "status": "registered",
        }

    def deregister(
        self,
        name: str,
        instance_id: str | None = None,
    ) -> bool:
        """Servis kaydini siler.

        Args:
            name: Servis adi.
            instance_id: Ornek ID (None=tumu).

        Returns:
            Basarili mi.
        """
        if name not in self._services:
            return False

        if instance_id is None:
            del self._services[name]
            self._instances.pop(name, None)
            return True

        instances = self._instances.get(name, [])
        original = len(instances)
        self._instances[name] = [
            i for i in instances
            if i["instance_id"] != instance_id
        ]
        self._metadata.pop(instance_id, None)
        return len(self._instances[name]) < original

    def heartbeat(
        self,
        name: str,
        instance_id: str,
    ) -> bool:
        """Kalp atisi gunceller.

        Args:
            name: Servis adi.
            instance_id: Ornek ID.

        Returns:
            Basarili mi.
        """
        for inst in self._instances.get(name, []):
            if inst["instance_id"] == instance_id:
                inst["last_heartbeat"] = time.time()
                return True
        return False

    def get_service(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Servis bilgisi getirir.

        Args:
            name: Servis adi.

        Returns:
            Servis bilgisi veya None.
        """
        svc = self._services.get(name)
        if not svc:
            return None
        return {
            **svc,
            "instance_count": len(
                self._instances.get(name, []),
            ),
        }

    def get_instances(
        self,
        name: str,
        healthy_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Servis orneklerini getirir.

        Args:
            name: Servis adi.
            healthy_only: Sadece sagliklilari.

        Returns:
            Ornek listesi.
        """
        instances = self._instances.get(name, [])
        if healthy_only:
            instances = [
                i for i in instances
                if i["status"] == "active"
            ]
        return list(instances)

    def set_instance_status(
        self,
        name: str,
        instance_id: str,
        status: str,
    ) -> bool:
        """Ornek durumunu ayarlar.

        Args:
            name: Servis adi.
            instance_id: Ornek ID.
            status: Yeni durum.

        Returns:
            Basarili mi.
        """
        for inst in self._instances.get(name, []):
            if inst["instance_id"] == instance_id:
                inst["status"] = status
                return True
        return False

    def set_metadata(
        self,
        name: str,
        instance_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """Metadata ayarlar.

        Args:
            name: Servis adi.
            instance_id: Ornek ID.
            key: Anahtar.
            value: Deger.

        Returns:
            Basarili mi.
        """
        for inst in self._instances.get(name, []):
            if inst["instance_id"] == instance_id:
                inst["metadata"][key] = value
                return True
        return False

    def get_metadata(
        self,
        instance_id: str,
    ) -> dict[str, Any]:
        """Metadata getirir.

        Args:
            instance_id: Ornek ID.

        Returns:
            Metadata.
        """
        return dict(
            self._metadata.get(instance_id, {}),
        )

    def cleanup_expired(self) -> int:
        """Suresi dolmus ornekleri temizler.

        Returns:
            Temizlenen sayi.
        """
        now = time.time()
        cleaned = 0
        for name in list(self._instances.keys()):
            original = len(self._instances[name])
            self._instances[name] = [
                i for i in self._instances[name]
                if i["ttl"] == 0
                or (now - i["last_heartbeat"])
                < i["ttl"]
            ]
            cleaned += original - len(
                self._instances[name],
            )
        return cleaned

    def list_services(self) -> list[dict[str, Any]]:
        """Servis listesi getirir.

        Returns:
            Servis listesi.
        """
        return [
            {
                "name": s["name"],
                "status": s["status"],
                "instances": len(
                    self._instances.get(
                        s["name"], [],
                    ),
                ),
            }
            for s in self._services.values()
        ]

    @property
    def service_count(self) -> int:
        """Servis sayisi."""
        return len(self._services)

    @property
    def total_instances(self) -> int:
        """Toplam ornek sayisi."""
        return sum(
            len(i) for i in
            self._instances.values()
        )
