"""
Token basina maliyet takipcisi modulu.

Token sayma, maliyet hesaplama,
butce takibi, saglayici karsilastirma,
maliyet optimizasyonu.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CostPerTokenTracker:
    """Token basina maliyet takipcisi.

    Attributes:
        _usage_records: Kullanim kayitlari.
        _budgets: Butce kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._usage_records: list[
            dict
        ] = []
        self._budgets: dict[
            str, dict
        ] = {}
        self._stats: dict[str, Any] = {
            "total_tokens": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "records_count": 0,
        }
        logger.info(
            "CostPerTokenTracker "
            "baslatildi"
        )

    @property
    def total_cost(self) -> float:
        """Toplam maliyet."""
        return self._stats["total_cost"]

    def record_usage(
        self,
        model_id: str = "",
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        input_cost_per_1k: float = 0.0,
        output_cost_per_1k: float = 0.0,
        task_id: str = "",
    ) -> dict[str, Any]:
        """Kullanim kaydeder.

        Args:
            model_id: Model ID.
            provider: Saglayici.
            input_tokens: Girdi token.
            output_tokens: Cikti token.
            input_cost_per_1k: Girdi maliyet.
            output_cost_per_1k: Cikti malyiet.
            task_id: Gorev ID.

        Returns:
            Kayit bilgisi.
        """
        try:
            rid = f"ur_{uuid4()!s:.8}"

            in_cost = (
                input_tokens
                * input_cost_per_1k
                / 1000
            )
            out_cost = (
                output_tokens
                * output_cost_per_1k
                / 1000
            )
            total = round(
                in_cost + out_cost, 6
            )
            total_tokens = (
                input_tokens + output_tokens
            )

            record = {
                "record_id": rid,
                "model_id": model_id,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": (
                    output_tokens
                ),
                "total_tokens": total_tokens,
                "input_cost": round(
                    in_cost, 6
                ),
                "output_cost": round(
                    out_cost, 6
                ),
                "total_cost": total,
                "task_id": task_id,
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._usage_records.append(
                record
            )

            self._stats[
                "total_tokens"
            ] += total_tokens
            self._stats[
                "total_input_tokens"
            ] += input_tokens
            self._stats[
                "total_output_tokens"
            ] += output_tokens
            self._stats[
                "total_cost"
            ] += total
            self._stats[
                "total_cost"
            ] = round(
                self._stats["total_cost"], 6
            )
            self._stats[
                "records_count"
            ] += 1

            # Butce kontrolu
            self._check_budgets(
                provider, total
            )

            return {
                "record_id": rid,
                "total_tokens": total_tokens,
                "total_cost": total,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def set_budget(
        self,
        name: str = "",
        provider: str = "",
        daily_limit: float = 0.0,
        monthly_limit: float = 0.0,
    ) -> dict[str, Any]:
        """Butce ayarlar.

        Args:
            name: Butce adi.
            provider: Saglayici.
            daily_limit: Gunluk limit.
            monthly_limit: Aylik limit.

        Returns:
            Butce bilgisi.
        """
        try:
            self._budgets[name] = {
                "name": name,
                "provider": provider,
                "daily_limit": daily_limit,
                "monthly_limit": (
                    monthly_limit
                ),
                "daily_spent": 0.0,
                "monthly_spent": 0.0,
                "alerts": [],
            }

            return {
                "name": name,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def _check_budgets(
        self,
        provider: str,
        cost: float,
    ) -> None:
        """Butce kontrol eder."""
        for b in self._budgets.values():
            if (
                b["provider"]
                and b["provider"] != provider
            ):
                continue

            b["daily_spent"] += cost
            b["monthly_spent"] += cost

            if (
                b["daily_limit"] > 0
                and b["daily_spent"]
                >= b["daily_limit"]
            ):
                b["alerts"].append({
                    "type": "daily_exceeded",
                    "at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                })

            if (
                b["monthly_limit"] > 0
                and b["monthly_spent"]
                >= b["monthly_limit"]
            ):
                b["alerts"].append({
                    "type": (
                        "monthly_exceeded"
                    ),
                    "at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                })

    def get_cost_by_model(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Model bazli maliyet getirir.

        Args:
            model_id: Model ID.

        Returns:
            Maliyet bilgisi.
        """
        try:
            records = [
                r
                for r in self._usage_records
                if r["model_id"] == model_id
            ]
            total = sum(
                r["total_cost"]
                for r in records
            )
            tokens = sum(
                r["total_tokens"]
                for r in records
            )

            return {
                "model_id": model_id,
                "total_cost": round(
                    total, 6
                ),
                "total_tokens": tokens,
                "usage_count": len(records),
                "avg_cost": (
                    round(
                        total / len(records),
                        6,
                    )
                    if records
                    else 0
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_cost_by_provider(
        self,
        provider: str = "",
    ) -> dict[str, Any]:
        """Saglayici bazli maliyet.

        Args:
            provider: Saglayici.

        Returns:
            Maliyet bilgisi.
        """
        try:
            records = [
                r
                for r in self._usage_records
                if r["provider"] == provider
            ]
            total = sum(
                r["total_cost"]
                for r in records
            )
            tokens = sum(
                r["total_tokens"]
                for r in records
            )

            return {
                "provider": provider,
                "total_cost": round(
                    total, 6
                ),
                "total_tokens": tokens,
                "usage_count": len(records),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def compare_providers(
        self,
    ) -> dict[str, Any]:
        """Saglayicilari karsilastirir."""
        try:
            by_prov: dict[
                str, dict
            ] = {}
            for r in self._usage_records:
                p = r["provider"]
                if p not in by_prov:
                    by_prov[p] = {
                        "cost": 0.0,
                        "tokens": 0,
                        "count": 0,
                    }
                by_prov[p]["cost"] += (
                    r["total_cost"]
                )
                by_prov[p]["tokens"] += (
                    r["total_tokens"]
                )
                by_prov[p]["count"] += 1

            comparison = []
            for p, data in (
                by_prov.items()
            ):
                cpt = (
                    round(
                        data["cost"]
                        / data["tokens"]
                        * 1000,
                        6,
                    )
                    if data["tokens"] > 0
                    else 0
                )
                comparison.append({
                    "provider": p,
                    "total_cost": round(
                        data["cost"], 6
                    ),
                    "total_tokens": (
                        data["tokens"]
                    ),
                    "cost_per_1k_tokens": cpt,
                    "usage_count": (
                        data["count"]
                    ),
                })

            comparison.sort(
                key=lambda x: x[
                    "cost_per_1k_tokens"
                ]
            )

            return {
                "comparison": comparison,
                "cheapest": (
                    comparison[0]["provider"]
                    if comparison
                    else None
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_budget_status(
        self,
        name: str = "",
    ) -> dict[str, Any]:
        """Butce durumu getirir.

        Args:
            name: Butce adi.

        Returns:
            Butce durumu.
        """
        try:
            b = self._budgets.get(name)
            if not b:
                return {
                    "retrieved": False,
                    "error": (
                        "Butce bulunamadi"
                    ),
                }

            return {
                **b,
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
                "total_records": len(
                    self._usage_records
                ),
                "total_budgets": len(
                    self._budgets
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
