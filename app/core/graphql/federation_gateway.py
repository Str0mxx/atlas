"""ATLAS Federasyon Gecidi modulu.

Sema birlestirme, uzak semalar,
tip birlestirme, sorgu planlama
ve hata toplama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FederationGateway:
    """Federasyon gecidi.

    Birden fazla GraphQL servisini birlestirir.

    Attributes:
        _services: Kayitli servisler.
        _merged_types: Birlesmis tipler.
    """

    def __init__(self) -> None:
        """Gecidi baslatir."""
        self._services: dict[
            str, dict[str, Any]
        ] = {}
        self._merged_types: dict[
            str, dict[str, Any]
        ] = {}
        self._query_plans: list[
            dict[str, Any]
        ] = []
        self._errors: list[
            dict[str, Any]
        ] = []

        logger.info(
            "FederationGateway baslatildi",
        )

    def register_service(
        self,
        name: str,
        url: str,
        types: list[str] | None = None,
        queries: list[str] | None = None,
    ) -> dict[str, Any]:
        """Servis kaydeder.

        Args:
            name: Servis adi.
            url: Servis URL.
            types: Sagladigi tipler.
            queries: Sagladigi sorgular.

        Returns:
            Kayit bilgisi.
        """
        self._services[name] = {
            "name": name,
            "url": url,
            "types": types or [],
            "queries": queries or [],
            "status": "active",
            "registered_at": time.time(),
        }

        # Tipleri birlestir
        for t in (types or []):
            if t not in self._merged_types:
                self._merged_types[t] = {
                    "sources": [],
                }
            self._merged_types[t][
                "sources"
            ].append(name)

        return {
            "name": name,
            "types": len(types or []),
            "queries": len(queries or []),
        }

    def remove_service(
        self,
        name: str,
    ) -> bool:
        """Servisi kaldirir.

        Args:
            name: Servis adi.

        Returns:
            Basarili mi.
        """
        svc = self._services.pop(name, None)
        if not svc:
            return False

        # Tipleri temizle
        for t in svc.get("types", []):
            if t in self._merged_types:
                sources = self._merged_types[t][
                    "sources"
                ]
                if name in sources:
                    sources.remove(name)
                if not sources:
                    del self._merged_types[t]

        return True

    def plan_query(
        self,
        query_fields: list[str],
    ) -> dict[str, Any]:
        """Sorgu plani olusturur.

        Args:
            query_fields: Sorgu alanlari.

        Returns:
            Plan bilgisi.
        """
        plan: dict[str, list[str]] = {}

        for field in query_fields:
            service = self._find_service_for(
                field,
            )
            if service:
                plan.setdefault(
                    service, [],
                ).append(field)

        result = {
            "services_involved": len(plan),
            "plan": plan,
            "fields": len(query_fields),
            "timestamp": time.time(),
        }

        self._query_plans.append(result)
        return result

    def _find_service_for(
        self,
        field: str,
    ) -> str | None:
        """Alan icin servis bulur.

        Args:
            field: Alan adi.

        Returns:
            Servis adi veya None.
        """
        for name, svc in self._services.items():
            if field in svc["queries"]:
                return name
            if field in svc["types"]:
                return name
        return None

    def execute_federated(
        self,
        query_fields: list[str],
        resolver_fn: Any | None = None,
    ) -> dict[str, Any]:
        """Federasyonlu sorgu yurutur.

        Args:
            query_fields: Sorgu alanlari.
            resolver_fn: Cozumleyici.

        Returns:
            Birlesmis sonuc.
        """
        plan = self.plan_query(query_fields)
        results: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []

        for service, fields in plan.get(
            "plan", {},
        ).items():
            for field in fields:
                if resolver_fn:
                    try:
                        results[field] = (
                            resolver_fn(
                                service, field,
                            )
                        )
                    except Exception as e:
                        errors.append({
                            "service": service,
                            "field": field,
                            "error": str(e),
                        })
                else:
                    results[field] = None

        if errors:
            self._errors.extend(errors)

        return {
            "data": results,
            "errors": errors if errors else None,
            "services_used": plan[
                "services_involved"
            ],
        }

    def stitch_schemas(self) -> dict[str, Any]:
        """Semalari birlestirir.

        Returns:
            Birlestirme sonucu.
        """
        all_types: list[str] = []
        all_queries: list[str] = []
        conflicts: list[str] = []

        for svc in self._services.values():
            all_types.extend(svc["types"])
            all_queries.extend(svc["queries"])

        # Cakisma tespiti
        type_counts: dict[str, int] = {}
        for t in all_types:
            type_counts[t] = (
                type_counts.get(t, 0) + 1
            )
        conflicts = [
            t for t, c in type_counts.items()
            if c > 1
        ]

        return {
            "total_types": len(set(all_types)),
            "total_queries": len(set(all_queries)),
            "conflicts": conflicts,
            "services": len(self._services),
        }

    def get_type_sources(
        self,
        type_name: str,
    ) -> list[str]:
        """Tip kaynaklarini getirir.

        Args:
            type_name: Tip adi.

        Returns:
            Kaynak servisler.
        """
        mt = self._merged_types.get(type_name)
        if not mt:
            return []
        return list(mt["sources"])

    def get_service(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Servis bilgisini getirir.

        Args:
            name: Servis adi.

        Returns:
            Bilgi veya None.
        """
        return self._services.get(name)

    def get_errors(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Hatalari getirir.

        Args:
            limit: Limit.

        Returns:
            Hata listesi.
        """
        return self._errors[-limit:]

    @property
    def service_count(self) -> int:
        """Servis sayisi."""
        return len(self._services)

    @property
    def merged_type_count(self) -> int:
        """Birlesmis tip sayisi."""
        return len(self._merged_types)

    @property
    def plan_count(self) -> int:
        """Plan sayisi."""
        return len(self._query_plans)

    @property
    def error_count(self) -> int:
        """Hata sayisi."""
        return len(self._errors)
