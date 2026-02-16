"""
Kişisel bütçe planlayıcı modülü.

Bütçe oluşturma, kategori bütçeleri,
takip, uyarılar ve ayarlamalar sağlar.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PersonalBudgetPlanner:
    """Kişisel bütçe planlayıcı.

    Bütçe oluşturur, kategorilere göre
    takip eder ve uyarılar üretir.

    Attributes:
        _budgets: Bütçe kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Planlayıcıyı başlatır."""
        self._budgets: list[dict] = []
        self._stats: dict[str, int] = {
            "budgets_created": 0,
        }
        logger.info(
            "PersonalBudgetPlanner "
            "baslatildi"
        )

    @property
    def budget_count(self) -> int:
        """Bütçe sayısı."""
        return len(self._budgets)

    def create_budget(
        self,
        name: str = "Monthly Budget",
        period: str = "monthly",
        total_limit: float = 10000.0,
    ) -> dict[str, Any]:
        """Bütçe oluşturur.

        Args:
            name: Bütçe adı.
            period: Dönem.
            total_limit: Toplam limit.

        Returns:
            Bütçe bilgisi.
        """
        try:
            bid = f"bud_{uuid4()!s:.8}"
            budget = {
                "budget_id": bid,
                "name": name,
                "period": period,
                "total_limit": total_limit,
                "spent": 0.0,
                "categories": {},
            }
            self._budgets.append(budget)
            self._stats[
                "budgets_created"
            ] += 1

            logger.info(
                f"Butce olusturuldu: "
                f"{name}, limit={total_limit}"
            )

            return {
                "budget_id": bid,
                "name": name,
                "period": period,
                "total_limit": total_limit,
                "created": True,
            }

        except Exception as e:
            logger.error(
                f"Butce olusturma "
                f"hatasi: {e}"
            )
            return {
                "budget_id": "",
                "name": name,
                "created": False,
                "error": str(e),
            }

    def set_category_budget(
        self,
        budget_id: str,
        category: str = "food",
        limit: float = 2000.0,
    ) -> dict[str, Any]:
        """Kategori bütçesi belirler.

        Args:
            budget_id: Bütçe ID.
            category: Kategori.
            limit: Kategori limiti.

        Returns:
            Kategori bütçesi sonucu.
        """
        try:
            for b in self._budgets:
                if b["budget_id"] == (
                    budget_id
                ):
                    b["categories"][
                        category
                    ] = {
                        "limit": limit,
                        "spent": 0.0,
                    }
                    return {
                        "budget_id": (
                            budget_id
                        ),
                        "category": category,
                        "limit": limit,
                        "set": True,
                    }

            return {
                "budget_id": budget_id,
                "category": category,
                "set": False,
                "error": "budget_not_found",
            }

        except Exception as e:
            logger.error(
                f"Kategori butce "
                f"hatasi: {e}"
            )
            return {
                "budget_id": budget_id,
                "category": category,
                "set": False,
                "error": str(e),
            }

    def track_spending(
        self,
        budget_id: str,
        category: str = "food",
        amount: float = 0.0,
    ) -> dict[str, Any]:
        """Harcama takibi yapar.

        Args:
            budget_id: Bütçe ID.
            category: Kategori.
            amount: Tutar.

        Returns:
            Takip sonucu.
        """
        try:
            for b in self._budgets:
                if b["budget_id"] == (
                    budget_id
                ):
                    b["spent"] += amount
                    if (
                        category
                        in b["categories"]
                    ):
                        b["categories"][
                            category
                        ]["spent"] += amount

                    remaining = round(
                        b["total_limit"]
                        - b["spent"],
                        2,
                    )
                    pct = round(
                        (
                            b["spent"]
                            / max(
                                b[
                                    "total_limit"
                                ],
                                1,
                            )
                        )
                        * 100,
                        1,
                    )

                    return {
                        "budget_id": (
                            budget_id
                        ),
                        "category": category,
                        "amount": amount,
                        "total_spent": round(
                            b["spent"], 2
                        ),
                        "remaining": (
                            remaining
                        ),
                        "used_pct": pct,
                        "tracked": True,
                    }

            return {
                "budget_id": budget_id,
                "tracked": False,
                "error": "budget_not_found",
            }

        except Exception as e:
            logger.error(
                f"Harcama takip "
                f"hatasi: {e}"
            )
            return {
                "budget_id": budget_id,
                "tracked": False,
                "error": str(e),
            }

    def check_alerts(
        self,
        budget_id: str,
    ) -> dict[str, Any]:
        """Bütçe uyarılarını kontrol eder.

        Args:
            budget_id: Bütçe ID.

        Returns:
            Uyarı bilgisi.
        """
        try:
            for b in self._budgets:
                if b["budget_id"] == (
                    budget_id
                ):
                    alerts: list[str] = []
                    pct = (
                        b["spent"]
                        / max(
                            b["total_limit"],
                            1,
                        )
                    ) * 100

                    if pct >= 100:
                        alerts.append(
                            "budget_exceeded"
                        )
                    elif pct >= 80:
                        alerts.append(
                            "approaching_limit"
                        )

                    for cat, info in b[
                        "categories"
                    ].items():
                        cat_pct = (
                            info["spent"]
                            / max(
                                info["limit"],
                                1,
                            )
                        ) * 100
                        if cat_pct >= 100:
                            alerts.append(
                                f"{cat}_exceeded"
                            )

                    if not alerts:
                        status = "on_track"
                    elif (
                        "budget_exceeded"
                        in alerts
                    ):
                        status = "over_budget"
                    else:
                        status = "warning"

                    return {
                        "budget_id": (
                            budget_id
                        ),
                        "alerts": alerts,
                        "alert_count": len(
                            alerts
                        ),
                        "status": status,
                        "checked": True,
                    }

            return {
                "budget_id": budget_id,
                "alerts": [],
                "checked": False,
                "error": "budget_not_found",
            }

        except Exception as e:
            logger.error(
                f"Uyari kontrol "
                f"hatasi: {e}"
            )
            return {
                "budget_id": budget_id,
                "alerts": [],
                "checked": False,
                "error": str(e),
            }

    def adjust_budget(
        self,
        budget_id: str,
        new_limit: float = 0.0,
    ) -> dict[str, Any]:
        """Bütçe limitini ayarlar.

        Args:
            budget_id: Bütçe ID.
            new_limit: Yeni limit.

        Returns:
            Ayarlama sonucu.
        """
        try:
            for b in self._budgets:
                if b["budget_id"] == (
                    budget_id
                ):
                    old = b["total_limit"]
                    b["total_limit"] = (
                        new_limit
                    )
                    change = round(
                        new_limit - old, 2
                    )

                    return {
                        "budget_id": (
                            budget_id
                        ),
                        "old_limit": old,
                        "new_limit": new_limit,
                        "change": change,
                        "adjusted": True,
                    }

            return {
                "budget_id": budget_id,
                "adjusted": False,
                "error": "budget_not_found",
            }

        except Exception as e:
            logger.error(
                f"Butce ayarlama "
                f"hatasi: {e}"
            )
            return {
                "budget_id": budget_id,
                "adjusted": False,
                "error": str(e),
            }
