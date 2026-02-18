"""
Veri akis haritacisi modulu.

Veri akis takibi, sinir otesi aktarim,
isleme esleme, depolama konumlari,
ucuncu taraf paylasimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DataFlowMapper:
    """Veri akis haritacisi.

    Attributes:
        _data_assets: Veri varliklari.
        _flows: Akis kayitlari.
        _processors: Isleyici kayitlari.
        _transfers: Aktarim kayitlari.
        _stats: Istatistikler.
    """

    DATA_CATEGORIES: list[str] = [
        "personal",
        "sensitive",
        "financial",
        "health",
        "biometric",
        "children",
        "public",
    ]

    LEGAL_BASES: list[str] = [
        "consent",
        "contract",
        "legal_obligation",
        "vital_interest",
        "public_interest",
        "legitimate_interest",
    ]

    def __init__(self) -> None:
        """Haritaciyi baslatir."""
        self._data_assets: dict[
            str, dict
        ] = {}
        self._flows: list[dict] = []
        self._processors: dict[
            str, dict
        ] = {}
        self._transfers: list[dict] = []
        self._stats: dict[str, int] = {
            "assets_registered": 0,
            "flows_mapped": 0,
            "processors_added": 0,
            "cross_border_transfers": 0,
        }
        logger.info(
            "DataFlowMapper baslatildi"
        )

    @property
    def asset_count(self) -> int:
        """Veri varligi sayisi."""
        return len(self._data_assets)

    def register_data_asset(
        self,
        name: str = "",
        category: str = "personal",
        storage_location: str = "",
        country: str = "",
        owner: str = "",
        legal_basis: str = "consent",
        retention_days: int = 365,
    ) -> dict[str, Any]:
        """Veri varligi kaydeder.

        Args:
            name: Varlik adi.
            category: Kategori.
            storage_location: Depolama.
            country: Ulke.
            owner: Sahip.
            legal_basis: Hukuki dayanak.
            retention_days: Saklama suresi.

        Returns:
            Kayit bilgisi.
        """
        try:
            if (
                category
                not in self.DATA_CATEGORIES
            ):
                return {
                    "registered": False,
                    "error": (
                        f"Gecersiz: "
                        f"{category}"
                    ),
                }

            aid = f"da_{uuid4()!s:.8}"
            self._data_assets[aid] = {
                "asset_id": aid,
                "name": name,
                "category": category,
                "storage_location": (
                    storage_location
                ),
                "country": country,
                "owner": owner,
                "legal_basis": legal_basis,
                "retention_days": (
                    retention_days
                ),
                "status": "active",
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "assets_registered"
            ] += 1

            return {
                "asset_id": aid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def add_processor(
        self,
        name: str = "",
        processor_type: str = "",
        country: str = "",
        dpa_signed: bool = False,
        contact: str = "",
    ) -> dict[str, Any]:
        """Veri isleyici ekler.

        Args:
            name: Isleyici adi.
            processor_type: Tip.
            country: Ulke.
            dpa_signed: DPA imzali mi.
            contact: Iletisim.

        Returns:
            Isleyici bilgisi.
        """
        try:
            pid = f"dp_{uuid4()!s:.8}"
            self._processors[pid] = {
                "processor_id": pid,
                "name": name,
                "processor_type": (
                    processor_type
                ),
                "country": country,
                "dpa_signed": dpa_signed,
                "contact": contact,
                "added_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "processors_added"
            ] += 1

            return {
                "processor_id": pid,
                "name": name,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def map_flow(
        self,
        source_asset_id: str = "",
        destination: str = "",
        purpose: str = "",
        legal_basis: str = "consent",
        processor_id: str = "",
        is_cross_border: bool = False,
        destination_country: str = "",
    ) -> dict[str, Any]:
        """Veri akisi esler.

        Args:
            source_asset_id: Kaynak ID.
            destination: Hedef.
            purpose: Amac.
            legal_basis: Hukuki dayanak.
            processor_id: Isleyici ID.
            is_cross_border: Sinir otesi.
            destination_country: Hedef ulke.

        Returns:
            Akis bilgisi.
        """
        try:
            asset = self._data_assets.get(
                source_asset_id
            )
            if not asset:
                return {
                    "mapped": False,
                    "error": (
                        "Varlik bulunamadi"
                    ),
                }

            fid = f"fl_{uuid4()!s:.8}"
            flow = {
                "flow_id": fid,
                "source_asset_id": (
                    source_asset_id
                ),
                "destination": destination,
                "purpose": purpose,
                "legal_basis": legal_basis,
                "processor_id": (
                    processor_id
                ),
                "is_cross_border": (
                    is_cross_border
                ),
                "destination_country": (
                    destination_country
                ),
                "mapped_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._flows.append(flow)
            self._stats[
                "flows_mapped"
            ] += 1

            if is_cross_border:
                self._transfers.append(
                    flow
                )
                self._stats[
                    "cross_border_transfers"
                ] += 1

            return {
                "flow_id": fid,
                "is_cross_border": (
                    is_cross_border
                ),
                "mapped": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "mapped": False,
                "error": str(e),
            }

    def get_cross_border_transfers(
        self,
    ) -> dict[str, Any]:
        """Sinir otesi aktarimlari getirir.

        Returns:
            Aktarim listesi.
        """
        try:
            return {
                "transfers": list(
                    self._transfers
                ),
                "count": len(
                    self._transfers
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_asset_flows(
        self,
        asset_id: str = "",
    ) -> dict[str, Any]:
        """Varlik akislarini getirir.

        Args:
            asset_id: Varlik ID.

        Returns:
            Akis bilgisi.
        """
        try:
            flows = [
                f
                for f in self._flows
                if f["source_asset_id"]
                == asset_id
            ]
            return {
                "asset_id": asset_id,
                "flows": flows,
                "count": len(flows),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_assets": len(
                    self._data_assets
                ),
                "total_flows": len(
                    self._flows
                ),
                "total_processors": len(
                    self._processors
                ),
                "cross_border": len(
                    self._transfers
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
