"""ATLAS API Kayit Defteri modulu.

API kayit, surum yonetimi,
endpoint katalogu, kullanim disi
takibi ve kesif servisi.
"""

import logging
import time
from typing import Any

from app.models.api_mgmt import (
    APIRecord,
    APIStatus,
)

logger = logging.getLogger(__name__)


class APIRegistry:
    """API kayit defteri.

    API'leri kaydeder, kataloglar
    ve yonetir.

    Attributes:
        _apis: API kayitlari.
        _endpoints: Endpoint katalogu.
    """

    def __init__(self) -> None:
        """API kayit defterini baslatir."""
        self._apis: dict[str, APIRecord] = {}
        self._endpoints: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._deprecations: dict[
            str, dict[str, Any]
        ] = {}

        logger.info("APIRegistry baslatildi")

    def register(
        self,
        name: str,
        base_path: str,
        version: str = "v1",
        metadata: dict[str, Any] | None = None,
    ) -> APIRecord:
        """API kaydeder.

        Args:
            name: API adi.
            base_path: Temel yol.
            version: Surum.
            metadata: Ek veri.

        Returns:
            API kaydi.
        """
        record = APIRecord(
            name=name,
            base_path=base_path,
            version=version,
            metadata=metadata or {},
        )
        self._apis[record.api_id] = record
        return record

    def add_endpoint(
        self,
        api_id: str,
        path: str,
        method: str = "GET",
        description: str = "",
        params: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Endpoint ekler.

        Args:
            api_id: API ID.
            path: Endpoint yolu.
            method: HTTP metodu.
            description: Aciklama.
            params: Parametreler.

        Returns:
            Endpoint bilgisi veya None.
        """
        api = self._apis.get(api_id)
        if not api:
            return None

        endpoint = {
            "path": path,
            "method": method,
            "description": description,
            "params": params or [],
        }
        api.endpoints.append(endpoint)

        if api_id not in self._endpoints:
            self._endpoints[api_id] = []
        self._endpoints[api_id].append(endpoint)

        return endpoint

    def deprecate(
        self,
        api_id: str,
        reason: str = "",
        sunset_date: str = "",
    ) -> bool:
        """API'yi kullanim disi birakir.

        Args:
            api_id: API ID.
            reason: Sebep.
            sunset_date: Bitis tarihi.

        Returns:
            Basarili ise True.
        """
        api = self._apis.get(api_id)
        if not api:
            return False

        api.status = APIStatus.DEPRECATED
        self._deprecations[api_id] = {
            "reason": reason,
            "sunset_date": sunset_date,
            "at": time.time(),
        }
        return True

    def disable(self, api_id: str) -> bool:
        """API'yi devre disi birakir.

        Args:
            api_id: API ID.

        Returns:
            Basarili ise True.
        """
        api = self._apis.get(api_id)
        if not api:
            return False
        api.status = APIStatus.DISABLED
        return True

    def enable(self, api_id: str) -> bool:
        """API'yi etkinlestirir.

        Args:
            api_id: API ID.

        Returns:
            Basarili ise True.
        """
        api = self._apis.get(api_id)
        if not api:
            return False
        api.status = APIStatus.ACTIVE
        return True

    def discover(
        self,
        query: str = "",
        status: str | None = None,
    ) -> list[APIRecord]:
        """API kesfeder.

        Args:
            query: Arama sorgusu.
            status: Durum filtresi.

        Returns:
            API listesi.
        """
        results = list(self._apis.values())
        if query:
            results = [
                a for a in results
                if query.lower() in a.name.lower()
                or query.lower()
                in a.base_path.lower()
            ]
        if status:
            results = [
                a for a in results
                if a.status.value == status
            ]
        return results

    def get_api(
        self,
        api_id: str,
    ) -> APIRecord | None:
        """API getirir.

        Args:
            api_id: API ID.

        Returns:
            API veya None.
        """
        return self._apis.get(api_id)

    def get_endpoints(
        self,
        api_id: str,
    ) -> list[dict[str, Any]]:
        """Endpoint listesi getirir.

        Args:
            api_id: API ID.

        Returns:
            Endpoint listesi.
        """
        return self._endpoints.get(api_id, [])

    def remove(self, api_id: str) -> bool:
        """API kaldirir.

        Args:
            api_id: API ID.

        Returns:
            Basarili ise True.
        """
        if api_id in self._apis:
            del self._apis[api_id]
            self._endpoints.pop(api_id, None)
            self._deprecations.pop(api_id, None)
            return True
        return False

    @property
    def api_count(self) -> int:
        """API sayisi."""
        return len(self._apis)

    @property
    def endpoint_count(self) -> int:
        """Toplam endpoint sayisi."""
        return sum(
            len(eps)
            for eps in self._endpoints.values()
        )

    @property
    def deprecated_count(self) -> int:
        """Kullanim disi API sayisi."""
        return sum(
            1 for a in self._apis.values()
            if a.status == APIStatus.DEPRECATED
        )
