"""ATLAS Amortisman Hesaplayıcı modülü.

Amortisman yöntemleri, defter değeri takibi,
vergi hesaplaması, elden çıkarma yönetimi,
raporlama.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DepreciationCalculator:
    """Amortisman hesaplayıcı.

    Varlık amortisman hesaplamalarını yapar.

    Attributes:
        _calculations: Hesaplama kayıtları.
        _disposals: Elden çıkarma kayıtları.
    """

    def __init__(self) -> None:
        """Hesaplayıcıyı başlatır."""
        self._calculations: dict[
            str, dict[str, Any]
        ] = {}
        self._disposals: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "calculations_done": 0,
            "disposals_processed": 0,
        }

        logger.info(
            "DepreciationCalculator "
            "baslatildi",
        )

    def calculate_depreciation(
        self,
        asset_id: str,
        cost: float,
        salvage_value: float = 0.0,
        useful_life_years: int = 5,
        method: str = "straight_line",
        year: int = 1,
    ) -> dict[str, Any]:
        """Amortisman hesaplar.

        Args:
            asset_id: Varlık kimliği.
            cost: Maliyet.
            salvage_value: Hurda değeri.
            useful_life_years: Faydalı ömür.
            method: Amortisman yöntemi.
            year: Hesaplama yılı.

        Returns:
            Hesaplama bilgisi.
        """
        depreciable = cost - salvage_value

        if method == "straight_line":
            annual = (
                depreciable
                / useful_life_years
            )
            accumulated = annual * min(
                year, useful_life_years,
            )
        elif method == "declining_balance":
            rate = (
                2.0 / useful_life_years
            )
            book = cost
            accumulated = 0.0
            for y in range(
                min(
                    year,
                    useful_life_years,
                )
            ):
                dep = book * rate
                if (
                    book - dep
                    < salvage_value
                ):
                    dep = (
                        book - salvage_value
                    )
                accumulated += dep
                book -= dep
            annual = dep if year <= useful_life_years else 0.0
        else:
            annual = (
                depreciable
                / useful_life_years
            )
            accumulated = annual * min(
                year, useful_life_years,
            )

        book_value = cost - accumulated

        self._calculations[asset_id] = {
            "asset_id": asset_id,
            "cost": cost,
            "method": method,
            "annual": round(annual, 2),
            "accumulated": round(
                accumulated, 2,
            ),
            "book_value": round(
                book_value, 2,
            ),
        }

        self._stats[
            "calculations_done"
        ] += 1

        return {
            "asset_id": asset_id,
            "method": method,
            "annual_depreciation": round(
                annual, 2,
            ),
            "accumulated": round(
                accumulated, 2,
            ),
            "book_value": round(
                book_value, 2,
            ),
            "calculated": True,
        }

    def get_book_value(
        self,
        asset_id: str,
    ) -> dict[str, Any]:
        """Defter değeri sorgular.

        Args:
            asset_id: Varlık kimliği.

        Returns:
            Değer bilgisi.
        """
        calc = self._calculations.get(
            asset_id,
        )
        if not calc:
            return {
                "asset_id": asset_id,
                "found": False,
            }

        return {
            "asset_id": asset_id,
            "cost": calc["cost"],
            "book_value": calc[
                "book_value"
            ],
            "accumulated": calc[
                "accumulated"
            ],
            "found": True,
        }

    def calculate_tax(
        self,
        asset_id: str,
        tax_rate: float = 0.2,
    ) -> dict[str, Any]:
        """Vergi hesabı yapar.

        Args:
            asset_id: Varlık kimliği.
            tax_rate: Vergi oranı.

        Returns:
            Vergi bilgisi.
        """
        calc = self._calculations.get(
            asset_id,
        )
        if not calc:
            return {
                "asset_id": asset_id,
                "found": False,
            }

        tax_benefit = (
            calc["annual"] * tax_rate
        )

        return {
            "asset_id": asset_id,
            "annual_depreciation": calc[
                "annual"
            ],
            "tax_rate": tax_rate,
            "tax_benefit": round(
                tax_benefit, 2,
            ),
            "calculated": True,
        }

    def handle_disposal(
        self,
        asset_id: str,
        sale_price: float = 0.0,
    ) -> dict[str, Any]:
        """Elden çıkarma işler.

        Args:
            asset_id: Varlık kimliği.
            sale_price: Satış fiyatı.

        Returns:
            İşlem bilgisi.
        """
        calc = self._calculations.get(
            asset_id,
        )
        book_value = (
            calc["book_value"]
            if calc
            else 0.0
        )

        gain_loss = sale_price - book_value

        self._disposals.append({
            "asset_id": asset_id,
            "sale_price": sale_price,
            "book_value": book_value,
            "gain_loss": round(
                gain_loss, 2,
            ),
        })

        self._stats[
            "disposals_processed"
        ] += 1

        return {
            "asset_id": asset_id,
            "sale_price": sale_price,
            "book_value": book_value,
            "gain_loss": round(
                gain_loss, 2,
            ),
            "disposed": True,
        }

    def generate_report(
        self,
    ) -> dict[str, Any]:
        """Amortisman raporu üretir.

        Returns:
            Rapor bilgisi.
        """
        total_cost = sum(
            c["cost"]
            for c in (
                self._calculations.values()
            )
        )
        total_accumulated = sum(
            c["accumulated"]
            for c in (
                self._calculations.values()
            )
        )
        total_book = sum(
            c["book_value"]
            for c in (
                self._calculations.values()
            )
        )

        return {
            "assets_calculated": len(
                self._calculations,
            ),
            "total_cost": round(
                total_cost, 2,
            ),
            "total_accumulated": round(
                total_accumulated, 2,
            ),
            "total_book_value": round(
                total_book, 2,
            ),
            "reported": True,
        }

    @property
    def calculation_count(self) -> int:
        """Hesaplama sayısı."""
        return self._stats[
            "calculations_done"
        ]

    @property
    def disposal_count(self) -> int:
        """Elden çıkarma sayısı."""
        return self._stats[
            "disposals_processed"
        ]
