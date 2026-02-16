"""ATLAS Varlık Takip Orkestratörü.

Tam varlık yönetim pipeline,
Register → Track → Maintain → Audit,
gerçek zamanlı görünürlük, analitik.
"""

import logging
from typing import Any

from app.core.assettrack.asset_location_mapper import (
    AssetLocationMapper,
)
from app.core.assettrack.asset_registry import (
    AssetRegistry,
)
from app.core.assettrack.barcode_scanner import (
    BarcodeScanner,
)
from app.core.assettrack.depreciation_calculator import (
    DepreciationCalculator,
)
from app.core.assettrack.inventory_auditor import (
    InventoryAuditor,
)
from app.core.assettrack.maintenance_scheduler import (
    AssetMaintenanceScheduler,
)
from app.core.assettrack.reorder_trigger import (
    InventoryReorderTrigger,
)
from app.core.assettrack.stock_level_tracker import (
    StockLevelTracker,
)

logger = logging.getLogger(__name__)


class AssetTrackOrchestrator:
    """Varlık takip orkestratörü.

    Tüm varlık takip bileşenlerini koordine eder.

    Attributes:
        registry: Varlık kayıt defteri.
        scanner: Barkod tarayıcı.
        stock: Stok takipçisi.
        maintenance: Bakım zamanlayıcı.
        depreciation: Amortisman hesaplayıcı.
        locations: Konum haritacısı.
        reorder: Sipariş tetikleyici.
        auditor: Envanter denetçisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.registry = AssetRegistry()
        self.scanner = BarcodeScanner()
        self.stock = StockLevelTracker()
        self.maintenance = (
            AssetMaintenanceScheduler()
        )
        self.depreciation = (
            DepreciationCalculator()
        )
        self.locations = (
            AssetLocationMapper()
        )
        self.reorder = (
            InventoryReorderTrigger()
        )
        self.auditor = InventoryAuditor()
        self._stats = {
            "pipelines_run": 0,
            "assets_managed": 0,
        }

        logger.info(
            "AssetTrackOrchestrator "
            "baslatildi",
        )

    def register_and_track(
        self,
        name: str,
        category: str = "equipment",
        purchase_cost: float = 0.0,
        location: str = "main",
    ) -> dict[str, Any]:
        """Register → Track → Label pipeline.

        Args:
            name: Varlık adı.
            category: Kategori.
            purchase_cost: Maliyet.
            location: Konum.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Register
        reg = self.registry.register_asset(
            name=name,
            category=category,
            purchase_cost=purchase_cost,
        )

        asset_id = reg["asset_id"]

        # 2. Track location
        self.locations.track_location(
            asset_id=asset_id,
            location=location,
        )

        # 3. Generate label
        self.scanner.generate_label(
            asset_id=asset_id,
            label_format="qr",
        )

        # 4. Calculate depreciation
        if purchase_cost > 0:
            self.depreciation.calculate_depreciation(
                asset_id=asset_id,
                cost=purchase_cost,
            )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "assets_managed"
        ] += 1

        return {
            "asset_id": asset_id,
            "name": name,
            "category": category,
            "location": location,
            "registered": True,
            "tracked": True,
            "labeled": True,
            "pipeline_complete": True,
        }

    def full_audit(
        self,
        location: str = "",
    ) -> dict[str, Any]:
        """Tam denetim çalıştırır.

        Args:
            location: Konum.

        Returns:
            Denetim bilgisi.
        """
        audit = (
            self.auditor.schedule_audit(
                audit_type="full",
                location=location,
            )
        )

        self.auditor.reconcile(
            audit["audit_id"],
        )

        return {
            "audit_id": audit["audit_id"],
            "location": location,
            "completed": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": (
                self._stats[
                    "pipelines_run"
                ]
            ),
            "assets_managed": (
                self._stats[
                    "assets_managed"
                ]
            ),
            "assets_registered": (
                self.registry.asset_count
            ),
            "scans_done": (
                self.scanner.scan_count
            ),
            "items_tracked": (
                self.stock.item_count
            ),
            "maintenances_done": (
                self.maintenance
                .maintenance_count
            ),
            "calculations_done": (
                self.depreciation
                .calculation_count
            ),
            "locations_tracked": (
                self.locations
                .location_count
            ),
            "orders_triggered": (
                self.reorder.order_count
            ),
            "audits_completed": (
                self.auditor.audit_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def managed_count(self) -> int:
        """Yönetilen varlık sayısı."""
        return self._stats[
            "assets_managed"
        ]
