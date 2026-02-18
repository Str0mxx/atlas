"""
ROI takipcisi modulu.

Yatirim takibi, getiri hesaplama,
geri odeme suresi, karsilastirma,
gorsellestirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FinDashROITracker:
    """ROI takipcisi.

    Attributes:
        _investments: Yatirim kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._investments: list[dict] = []
        self._stats: dict[str, int] = {
            "investments_tracked": 0,
            "returns_recorded": 0,
        }
        logger.info(
            "FinDashROITracker baslatildi"
        )

    @property
    def investment_count(self) -> int:
        """Yatirim sayisi."""
        return len(self._investments)

    def track_investment(
        self,
        name: str = "",
        amount: float = 0.0,
        category: str = "technology",
        expected_return: float = 0.0,
        period_months: int = 12,
    ) -> dict[str, Any]:
        """Yatirim takip eder.

        Args:
            name: Yatirim adi.
            amount: Tutar.
            category: Kategori.
            expected_return: Beklenen getiri.
            period_months: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            iid = f"iv_{uuid4()!s:.8}"
            investment = {
                "investment_id": iid,
                "name": name,
                "amount": amount,
                "category": category,
                "expected_return": (
                    expected_return
                ),
                "period_months": (
                    period_months
                ),
                "actual_returns": [],
                "total_return": 0.0,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._investments.append(
                investment
            )
            self._stats[
                "investments_tracked"
            ] += 1

            return {
                "investment_id": iid,
                "name": name,
                "amount": amount,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def record_return(
        self,
        investment_id: str = "",
        amount: float = 0.0,
        period: str = "",
    ) -> dict[str, Any]:
        """Getiri kaydeder.

        Args:
            investment_id: Yatirim ID.
            amount: Tutar.
            period: Donem.

        Returns:
            Kayit bilgisi.
        """
        try:
            for inv in self._investments:
                if (
                    inv["investment_id"]
                    == investment_id
                ):
                    inv[
                        "actual_returns"
                    ].append({
                        "amount": amount,
                        "period": period,
                        "timestamp": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        ),
                    })
                    inv[
                        "total_return"
                    ] += amount
                    self._stats[
                        "returns_recorded"
                    ] += 1

                    return {
                        "investment_id": (
                            investment_id
                        ),
                        "return_amount": (
                            amount
                        ),
                        "total_return": round(
                            inv[
                                "total_return"
                            ],
                            2,
                        ),
                        "recorded": True,
                    }

            return {
                "investment_id": investment_id,
                "recorded": False,
                "reason": "not_found",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def calculate_roi(
        self,
        investment_id: str = "",
    ) -> dict[str, Any]:
        """ROI hesaplar.

        Args:
            investment_id: Yatirim ID.

        Returns:
            ROI bilgisi.
        """
        try:
            for inv in self._investments:
                if (
                    inv["investment_id"]
                    == investment_id
                ):
                    invested = inv["amount"]
                    returned = inv[
                        "total_return"
                    ]
                    net = returned - invested
                    roi = (
                        (net / invested * 100)
                        if invested > 0
                        else 0.0
                    )

                    status = (
                        "profitable"
                        if roi > 0
                        else "break_even"
                        if roi == 0
                        else "loss"
                    )

                    return {
                        "investment_id": (
                            investment_id
                        ),
                        "name": inv["name"],
                        "invested": round(
                            invested, 2
                        ),
                        "returned": round(
                            returned, 2
                        ),
                        "net_return": round(
                            net, 2
                        ),
                        "roi_percentage": (
                            round(roi, 1)
                        ),
                        "status": status,
                        "calculated": True,
                    }

            return {
                "investment_id": investment_id,
                "calculated": False,
                "reason": "not_found",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def calculate_payback_period(
        self,
        investment_id: str = "",
    ) -> dict[str, Any]:
        """Geri odeme suresi hesaplar.

        Args:
            investment_id: Yatirim ID.

        Returns:
            Geri odeme bilgisi.
        """
        try:
            for inv in self._investments:
                if (
                    inv["investment_id"]
                    == investment_id
                ):
                    invested = inv["amount"]
                    returns = inv[
                        "actual_returns"
                    ]

                    if not returns:
                        return {
                            "investment_id": (
                                investment_id
                            ),
                            "payback_months": (
                                None
                            ),
                            "status": (
                                "no_returns"
                            ),
                            "calculated": True,
                        }

                    cumulative = 0.0
                    payback = None
                    for i, ret in enumerate(
                        returns
                    ):
                        cumulative += ret[
                            "amount"
                        ]
                        if (
                            cumulative
                            >= invested
                            and payback is None
                        ):
                            payback = i + 1

                    avg_return = (
                        sum(
                            r["amount"]
                            for r in returns
                        )
                        / len(returns)
                    )
                    est_months = (
                        int(
                            invested
                            / avg_return
                        )
                        if avg_return > 0
                        else None
                    )

                    return {
                        "investment_id": (
                            investment_id
                        ),
                        "invested": round(
                            invested, 2
                        ),
                        "cumulative_return": (
                            round(
                                cumulative, 2
                            )
                        ),
                        "payback_months": (
                            payback
                        ),
                        "estimated_months": (
                            est_months
                        ),
                        "paid_back": (
                            payback is not None
                        ),
                        "calculated": True,
                    }

            return {
                "investment_id": investment_id,
                "calculated": False,
                "reason": "not_found",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def compare_investments(
        self,
    ) -> dict[str, Any]:
        """Yatirimlari karsilastirir.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            comparisons = []
            for inv in self._investments:
                invested = inv["amount"]
                returned = inv[
                    "total_return"
                ]
                roi = (
                    (
                        (returned - invested)
                        / invested
                        * 100
                    )
                    if invested > 0
                    else 0.0
                )

                comparisons.append({
                    "investment_id": inv[
                        "investment_id"
                    ],
                    "name": inv["name"],
                    "category": inv[
                        "category"
                    ],
                    "invested": round(
                        invested, 2
                    ),
                    "returned": round(
                        returned, 2
                    ),
                    "roi": round(roi, 1),
                })

            comparisons.sort(
                key=lambda x: x["roi"],
                reverse=True,
            )

            return {
                "comparisons": comparisons,
                "investment_count": len(
                    comparisons
                ),
                "best_roi": (
                    comparisons[0]
                    if comparisons
                    else None
                ),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }
